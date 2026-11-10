"""Connection manager for the HomiSmart integration.

Owns the HomiSmart client, mirrors its devices into Home Assistant's device
registry, and forwards client events to entities through the dispatcher.
"""
from __future__ import annotations

import logging
from typing import Any

from homismart_client import HomismartClient
from homismart_client.devices import CurtainDevice, HomismartDevice, SwitchableDevice
from homismart_client.enums import DeviceType

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util.ssl import get_default_context

from .const import DOMAIN, MANUFACTURER, PLATFORMS, SIGNAL_NEW_DEVICE, SIGNAL_UPDATE_DEVICE

_LOGGER = logging.getLogger(__name__)

type HomiSmartConfigEntry = ConfigEntry[HomiSmartCoordinator]

# Vendor naming: a "SWITCH" (type 2) is a wall light switch, so it becomes a
# light; sockets and the other relays become switches.
PLATFORM_BY_TYPE: dict[DeviceType, Platform] = {
    DeviceType.SOCKET: Platform.SWITCH,
    DeviceType.SOCKET_ALT: Platform.SWITCH,
    DeviceType.WATER_HEATER_SWITCH: Platform.SWITCH,
    DeviceType.TWO_GANG_SWITCH: Platform.SWITCH,
    DeviceType.SWITCH: Platform.LIGHT,
    DeviceType.SHUTTER: Platform.COVER,
    DeviceType.CURTAIN: Platform.COVER,
}

MODEL_BY_TYPE: dict[DeviceType, str] = {
    DeviceType.SOCKET: "Socket",
    DeviceType.SOCKET_ALT: "Socket",
    DeviceType.WATER_HEATER_SWITCH: "Water heater switch",
    DeviceType.TWO_GANG_SWITCH: "Two-gang switch",
    DeviceType.SWITCH: "Light switch",
    DeviceType.SHUTTER: "Shutter",
    DeviceType.CURTAIN: "Curtain",
}


def platform_for(device: HomismartDevice) -> Platform | None:
    """Return the Home Assistant platform for a device, or None if unsupported."""
    if (device_type := device.device_type_enum) is not None:
        return PLATFORM_BY_TYPE.get(device_type)
    # Unknown type code: fall back to what the client could tell about it.
    if isinstance(device, CurtainDevice):
        return Platform.COVER
    if isinstance(device, SwitchableDevice):
        return Platform.SWITCH
    return None


def split_gang_names(gang_names: list[str]) -> tuple[str, list[str]]:
    """Split gang names into a name for the unit and a name for each gang.

    Home Assistant shows a child device as "<parent> <child>", so the shared
    leading words name the unit and the rest names each gang:
    ["Master bdr 1", "Master bdr 2"] -> ("Master bdr", ["1", "2"]).
    Gangs with nothing in common keep their names under a generic unit name.
    """
    word_lists = [name.split() for name in gang_names]
    common: list[str] = []
    for words in zip(*word_lists):
        if len({word.casefold() for word in words}) > 1:
            break
        common.append(words[0])
    rests = [" ".join(words[len(common):]) for words in word_lists]
    if len(gang_names) < 2 or not common or not all(rests):
        return MODEL_BY_TYPE[DeviceType.TWO_GANG_SWITCH], gang_names
    return " ".join(common), rests


