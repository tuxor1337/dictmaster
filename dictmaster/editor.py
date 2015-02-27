# -*- coding: utf-8 -*-

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
        self._status = "Done removing duplicate entries ({} entries affected).".format(self._c.rowcount)

    def dupsyns_remove(self):
        self._status = "Removing duplicate synonyms..."
        dubs = self._c.execute('''
            DELETE FROM synonyms
            WHERE id NOT IN (SELECT max(id) FROM synonyms GROUP BY wid,syn)
        ''')
        self._status = "Done removing duplicate synonyms ({} entries affected).".format(self._c.rowcount)

    def dupidx_enumerate(self):
        self._c.execute('''
            SELECT word
            FROM dict
            GROUP BY word
            HAVING COUNT(*) > 1
        ''')
        dubs = self._c.fetchall()
        no = len(dubs)
        for i,dbl in enumerate(dubs):
            self._status = "Enumerating ambivalent entries %d of %d..." % (i,no)
            self._c.execute('''SELECT id FROM dict WHERE word=?''',(dbl[0],))
            for j,wid in enumerate(self._c.fetchall()):
                self._c.execute('''
                    INSERT INTO synonyms(wid,syn)
                    VALUES (?,?)
                ''', (wid[0],dbl[0]))
                self._c.execute('''
                    UPDATE dict
                    SET word=?
                    WHERE id=?
                ''', ("%s(%d)" % (dbl[0],j+1),wid[0]))

    def dupidx_cat(self):
        self._c.execute('''
            SELECT id, word, def
            FROM dict
            GROUP BY word
            HAVING COUNT(*) > 1
        ''')
        critical = self._c.fetchall()
        no = len(critical)
        for i,entry in enumerate(critical):
            self._status = "Concatenating ambivalent entries %d of %d..." % (i,no)
            self._c.execute('''
                SELECT id, def
                FROM dict
                WHERE word=?
                AND id!=?
            ''', (entry[1],entry[0]))
            dups = self._c.fetchall()
            self._c.executemany('''
                DELETE FROM dict WHERE id=?
            ''', [(d[0],) for d in dups])
            self._c.executemany('''
                UPDATE synonyms
                SET wid=?
                WHERE wid=?
            ''', [(entry[0],d[0]) for d in dups])
            self._c.execute('''
                UPDATE dict
                SET def=?
                WHERE id=?
            ''', (entry[2] + "".join(d[1] for d in dups),entry[0]))

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

