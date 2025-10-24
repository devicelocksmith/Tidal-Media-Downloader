#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   english.py
@Time    :   2021/11/24
@Author  :   Yaronzz & jee019
@Version :   1.2
@Contact :   yaronhuang@foxmail.com
@Desc    :   
'''


class LangEnglish(object):
    SETTING = "SETTINGS"
    VALUE = "VALUE"
    SETTING_DOWNLOAD_PATH = "Download path"
    SETTING_ONLY_M4A = "Convert mp4 to m4a"
    SETTING_ADD_EXPLICIT_TAG = "Add explicit tag"
    SETTING_ADD_HYPHEN = "Add hyphen"
    SETTING_ADD_YEAR = "Add year before album-folder"
    SETTING_USE_TRACK_NUM = "Add user track number"
    SETTING_AUDIO_QUALITY = "Audio quality"
    SETTING_VIDEO_QUALITY = "Video quality"
    SETTING_CHECK_EXIST = "Check exist"
    SETTING_ARTIST_BEFORE_TITLE = "ArtistName before track-title"
    SETTING_ALBUMID_BEFORE_FOLDER = "Id before album-folder"
    SETTING_INCLUDE_EP = "Include singles & EPs"
    SETTING_SAVE_COVERS = "Save covers"
    SETTING_LANGUAGE = "Language"
    SETTING_USE_PLAYLIST_FOLDER = "Use playlist folder"
    SETTING_MULITHREAD_DOWNLOAD = "Multi thread download"
    SETTING_ALBUM_FOLDER_FORMAT = "Album folder format"
    SETTING_PLAYLIST_FOLDER_FORMAT = "Playlist folder format"
    SETTING_TRACK_FILE_FORMAT = "Track file format"
    SETTING_VIDEO_FILE_FORMAT = "Video file format"
    SETTING_SHOW_PROGRESS = "Show progress"
    SETTING_SHOW_TRACKINFO = "Show Track Info"
    SETTING_SAVE_ALBUMINFO = "Save AlbumInfo.txt"
    SETTING_DOWNLOAD_VIDEOS = "Download videos"
    SETTING_ADD_LYRICS = "Add lyrics"
    SETTING_LYRICS_SERVER_PROXY = "Lyrics server proxy"
    SETTING_ADD_LRC_FILE = "Save timed lyrics (.lrc file)"
    SETTING_PATH = "Settings path"
    SETTING_APIKEY = "APIKey support"
    SETTING_CUSTOM_CLIENT_ID = "Custom client ID override"
    SETTING_CUSTOM_CLIENT_SECRET = "Custom client secret override"
    SETTING_CUSTOM_PKCE_AUTHORIZE_URL = "Custom PKCE authorize URL"
    SETTING_CUSTOM_PKCE_TOKEN_URL = "Custom PKCE token URL"
    SETTING_CUSTOM_PKCE_REDIRECT_URL = "Custom PKCE redirect URL"
    SETTING_CUSTOM_PKCE_SCOPE = "Custom PKCE scope"
    SETTING_CUSTOM_PKCE_SUPPORTS = "Override supports PKCE"
    SETTING_ADD_TYPE_FOLDER = "Add Type-Folder"
    SETTING_DOWNLOAD_DELAY = "Use Download Delay"
    SETTING_METADATA_REFRESH_DELAY = "Use metadata refresh delay"
    SETTING_LISTENER_ENABLED = "Listener mode enabled"
    SETTING_LISTENER_PORT = "Listener port"
    SETTING_LISTENER_SECRET = "Listener secret"

    CHOICE = "CHOICE"
    FUNCTION = "FUNCTION"
    CHOICE_ENTER = "Enter"
    CHOICE_ENTER_URLID = "Enter 'Url/ID':"
    CHOICE_EXIT = "Exit"
    CHOICE_LOGIN = "Check AccessToken"
    CHOICE_SETTINGS = "Settings"
    CHOICE_SET_ACCESS_TOKEN = "Set AccessToken"
    CHOICE_DOWNLOAD_BY_URL = "Download by url or ID"
    CHOICE_LOGOUT = "Logout"
    CHOICE_APIKEY = "Select APIKey"
    CHOICE_PKCE_LOGIN = "Login via PKCE"
    CHOICE_LISTENER = "Start listener mode"
    CHOICE_CUSTOM_API_SETTINGS = "Configure custom API settings"

    PRINT_ERR = "[ERR]"
    PRINT_INFO = "[INFO]"
    PRINT_SUCCESS = "[SUCCESS]"

    PRINT_ENTER_CHOICE = "Enter Choice:"
    PRINT_LATEST_VERSION = "Latest version:"
    # PRINT_USERNAME = "username:"
    # PRINT_PASSWORD = "password:"

    CHANGE_START_SETTINGS = "Start settings('0'-Return,'1'-Yes):"
    CHANGE_DOWNLOAD_PATH = "Download path('0'-not modify):"
    CHANGE_AUDIO_QUALITY = "Audio quality('0'-Normal,'1'-High,'2'-HiFi,'3'-Master,'4'-Max):"
    CHANGE_VIDEO_QUALITY = "Video quality(1080, 720, 480, 360):"
    CHANGE_ONLYM4A = "Convert mp4 to m4a('0'-No,'1'-Yes):"
    CHANGE_ADD_EXPLICIT_TAG = "Add explicit tag to file names('0'-No,'1'-Yes):"
    CHANGE_ADD_HYPHEN = "Use hyphens instead of spaces in file names('0'-No,'1'-Yes):"
    CHANGE_ADD_YEAR = "Add year to album folder names('0'-No,'1'-Yes):"
    CHANGE_USE_TRACK_NUM = "Add track number before file names('0'-No,'1'-Yes):"
    CHANGE_CHECK_EXIST = "Check exist file before download track('0'-No,'1'-Yes):"
    CHANGE_ARTIST_BEFORE_TITLE = "Add artistName before track title('0'-No,'1'-Yes):"
    CHANGE_INCLUDE_EP = "Include singles and EPs when downloading an artist's albums('0'-No,'1'-Yes):"
    CHANGE_ALBUMID_BEFORE_FOLDER = "Add id before album folder('0'-No,'1'-Yes):"
    CHANGE_SAVE_COVERS = "Save covers('0'-No,'1'-Yes):"
    CHANGE_LANGUAGE = "Select language"
    CHANGE_ALBUM_FOLDER_FORMAT = "Album folder format('0'-not modify,'default'-to set default):"
    CHANGE_PLAYLIST_FOLDER_FORMAT = "Playlist folder format('0'-not modify,'default'-to set default):"
    CHANGE_TRACK_FILE_FORMAT = "Track file format('0'-not modify,'default'-to set default):"
    CHANGE_VIDEO_FILE_FORMAT = "Video file format('0'-not modify,'default'-to set default):"
    CHANGE_SHOW_PROGRESS = "Show progress('0'-No,'1'-Yes):"
    CHANGE_SHOW_TRACKINFO = "Show track info('0'-No,'1'-Yes):"
    CHANGE_SAVE_ALBUM_INFO = "Save AlbumInfo.txt('0'-No,'1'-Yes):"
    CHANGE_DOWNLOAD_VIDEOS = "Download videos (when downloading playlists, albums, mixes)('0'-No,'1'-Yes):"
    CHANGE_ADD_LYRICS = "Add lyrics('0'-No,'1'-Yes):"
    CHANGE_LYRICS_SERVER_PROXY = "Lyrics server proxy('0'-not modify):"
    CHANGE_ADD_LRC_FILE = "Save timed lyrics .lrc file ('0'-No,'1'-Yes):"
    CHANGE_ADD_TYPE_FOLDER = "Add Type-Folder,eg Album/Video/Playlist('0'-No,'1'-Yes):"
    CHANGE_MULITHREAD_DOWNLOAD = "Multi thread download('0'-No,'1'-Yes):"
    CHANGE_USE_DOWNLOAD_DELAY = "Use Download Delay('0'-No,'1'-Yes):"
    CHANGE_METADATA_REFRESH_DELAY = "Use metadata refresh delay('0'-No,'1'-Yes):"
    CHANGE_ENABLE_LISTENER = "Enable listener mode('0'-No,'1'-Yes):"
    CHANGE_LISTENER_SECRET = "Listener secret('0'-not modify):"
    CHANGE_LISTENER_PORT = "Listener port('0'-not modify):"

    CUSTOM_API_OVERRIDES_INFO = "Leave blank to keep the current value. Enter '0' to clear an override."
    CUSTOM_PROMPT_CLIENT_ID = "Custom client ID override (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_CLIENT_SECRET = "Custom client secret override (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_PKCE_AUTHORIZE_URL = "Custom PKCE authorize URL (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_PKCE_TOKEN_URL = "Custom PKCE token URL (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_PKCE_REDIRECT_URL = "Custom PKCE redirect URL (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_PKCE_SCOPE = "Custom PKCE scope (current: {current}) ('0'-clear):"
    CUSTOM_PROMPT_PKCE_SUPPORTS = "Override PKCE support flag (current: {current}) ('0'-clear,'1'-force enable,'2'-force disable):"
    CUSTOM_API_OVERRIDES_SAVED = "Custom API overrides saved."
    CUSTOM_VALUE_UNSET = "not set"

    # {} are required in these strings
    AUTH_START_LOGIN = "Starting login process..."
    AUTH_LOGIN_CODE = "Your login code is {}"
    AUTH_NEXT_STEP = "Go to {} within the next {} to complete setup."
    AUTH_WAITING = "Waiting for authorization..."
    AUTH_TIMEOUT = "Operation timed out."

    MSG_VALID_ACCESSTOKEN = "AccessToken good for {}."
    MSG_INVALID_ACCESSTOKEN = "Expired AccessToken. Attempting to refresh it."
    MSG_PATH_ERR = "Path is error!"
    MSG_INPUT_ERR = "Input error!"

    MODEL_ALBUM_PROPERTY = "ALBUM-PROPERTY"
    MODEL_TRACK_PROPERTY = "TRACK-PROPERTY"
    MODEL_VIDEO_PROPERTY = "VIDEO-PROPERTY"
    MODEL_ARTIST_PROPERTY = "ARTIST-PROPERTY"
    MODEL_PLAYLIST_PROPERTY = "PLAYLIST-PROPERTY"

    MODEL_TITLE = 'Title'
    MODEL_TRACK_NUMBER = 'Track Number'
    MODEL_VIDEO_NUMBER = 'Video Number'
    MODEL_RELEASE_DATE = 'Release Date'
    MODEL_VERSION = 'Version'
    MODEL_EXPLICIT = 'Explicit'
    MODEL_ALBUM = 'Album'
    MODEL_ID = 'ID'
    MODEL_NAME = 'Name'
    MODEL_TYPE = 'Type'
