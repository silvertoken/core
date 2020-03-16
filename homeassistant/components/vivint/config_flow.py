"""Config flow for Vivint integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pyvivintsky.vivint_sky import VivintSky

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
DATA_SCHEMA = vol.Schema({"host": str, "username": str, "password": str})


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host):
        """Initialize."""
        self.host = host

    async def authenticate(self, username, password) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = PlaceholderHub(data["host"])

    if not await hub.authenticate(data["username"], data["password"]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "Name of the device"}


class VivintConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vivint."""

    VERSION = 1

    # Vivint Sky API uses PubNub and channel subscriptions to push events
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Optional(CONF_USERNAME): str, vol.Optional(CONF_PASSWORD): str}
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return await self._show_setup_form(user_input)

        errors = {}
        vivint = VivintSky(user_input.get(CONF_USERNAME), user_input.get(CONF_PASSWORD))
        try:
            vivint.connect()
        except:
            errors["base"] = "connection_error"
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title="Vivint",
            data={
                CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                CONF_USERNAME: user_input.get(CONF_USERNAME),
            },
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
