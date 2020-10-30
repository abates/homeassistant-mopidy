"""Mopidy HTTP/JSON-RPC implementation"""

from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )

    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_forward_entry_unload(entry, "media_player")


async def update_listener(hass: HomeAssistantType, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)