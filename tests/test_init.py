"""Setup, unload, connection handling and re-authentication."""
from __future__ import annotations

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import FakeServer, wait_for


async def test_setup_and_unload(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """The entry loads, creates entities, and unloads cleanly."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("switch.mamad_socket").state == STATE_ON

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert server.current.closed


async def test_server_unreachable_retries(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """No connection at startup: Home Assistant retries later."""
    server.reachable = False
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_rejected_password_at_startup_starts_reauth(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """A rejected password fails fast and asks the user to re-authenticate."""
    server.password_hash = "changed"
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler("homismart")
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_connection_loss_and_recovery(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """Entities go unavailable while the cloud is gone and come back after."""
    server.reachable = False
    await server.drop()
    await wait_for(lambda: hass.states.get("switch.mamad_socket").state == STATE_UNAVAILABLE)

    server.reachable = True
    await wait_for(lambda: hass.states.get("switch.mamad_socket").state == STATE_ON, timeout=5)


async def test_password_changed_while_running_starts_reauth(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """If the password stops working on reconnect, the user is asked for it."""
    server.password_hash = "changed"
    await server.drop()
    await wait_for(lambda: hass.config_entries.flow.async_progress_by_handler("homismart"))
    flow = hass.config_entries.flow.async_progress_by_handler("homismart")[0]
    assert flow["context"]["source"] == SOURCE_REAUTH
