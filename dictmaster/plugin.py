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

from pyglossary.glossary import Glossary

from dictmaster.util import mkdir_p, CancelableThread, FLAGS, remove_accents

class BasePlugin(CancelableThread):
    stages = {
        "UrlFetcher": None,
        "Fetcher": None,
        "Unzipper": None,
        "Processor": None,
    }
    curr_stage = None
    output_directory = ""
    output_db = ""
    dictname = ""
    enumerate = True

    def __init__(self, dirname, popts=[]):
        super(BasePlugin, self).__init__()
        self.output_directory = dirname
        self.output_db = os.path.join(dirname, "db.sqlite")
        self.setup()

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
            ''')
            c.execute('''
                INSERT INTO info(key,value) VALUES (?,?)
            ''', ("bookname", self.dictname))
            self.post_setup(c)
            conn.commit()
            conn.close()

    def post_setup(self, cursor): pass

    def set_name(self, name):
        self.dictname = name
        conn = sqlite3.connect(self.output_db)
        c = conn.cursor()
        c.execute('''
            UPDATE info SET value=? WHERE key=?
        ''', (name, "bookname"))
        conn.commit()
        conn.close()

    def reset(self):
        if os.path.exists(self.output_directory):
            shutil.rmtree(self.output_directory)
        self.setup()

    def progress(self):
        if self.curr_stage == None: return "Setup..."
        return self.curr_stage.progress()

    def run(self):
        if self.curr_stage is None:
            stages = [
                self.stages["UrlFetcher"],
                self.stages["Fetcher"],
                self.stages["Unzipper"],
                self.stages["Processor"],
            ]
        else:
            stages = [self.curr_stage]
        for s in stages:
            if s is None: continue
            s.start()
            self.curr_stage = s
            s.join()
            if self._canceled: break

    def cancel(self):
        CancelableThread.cancel(self)
        if self.curr_stage: self.curr_stage.cancel()

    def optimize_data(self, enumerate=None):
        if enumerate is None:
            enumerate = self.enumerate
        self._conn = sqlite3.connect(self.output_db)
        self._c = self._conn.cursor()

        self.remove_empty()
        self.dupentries_remove()
        if enumerate: self.dupidx_enumerate()
        else: self.dupidx_cat()
        self.dupsyns_remove()

        self._conn.commit()
        self._conn.close()

    def remove_empty(self):
        """ Remove empty synonyms """
        self._c.execute('''DELETE FROM synonyms WHERE syn="" OR syn=" "''')

    def dupentries_remove(self):
        """ Remove dict entries where both word and definition agree """
        self._status = "Removing duplicate entries..."
        self._c.execute('''
            CREATE TEMP TABLE TempDict
            (id INTEGER PRIMARY KEY, MaxId INTEGER)
        ''');
        self._c.execute('''
            INSERT INTO TempDict (id, MaxId)
            SELECT k.id, q.MaxId
            FROM dict k
            JOIN (SELECT MAX(d.id) as MaxId, d.word, d.def
                  FROM dict d
                  GROUP BY d.word,d.def) q
            ON q.word = k.word
            AND q.def = k.def
        ''')
        affected = self._c.execute('''
            SELECT COUNT(*) FROM TempDict WHERE MaxId <> id
        ''').fetchone()[0]
        self._status = "Removing {} duplicate entries...".format(affected)
        self._c.execute('''
            UPDATE synonyms
            SET wid = (SELECT MaxId
                       FROM TempDict d
                       WHERE d.id = synonyms.wid)
        ''')
        self._c.execute('''
            DELETE FROM dict
            WHERE id NOT IN (SELECT MaxId FROM TempDict)
        ''')
        self._c.execute('''DROP TABLE TempDict''');
        self._status = "Done removing duplicate entries ({} entries affected).".format(affected)

    def dupsyns_remove(self):
        """ Remove synonym entries where both synonym and wid agree """
        self._status = "Removing duplicate synonyms..."
        dubs = self._c.execute('''
            DELETE FROM synonyms
            WHERE id NOT IN (SELECT max(id) FROM synonyms GROUP BY wid,syn)
        ''')
        self._status = "Done removing duplicate synonyms ({} entries affected).".format(self._c.rowcount)

    def dupidx_enumerate(self):
        """ Enumerate all dict entries for each term """
        lines = self._c.execute('''SELECT id, word FROM dict''')
        data = {}
        for entry in lines:
            if entry[1] not in data: data[entry[1]] = []
            data[entry[1]].append(entry[0])
        no = len(data.keys())
        for i,key in enumerate(data.keys()):
            dups = data[key]
            self._status = "Enumerating ambivalent entries %d of %d..." % (i,no)
            if len(dups) > 1:
                self._c.executemany('''
                    INSERT INTO synonyms(wid,syn)
                    VALUES (?,?)
                ''', [(wid,key) for wid in dups])
                self._c.executemany('''
                    UPDATE dict
                    SET word=?
                    WHERE id=?
                ''', [("%s(%d)" % (key,j+1),wid) for j,wid in enumerate(dups)])

    def dupidx_cat(self):
        """ Concatenate all dict entries for each term """
        lines = self._c.execute('''SELECT id, word, def FROM dict''')
        data = {}
        for entry in lines:
            if entry[1] not in data:
                data[entry[1]] = {
                    "id": entry[0],
                    "def": entry[2],
                    "dups": []
                }
            else:
                data[entry[1]]["dups"].append(entry[0])
                data[entry[1]]["def"] += entry[2]
        no = len(data.keys())
        for i,key in enumerate(data.keys()):
            value = data[key]
            self._status = "Concatenating ambivalent entries %d of %d..." % (i,no)
            if len(value["dups"]) > 0:
                self._c.executemany('''
                    DELETE FROM dict WHERE id=?
                ''', [(d,) for d in value["dups"]])
                self._c.executemany('''
                    UPDATE synonyms
                    SET wid=?
                    WHERE wid=?
                ''', [(value["id"],d) for d in value["dups"]])
                self._c.execute('''
                    UPDATE dict
                    SET def=?
                    WHERE id=?
                ''', (value["def"],value["id"]))

    def export(self):
        fname = os.path.join(self.output_directory, "stardict.ifo")
        with sqlite3.connect(self.output_db) as conn:
            c = conn.cursor()
            info = {}; data = []
            for row in c.execute('''SELECT key,value FROM info''').fetchall():
                info[row[0]]=row[1]
            c.execute('''SELECT word,def,id FROM dict''')
            rows = c.fetchall()
            no = len(rows)
            syns = c.execute('''SELECT syn,wid FROM synonyms''').fetchall()
            syn_list = {wid: [] for word, definition, wid in rows}
            [syn_list[wid].append(syn) for syn, wid in syns]
            if "sametypesequence" in info:
                defiFormat = info["sametypesequence"]
            else:
                defiFormat = "h"
            Glossary.init()
            g = Glossary()
            for i, (word, definition, wid) in enumerate(rows):
                self._status = "Reading from db entry %d of %d..." % (i,no)
                g.addEntryObj(g.newEntry(
                    [word] + syn_list[wid],
                    definition,
                    defiFormat=defiFormat))
            self._status = "Writing to output file..."
            g.setInfo("bookname", info["bookname"])
            g.write(fname, "Stardict")
