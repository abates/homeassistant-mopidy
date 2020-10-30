"""Support to interact with a Music Player Daemon."""
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
import logging
from datetime import timedelta
from typing import Optional
from urllib.parse import urljoin, urlparse

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType
import voluptuous as vol
from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_STOP,
)

from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    CONF_VERIFY_SSL,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)

from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA_BASE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import ssl
from homeassistant.util.dt import utcnow

from .const import CONF_AUTO_SHUFFLE, DOMAIN, SERVICE_SHUFFLE, DEFAULT_NAME

from mopidy_client import Client

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA_BASE.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_URL): cv.string,
    }
)

SUPPORT_MOPIDY = (
    SUPPORT_PAUSE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PLAY
    | SUPPORT_CLEAR_PLAYLIST
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_SEEK
    | SUPPORT_STOP
)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
):
    """Set up the Mopidy platform."""
    ws_url = config_entry.data[CONF_URL]
    validate_cert = config_entry.data[CONF_VERIFY_SSL]

    _LOGGER.debug("Setting up mopidy server at url %s", ws_url)

    device = MopidyDevice(hass, ws_url, validate_cert, options=config_entry.options)
    async_add_entities([device], True)

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SHUFFLE, {}, "async_shuffle_tracklist"
    )


def notify(f):
    async def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(f):
            await f(*args, **kwargs)
        else:
            f(*args, **kwargs)

        if args[0].entity_id:
            args[0].async_schedule_update_ha_state()

    return wrapper


class MopidyDevice(MediaPlayerEntity):
    def __init__(self, hass, ws_url, validate_cert=True, options={}):
        self.hass = hass
        self._ws_url = ws_url
        self._options = options

        _url = urlparse(ws_url)
        if _url.scheme == "ws":
            _url = _url._replace(scheme="http")
        elif _url.scheme == "wss":
            _url = _url._replace(scheme="https")
        else:
            raise f"Unknown scheme {_url.scheme} for websocket url"

        self._url = _url.geturl()
        self._validate_cert = validate_cert
        self._state = None
        self._playlist = None
        self._current_track = None
        self._repeat = None
        self._shuffle = None
        self._position = 0
        self._position_last_updated = utcnow()
        self._media_image_url = None
        self._track_num = None
        self._remove_listener = None

        self._client = Client(ws_url)

        self._client.on_playlist_changed(self._playlist_changed)
        self._client.on_playback_state_changed(self._playback_state_changed)
        self._client.on_track_playback_started(self._track_playback_started)
        self._client.on_options_changed(self._options_changed)
        self._client.on_seeked(self._seeked)

    async def async_added_to_hass(self):
        context = None
        if self._validate_cert:
            context = ssl.client_context()

        await self._client.connect(
            validate_cert=self._validate_cert, ssl_options=context
        )
        state = await self._client.playback.get_state()
        await self._playback_state_changed(None, state)
        tl_track = await self._client.playback.get_current_tl_track()
        if tl_track:
            await self._track_playback_started(tl_track)

    async def async_will_remove_from_hass(self):
        """Disconnect callbacks."""
        await super().async_will_remove_from_hass()
        _LOGGER.debug("Disconnecting from %s", self._ws_url)
        await self._client.disconnect()

    @notify
    def _playlist_changed(self, playlist):
        self._playlist = playlist

    @notify
    def _playback_state_changed(self, old_state, new_state):
        if new_state == "paused":
            if self._remove_listener:
                self._remove_listener()
                self._remove_listener = None
            new_state = STATE_PAUSED
        elif new_state == "playing":
            new_state = STATE_PLAYING
        elif new_state == "stopped":
            if self._remove_listener:
                self._remove_listener()
                self._remove_listener = None
            new_state = STATE_IDLE
        else:
            new_state = STATE_UNKNOWN
        self._state = new_state

    @notify
    async def _update_pos(self, t):
        pos = await self._client.playback.get_time_position()
        if pos:
            self._position_last_updated = utcnow()
            self._position = pos / 1000
        else:
            self._position = 0

    @notify
    async def _track_playback_started(self, tl_track):
        if self._remove_listener:
            self._remove_listener()

        self._remove_listener = async_track_time_interval(
            self.hass, self._update_pos, timedelta(seconds=1)
        )

        self._current_track = tl_track.track
        # self._current_track = self._client.playback.get_current_track()
        if self._current_track:
            images = await self._client.library.get_images(
                uris=[self._current_track.uri]
            )
            if (
                images[self._current_track.uri]
                and len(images[self._current_track.uri]) > 0
            ):
                url = images[self._current_track.uri][0].uri
                self._media_image_url = urljoin(self._url, url)
            else:
                self._media_image_url = None

            self._track_num = await self._client.tracklist.index()
        else:
            self._media_image_url = None

    @notify
    async def _options_changed(self):
        self._shuffle = await self._client.tracklist.get_random()
        self._repeat = await self._client.tracklist.get_repeat()

    @notify
    def _seeked(self, time_position):
        # mopidy gives time_position in milliseconds, but HomeAssistant
        # wants seconds
        self._position_last_updated = utcnow()
        self._position = time_position / 1000

    async def async_shuffle_tracklist(self):
        await self._client.tracklist.shuffle()

    @property
    def unique_id(self):
        return self._ws_url

    @property
    def should_poll(self) -> bool:
        False

    @property
    def state(self):
        """State of the player."""
        return self._state

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        if self._current_track:
            return self._current_track.uri
        return None

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        if self._current_track:
            # track length from mopidy is in milliseconds, convert
            # to seconds for HomeAssistant
            return self._current_track.length / 1000
        return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        return self._position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        return self._position_last_updated

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        return self._media_image_url

    @property
    def media_title(self):
        """Title of current playing media."""
        if self._current_track:
            return self._current_track.name
        return None

    @property
    def media_artist(self):
        """Artist of current playing media, music track only."""
        if self._current_track:
            return [artist.name for artist in self._current_track.artists]
        return None

    @property
    def media_album_name(self):
        """Album name of current playing media, music track only."""
        if self._current_track:
            return self._current_track.album.name
        return None

    @property
    def media_track(self):
        """Track number of current playing media, music track only."""
        return self._track_num

    @property
    def media_playlist(self):
        """Title of Playlist currently playing."""
        if self._playlist:
            return self._playlist.name
        return None

    @property
    def shuffle(self):
        """Boolean if shuffle is enabled."""
        return self._shuffle

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        if self._state is None:
            return 0

        return SUPPORT_MOPIDY

    async def async_media_play(self):
        """Send play command."""
        await self._client.playback.play()

    async def async_media_pause(self):
        """Send pause command."""
        await self._client.playback.pause()

    async def async_media_stop(self):
        """Send stop command."""
        await self._client.playback.stop()

    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._client.playback.previous()

    async def async_media_next_track(self):
        """Send next track command."""
        await self._client.playback.next()

    async def async_media_seek(self, position):
        """Send seek command."""
        await self._client.playback.seek(position * 1000)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Send the media player the command for playing a playlist."""
        _LOGGER.debug("Playing playlist: %s", media_id)
        if media_type == MEDIA_TYPE_PLAYLIST:
            await self._client.tracklist.clear()
            await self._client.tracklist.add(media_id)
            if self._options.get(CONF_AUTO_SHUFFLE):
                await self.async_shuffle_tracklist()

            await self._client.playback.play()
        else:
            await self._client.clear()
            await self._client.tracklist.add(media_id)
            await self._client.playback.play()

    async def async_clear_playlist(self):
        """Clear players playlist."""
        await self._client.tracklist.clear()

    async def async_set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        await self._client.tracklist.set_random(shuffle)
