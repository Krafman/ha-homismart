"""Controlling covers, lights and switches."""
from __future__ import annotations

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.cover import ATTR_CURRENT_POSITION, ATTR_POSITION, CoverState
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .conftest import FakeServer, wait_for


async def _call(hass: HomeAssistant, domain: str, service: str, entity_id: str, **data) -> None:
    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


async def test_cover_uses_home_assistant_direction(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """HomiSmart 100 (closed) is position 0 in Home Assistant, and back."""
    state = hass.states.get("cover.study_blinds")
    assert state.state == CoverState.CLOSED
    assert state.attributes[ATTR_CURRENT_POSITION] == 0

    await _call(hass, "cover", "set_cover_position", "cover.study_blinds", **{ATTR_POSITION: 25})
    assert server.commands()[-1]["curtainState"] == 75
    await wait_for(
        lambda: hass.states.get("cover.study_blinds").attributes[ATTR_CURRENT_POSITION] == 25
    )
    assert hass.states.get("cover.study_blinds").state == CoverState.OPEN

    await _call(hass, "cover", "open_cover", "cover.study_blinds")
    await _call(hass, "cover", "close_cover", "cover.study_blinds")
    await _call(hass, "cover", "stop_cover", "cover.study_blinds")
    assert [c["curtainState"] for c in server.commands()[-3:]] == [0, 100, 99]


async def test_light_on_off(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """Wall switches act as on/off lights, with state pushed back by the cloud."""
    await _call(hass, "light", "turn_on", "light.hall_light")
    assert server.commands()[-1] == server.commands()[-1] | {"id": "02000000000001", "power": True}
    await wait_for(lambda: hass.states.get("light.hall_light").state == STATE_ON)
    assert hass.states.get("light.hall_light").attributes["supported_color_modes"] == ["onoff"]

    await _call(hass, "light", "turn_off", "light.hall_light")
    await wait_for(lambda: hass.states.get("light.hall_light").state == STATE_OFF)


async def test_gang_switches_independently(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """Each gang of a two-gang switch is its own switch."""
    await _call(hass, "switch", "turn_on", "switch.landing_2")
    assert server.commands()[-1]["id"] == "07000000000002-2"
    await wait_for(lambda: hass.states.get("switch.landing_2").state == STATE_ON)
    assert hass.states.get("switch.landing_1").state == STATE_ON


async def test_command_sent_even_if_state_already_matches(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """A stale cache must never swallow a command."""
    assert hass.states.get("switch.lounge_socket").state == STATE_ON
    await _call(hass, "switch", "turn_on", "switch.lounge_socket")
    assert server.commands()[-1]["power"] is True
