import logging
from homeassistant.const import CONF_URL, CONF_NAME
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from . import unique_id

_LOGGER = logging.getLogger(__name__)


class MopidyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Mopidy"): str,
                    vol.Required(
                        CONF_URL, default="ws://localhost:6680/mopidy/ws"
                    ): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        # check for existing
        entries = self._async_current_entries()
        for entry in entries:
            _LOGGER.debug("Entry: %s", entry.unique_id)
            if (
                entry.data[CONF_URL] == user_input[CONF_URL]
                or entry.unique_id == user_input[CONF_NAME]
            ):
                return self.async_abort(reason="server_exists")

        # attempt to connect

        await self.async_set_unique_id(user_input[CONF_NAME])
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={
                CONF_URL: user_input[CONF_URL],
            },
        )
