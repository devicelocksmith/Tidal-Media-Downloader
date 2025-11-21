#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :  events.py
@Date    :  2022/06/10
@Author  :  Yaronzz
@Version :  1.0
@Contact :  yaronhuang@foxmail.com
@Desc    :
"""

import contextlib
import http.server
import json
import os
import queue
import sys
import threading
import time

import aigpy

try:
    import msvcrt  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - not available on POSIX
    msvcrt = None

from . import apiKey
from .download import (
    downloadAlbumInfo,
    downloadCover,
    downloadTrack,
    downloadTracks,
    downloadVideo,
    downloadVideos,
)
from .enums import AudioQuality, Type, VideoQuality
from .lang.language import LANG
from .model import Album, Artist, Mix, Playlist, Track, Video
from .printf import Printf
from .settings import SETTINGS, TOKEN, TokenSettings
from urllib.parse import urlencode

from .tidal import TIDAL_API


def _build_redirect_uri(payload: dict) -> str:
    """Extract a usable redirect URI from the incoming payload."""

    def _normalize(value):
        if value is None:
            return ""
        return str(value).strip()

    normalized = _normalize(payload.get("normalizedUri"))
    if normalized:
        return normalized

    pkce_uri = _normalize(payload.get("pkceUri"))
    if pkce_uri:
        return pkce_uri

    scheme = _normalize(payload.get("scheme"))
    path = _normalize(payload.get("path"))
    params = payload.get("params")
    if scheme and path:
        if isinstance(params, dict) and params:
            pairs = {}
            for key, value in params.items():
                if key is None:
                    continue
                pairs[str(key)] = "" if value is None else str(value)
            query = urlencode(pairs)
            query = f"?{query}" if query else ""
        else:
            query = ""

        path = path.lstrip("/")
        if path:
            return f"{scheme}://{path}{query}"
        return f"{scheme}://{query.lstrip('?')}"

    return ""


def _create_pkce_handler(result_queue: "queue.Queue[str]", stop_event: threading.Event):
    class _PkceHandler(http.server.BaseHTTPRequestHandler):
        server_version = "TidalPKCE/1.0"
        sys_version = ""

        def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence default logging
            return

        def do_POST(self):  # type: ignore[override]
            if self.path.rstrip("/") != "/pkce":
                self.send_response(404)
                self.end_headers()
                return

            if stop_event.is_set():
                self.send_response(409)
                self.end_headers()
                return

            content_length = self.headers.get("Content-Length")
            try:
                length = int(content_length) if content_length else 0
            except ValueError:
                length = 0

            body = self.rfile.read(max(length, 0))
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            if not isinstance(payload, dict):
                self.send_response(400)
                self.end_headers()
                return

            redirect_uri = _build_redirect_uri(payload)
            if not redirect_uri:
                self.send_response(400)
                self.end_headers()
                return

            redirect_uri = redirect_uri.strip()
            if not redirect_uri:
                self.send_response(400)
                self.end_headers()
                return

            if stop_event.is_set():
                self.send_response(409)
                self.end_headers()
                return

            result_queue.put(redirect_uri)
            stop_event.set()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"received"}')

            threading.Thread(target=self.server.shutdown, daemon=True).start()

    return _PkceHandler


def _resolve_listener_port() -> int:
    """Return the configured listener port with validation."""

    port = SETTINGS.listenerPort or 8123
    try:
        port = int(port)
    except (TypeError, ValueError):
        return 8123

    if port <= 0 or port > 65535:
        return 8123
    return port


def _start_pkce_server(result_queue: "queue.Queue[str]"):
    stop_event = threading.Event()
    ready_event = threading.Event()
    server_info = {"server": None, "port": None, "error": None, "stop_event": stop_event}

    def _run():
        handler = _create_pkce_handler(result_queue, stop_event)
        port = _resolve_listener_port()
        try:
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        except Exception as exc:  # pragma: no cover - network failures
            server_info["error"] = exc
            server_info["port"] = port
            ready_event.set()
            return

        httpd.timeout = 0.5
        server_info["server"] = httpd
        server_info["port"] = httpd.server_address[1]
        ready_event.set()

        with contextlib.suppress(Exception):
            httpd.serve_forever()
        httpd.server_close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    ready_event.wait()
    server_info["thread"] = thread
    return server_info


def _stop_pkce_server(server_info: dict) -> None:
    stop_event = server_info.get("stop_event")
    if isinstance(stop_event, threading.Event):
        stop_event.set()

    server = server_info.get("server")
    if server is not None:
        with contextlib.suppress(Exception):
            server.shutdown()

    thread = server_info.get("thread")
    if isinstance(thread, threading.Thread):
        thread.join(timeout=1)


def _read_user_redirect_input(cancel_event: threading.Event) -> str:
    prompt = "Redirect URL('0'-Cancel):"
    aigpy.cmd.colorPrint(prompt, aigpy.cmd.TextColor.Yellow, None)
    sys.stdout.flush()

    if os.name == 'nt' and msvcrt is not None:
        buffer = []
        while not cancel_event.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ('\r', '\n'):
                    print("")
                    return ''.join(buffer)
                if ch == '\003':
                    raise KeyboardInterrupt
                if ch == '\b':
                    if buffer:
                        buffer.pop()
                        print('\b \b', end='', flush=True)
                    continue
                buffer.append(ch)
                print(ch, end='', flush=True)
                sys.stdout.flush()
            else:
                time.sleep(0.05)
        return ""

    import select

    while not cancel_event.is_set():
        try:
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
        except (OSError, ValueError):  # pragma: no cover - defensive
            readable = []
        if readable:
            line = sys.stdin.readline()
            return line.rstrip('\r\n')
    return ""

'''
=================================
START DOWNLOAD
=================================
'''


def start_album(obj: Album):
    Printf.album(obj)
    tracks, videos = TIDAL_API.getItems(obj.id, Type.Album)
    if SETTINGS.saveAlbumInfo:
        downloadAlbumInfo(obj, tracks)
    if SETTINGS.saveCovers and obj.cover is not None:
        downloadCover(obj)
    downloadTracks(tracks, obj)
    if SETTINGS.downloadVideos:
        downloadVideos(videos, obj)


def start_track(obj: Track):
    album = TIDAL_API.getAlbum(obj.album.id)
    if SETTINGS.saveCovers:
        downloadCover(album)
    downloadTrack(obj, album)


def start_video(obj: Video):
    downloadVideo(obj, obj.album)


def start_artist(obj: Artist):
    albums = TIDAL_API.getArtistAlbums(obj.id, SETTINGS.includeEP)
    Printf.artist(obj, len(albums))
    for item in albums:
        start_album(item)


def start_playlist(obj: Playlist):
    Printf.playlist(obj)
    tracks, videos = TIDAL_API.getItems(obj.uuid, Type.Playlist)
    downloadTracks(tracks, None, obj)
    if SETTINGS.downloadVideos:
        downloadVideos(videos, None, obj)


def start_mix(obj: Mix):
    Printf.mix(obj)
    downloadTracks(obj.tracks, None, None)
    downloadVideos(obj.videos, None, None)


def start_file(string):
    txt = aigpy.file.getContent(string)
    if aigpy.string.isNull(txt):
        Printf.err("Nothing can read!")
        return
    array = txt.split('\n')
    for item in array:
        if aigpy.string.isNull(item):
            continue
        if item[0] == '#':
            continue
        if item[0] == '[':
            continue
        start(item)


def start_type(etype: Type, obj):
    if etype == Type.Album:
        start_album(obj)
    elif etype == Type.Track:
        start_track(obj)
    elif etype == Type.Video:
        start_video(obj)
    elif etype == Type.Artist:
        start_artist(obj)
    elif etype == Type.Playlist:
        start_playlist(obj)
    elif etype == Type.Mix:
        start_mix(obj)


def start(string):
    if aigpy.string.isNull(string):
        Printf.err('Please enter something.')
        return

    strings = string.split(" ")
    for item in strings:
        if aigpy.string.isNull(item):
            continue
        if os.path.exists(item):
            start_file(item)
            return

        try:
            etype, obj = TIDAL_API.getByString(item)
        except Exception as e:
            Printf.err(str(e) + " [" + item + "]")
            return

        try:
            start_type(etype, obj)
        except Exception as e:
            Printf.err(str(e))


'''
=================================
CHANGE SETTINGS
=================================
'''


def changePathSettings():
    Printf.settings()
    SETTINGS.downloadPath = Printf.enterPath(
        LANG.select.CHANGE_DOWNLOAD_PATH,
        LANG.select.MSG_PATH_ERR,
        '0',
        SETTINGS.downloadPath)
    SETTINGS.albumFolderFormat = Printf.enterFormat(
        LANG.select.CHANGE_ALBUM_FOLDER_FORMAT,
        SETTINGS.albumFolderFormat,
        SETTINGS.getDefaultPathFormat(Type.Album))
    SETTINGS.playlistFolderFormat = Printf.enterFormat(
        LANG.select.CHANGE_PLAYLIST_FOLDER_FORMAT,
        SETTINGS.playlistFolderFormat,
        SETTINGS.getDefaultPathFormat(Type.Playlist))
    SETTINGS.trackFileFormat = Printf.enterFormat(
        LANG.select.CHANGE_TRACK_FILE_FORMAT,
        SETTINGS.trackFileFormat,
        SETTINGS.getDefaultPathFormat(Type.Track))
    SETTINGS.videoFileFormat = Printf.enterFormat(
        LANG.select.CHANGE_VIDEO_FILE_FORMAT,
        SETTINGS.videoFileFormat,
        SETTINGS.getDefaultPathFormat(Type.Video))
    SETTINGS.save()


def changeQualitySettings():
    Printf.settings()
    SETTINGS.audioQuality = AudioQuality(
        int(Printf.enterLimit(LANG.select.CHANGE_AUDIO_QUALITY,
                              LANG.select.MSG_INPUT_ERR,
                              ['0', '1', '2', '3', '4'])))
    SETTINGS.videoQuality = VideoQuality(
        int(Printf.enterLimit(LANG.select.CHANGE_VIDEO_QUALITY,
                              LANG.select.MSG_INPUT_ERR,
                              ['1080', '720', '480', '360'])))
    SETTINGS.save()


def changeSettings():
    Printf.settings()
    SETTINGS.showProgress = Printf.enterBool(LANG.select.CHANGE_SHOW_PROGRESS)
    SETTINGS.showTrackInfo = Printf.enterBool(LANG.select.CHANGE_SHOW_TRACKINFO)
    SETTINGS.checkExist = Printf.enterBool(LANG.select.CHANGE_CHECK_EXIST)
    SETTINGS.includeEP = Printf.enterBool(LANG.select.CHANGE_INCLUDE_EP)
    SETTINGS.saveCovers = Printf.enterBool(LANG.select.CHANGE_SAVE_COVERS)
    SETTINGS.saveAlbumInfo = Printf.enterBool(LANG.select.CHANGE_SAVE_ALBUM_INFO)
    SETTINGS.downloadVideos = Printf.enterBool(LANG.select.CHANGE_DOWNLOAD_VIDEOS)
    SETTINGS.lyricFile = Printf.enterBool(LANG.select.CHANGE_ADD_LRC_FILE)
    SETTINGS.multiThread = Printf.enterBool(LANG.select.CHANGE_MULITHREAD_DOWNLOAD)
    SETTINGS.usePlaylistFolder = Printf.enterBool(LANG.select.SETTING_USE_PLAYLIST_FOLDER + "('0'-No,'1'-Yes):")
    SETTINGS.downloadDelay = Printf.enterBool(LANG.select.CHANGE_USE_DOWNLOAD_DELAY)

    SETTINGS.metadataRefreshDelay = Printf.enterBool(
        LANG.get(
            'CHANGE_METADATA_REFRESH_DELAY',
            "Use metadata refresh delay('0'-No,'1'-Yes):",
        )
    )

    SETTINGS.listenerEnabled = Printf.enterBool(
        LANG.get('CHANGE_ENABLE_LISTENER', "Enable listener mode('0'-No,'1'-Yes):")
    )

    secret = Printf.enter(LANG.get('CHANGE_LISTENER_SECRET', "Listener secret('0'-not modify):"))
    if secret != '0' and not aigpy.string.isNull(secret):
        SETTINGS.listenerSecret = secret

    port_value = Printf.enter(LANG.get('CHANGE_LISTENER_PORT', "Listener port('0'-not modify):"))
    if port_value != '0' and not aigpy.string.isNull(port_value):
        try:
            port_int = int(port_value)
            if port_int > 0 and port_int <= 65535:
                SETTINGS.listenerPort = port_int
            else:
                Printf.err(LANG.select.MSG_INPUT_ERR)
        except ValueError:
            Printf.err(LANG.select.MSG_INPUT_ERR)

    SETTINGS.language = Printf.enter(LANG.select.CHANGE_LANGUAGE + "(" + LANG.getLangChoicePrint() + "):")
    LANG.setLang(SETTINGS.language)
    SETTINGS.save()


def configureCustomApiSettings():
    Printf.settings()
    Printf.info(
        LANG.get(
            'CUSTOM_API_OVERRIDES_INFO',
            "Leave blank to keep the current value. Enter '0' to clear an override (set it to null). PKCE logins don't require a client secret, and the PKCE token URL override is optional—set it only when your provider uses a non-default token endpoint (long-term credential logins also use the default).",
        )
    )

    def _prompt(prompt_key, default_prompt, current_value, mask_current=False):
        shown_current = current_value if not mask_current else Printf._mask_listener_secret(current_value)
        if not shown_current:
            shown_current = LANG.get('CUSTOM_VALUE_UNSET', 'not set')
        prompt_text = LANG.get(prompt_key, default_prompt).format(current=shown_current)
        raw = Printf.enter(prompt_text)
        if raw == '0':
            return None
        if aigpy.string.isNull(raw):
            return current_value
        return raw.strip()

    SETTINGS.customClientId = _prompt(
        'CUSTOM_PROMPT_CLIENT_ID',
        "Custom client ID override (current: {current}) ('0'-clear):",
        SETTINGS.customClientId,
    )
    SETTINGS.customClientSecret = _prompt(
        'CUSTOM_PROMPT_CLIENT_SECRET',
        "Custom client secret override (not required for PKCE; enter '0' to clear/set null) (current: {current}):",
        SETTINGS.customClientSecret,
        mask_current=True,
    )
    SETTINGS.customPkceAuthorizeUrl = _prompt(
        'CUSTOM_PROMPT_PKCE_AUTHORIZE_URL',
        "Custom PKCE authorize URL (current: {current}) ('0'-clear):",
        SETTINGS.customPkceAuthorizeUrl,
    )
    SETTINGS.customPkceTokenUrl = _prompt(
        'CUSTOM_PROMPT_PKCE_TOKEN_URL',
        "Custom PKCE token URL (optional; set only if your provider uses a non-default token endpoint—long-term credentials use the default) (current: {current}) ('0'-clear):",
        SETTINGS.customPkceTokenUrl,
    )
    SETTINGS.customPkceRedirectUri = _prompt(
        'CUSTOM_PROMPT_PKCE_REDIRECT_URL',
        "Custom PKCE redirect URL (current: {current}) ('0'-clear):",
        SETTINGS.customPkceRedirectUri,
    )
    SETTINGS.customPkceScope = _prompt(
        'CUSTOM_PROMPT_PKCE_SCOPE',
        "Custom PKCE scope (current: {current}) ('0'-clear):",
        SETTINGS.customPkceScope,
    )

    support_prompt = LANG.get(
        'CUSTOM_PROMPT_PKCE_SUPPORTS',
        "Override PKCE support flag (current: {current}) ('0'-clear,'1'-force enable,'2'-force disable):",
    ).format(current=str(SETTINGS.customSupportsPkce))
    support_raw = Printf.enter(support_prompt)
    if support_raw == '0':
        SETTINGS.customSupportsPkce = None
    elif support_raw == '1':
        SETTINGS.customSupportsPkce = True
    elif support_raw == '2':
        SETTINGS.customSupportsPkce = False
    elif support_raw and support_raw.lower() in ('true', 'false'):
        SETTINGS.customSupportsPkce = support_raw.lower() == 'true'

    SETTINGS.save()
    updateActiveApiKey()
    Printf.success(LANG.get('CUSTOM_API_OVERRIDES_SAVED', 'Custom API overrides saved.'))


def updateActiveApiKey():
    TIDAL_API.apiKey = SETTINGS.apply_api_key_overrides(apiKey.getItem(SETTINGS.apiKeyIndex))


def changeApiKey():
    item = apiKey.getItem(SETTINGS.apiKeyIndex)
    ver = apiKey.getVersion()

    Printf.info(f'Current APIKeys: {str(SETTINGS.apiKeyIndex)} {item["platform"]}-{item["formats"]}')
    Printf.info(f'Current Version: {str(ver)}')
    Printf.apikeys(apiKey.getItems())
    index = int(Printf.enterLimit("APIKEY index:", LANG.select.MSG_INPUT_ERR, apiKey.getLimitIndexs()))

    changed = index != SETTINGS.apiKeyIndex
    if changed:
        SETTINGS.apiKeyIndex = index
        SETTINGS.save()
    updateActiveApiKey()
    return changed


'''
=================================
LOGIN
=================================
'''


def apiSupportsPkce():
    if TIDAL_API.apiKey is None:
        return False
    value = TIDAL_API.apiKey.get('supportsPkce')
    if isinstance(value, str):
        return value.lower() == 'true'
    return bool(value)


def __displayTime__(seconds, granularity=2):
    if seconds <= 0:
        return "unknown"

    result = []
    intervals = (
        ('weeks', 604800),
        ('days', 86400),
        ('hours', 3600),
        ('minutes', 60),
        ('seconds', 1),
    )

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


def loginByWeb():
    try:
        print(LANG.select.AUTH_START_LOGIN)
        # get device code
        url = TIDAL_API.getDeviceCode()

        print(LANG.select.AUTH_NEXT_STEP.format(
            aigpy.cmd.green(url),
            aigpy.cmd.yellow(__displayTime__(TIDAL_API.key.authCheckTimeout))))
        print(LANG.select.AUTH_WAITING)

        start = time.time()
        elapsed = 0
        while elapsed < TIDAL_API.key.authCheckTimeout:
            elapsed = time.time() - start
            if not TIDAL_API.checkAuthStatus():
                time.sleep(TIDAL_API.key.authCheckInterval + 1)
                continue

            Printf.success(LANG.select.MSG_VALID_ACCESSTOKEN.format(
                __displayTime__(int(TIDAL_API.key.expiresIn))))

            TOKEN.userid = TIDAL_API.key.userId
            TOKEN.countryCode = TIDAL_API.key.countryCode
            TOKEN.accessToken = TIDAL_API.key.accessToken
            TOKEN.refreshToken = TIDAL_API.key.refreshToken
            TOKEN.expiresAfter = time.time() + int(TIDAL_API.key.expiresIn)
            TOKEN.save()
            return True

        raise Exception(LANG.select.AUTH_TIMEOUT)
    except Exception as e:
        Printf.err(f"Login failed.{str(e)}")
        return False


def loginByPkce():
    if not apiSupportsPkce():
        Printf.err('PKCE login is not available in the current configuration.')
        return False

    try:
        authorize_url = TIDAL_API.startPkceAuthorization()
    except Exception as e:
        Printf.err(str(e))
        return False

    Printf.info('Open the following URL in your browser to authenticate:')
    print(aigpy.cmd.green(authorize_url))
    Printf.info('After approving access, paste the final redirect URL below or send it to the local /pkce endpoint.')

    redirect_queue: "queue.Queue[str]" = queue.Queue()
    server_info = _start_pkce_server(redirect_queue)
    server_error = server_info.get('error')
    if server_error is not None:
        Printf.info(f"Local /pkce endpoint unavailable: {server_error}. Manual entry only.")
    else:
        port = server_info.get('port')
        if port:
            Printf.info(f"Listening for redirect callbacks on http://127.0.0.1:{port}/pkce")

    stop_event = server_info.get('stop_event')
    if not isinstance(stop_event, threading.Event):
        stop_event = threading.Event()
        server_info['stop_event'] = stop_event

    try:
        user_input = _read_user_redirect_input(stop_event)
    except KeyboardInterrupt:
        _stop_pkce_server(server_info)
        raise

    http_redirect = ""
    with contextlib.suppress(queue.Empty):
        http_redirect = redirect_queue.get_nowait()

    _stop_pkce_server(server_info)

    redirect_choice = http_redirect.strip() if http_redirect else ""
    if redirect_choice:
        Printf.info("Received redirect URL from local endpoint.")
    else:
        redirect_choice = (user_input or "").strip()

    if redirect_choice == '0' and not http_redirect:
        return False

    if not redirect_choice:
        Printf.err('No redirect URL received.')
        return False

    try:
        TIDAL_API.completePkceAuthorization(redirect_choice)
    except Exception as e:
        Printf.err(str(e))
        return False

    expires = TIDAL_API.key.expiresIn if TIDAL_API.key.expiresIn is not None else 0
    Printf.success(LANG.select.MSG_VALID_ACCESSTOKEN.format(__displayTime__(int(expires))))

    TOKEN.userid = TIDAL_API.key.userId
    TOKEN.countryCode = TIDAL_API.key.countryCode
    TOKEN.accessToken = TIDAL_API.key.accessToken
    TOKEN.refreshToken = TIDAL_API.key.refreshToken
    TOKEN.expiresAfter = time.time() + int(expires) if expires else 0
    TOKEN.save()
    return True


def loginByConfig():
    try:
        if aigpy.string.isNull(TOKEN.accessToken):
            return False

        if TIDAL_API.verifyAccessToken(TOKEN.accessToken):
            Printf.info(LANG.select.MSG_VALID_ACCESSTOKEN.format(
                __displayTime__(int(TOKEN.expiresAfter - time.time()))))

            TIDAL_API.key.countryCode = TOKEN.countryCode
            TIDAL_API.key.userId = TOKEN.userid
            TIDAL_API.key.accessToken = TOKEN.accessToken
            return True

        Printf.info(LANG.select.MSG_INVALID_ACCESSTOKEN)
        if TIDAL_API.refreshAccessToken(TOKEN.refreshToken):
            Printf.success(LANG.select.MSG_VALID_ACCESSTOKEN.format(
                __displayTime__(int(TIDAL_API.key.expiresIn))))

            TOKEN.userid = TIDAL_API.key.userId
            TOKEN.countryCode = TIDAL_API.key.countryCode
            TOKEN.accessToken = TIDAL_API.key.accessToken
            TOKEN.expiresAfter = time.time() + int(TIDAL_API.key.expiresIn)
            TOKEN.save()
            return True
        else:
            TokenSettings().save()
            return False
    except Exception as e:
        return False


def loginByAccessToken():
    try:
        print("-------------AccessToken---------------")
        token = Printf.enter("accessToken('0' go back):")
        if token == '0':
            return
        TIDAL_API.loginByAccessToken(token, TOKEN.userid)
    except Exception as e:
        Printf.err(str(e))
        return

    print("-------------RefreshToken---------------")
    refreshToken = Printf.enter("refreshToken('0' to skip):")
    if refreshToken == '0':
        refreshToken = TOKEN.refreshToken

    TOKEN.accessToken = token
    TOKEN.refreshToken = refreshToken
    TOKEN.expiresAfter = 0
    TOKEN.countryCode = TIDAL_API.key.countryCode
    TOKEN.save()
