"""Base entity for the HomiSmart integration."""
from __future__ import annotations

from homismart_client.devices import HomismartDevice

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .coordinator import SIGNAL_UPDATE_DEVICE, HomiSmartCoordinator


class HomiSmartEntity(Entity):
    """Base representation of a HomiSmart device entity."""

    # This entity is push-based, so we should not poll it for updates.
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HomiSmartCoordinator, device: HomismartDevice
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.device = device
        self._attr_unique_id = self.device.id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the device registry."""
        # Use the hub/parent ID to group related entities under one device.
        via_device = (DOMAIN, self.device.pid) if self.device.pid else None

        # Nicely format the device type name from the enum.
        device_type_name = "Unknown"
        if self.device.device_type_enum:
            device_type_name = self.device.device_type_enum.name.replace("_", " ").title()

        return DeviceInfo(
            identifiers={(DOMAIN, self.device.id)},
            name=self.device.name,
            manufacturer="HomiSmart",
            model=f"{device_type_name} ({self.device.device_type_code})",
            sw_version=str(self.device.version) if self.device.version is not None else None,
            via_device=via_device,
        )

    @property
    def available(self) -> bool:
        """Return True if the device is online and available."""
        return self.device.is_online

    async def async_added_to_hass(self) -> None:
        """Register a callback for when the entity is added to hass."""
        await super().async_added_to_hass()
        # Register a listener for updates specific to this entity's ID.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_UPDATE_DEVICE}_{self.device.id}", self._update_callback
            )
        )

    @callback
    def _update_callback(self) -> None:
        """Handle received data from the dispatcher and update the entity's state."""
        self.async_write_ha_state()
