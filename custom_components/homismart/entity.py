"""Base entity and platform setup shared by the HomiSmart platforms."""
from __future__ import annotations

from collections.abc import Callable

from homismart_client.devices import HomismartDevice

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SIGNAL_NEW_DEVICE, SIGNAL_UPDATE_DEVICE
from .coordinator import HomiSmartConfigEntry, HomiSmartCoordinator


class HomiSmartEntity[DeviceT: HomismartDevice](Entity):
    """An entity for one HomiSmart device. Push-updated, never polled."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None  # The entity is the device's main feature.

    def __init__(self, coordinator: HomiSmartCoordinator, device: DeviceT) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = device.id

    @property
    def device_info(self) -> DeviceInfo | ChildDeviceInfo:
        """Return this device's info; its hub and unit are registered first."""
        return self.coordinator.device_info(self.device)

    @property
    def available(self) -> bool:
        """Return True if HomiSmart is reachable and the device is online."""
        return self.coordinator.connected and self.device.is_online

    async def async_added_to_hass(self) -> None:
        """Write state whenever the client reports a change for this device."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_DEVICE.format(self.device.id),
                self.async_write_ha_state,
            )
        )

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Nothing to re-key: updates are keyed on the HomiSmart device ID."""
        super().async_entity_id_changed(old_entity_id)


@callback
def async_setup_platform(
    hass: HomeAssistant,
    entry: HomiSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    platform: Platform,
    entity_factory: Callable[[HomiSmartCoordinator, HomismartDevice], HomiSmartEntity],
) -> None:
    """Add entities for known devices of a platform, and for ones found later."""
    coordinator = entry.runtime_data

    @callback
    def add(device: HomismartDevice) -> None:
        async_add_entities([entity_factory(coordinator, device)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_DEVICE.format(platform), add)
    )
    for device in coordinator.devices_for(platform):
        add(device)
