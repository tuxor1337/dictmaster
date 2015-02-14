# -*- coding: utf-8 -*-

import os
import shutil

from dictmaster.pthread import PluginThread
from dictmaster.postprocessor import BglProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = None
        postprocessor = BglProcessor(self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self
        )
        self._stages = [
            postprocessor,
            editor
        ]

    def reset(self):
        if os.path.exists(self.output_directory):
            for f in os.listdir(self.output_directory):
                if f != "raw":
                    f = os.path.join(self.output_directory, f)
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
        self.setup_dirs()
