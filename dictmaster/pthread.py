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
import shutil
import sqlite3

from dictmaster.util import mkdir_p, CancelableThread, FLAGS

class PluginThread(CancelableThread):
    _stages = []
    _curr_stage = None

    dictname = ""
    output_directory = ""
    output_db = ""
    force_process = False

    def __init__(self, popts, dirname):
        super(PluginThread, self).__init__()
        self.output_directory = dirname
        self.output_db = os.path.join(dirname, "db.sqlite")

    def setup(self):
        mkdir_p(os.path.join(self.output_directory, "raw"))
        mkdir_p(os.path.join(self.output_directory, "zip"))
        mkdir_p(os.path.join(self.output_directory, "res"))
        if not os.path.exists(self.output_db):
            conn = sqlite3.connect(self.output_db)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE raw (
                    id INTEGER PRIMARY KEY,
                    uri TEXT,
                    data TEXT,
                    flag INTEGER
                )
            ''');
            c.execute('''
                CREATE INDEX raw_uri_idx ON raw (uri)
            ''')
            c.execute('''
                CREATE INDEX raw_data_idx ON raw (data)
            ''')
            c.execute('''
                CREATE TABLE dict (
                    id INTEGER PRIMARY KEY,
                    word TEXT,
                    def TEXT,
                    rawid INTEGER
                )
            ''');
            c.execute('''
                CREATE TABLE synonyms (
                    id INTEGER PRIMARY KEY,
                    wid INTEGER,
                    syn TEXT
                )
            ''');
            c.execute('''
                CREATE INDEX synonym_wid_idx ON synonyms (wid)
            ''')
            c.execute('''
                CREATE TABLE info (
                    id INTEGER PRIMARY KEY,
                    key TEXT,
                    value TEXT
                )
            ''');
            self.post_setup(c)
            c.execute('''
                INSERT INTO info(key,value) VALUES (?,?)
            ''', ("bookname", self.dictname))
            conn.commit()
            conn.close()

    def post_setup(self, cursor): pass
    def reset(self):
        if os.path.exists(self.output_directory):
            shutil.rmtree(self.output_directory)

    def progress(self):
        if self._curr_stage == None: return "Setup..."
        return self._curr_stage.progress()

    def run(self):
        self.setup()
        if self.force_process:
            conn = sqlite3.connect(self.output_db)
            c = conn.cursor()
            c.execute("DELETE FROM dict")
            c.execute("DELETE FROM synonyms")
            c.execute("UPDATE raw SET flag = flag & ~?", (FLAGS["PROCESSED"],))
            conn.commit()
            conn.close()
        for stage in self._stages:
            stage.start()
            self._curr_stage = stage
            stage.join()
            if self._canceled: break
            print(" done.")

    def cancel(self):
        CancelableThread.cancel(self)
        if self._curr_stage: self._curr_stage.cancel()

