"""Config flow for the HomiSmart integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol
from homismart_client import AuthenticationError, HomismartClient

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


async def async_validate_login(username: str, password: str) -> dict[str, str]:
    """Try to log in; return form errors, or an empty dict if it worked."""
    try:
        client = HomismartClient(username=username, password=password)
    except Exception:
        _LOGGER.exception("Unexpected error creating the HomiSmart client")
        return {"base": "unknown"}
    try:
        await client.connect(timeout=30)
    except AuthenticationError:
        return {"base": "invalid_auth"}
    except Exception as err:  # Timeouts, DNS, TLS, WebSocket errors.
        _LOGGER.debug("Could not connect to HomiSmart: %s", err)
        return {"base": "cannot_connect"}
    finally:
        await client.disconnect()
    return {}


class HomiSmartConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomiSmart."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the HomiSmart account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # One entry per HomiSmart account.
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()
            errors = await async_validate_login(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Started by Home Assistant when the stored password stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        username = entry.data[CONF_USERNAME]
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await async_validate_login(username, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"username": username},
        )
