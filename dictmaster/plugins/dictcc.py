# -*- coding: utf-8 -*-
#
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
import sys

from dictmaster.util import FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Unzipper
from dictmaster.stages.processor import DictfileProcessor

class Plugin(BasePlugin):
    enumerate = False

    def __init__(self, popts, dirname):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) dict.cc zip file!")
        self.zfile = popts[0]
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "dict.cc %s" % os.path.basename(self.zfile)
        self.stages['Unzipper'] = Unzipper(self)
        self.stages['Processor'] = DictfileProcessor(self)

    def post_setup(self, cursor):
        cursor.execute('''
            INSERT INTO raw (uri, data, flag)
            VALUES (?,?,?)
        ''', (None, self.zfile, FLAGS["ZIP_FETCHER"] | FLAGS["FETCHED"]))
