# -*- coding: utf-8 -*-

import os
import shutil

from dictmaster.util import mkdir_p, CancelableThread

class PluginThread(CancelableThread):
    _stages = []
    _curr_stage = None

    output_directory = ""
    data = []

    def __init__(self, popts, dirname):
        super(PluginThread, self).__init__()
        self.output_directory = dirname
        self.setup_dirs()

    def setup_dirs(self):
        mkdir_p(os.path.join(self.output_directory, "raw"))

    def reset(self):
        shutil.rmtree(self.output_directory)
        self.setup_dirs()

    def progress(self):
        if self._curr_stage == None or self._canceled: return "Sleeping..."
        return self._curr_stage.progress()

    def run(self):
        for stage in self._stages:
            if self._canceled:
                break
            stage.start()
            self._curr_stage = stage
            stage.join()
            print "done."

    def cancel(self):
        CancelableThread.cancel(self)
        if self._curr_stage:
            self._curr_stage.cancel()

