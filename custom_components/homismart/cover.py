"""Cover platform for the HomiSmart integration: curtains and shutters."""
from __future__ import annotations

from typing import Any

from homismart_client.devices import CurtainDevice
from homismart_client.enums import DeviceType

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HomiSmartConfigEntry, HomiSmartCoordinator
from .entity import HomiSmartEntity, async_setup_platform


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomiSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HomiSmart covers."""
    async_setup_platform(hass, entry, async_add_entities, Platform.COVER, HomiSmartCover)


class HomiSmartCover(HomiSmartEntity[CurtainDevice], CoverEntity):
    """A HomiSmart curtain or shutter.

    Home Assistant positions run 0 = closed to 100 = open; HomiSmart counts the
    other way. The client's open_percentage / set_open_percentage convert, so
    this entity only deals in Home Assistant's convention.
    """

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )

    def __init__(self, coordinator: HomiSmartCoordinator, device: CurtainDevice) -> None:
        """Initialize the cover."""
        super().__init__(coordinator, device)
        self._attr_device_class = (
            CoverDeviceClass.SHUTTER
            if device.device_type_enum == DeviceType.SHUTTER
            else CoverDeviceClass.CURTAIN
        )

    @property
    def current_cover_position(self) -> int | None:
        """Return how far the cover is open (0 = closed, 100 = open)."""
        return self.device.open_percentage

    @property
    def is_closed(self) -> bool | None:
        """Return True if fully closed, None if the position is unknown."""
        position = self.device.open_percentage
        return None if position is None else position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.device.open_fully()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self.device.close_fully()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a position (0 = closed, 100 = open)."""
        await self.device.set_open_percentage(kwargs[ATTR_POSITION])

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.device.stop()
