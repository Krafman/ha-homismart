"""Switch platform for the HomiSmart integration."""
from __future__ import annotations

import logging

from homismart_client.devices import SwitchableDevice
from homismart_client.enums import DeviceType

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_SWITCH
from .coordinator import HomiSmartCoordinator
from .entity import HomiSmartEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomiSmart switch platform."""
    coordinator: HomiSmartCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_add_switch(device: SwitchableDevice) -> None:
        """Add a new HomiSmart switch entity."""
        _LOGGER.info("Adding new switch: %s", device.name)
        async_add_entities([HomiSmartSwitch(coordinator, device)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_SWITCH, async_add_switch)
    )

    for device in coordinator.device_registry.values():
        if isinstance(device, SwitchableDevice):
            dt = device.device_type_enum
            if dt in (
                DeviceType.SOCKET,
                DeviceType.SOCKET_ALT,
                DeviceType.DOUBLE_SWITCH_OR_SOCKET,
                DeviceType.SWITCH_MULTI_GANG_A,
            ):
                # Only add outlet/switch types. Lights are handled separately.
                async_add_switch(device)


class HomiSmartSwitch(HomiSmartEntity, SwitchEntity):
    """Representation of a HomiSmart switchable device as a switch."""

    _attr_name = None

    def __init__(self, coordinator: HomiSmartCoordinator, device: SwitchableDevice) -> None:
        super().__init__(coordinator, device)
        self.device: SwitchableDevice = device

        if device.device_type_enum == DeviceType.SWITCH_MULTI_GANG_A:
            self._attr_device_class = SwitchDeviceClass.SWITCH
        else:
            self._attr_device_class = SwitchDeviceClass.OUTLET

    @property
    def is_on(self) -> bool:
        return self.device.is_on

    async def async_turn_on(self, **kwargs) -> None:
        await self.device.turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        await self.device.turn_off()

    async def async_toggle(self, **kwargs) -> None:
        await self.device.toggle()
