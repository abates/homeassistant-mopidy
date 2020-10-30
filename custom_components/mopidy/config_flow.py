from typing import Optional
from homeassistant.util import ssl
from homeassistant.core import callback
import logging
from ssl import SSLCertVerificationError
from tornado.httpclient import HTTPClientError

from tornado.simple_httpclient import HTTPTimeoutError
from homeassistant.const import CONF_API_VERSION, CONF_URL, CONF_NAME, CONF_VERIFY_SSL
import voluptuous as vol
from homeassistant import config_entries
from .const import (
    CONF_AUTO_SHUFFLE,
    CONF_SKIP_VERIFICATION,
    DEFAULT_AUTO_SHUFFLE,
    DEFAULT_NAME,
    DEFAULT_URL,
    DOMAIN,
)
from mopidy_client import Client

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Init object."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        settings_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AUTO_SHUFFLE,
                    default=self.config_entry.options.get(
                        CONF_AUTO_SHUFFLE, DEFAULT_AUTO_SHUFFLE
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=settings_schema)


class MopidyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mopidy media player config flo."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def _show_setup_form(self, user_input={}, errors={}):
        """Show the setup form to the user."""
        _LOGGER.debug("Errors: %s", errors)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)
                    ): str,
                    vol.Required(
                        CONF_URL,
                        default=user_input.get(CONF_URL, DEFAULT_URL),
                    ): str,
                    vol.Optional(
                        CONF_SKIP_VERIFICATION,
                        default=False,
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}
        if user_input is None:
            return await self._show_setup_form()

        # check for existing
        entries = self._async_current_entries()
        for entry in entries:
            if entry.data[CONF_URL] == user_input[CONF_URL]:
                errors[CONF_URL] = "server_exists"
                return await self._show_setup_form(user_input, errors)
            elif entry.unique_id == user_input[CONF_URL]:
                errors[CONF_NAME] = "name_exists"
                return await self._show_setup_form(user_input, errors)

        # attempt to connect
        validate_cert = not user_input[CONF_SKIP_VERIFICATION]
        try:
            context = None
            if validate_cert:
                context = ssl.client_context()

            version = await Client.test_connection(
                user_input[CONF_URL], validate_cert=validate_cert, ssl_options=context
            )
            if version is None:
                errors[CONF_URL] = f"unkonwn_version"
        except ConnectionRefusedError:
            errors[CONF_URL] = "connection_refused"
        except HTTPTimeoutError:
            errors[CONF_URL] = "connection_timeout"
        except HTTPClientError as error:
            # connection_error_301
            # connection_error_302
            # connection_error_404
            errors[CONF_URL] = f"connection_error_{error.code}"
        except SSLCertVerificationError:
            errors[CONF_URL] = "ssl_verification"
        except Exception:
            errors[CONF_URL] = "unknown_error"

        if bool(errors):
            return await self._show_setup_form(user_input, errors)

        await self.async_set_unique_id(user_input[CONF_URL])
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={
                CONF_URL: user_input[CONF_URL],
                CONF_VERIFY_SSL: validate_cert,
            },
        )
