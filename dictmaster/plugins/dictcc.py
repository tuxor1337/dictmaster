# -*- coding: utf-8 -*-

from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Unzipper
from dictmaster.postprocessor import DictfileProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "dict.cc %s" % popts
        postprocessor = DictfileProcessor(self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self,
            enumerate=False
        )
        self._stages = [
            Unzipper(self.output_directory),
            postprocessor,
            editor
        ]
