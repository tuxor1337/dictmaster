# -*- coding: utf-8 -*-

import os
import sys

from dictmaster.utils import FLAGS
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Unzipper
from dictmaster.postprocessor import DictfileProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) dict.cc zip file!")
        self.zfile = popts[0]
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "dict.cc %s" % os.path.basename(self.zfile)
        self._stages = [
            Unzipper(self),
            DictfileProcessor(self),
            Editor(plugin=self, enumerate=False)
        ]

    def post_setup(self, cursor):
        cursor.execute('''
            INSERT INTO raw (uri, data, flag)
            VALUES (?,?,?)
        ''', (None, self.zfile, FLAGS["ZIP_FETCHER"] | FLAGS["FETCHED"]))
