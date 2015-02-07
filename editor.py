# -*- coding: utf-8 -*-

import sys, os

from pyglossary.glossary import Glossary
import re, sqlite3, unicodedata

import warnings
warnings.filterwarnings('error', category=UnicodeWarning)

class glossEditor(object):
    def __init__(self, gloss, db=None):
        self.g = gloss
        if db == None:
            self.conn = sqlite3.connect(":memory:")
            self.conn.text_factory = str
            self.c = self.conn.cursor()
            self.c.execute('''CREATE TABLE dict
                (id INTEGER PRIMARY KEY,
                wort TEXT, def TEXT)''');
            self.c.execute('''CREATE TABLE synonyms
                (id INTEGER PRIMARY KEY,
                wid INTEGER, syn TEXT)''');
            self.c.execute('''CREATE TABLE info
                (id INTEGER PRIMARY KEY,
                key TEXT, value TEXT)''');
            self.glossToDB()
        else:
            try:
                self.conn = sqlite3.connect(db)
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
                wort = edited[0]
                self.c.execute("INSERT INTO dict(wort,def) VALUES (?,?)",(wort,edited[1]))
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
        self.remove_dups()
        self.enumerate_dups()
        self.remove_dup_syns()

    def preview_entry(self,word):
        self.c.execute('''SELECT wid FROM synonyms WHERE syn LIKE ?''',(word+"%",))
        wids = self.c.fetchall()
        output = []
        for (wid,) in wids:
            self.c.execute('''SELECT wort,def FROM dict WHERE id=?''',(wid,))
            output.append(self.c.fetchone())
        return output

    def remove_empty(self):
        self.c.execute('''DELETE FROM synonyms WHERE syn="" OR syn=" "''')

    def remove_dups(self):
        dubs = self.c.execute('''SELECT id,wort,def
            FROM dict GROUP BY wort,def HAVING COUNT(*) > 1''').fetchall()
        no, i = len(dubs), 0
        for dbl in dubs:
            i += 1
            if i % 3 == 0:
                sys.stdout.write("Entferne doppelte Einträge %3d von %3d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''SELECT id FROM dict WHERE wort=? AND def=?''',(dbl[1],dbl[2]))
            old_ids = self.c.fetchall()
            for old in old_ids:
                self.c.execute('''UPDATE synonyms SET wid=? WHERE wid=?''',(dbl[0],old[0]))
            self.c.execute('''DELETE FROM dict WHERE wort=? AND def=? AND id!=?''',(dbl[1],dbl[2],dbl[0]))
        print "Entferne doppelte Einträge %3d von %3d... done." % (no,no)

    def remove_dup_syns(self):
        dubs = self.c.execute('''SELECT id,wid,syn
            FROM synonyms GROUP BY wid,syn HAVING COUNT(*) > 1''').fetchall()
        no, i = len(dubs), 0
        for dbl in dubs:
            i += 1
            if i % 3 == 0:
                sys.stdout.write("Entferne doppelte Einträge %3d von %3d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''DELETE FROM synonyms WHERE wid=? AND syn=? AND id!=?''',(dbl[1],dbl[2],dbl[0]))
        print "Entferne doppelte Einträge %3d von %3d... done." % (no,no)

    def enumerate_dups(self):
        self.c.execute('''SELECT wort FROM dict GROUP BY wort HAVING COUNT(*) > 1''')
        dubs = self.c.fetchall()
        no = len(dubs)
        i = 0
        for dbl in dubs:
            i += 1
            if i % 7 == 0:
                sys.stdout.write("Nummeriere mehrdeutige Einträge %5d von %5d...\r" % (i,no))
                sys.stdout.flush()
            self.c.execute('''SELECT id FROM dict WHERE wort=?''',(dbl[0],))
            for j,wid in enumerate(self.c.fetchall()):
                self.c.execute('''INSERT INTO synonyms(wid,syn)
                                            VALUES (?,?)''',(wid[0],dbl[0]))
                self.c.execute('''UPDATE dict SET wort=? WHERE id=?''',("%s(%d)" % (dbl[0],j+1),wid[0]))
        print "Nummeriere mehrdeutige Einträge %5d von %5d... done." % (no,no)

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
    curs.execute('''SELECT wort,def,id FROM dict''')
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

