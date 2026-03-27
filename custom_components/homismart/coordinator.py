"""Data Coordinator for the HomiSmart integration."""
import logging

from homismart_client import HomismartClient
from homismart_client.devices import CurtainDevice, HomismartDevice, SwitchableDevice
from homismart_client.enums import DeviceType

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    SIGNAL_NEW_COVER,
    SIGNAL_NEW_LIGHT,
    SIGNAL_NEW_SWITCH,
    SIGNAL_UPDATE_DEVICE,
)

_LOGGER = logging.getLogger(__name__)


class HomiSmartCoordinator:
    """Manages a single HomiSmart connection and dispatches data to entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.client = HomismartClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            loop=hass.loop,
        )
        self.device_registry: dict[str, HomismartDevice] = {}

    @callback
    def _handle_new_device(self, device: HomismartDevice) -> None:
        """Handle a new device discovered by the client and dispatch it."""
        try:
            _LOGGER.info("Discovered new HomiSmart device: %s", device)
            self.device_registry[device.id] = device

            device_type = device.device_type_enum

            if device_type is None:
                # Fall back to instance checks when type is unknown.
                if isinstance(device, SwitchableDevice):
                    async_dispatcher_send(self.hass, SIGNAL_NEW_LIGHT, device)
                elif isinstance(device, CurtainDevice):
                    async_dispatcher_send(self.hass, SIGNAL_NEW_COVER, device)
                return

            # Vendor naming: "SWITCH" (type 2) = wall light switches -> HA lights
            #                "SOCKET" (type 1) = power outlets -> HA switches
            if device_type in (
                DeviceType.SOCKET,
                DeviceType.DOUBLE_SWITCH_OR_SOCKET,
                DeviceType.SOCKET_ALT,
                DeviceType.SWITCH_MULTI_GANG_A,
            ):
                async_dispatcher_send(self.hass, SIGNAL_NEW_SWITCH, device)
            elif device_type == DeviceType.SWITCH:
                async_dispatcher_send(self.hass, SIGNAL_NEW_LIGHT, device)
            elif device_type in (DeviceType.CURTAIN, DeviceType.SHUTTER):
                async_dispatcher_send(self.hass, SIGNAL_NEW_COVER, device)
            # Add other device types (e.g., locks) here in the future.
        except Exception:
            _LOGGER.exception(
                "Error handling new device: %s",
                getattr(device, "id", "unknown"),
            )

    @callback
    def _handle_device_update(self, device: HomismartDevice) -> None:
        """Handle a device state update and dispatch the signal."""
        _LOGGER.debug("Device state updated: %s", device.raw)
        self.device_registry[device.id] = device
        # Dispatch an update signal specific to this device's ID.
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE_DEVICE}_{device.id}")

    @callback
    def _handle_hub_update(self, hub: HomismartDevice) -> None:
        """Handle a hub discovery or update and register it in HA's device registry."""
        _LOGGER.info("Hub update: %s (online=%s)", hub.name, hub.is_online)
        self.device_registry[hub.id] = hub
        # Register the hub in HA's device registry so child entities can
        # reference it via via_device.
        dev_reg = dr.async_get(self.hass)
        dev_reg.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, hub.id)},
            name=hub.name,
            manufacturer="HomiSmart",
            model="Hub",
        )
        # Notify all entities so they can re-evaluate availability.
        for device_id in self.device_registry:
            async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE_DEVICE}_{device_id}")

    async def connect(self) -> None:
        """Connect to the HomiSmart WebSocket and start listening for events."""
        _LOGGER.info("Starting HomiSmart client connection.")
        # Register event listeners before connecting.
        self.client.session.register_event_listener(
            "new_device_added", self._handle_new_device
        )
        self.client.session.register_event_listener(
            "device_updated", self._handle_device_update
        )
        self.client.session.register_event_listener(
            "new_hub_added", self._handle_hub_update
        )
        self.client.session.register_event_listener(
            "hub_updated", self._handle_hub_update
        )

        # connect() returns after successful login. The library manages
        # the receive loop, heartbeat, and reconnection internally.
        await self.client.connect(timeout=30)

    async def disconnect(self) -> None:
        """Disconnect the HomiSmart client and clean up."""
        _LOGGER.info("Disconnecting HomiSmart client.")
        await self.client.disconnect()
