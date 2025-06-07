"""Config flow for HomiSmart integration."""
import asyncio
import logging
from typing import Any

import voluptuous as vol
from homismart_client import AuthenticationError, HomismartClient

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema for the user configuration step.
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect and authenticate.

    Raises:
        AuthenticationError: If credentials are invalid.
        ConnectionError: If the client cannot connect to the server.
    """
    client = HomismartClient(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )

    connect_task = None
    login_event = asyncio.Event()
    login_successful = {"ok": False}

    # Define proper callbacks
    def on_auth(username: str):
        _LOGGER.info("Validation successful for user: %s", username)
        login_successful["ok"] = True
        login_event.set()

    def on_error(error_details: dict):
        _LOGGER.warning("Validation error: %s", error_details)
        login_successful["ok"] = False
        login_event.set()

    # Register working callbacks
    client.session.register_event_listener("session_authenticated", on_auth)
    client.session.register_event_listener("session_error", on_error)

    try:
        connect_task = asyncio.create_task(client.connect())
        await asyncio.wait_for(login_event.wait(), timeout=30.0)

        if not login_successful["ok"]:
            raise AuthenticationError("Invalid credentials or server rejected login")

    except asyncio.TimeoutError as exc:
        _LOGGER.error("Timeout during credential validation.")
        raise ConnectionError("Timeout validating credentials") from exc

    finally:
        if connect_task and not connect_task.done():
            connect_task.cancel()
        if client:
            await client.disconnect()


class HomiSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomiSmart."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Set a unique ID to prevent multiple configurations for the same user.
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            try:
                await validate_input(self.hass, user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except-in-config-flow
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
            else:
                # If validation is successful, create the config entry.
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        # Show the form to the user.
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
