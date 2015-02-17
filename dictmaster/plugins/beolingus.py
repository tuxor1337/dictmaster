# -*- coding: utf-8 -*-

import os
import shutil

from dictmaster.util import mkdir_p
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import ZipFetcher, Unzipper
from dictmaster.postprocessor import DictfileProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        if popts == "de-en":
            self.dictname = "BEOLINGUS Deutsch-Englisch"
            flipCols = False
        else:
            self.dictname = "BEOLINGUS Englisch-Deutsch"
            flipCols = True
        fetcher = ZipFetcher(
            self.output_directory,
            urls=["http://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt.zip"]
        )
        postprocessor = DictfileProcessor(self,
            fieldSplit="::",
            subfieldSplit="|",
            subsubfieldSplit=";",
            flipCols=flipCols
        )
        self._stages = [
            fetcher,
            Unzipper(self.output_directory),
            postprocessor,
            Editor(plugin=self)
        ]

    def setup_dirs(self):
        if os.path.exists(os.path.join(self.output_directory, "raw")):
            shutil.rmtree(os.path.join(self.output_directory, "raw"))
        PluginThread.setup_dirs(self)
        mkdir_p(os.path.join(self.output_directory, "zip"))
