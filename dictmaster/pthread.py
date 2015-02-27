# -*- coding: utf-8 -*-

import os
import shutil
import sqlite3

from dictmaster.util import mkdir_p, CancelableThread

class PluginThread(CancelableThread):
    _stages = []
    _curr_stage = None

    dictname = ""
    output_directory = ""
    output_db = ""

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
                    flag INT
                )
            ''');
            c.execute('''
                CREATE INDEX raw_uri_idx ON raw (uri)
            ''')
            c.execute('''
                CREATE TABLE dict (
                    id INTEGER PRIMARY KEY,
                    word TEXT,
                    def TEXT,
                    rawid INT
                )
            ''');
            c.execute('''
                CREATE TABLE synonyms (
                    id INT PRIMARY KEY,
                    wid INT,
                    syn TEXT
                )
            ''');
            c.execute('''
                CREATE INDEX synonym_wid_idx ON synonyms (wid)
            ''')
            c.execute('''
                CREATE TABLE info (
                    id INT PRIMARY KEY,
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
        if self._canceled: return "Sleeping..."
        return self._curr_stage.progress()

    def run(self):
        self.setup()
        for stage in self._stages:
            stage.start()
            self._curr_stage = stage
            stage.join()
            if self._canceled: break
            print " done."

    def cancel(self):
        CancelableThread.cancel(self)
        if self._curr_stage: self._curr_stage.cancel()

