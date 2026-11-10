"""Diagnostics for the HomiSmart integration (Settings > device > Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import HomiSmartConfigEntry, platform_for

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HomiSmartConfigEntry
) -> dict[str, Any]:
    """Return the connection state and the raw data of every device."""
    coordinator = entry.runtime_data
    client = coordinator.client
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "connection": {"connected": client.is_connected, "logged_in": client.is_logged_in},
        "hubs": [hub.raw for hub in client.session.get_all_hubs()],
        "devices": [
            {"platform": platform_for(device), "raw": device.raw}
            for device in client.session.get_all_devices()
        ],
    }
