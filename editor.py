# -*- coding: utf-8 -*-

import sys, os

from pyglossary.glossary import Glossary
import re, sqlite3, unicodedata

import warnings
warnings.filterwarnings('error', category=UnicodeWarning)

class glossEditor(object):
    def __init__(self, gloss, plugin, db_file):
        self.g = gloss
        self.plugin = plugin
        if not os.path.exists(db_file):
            self.conn = sqlite3.connect(db_file)
            self.conn.text_factory = str
            self.c = self.conn.cursor()
            self.c.execute('''CREATE TABLE dict
                (id INTEGER PRIMARY KEY,
                word TEXT, def TEXT)''');
            self.c.execute('''CREATE TABLE synonyms
                (id INTEGER PRIMARY KEY,
                wid INTEGER, syn TEXT)''');
            self.c.execute('''CREATE TABLE info
                (id INTEGER PRIMARY KEY,
                key TEXT, value TEXT)''');
            self.glossToDB()
        else:
            try:
                self.conn = sqlite3.connect(db_file)
                self.conn.text_factory = str
                self.c = self.conn.cursor()
            except sqlite3.OperationalError:
                print("No or corrupt sqlite database. Exiting...")
                sys.exit()

    def glossToDB(self):
        no = len(self.g.data)
        for i,entry in enumerate(self.g.data):
            edited = [entry[0].strip(),entry[1].strip()]
            try:
                alts = entry[2]['alts']
            except:
                alts = []
            if i % 20 == 0:
                sys.stdout.write("Reading entry %5d of %5d...\r" % (i,no))
                sys.stdout.flush()
            edited = [ed.strip() for ed in edited]
            if len(edited) > 1 and edited[0] != "" and edited[1] != "":
                alts = findSynonyms((edited[0],edited[1],{'alts':alts}))
                word = edited[0]
                self.c.execute("INSERT INTO dict(word,def) VALUES (?,?)",(word,edited[1]))
                tmp_id = self.c.lastrowid
                for a in alts:
                    try:
                        self.c.execute('''INSERT INTO synonyms(wid,syn)
                                                VALUES (?,?)''',(tmp_id, a))
                    except sqlite3.InterfaceError:
                        sys.exit("Problem: %s; %s" % (tmp_id, a))
        print "Reading entry %5d of %5d...done." % (no,no)
        print "Reading meta info...",
        for key in self.g.infoKeys():
            self.c.execute("INSERT INTO info(key,value) VALUES (?,?)",(key,self.g.getInfo(key)))
        print "done."

        self.remove_empty()
        self.dupentries_remove()
        if self.plugin["editor"]["dups"] == "enumerate":
            self.dupidx_enumerate()
        elif self.plugin["editor"]["dups"] == "cat":
            self.dupidx_cat()
        self.dupsyns_remove()

    def preview_entry(self,word):
        self.c.execute('''SELECT wid FROM synonyms WHERE syn LIKE ?''',(word+"%",))
        wids = self.c.fetchall()
        output = []
        for (wid,) in wids:
            self.c.execute('''SELECT word,def FROM dict WHERE id=?''',(wid,))
            output.append(self.c.fetchone())
        return output

    def remove_empty(self):
        self.c.execute('''DELETE FROM synonyms WHERE syn="" OR syn=" "''')

    def dupentries_remove(self):
        dubs = self.c.execute('''SELECT id,word,def
            FROM dict GROUP BY word,def HAVING COUNT(*) > 1''').fetchall()
        no, i = len(dubs), 0
        for dbl in dubs:
            i += 1
            if i % 3 == 0:
                sys.stdout.write("Removing duplicates %3d of %3d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''SELECT id FROM dict WHERE word=? AND def=?''',(dbl[1],dbl[2]))
            old_ids = self.c.fetchall()
            for old in old_ids:
                self.c.execute('''UPDATE synonyms SET wid=? WHERE wid=?''',(dbl[0],old[0]))
            self.c.execute('''DELETE FROM dict WHERE word=? AND def=? AND id!=?''',(dbl[1],dbl[2],dbl[0]))
        print "Removing duplicates %3d of %3d... done." % (no,no)

    def dupsyns_remove(self):
        sys.stdout.write("Removing duplicate synonyms...")
        sys.stdout.flush()
        dubs = self.c.execute('''DELETE FROM synonyms WHERE id NOT IN
            (SELECT max(id) FROM synonyms GROUP BY wid,syn)
        ''')
        sys.stdout.write("done (%d entries affected).\n" % self.c.rowcount)

    def dupidx_enumerate(self):
        self.c.execute('''SELECT word FROM dict GROUP BY word HAVING COUNT(*) > 1''')
        dubs = self.c.fetchall()
        no = len(dubs)
        i = 0
        for dbl in dubs:
            i += 1
            if i % 7 == 0:
                sys.stdout.write("Enumerating ambivalent entries %5d of %5d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''SELECT id FROM dict WHERE word=?''',(dbl[0],))
            for j,wid in enumerate(self.c.fetchall()):
                self.c.execute('''INSERT INTO synonyms(wid,syn)
                                            VALUES (?,?)''',(wid[0],dbl[0]))
                self.c.execute('''UPDATE dict SET word=? WHERE id=?''',("%s(%d)" % (dbl[0],j+1),wid[0]))
        print "Enumerating ambivalent entries %5d of %5d... done." % (no,no)

    def dupidx_cat(self):
        self.c.execute('''SELECT id,word,def FROM dict GROUP BY word HAVING COUNT(*) > 1''')
        critical = self.c.fetchall()
        no = len(critical)
        for i,entry in enumerate(critical):
            if i % 7 == 0:
                sys.stdout.write("Concatenating ambivalent entries %5d of %5d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''SELECT id,def FROM dict WHERE word=? AND id!=?''',(entry[1],entry[0]))
            dups = self.c.fetchall()
            defn = entry[2]
            for dup in dups:
                self.c.execute('''DELETE FROM dict WHERE id=?''', (dup[0],))
                self.c.execute('''UPDATE synonyms SET wid=? WHERE wid=?''', (entry[0],dup[0]))
                defn += dup[1]
            self.c.execute('''UPDATE dict SET def=? WHERE id=?''',(defn,entry[0]))
        print "Concatenating ambivalent entries %5d of %5d... done." % (no,no)

    def write(self,fname):
        if fname[-6:].lower() == "sqlite":
            try:
                os.unlink(fname)
            except OSError: pass
            outfile_db = sqlite3.connect(fname)
            outfile_db.text_factory = str
            query = "".join(line for line in self.conn.iterdump())
            print "Writing to output file...",
            outfile_db.executescript(query)
        else:
            _,self.g.data = dictFromSqlite(self.c)
            print "Writing to output file...",
            self.g.write(fname)
        print "done."

def print_warning(msg):
    print "W: %s" % msg

def dictFromSqlite(curs):
    info = {}; data = []
    for row in curs.execute('''SELECT key,value FROM info'''):
        info[row[0]]=row[1]
    curs.execute('''SELECT word,def,id FROM dict''')
    rows = curs.fetchall(); no = len(rows)
    syns = curs.execute('''SELECT syn,wid FROM synonyms''').fetchall()
    syn_list = {x[2]:[] for x in rows}
    [syn_list[syn[1]].append(syn[0]) for syn in syns]
    if "sametypesequence" in info:
        defiFormat = info["sametypesequence"]
    else:
        defiFormat = "h"
    print("Format is %s" % defiFormat)
    for i,row in enumerate(rows):
        sys.stdout.write("Writing entry %5d of %5d...\r" % (i,no))
        sys.stdout.flush()
        data.append((row[0],row[1],{'defiFormat': defiFormat, 'alts':syn_list[row[2]]}))
    print "Writing entry %5d of %5d...done." % (no,no)
    return (info,data)

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
            if a not in alts and a != entry[0]:
                alts.append(a)
        except UnicodeWarning:
            # ignore for now...
            # print "Provided data is not encoded in utf-8: %s" % (entry[0],)
            pass

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

