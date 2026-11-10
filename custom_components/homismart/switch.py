"""Switch platform for the HomiSmart integration: sockets and relays."""
from __future__ import annotations

from typing import Any

from homismart_client.devices import SwitchableDevice
from homismart_client.enums import DeviceType

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HomiSmartConfigEntry, HomiSmartCoordinator
from .entity import HomiSmartEntity, async_setup_platform

OUTLET_TYPES = {DeviceType.SOCKET, DeviceType.SOCKET_ALT}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomiSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HomiSmart switches."""
    async_setup_platform(hass, entry, async_add_entities, Platform.SWITCH, HomiSmartSwitch)


class HomiSmartSwitch(HomiSmartEntity[SwitchableDevice], SwitchEntity):
    """A HomiSmart socket, relay or gang of a multi-gang switch."""

    def __init__(self, coordinator: HomiSmartCoordinator, device: SwitchableDevice) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device)
        self._attr_device_class = (
            SwitchDeviceClass.OUTLET
            if device.device_type_enum in OUTLET_TYPES
            else SwitchDeviceClass.SWITCH
        )

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.device.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.device.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.device.turn_off()
