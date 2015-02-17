# -*- coding: utf-8 -*-

import os
import sys

from dictmaster.pthread import PluginThread
from dictmaster.postprocessor import BglProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        bgl_file = popts
        if not os.path.exists(bgl_file):
            sys.exit("Provide full path to (existing) BGL file!")
        bgl_file_base = os.path.basename(bgl_file)[:-4]
        super(Plugin, self).__init__(popts, os.path.join(dirname,bgl_file_base))
        self.dictname = None
        self._stages = [
            BglProcessor(self, bgl_file),
            Editor(plugin=self)
        ]
