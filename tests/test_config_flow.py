"""The setup and re-authentication forms."""
from __future__ import annotations

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homismart.const import DOMAIN

from .conftest import PASSWORD, USERNAME, FakeServer


async def _submit_user_form(hass: HomeAssistant, password: str):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: password}
    )


async def test_user_flow_creates_entry(hass: HomeAssistant, server: FakeServer) -> None:
    """Valid credentials create an entry named after the account."""
    result = await _submit_user_form(hass, PASSWORD)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"] == {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    assert result["result"].unique_id == USERNAME


async def test_user_flow_wrong_password(hass: HomeAssistant, server: FakeServer) -> None:
    """A rejected password shows 'invalid_auth', and the user can retry."""
    result = await _submit_user_form(hass, "wrong")
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect(hass: HomeAssistant, server: FakeServer) -> None:
    """An unreachable cloud shows 'cannot_connect'."""
    server.reachable = False
    result = await _submit_user_form(hass, PASSWORD)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_account_already_configured(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """The same account can't be added twice."""
    result = await _submit_user_form(hass, PASSWORD)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_updates_password(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """Re-authentication checks the new password and stores it."""
    server.password_hash = __import__("hashlib").md5(b"new-password").hexdigest()
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["username"] == USERNAME

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: PASSWORD}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-password"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-password"
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(config_entry.entry_id)
