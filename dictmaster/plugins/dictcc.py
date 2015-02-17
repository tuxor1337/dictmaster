# -*- coding: utf-8 -*-

from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Unzipper
from dictmaster.postprocessor import DictfileProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "dict.cc %s" % popts
        self._stages = [
            Unzipper(self.output_directory),
            DictfileProcessor(self),
            Editor(plugin=self, enumerate=False)
        ]
