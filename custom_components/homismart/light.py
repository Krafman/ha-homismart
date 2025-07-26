"""Light platform for the HomiSmart integration."""
from __future__ import annotations

import logging

from homismart_client.devices import SwitchableDevice
from homismart_client.enums import DeviceType

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomiSmartCoordinator, SIGNAL_NEW_LIGHT
from .entity import HomiSmartEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomiSmart light platform."""
    coordinator: HomiSmartCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Callback to add a new light entity.
    @callback
    def async_add_light(device: SwitchableDevice) -> None:
        """Add a new HomiSmart light entity."""
        if device.device_type_enum == DeviceType.SWITCH:
            _LOGGER.info("Adding new light: %s", device.name)
            async_add_entities([HomiSmartLight(coordinator, device)])

    # Register a listener for new light devices.
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_LIGHT, async_add_light)
    )

    # Add any lights that are already known by the coordinator.
    for device in coordinator.device_registry.values():
        if isinstance(device, SwitchableDevice) and device.device_type_enum == DeviceType.SWITCH:
            async_add_light(device)


class HomiSmartLight(HomiSmartEntity, LightEntity):
    """Representation of a HomiSmart switchable device as a light."""

    # Set entity name to None, so Home Assistant will use the device name.
    _attr_name = None

    def __init__(
        self, coordinator: HomiSmartCoordinator, device: SwitchableDevice
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, device)
        # Type hint the device for this specific platform.
        self.device: SwitchableDevice = device

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self.device.is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        await self.device.turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self.device.turn_off()

    async def async_toggle(self, **kwargs) -> None:
        """Toggle the light state."""
        await self.device.toggle()
