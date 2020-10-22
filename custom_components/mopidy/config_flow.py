from homeassistant.const import CONF_URL, CONF_NAME
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from . import unique_id


class MopidyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_URL): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        id = unique_id(user_input[CONF_URL])
        entries = self._async_current_entries()
        for entry in entries:
            if entry.data[CONF_URL] == id:
                return self.async_abort(reason="server_exists")

        return self.async_create_entry(
            title=id,
            data={
                CONF_NAME: user_input[CONF_NAME],
                CONF_URL: user_input[CONF_URL],
            },
        )
