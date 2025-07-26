"""Cover platform for the HomiSmart integration."""
from __future__ import annotations

import logging
from typing import Any

from homismart_client.devices import CurtainDevice
from homismart_client.enums import DeviceType

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
    CoverDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomiSmartCoordinator, SIGNAL_NEW_COVER
from .entity import HomiSmartEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomiSmart cover platform."""
    coordinator: HomiSmartCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Callback to add a new cover entity.
    @callback
    def async_add_cover(device: CurtainDevice) -> None:
        """Add a new HomiSmart cover entity."""
        _LOGGER.info("Adding new cover: %s", device.name)
        async_add_entities([HomiSmartCover(coordinator, device)])

    # Register a listener for new cover devices.
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_COVER, async_add_cover)
    )

    # Add any covers that are already known by the coordinator.
    for device in coordinator.device_registry.values():
        if isinstance(device, CurtainDevice):
            async_add_cover(device)


class HomiSmartCover(HomiSmartEntity, CoverEntity):
    """Representation of a HomiSmart curtain/blind device as a cover."""

    # Set entity name to None, so Home Assistant will use the device name.
    _attr_name = None
    # Define the supported features for this cover entity.
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )

    def __init__(
        self, coordinator: HomiSmartCoordinator, device: CurtainDevice
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator, device)
        # Type hint the device for this specific platform.
        self.device: CurtainDevice = device
        if device.device_type_enum == DeviceType.SHUTTER:
            self._attr_device_class = CoverDeviceClass.SHUTTER

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the cover (0-100)."""
        return self.device.current_level

    @property
    def is_closed(self) -> bool | None:
        """Return true if the cover is closed, None if position is unknown."""
        if self.device.current_level is None:
            return None
        return self.device.current_level == 100

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.device.open_fully()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self.device.close_fully()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        await self.device.set_level(position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover's movement."""
        await self.device.stop()
