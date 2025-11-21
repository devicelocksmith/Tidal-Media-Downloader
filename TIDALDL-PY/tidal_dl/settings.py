#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   settings.py
@Time    :   2020/11/08
@Author  :   Yaronzz
@Version :   3.0
@Contact :   yaronhuang@foxmail.com
@Desc    :
'''
import json
from typing import Optional

import aigpy
import base64

from .lang.language import *
from .enums import *


class Settings(aigpy.model.ModelBase):
    checkExist = True
    includeEP = True
    saveCovers = True
    language = 0
    lyricFile = False
    apiKeyIndex = 0
    showProgress = True
    showTrackInfo = True
    saveAlbumInfo = False
    downloadVideos = True
    multiThread = False
    downloadDelay = True
    listenerEnabled = False
    listenerSecret = "change-this-listener-secret"
    listenerPort = 8123
    customClientId = None
    customClientSecret = None
    customSupportsPkce = None
    customPkceAuthorizeUrl = None
    customPkceTokenUrl = None
    customPkceRedirectUri = None
    customPkceScope = None
    metadataRefreshDelay = False

    downloadPath = "./download/"
    audioQuality = AudioQuality.Normal
    videoQuality = VideoQuality.P360
    usePlaylistFolder = True
    albumFolderFormat = R"{ArtistName}/{Flag} {AlbumTitle} [{AlbumID}] [{AlbumYear}]"
    playlistFolderFormat = R"Playlist/{PlaylistName} [{PlaylistUUID}]"
    trackFileFormat = R"{TrackNumber} - {ArtistName} - {TrackTitle}{ExplicitFlag}"
    videoFileFormat = R"{VideoNumber} - {ArtistName} - {VideoTitle}{ExplicitFlag}"

    def getDefaultPathFormat(self, type: Type):
        if type == Type.Album:
            return R"{ArtistName}/{Flag} {AlbumTitle} [{AlbumID}] [{AlbumYear}]"
        elif type == Type.Playlist:
            return R"Playlist/{PlaylistName} [{PlaylistUUID}]"
        elif type == Type.Track:
            return R"{TrackNumber} - {ArtistName} - {TrackTitle}{ExplicitFlag}"
        elif type == Type.Video:
            return R"{VideoNumber} - {ArtistName} - {VideoTitle}{ExplicitFlag}"
        return ""

    def getAudioQuality(self, value):
        for item in AudioQuality:
            if item.name == value:
                return item
        return AudioQuality.Normal

    def getVideoQuality(self, value):
        for item in VideoQuality:
            if item.name == value:
                return item
        return VideoQuality.P360

    def read(self, path):
        self._path_ = path
        txt = aigpy.file.getContent(self._path_)
        if len(txt) > 0:
            data = json.loads(txt)
            if aigpy.model.dictToModel(data, self) is None:
                return

        self.audioQuality = self.getAudioQuality(self.audioQuality)
        self.videoQuality = self.getVideoQuality(self.videoQuality)

        if self.albumFolderFormat is None:
            self.albumFolderFormat = self.getDefaultPathFormat(Type.Album)
        if self.trackFileFormat is None:
            self.trackFileFormat = self.getDefaultPathFormat(Type.Track)
        if self.playlistFolderFormat is None:
            self.playlistFolderFormat = self.getDefaultPathFormat(Type.Playlist)
        if self.videoFileFormat is None:
            self.videoFileFormat = self.getDefaultPathFormat(Type.Video)
        if self.apiKeyIndex is None:
            self.apiKeyIndex = 0

        if self.listenerSecret is None or self.listenerSecret == "":
            self.listenerSecret = "change-this-listener-secret"
        try:
            self.listenerPort = int(self.listenerPort)
        except (TypeError, ValueError):
            self.listenerPort = 8123
        if self.listenerPort <= 0 or self.listenerPort > 65535:
            self.listenerPort = 8123

        if isinstance(self.customSupportsPkce, str):
            if self.customSupportsPkce.lower() == 'true':
                self.customSupportsPkce = True
            elif self.customSupportsPkce.lower() == 'false':
                self.customSupportsPkce = False
            else:
                self.customSupportsPkce = None

        delay_raw = getattr(self, 'metadataRefreshDelay', False)
        if isinstance(delay_raw, (int, float)):
            self.metadataRefreshDelay = delay_raw > 0
        else:
            self.metadataRefreshDelay = bool(delay_raw)

        LANG.setLang(self.language)

    def save(self):
        data = aigpy.model.modelToDict(self)
        data['audioQuality'] = self.audioQuality.name
        data['videoQuality'] = self.videoQuality.name
        txt = json.dumps(data)
        aigpy.file.write(self._path_, txt, 'w+')

    def has_custom_api_settings(self) -> bool:
        return any(
            (
                self.customClientId,
                self.customClientSecret,
                self.customSupportsPkce is not None,
                self.customPkceAuthorizeUrl,
                self.customPkceTokenUrl,
                self.customPkceRedirectUri,
                self.customPkceScope,
            )
        )

    def apply_api_key_overrides(self, api_key: Optional[dict]) -> dict:
        combined = dict(api_key or {})

        if self.customClientId:
            combined['clientId'] = self.customClientId
        if self.customClientSecret:
            combined['clientSecret'] = self.customClientSecret
        if self.customSupportsPkce is not None:
            combined['supportsPkce'] = self.customSupportsPkce
        if self.customPkceAuthorizeUrl:
            combined['pkceAuthorizeUrl'] = self.customPkceAuthorizeUrl
        if self.customPkceTokenUrl:
            combined['pkceTokenUrl'] = self.customPkceTokenUrl
        if self.customPkceRedirectUri:
            combined['pkceRedirectUri'] = self.customPkceRedirectUri
        if self.customPkceScope:
            combined['pkceScope'] = self.customPkceScope

        return combined


class TokenSettings(aigpy.model.ModelBase):
    userid = None
    countryCode = None
    accessToken = None
    refreshToken = None
    expiresAfter = 0

    def __encode__(self, string):
        sw = bytes(string, 'utf-8')
        st = base64.b64encode(sw)
        return st

    def __decode__(self, string):
        try:
            sr = base64.b64decode(string)
            st = sr.decode()
            return st
        except:
            return string

    def read(self, path):
        self._path_ = path
        txt = aigpy.file.getContent(self._path_)
        if len(txt) > 0:
            data = json.loads(self.__decode__(txt))
            aigpy.model.dictToModel(data, self)

    def save(self):
        data = aigpy.model.modelToDict(self)
        txt = json.dumps(data)
        aigpy.file.write(self._path_, self.__encode__(txt), 'wb')


# Singleton
SETTINGS = Settings()
TOKEN = TokenSettings()
