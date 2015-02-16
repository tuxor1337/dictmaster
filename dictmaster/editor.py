# -*- coding: utf-8 -*-

import os
import sqlite3
import unicodedata
import time

import warnings
warnings.filterwarnings('error', category=UnicodeWarning)

from pyglossary.glossary import Glossary

from dictmaster.util import CancelableThread

class Editor(CancelableThread):
    plugin = None
    data = []
    enumerate = True
    auto_synonyms = True
    dictname = ""
    output_directory = ""
    conn = None
    c = None

    _status = ""

    def __init__(self, output_directory, plugin, enumerate=True, auto_synonyms=True):
        super(Editor, self).__init__()
        self.auto_synonyms = auto_synonyms
        self.output_directory = output_directory
        self.enumerate = enumerate
        self.dictname = plugin.dictname
        self.plugin = plugin

    def progress(self):
        if self._canceled: return "Sleeping..."
        else: return self._status

    def run(self):
        db_file = os.path.join(self.output_directory, "db.sqlite")
        """
        Force creating a new database, since there is no use of starting from
        an existing database at the moment.
        """
        if os.path.exists(db_file):
            os.remove(db_file)
        if not os.path.exists(db_file):
            self.conn = sqlite3.connect(db_file)
            self.conn.text_factory = str
            self.c = self.conn.cursor()
            self.c.execute('''
                CREATE TABLE dict
                (id INTEGER PRIMARY KEY, word TEXT, def TEXT)
            ''');
            self.c.execute('''
                CREATE TABLE synonyms
                (id INTEGER PRIMARY KEY, wid INTEGER, syn TEXT)
            ''');
            self.c.execute('''
                CREATE TABLE info
                (id INTEGER PRIMARY KEY, key TEXT, value TEXT)
            ''');
            self.data = self.plugin.data
            self.glossToDB()
        else:
            try:
                self.conn = sqlite3.connect(db_file)
                self.conn.text_factory = str
                self.c = self.conn.cursor()
            except sqlite3.OperationalError:
                print("No or corrupt sqlite database. Exiting...")
                raise
        self.conn.commit()
        self.write(os.path.join(self.output_directory, "stardict.ifo"))
        self.conn.close()

    def glossToDB(self):
        for i,entry in enumerate(self.data):
            if self._canceled: break
            edited = [entry[0].strip(),entry[1].strip()]
            try: alts = entry[2]['alts']
            except: alts = []
            edited = [ed.strip() for ed in edited]
            if len(edited) > 1 and edited[0] != "" and edited[1] != "":
                if self.auto_synonyms:
                    alts = findSynonyms((edited[0],edited[1],{'alts':alts}))
                word = edited[0]
                self.c.execute("INSERT INTO dict(word,def) VALUES (?,?)",(word,edited[1]))
                tmp_id = self.c.lastrowid
                for a in alts:
                    try: self.c.execute('''INSERT INTO synonyms(wid,syn)
                                                VALUES (?,?)''',(tmp_id, a))
                    except sqlite3.InterfaceError:
                        sys.exit("Problem: %s; %s" % (tmp_id, a))
            self._status = "Writing to db entry {} of {}...".format(i, len(self.data))
        self._status = "Storing meta info..."

        self.c.execute("""
            INSERT INTO info(key,value) VALUES (?,?)
        """, ("bookname", self.dictname))

        self.remove_empty()
        self.dupentries_remove()
        if self.enumerate: self.dupidx_enumerate()
        else: self.dupidx_cat()
        self.dupsyns_remove()

    def remove_empty(self):
        self.c.execute('''DELETE FROM synonyms WHERE syn="" OR syn=" "''')

    def dupentries_remove(self):
        self._status = "Removing duplicate entries (this might take a few minutes)..."
        start_time = time.time()
        self.c.execute('''
            CREATE TEMP TABLE TempDict AS
                SELECT k.id, q.MaxId
                FROM dict k
                JOIN (SELECT MAX(d.id) as MaxId, d.word, d.def
                      FROM dict d
                      GROUP BY d.word,d.def) q
                ON q.word = k.word
                AND q.def = k.def
        ''')
        affected = self.c.execute("SELECT COUNT(*) FROM TempDict GROUP BY MaxId").fetchall()[0][0]
        self._status = "Removing {} duplicate entries...".format(affected)
        self.c.execute('''
            UPDATE synonyms
            SET wid = (SELECT MaxId
                       FROM TempDict d
                       WHERE d.id = synonyms.wid)
        ''')
        self.c.execute('''
            DELETE FROM dict
            WHERE id NOT IN (SELECT MaxId FROM TempDict)
        ''')
        #print "\n%d seconds\n" % (time.time() - start_time,)
        self._status = "Done removing duplicate entries ({} entries affected).".format(self.c.rowcount)

    def dupsyns_remove(self):
        self._status = "Removing duplicate synonyms..."
        dubs = self.c.execute('''
            DELETE FROM synonyms
            WHERE id NOT IN (SELECT max(id)
                             FROM synonyms
                             GROUP BY wid,syn)
        ''')
        self._status = "Done removing duplicate synonyms ({} entries affected).".format(self.c.rowcount)

    def dupidx_enumerate(self):
        self.c.execute('''
            SELECT word
            FROM dict
            GROUP BY word
            HAVING COUNT(*) > 1
        ''')
        dubs = self.c.fetchall()
        no = len(dubs)
        for i,dbl in enumerate(dubs):
            self._status = "Enumerating ambivalent entries %5d of %5d..." % (i,no)
            self.c.execute('''SELECT id FROM dict WHERE word=?''',(dbl[0],))
            for j,wid in enumerate(self.c.fetchall()):
                self.c.execute('''
                    INSERT INTO synonyms(wid,syn)
                    VALUES (?,?)
                ''', (wid[0],dbl[0]))
                self.c.execute('''
                    UPDATE dict
                    SET word=?
                    WHERE id=?
                ''', ("%s(%d)" % (dbl[0],j+1),wid[0]))

    def dupidx_cat(self):
        self.c.execute('''
            SELECT id, word, def
            FROM dict
            GROUP BY word
            HAVING COUNT(*) > 1
        ''')
        critical = self.c.fetchall()
        no = len(critical)
        for i,entry in enumerate(critical):
            self._status = "Concatenating ambivalent entries %5d of %5d..." % (i,no)
            self.c.execute('''
                SELECT id, def
                FROM dict
                WHERE word=?
                AND id!=?
            ''', (entry[1],entry[0]))
            dups = self.c.fetchall()
            defn = entry[2]
            for dup in dups:
                self.c.execute('''DELETE FROM dict WHERE id=?''', (dup[0],))
                self.c.execute('''
                    UPDATE synonyms
                    SET wid=?
                    WHERE wid=?
                ''', (entry[0],dup[0]))
                defn += dup[1]
            self.c.execute('''
                UPDATE dict
                SET def=?
                WHERE id=?
            ''', (defn,entry[0]))

    def write(self,fname):
        if fname[-6:].lower() == "sqlite":
            try: os.unlink(fname)
            except OSError: pass
            outfile_db = sqlite3.connect(fname)
            outfile_db.text_factory = str
            query = "".join(line for line in self.conn.iterdump())
            self._status = "Writing to output file..."
            outfile_db.executescript(query)
        else:
            info, self.data = self.dictFromSqlite()
            self._status = "Writing to output file..."
            g = Glossary()
            g.data = self.data
            g.setInfo("bookname", info["bookname"])
            g.write(fname)

    def dictFromSqlite(self):
        info = {}; data = []
        for row in self.c.execute('''SELECT key,value FROM info''').fetchall():
            info[row[0]]=row[1]
        self.c.execute('''SELECT word,def,id FROM dict''')
        rows = self.c.fetchall(); no = len(rows)
        syns = self.c.execute('''SELECT syn,wid FROM synonyms''').fetchall()
        syn_list = {x[2]:[] for x in rows}
        [syn_list[syn[1]].append(syn[0]) for syn in syns]
        if "sametypesequence" in info: defiFormat = info["sametypesequence"]
        else: defiFormat = "h"
        for i,row in enumerate(rows):
            self._status = "Writing entry %5d of %5d..." % (i,no)
            data.append((row[0],row[1],{'defiFormat': defiFormat, 'alts':syn_list[row[2]]}))
        return (info, data)

def remove_accents(input_str):
    if not isinstance(input_str, unicode):
        input_str = unicode(input_str,"utf8")
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def findSynonyms(entry):
    greek_alph = u'αιηωυεοςρτθπσδφγξκλζχψβνμ'
    latin_alph = u'aihwueosrtqpsdfgcklzxybnm'

    def add_alt(alts,a):
        try:
            if a not in alts and a != entry[0]: alts.append(a)
        except UnicodeWarning: pass

    def add_greek_alt(alts,a):
        orig_a = a
        a = remove_accents(a).lower().encode("utf8")
        add_alt(alts,a)
        add_alt(alts,a.replace("-",""))
        for x,y in zip(greek_alph,latin_alph):
            a = a.replace(x.encode("utf8"),y.encode("utf8"))
        add_alt(alts,a)
        add_alt(alts,a.replace("-",""))

    alts = entry[2]['alts']
    add_greek_alt(alts,entry[0])
    for delimiter in [",","#",";"]:
        [add_greek_alt(alts,c.strip()) for c in entry[0].split(delimiter)]

    return alts

