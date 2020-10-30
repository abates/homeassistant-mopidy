from typing import Optional
from homeassistant.util import ssl
import logging
from ssl import SSLCertVerificationError
from tornado.httpclient import HTTPClientError

from tornado.simple_httpclient import HTTPTimeoutError
from homeassistant.const import CONF_URL, CONF_NAME
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from mopidy_client import Client
from . import unique_id

_LOGGER = logging.getLogger(__name__)


class MopidyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    async def _show_setup_form(self, user_input={}, errors={}):
        """Show the setup form to the user."""
        _LOGGER.debug("Errors: %s", errors)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, "Mopidy")
                    ): str,
                    vol.Required(
                        CONF_URL,
                        default=user_input.get(
                            CONF_URL, "ws://localhost:6680/mopidy/ws"
                        ),
                    ): str,
                    vol.Optional(
                        "no_check_cert",
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
            elif entry.unique_id == unique_id(user_input[CONF_URL]):
                errors[CONF_NAME] = "name_exists"
                return await self._show_setup_form(user_input, errors)

        # attempt to connect
        validate_cert = not user_input["no_check_cert"]
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

        await self.async_set_unique_id(unique_id(user_input[CONF_URL]))
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={
                CONF_URL: user_input[CONF_URL],
                "validate_cert": validate_cert,
            },
        )
