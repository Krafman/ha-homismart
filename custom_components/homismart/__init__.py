"""The HomiSmart integration."""
from __future__ import annotations

from homismart_client import AuthenticationError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import HomiSmartConfigEntry, HomiSmartCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: HomiSmartConfigEntry) -> None:
    """Connect to HomiSmart and set up the platforms."""
    coordinator = HomiSmartCoordinator(hass, entry)
    try:
        await coordinator.async_connect()
    except AuthenticationError as err:
        await coordinator.async_disconnect()
        raise ConfigEntryAuthFailed(str(err)) from err  # Prompts re-authentication.
    except Exception as err:
        await coordinator.async_disconnect()
        raise ConfigEntryNotReady(f"Failed to connect to HomiSmart: {err}") from err

    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_disconnect)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: HomiSmartConfigEntry) -> None:
    """Unload the platforms; the connection closes via async_on_unload."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
