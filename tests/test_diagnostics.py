"""Diagnostics download and the files the integration ships."""
from __future__ import annotations

import json
from pathlib import Path

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.homismart.diagnostics import async_get_config_entry_diagnostics

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "homismart"


async def test_diagnostics_redact_credentials(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Diagnostics include device data but never the account credentials."""
    data = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert data["entry"] == {CONF_USERNAME: "**REDACTED**", CONF_PASSWORD: "**REDACTED**"}
    assert data["connection"] == {"connected": True, "logged_in": True}
    assert {d["raw"]["id"] for d in data["devices"]} >= {"04518788000212"}
    assert "correct-password" not in json.dumps(data, default=str)


def test_translations_match_strings() -> None:
    """translations/en.json is a copy of strings.json and covers every step."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))
    assert english == strings
    assert {"user", "reauth_confirm"} <= strings["config"]["step"].keys()
    assert {"invalid_auth", "cannot_connect", "unknown"} <= strings["config"]["error"].keys()


def test_brand_images() -> None:
    """Brand images are PNGs at the sizes Home Assistant expects."""
    sizes = {"icon.png": 256, "icon@2x.png": 512, "logo.png": 256, "logo@2x.png": 512}
    for name, size in sizes.items():
        header = (INTEGRATION / "brand" / name).read_bytes()[:24]
        assert header[:8] == b"\x89PNG\r\n\x1a\n", name
        width, height = int.from_bytes(header[16:20]), int.from_bytes(header[20:24])
        assert (width, height) == (size, size), name
