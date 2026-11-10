"""Light platform for the HomiSmart integration: wall light switches."""
from __future__ import annotations

from typing import Any

from homismart_client.devices import SwitchableDevice

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HomiSmartConfigEntry
from .entity import HomiSmartEntity, async_setup_platform


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomiSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HomiSmart lights."""
    async_setup_platform(hass, entry, async_add_entities, Platform.LIGHT, HomiSmartLight)


class HomiSmartLight(HomiSmartEntity[SwitchableDevice], LightEntity):
    """A HomiSmart wall switch controlling a light (on/off only)."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        return self.device.is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.device.turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.device.turn_off()
