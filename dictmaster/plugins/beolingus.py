# -*- coding: utf-8 -*-

import os
import shutil

from dictmaster.util import FLAGS
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import ZipFetcher, Unzipper
from dictmaster.postprocessor import DictfileProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        if popts == "de-en":
            self.dictname = u"BEOLINGUS Deutsch-Englisch"
            flipCols = False
        else:
            self.dictname = u"BEOLINGUS Englisch-Deutsch"
            flipCols = True
        postprocessor = DictfileProcessor(self,
            fieldSplit="::",
            subfieldSplit="|",
            subsubfieldSplit=";",
            flipCols=flipCols
        )
        self._stages = [
            ZipFetcher(self),
            Unzipper(self),
            postprocessor,
            Editor(self)
        ]

    def post_setup(self, cursor):
        url = "http://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt.zip"
        cursor.execute('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', (url, FLAGS["ZIP_FETCHER"]))

