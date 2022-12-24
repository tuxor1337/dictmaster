# This file is part of dictmaster
# Copyright (C) 2018  Thomas Vogt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import shutil

from dictmaster.util import FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import ZipFetcher
from dictmaster.stages.unzipper import Unzipper
from dictmaster.stages.processor import DictfileProcessor

POPTS_DEFAULT = ["de-en"]

class Plugin(BasePlugin):
    def __init__(self, dirname, popts=POPTS_DEFAULT):
        super().__init__(dirname)
        if len(popts) > 0 and popts[0] == "de-en":
            self.dictname = "BEOLINGUS Deutsch-Englisch"
            flipCols = False
        else:
            self.dictname = "BEOLINGUS Englisch-Deutsch"
            flipCols = True
        postprocessor = DictfileProcessor(self,
            fieldSplit="::",
            subfieldSplit="|",
            subsubfieldSplit=";",
            flipCols=flipCols
        )
        self.stages['Fetcher'] = ZipFetcher(self)
        self.stages['Unzipper'] = Unzipper(self)
        self.stages['Processor'] = postprocessor

    def post_setup(self, cursor):
        self.set_name(self.dictname, cursor=cursor)
        url = "http://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt.zip"
        cursor.execute('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', (url, FLAGS["ZIP_FETCHER"]))

