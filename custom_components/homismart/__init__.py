"""The HomiSmart integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import HomiSmartCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomiSmart from a config entry."""
    # Create the coordinator instance.
    coordinator = HomiSmartCoordinator(hass, entry)

    # Start the connection process.
    await coordinator.connect()

    # Store the coordinator in hass.data for platforms to access.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward the setup to the relevant platforms (light, cover).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HomiSmart config entry."""
    # Unload the platforms.
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Pop the coordinator from hass.data.
        coordinator: HomiSmartCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Disconnect the client.
        await coordinator.disconnect()

    return unload_ok