class HomiSmartCoordinator:
    """Owns the HomiSmart connection and forwards its events to entities."""

    def __init__(self, hass: HomeAssistant, entry: HomiSmartConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.client = HomismartClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            ssl_context=get_default_context(),
        )
        self.devices: dict[str, HomismartDevice] = {}
        self._hubs: dict[str, HomismartDevice] = {}
        # Discovered devices not yet handed to their platform, see _announce_new_devices.
        self._unannounced: dict[str, Platform] = {}

    @property
    def connected(self) -> bool:
        """Return True while the HomiSmart connection is up."""
        return self.client.is_connected

    def devices_for(self, platform: Platform) -> list[HomismartDevice]:
        """Return the announced devices that belong to a platform."""
        return [
            device
            for device_id, device in self.devices.items()
            if device_id not in self._unannounced and platform_for(device) == platform
        ]

    async def async_connect(self) -> None:
        """Connect to HomiSmart. Raises AuthenticationError on bad credentials."""
        listeners = {
            "new_device_added": self._handle_new_device,
            "device_updated": self._handle_device_update,
            "device_deleted": self._handle_device_deleted,
            "new_hub_added": self._handle_hub_update,
            "hub_updated": self._handle_hub_update,
            "connection_lost": self._handle_connection_change,
            "connection_restored": self._handle_connection_change,
            "session_error": self._handle_session_error,
        }
        for event, handler in listeners.items():
            self.client.session.register_event_listener(event, handler)
        # Returns after login; the client then keeps the connection alive.
        await self.client.connect(timeout=30)

    async def async_disconnect(self) -> None:
        """Disconnect from HomiSmart."""
        await self.client.disconnect()

    # --- Client event handlers ------------------------------------------------

    @callback
    def _handle_new_device(self, device: HomismartDevice) -> None:
        """Track a newly discovered device; it is announced once the list is in."""
        if (platform := platform_for(device)) is None:
            _LOGGER.debug("No Home Assistant platform for %s", device)
            return
        self.devices[device.id] = device
        self._remove_stale_entities(device.id, keep=platform)
        if not self._unannounced:
            self.hass.loop.call_soon(self._announce_new_devices)
        self._unannounced[device.id] = platform

    @callback
    def _announce_new_devices(self) -> None:
        """Hand newly discovered devices to their platforms.

        The client reports a device list one device at a time, and entities
        are added eagerly. Waiting until the whole list is processed means a
        multi-gang unit is named from all of its gangs, not just the first.
        """
        unannounced, self._unannounced = self._unannounced, {}
        for device_id, platform in unannounced.items():
            if (device := self.devices.get(device_id)) is not None:
                async_dispatcher_send(self.hass, SIGNAL_NEW_DEVICE.format(platform), device)

    @callback
    def _handle_device_update(self, device: HomismartDevice) -> None:
        """Tell the device's entity that its state changed."""
        if device.id in self.devices:
            self.devices[device.id] = device
            async_dispatcher_send(self.hass, SIGNAL_UPDATE_DEVICE.format(device.id))

    @callback
    def _handle_device_deleted(self, device: HomismartDevice) -> None:
        """Remove a device that no longer exists on the HomiSmart account.

        Removing it from the device registry also removes its entities.
        """
        if self.devices.pop(device.id, None) is None:
            return
        dev_reg = dr.async_get(self.hass)
        identifier = (DOMAIN, device.id)
        entry_id = self.entry.entry_id
        if entry := (
            dev_reg.async_get_device_by_identifier(identifier, entry_id)
            or dev_reg.async_get_child_device_by_identifier(identifier, entry_id)
        ):
            dev_reg.async_remove_device(entry.id)
        # A multi-gang unit goes once its last gang is gone.
        if device.relay_number is not None and not self._gangs_of(device.unit_id):
            if unit := dev_reg.async_get_device_by_identifier(
                (DOMAIN, device.unit_id), entry_id
            ):
                dev_reg.async_remove_device(unit.id)

    @callback
    def _handle_hub_update(self, hub: HomismartDevice) -> None:
        """Keep the hub's device up to date; its state affects every device."""
        self._hubs[hub.id] = hub
        self._register_hub(hub.id)
        self._update_all_entities()

    @callback
    def _handle_connection_change(self) -> None:
        """Connection dropped or came back: entities re-check availability."""
        _LOGGER.info("HomiSmart connection %s", "restored" if self.connected else "lost")
        self._update_all_entities()

    @callback
    def _handle_session_error(self, error: dict[str, Any]) -> None:
        """Ask the user to re-authenticate when the stored password stops working."""
        if isinstance(error, dict) and error.get("type") == "authentication_failed":
            _LOGGER.warning("HomiSmart rejected the stored password; starting re-authentication")
            self.entry.async_start_reauth(self.hass)

    @callback
    def _update_all_entities(self) -> None:
        for device_id in list(self.devices):
            async_dispatcher_send(self.hass, SIGNAL_UPDATE_DEVICE.format(device_id))

    # --- Device registry ---------------------------------------------------------

    @callback
    def device_info(self, device: HomismartDevice) -> DeviceInfo | ChildDeviceInfo:
        """Return a device's device info, registering its hub and unit first.

        Each gang of a multi-gang switch becomes a child device of one device
        for the physical unit; a child must point at an existing parent, so
        parents are registered here. Entities call this when they are added,
        by which time the whole device list (and so every gang) is known.
        """
        hub_device_id = (
            self._register_hub(device.pid) if device.pid and device.pid != device.id else None
        )
        model = MODEL_BY_TYPE.get(device.device_type_enum, "Unknown")  # type: ignore[arg-type]
        model_id = str(device.device_type_code) if device.device_type_code is not None else None

        if device.relay_number is None:
            return DeviceInfo(
                identifiers={(DOMAIN, device.id)},
                name=device.name,
                manufacturer=MANUFACTURER,
                model=model,
                model_id=model_id,
                via_device_id=hub_device_id,
            )

        gangs = self._gangs_of(device.unit_id)
        unit_name, gang_names = split_gang_names([gang.name or gang.id for gang in gangs])
        unit = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, device.unit_id)},
            name=unit_name,
            manufacturer=MANUFACTURER,
            model=model,
            model_id=model_id,
            via_device_id=hub_device_id,
        )
        return ChildDeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=gang_names[[gang.id for gang in gangs].index(device.id)],
            parent_device_id=unit.id,
        )

    @callback
    def _register_hub(self, hub_id: str) -> str:
        """Register (or refresh) a hub in the device registry and return its id."""
        hub = self._hubs.get(hub_id)
        return (
            dr.async_get(self.hass)
            .async_get_or_create(
                config_entry_id=self.entry.entry_id,
                identifiers={(DOMAIN, hub_id)},
                # Until the hub's own data arrives, give it a sensible name.
                name=(hub.name if hub and hub.name else "HomiSmart hub"),
                manufacturer=MANUFACTURER,
                model="Hub",
                sw_version=str(hub.version) if hub and hub.version is not None else None,
            )
            .id
        )

    def _gangs_of(self, unit_id: str) -> list[HomismartDevice]:
        return sorted(
            (d for d in self.devices.values() if d.relay_number is not None and d.unit_id == unit_id),
            key=lambda d: d.relay_number or 0,
        )

    @callback
    def _remove_stale_entities(self, unique_id: str, keep: Platform) -> None:
        """Remove registry entries an older version left on another platform.

        Earlier versions created e.g. lights for shutters; those entries would
        otherwise linger forever next to the right entity.
        """
        ent_reg = er.async_get(self.hass)
        for platform in PLATFORMS:
            if platform != keep and (
                entity_id := ent_reg.async_get_entity_id(platform, DOMAIN, unique_id)
            ):
                _LOGGER.info("Removing stale entity %s", entity_id)
                ent_reg.async_remove(entity_id)
