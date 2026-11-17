"""The HomiSmart integration."""
from __future__ import annotations

from homismart_client import AuthenticationError, HomismartError
from websockets.exceptions import WebSocketException

from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .config_flow import account_unique_id
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
    except (TimeoutError, OSError, WebSocketException, HomismartError) as err:
        await coordinator.async_disconnect()
        raise ConfigEntryNotReady(f"Failed to connect to HomiSmart: {err}") from err

    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_disconnect)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: HomiSmartConfigEntry) -> None:
    """Migrate older config entries.

    1.1 -> 1.2: the unique ID becomes the normalized (lower-case) account
    email, so the same account can't be added twice with different casing.
    """
    if entry.version == 1 and entry.minor_version < 2:
        hass.config_entries.async_update_entry(
            entry,
            unique_id=account_unique_id(entry.data[CONF_USERNAME]),
            minor_version=2,
        )


async def async_unload_entry(hass: HomeAssistant, entry: HomiSmartConfigEntry) -> None:
    """Unload the platforms; the connection closes via async_on_unload."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
