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
import sqlite3

from pyglossary.glossary import Glossary

from dictmaster.util import CancelableThread, remove_accents

class Editor(CancelableThread):
    plugin = None
    enumerate = True

    _conn = None
    _c = None
    _status = ""

    def __init__(self, plugin, enumerate=True):
        super(Editor, self).__init__()
        self.enumerate = enumerate
        self.plugin = plugin

    def progress(self):
        if self._canceled: return "Sleeping..."
        else: return self._status

    def run(self):
        self._conn = sqlite3.connect(self.plugin.output_db)
        self._c = self._conn.cursor()

        self.remove_empty()
        self.dupentries_remove()
        if self.enumerate: self.dupidx_enumerate()
        else: self.dupidx_cat()
        self.dupsyns_remove()

        self._conn.commit()
        self.write(os.path.join(self.plugin.output_directory, "stardict.ifo"))
        self._conn.close()

    def remove_empty(self):
        self._c.execute('''DELETE FROM synonyms WHERE syn="" OR syn=" "''')

    def dupentries_remove(self):
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
        self._status = "Removing duplicate synonyms..."
        dubs = self._c.execute('''
            DELETE FROM synonyms
            WHERE id NOT IN (SELECT max(id) FROM synonyms GROUP BY wid,syn)
        ''')
        self._status = "Done removing duplicate synonyms ({} entries affected).".format(self._c.rowcount)

    def dupidx_enumerate(self):
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

    def write(self,fname):
        info, self.data = self.dictFromSqlite()
        self._status = "Writing to output file..."
        g = Glossary()
        g.data = self.data
        g.setInfo("bookname", info["bookname"].encode("utf-8"))
        g.write(fname)

    def dictFromSqlite(self):
        info = {}; data = []
        for row in self._c.execute('''SELECT key,value FROM info''').fetchall():
            info[row[0]]=row[1]
        self._c.execute('''SELECT word,def,id FROM dict''')
        rows = self._c.fetchall(); no = len(rows)
        syns = self._c.execute('''SELECT syn,wid FROM synonyms''').fetchall()
        syn_list = {x[2]:[] for x in rows}
        [syn_list[syn[1]].append(syn[0].encode("utf-8")) for syn in syns]
        if "sametypesequence" in info: defiFormat = info["sametypesequence"]
        else: defiFormat = "h"
        for i,row in enumerate(rows):
            self._status = "Reading from db entry %d of %d..." % (i,no)
            data.append((
                row[0].encode("utf-8"),
                row[1].encode("utf-8"),
                {'defiFormat': defiFormat, 'alts':syn_list[row[2]]}
            ))
        return (info, data)
