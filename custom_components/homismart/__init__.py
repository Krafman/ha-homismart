"""The HomiSmart integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import HomiSmartCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomiSmart from a config entry."""
    coordinator = HomiSmartCoordinator(hass, entry)

    try:
        await coordinator.connect()
    except Exception as exc:
        raise ConfigEntryNotReady(
            f"Failed to connect to HomiSmart: {exc}"
        ) from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HomiSmart config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: HomiSmartCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.disconnect()

    return unload_ok
