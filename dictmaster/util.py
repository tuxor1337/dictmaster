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

import sys
import time
import os
import errno
import sqlite3
import random

try:
    from urllib2 import URLError, HTTPError
    import urllib2, httplib
except ImportError:
    from urllib.error import URLError, HTTPError
    import urllib.request as urllib2
    import http.client as httplib

import pkgutil
import importlib

import unicodedata

from pyquery import PyQuery as pq
from lxml import etree

import threading

import dictmaster.plugins
pth = dictmaster.plugins.__path__
PLUGINS = [name for _,name,_ in pkgutil.iter_modules(pth)]

FLAGS = {
    "FETCHED": 1 << 0,
    "PROCESSED": 1 << 1,
    "RAW_FETCHER": 1 << 2,
    "URL_FETCHER": 1 << 3,
    "ZIP_FETCHER": 1 << 4,
    "FILE": 1 << 5,
    "MEMORY": 1 << 6,
    "DUPLICATE": 1 << 7
}

URL_HEADER = {
    "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0",
}

def warn_nl(msg):
    sys.stdout.write("\r\n{}\n".format(msg))
    sys.stdout.flush()

def mkdir_p(path):
    try: os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path): pass
        else: raise

def load_plugin(plugin_name, popts=None, dirname=""):
    if dirname == "": dirname = "data/%s/" % plugin_name
    try:
        plugin_module = importlib.import_module("dictmaster.plugins.%s" % plugin_name)
        importlib.reload(plugin_module)
        if popts is None:
            pthread = plugin_module.Plugin(dirname)
        else:
            pthread = plugin_module.Plugin(dirname, popts=popts)
    except ImportError as e:
        print(e.args); pthread = None
    return pthread

def words_to_db(word_file, cursor, word_codec):
    wordlist = [w.decode(word_codec[0]).strip() for w in open(word_file,"rb")]
    tmplist = []
    for w in wordlist:
        try: tmplist.append(urllib2.quote(w.encode(word_codec[1]), ""))
        except: print("Codec error reading word file:", w); break
    cursor.executemany('''
        INSERT INTO raw (uri,flag) VALUES (?,?)
    ''', [(w, FLAGS["RAW_FETCHER"]) for w in tmplist])

def find_synonyms(term, definition, alts):
    greek_alph = u'αιηωυεοςρτθπσδφγξκλζχψβνμ'
    latin_alph = u'aihwueosrtqpsdfgcklzxybnm'

    def add_alt(alts, a):
        if a not in alts and a != term: alts.append(a)

    def add_greek_alt(alts, a):
        orig_a = a
        a = remove_accents(a).lower()
        add_alt(alts, a)
        add_alt(alts, a.replace("-",""))
        for x,y in zip(greek_alph,latin_alph):
            a = a.replace(x,y)
        add_alt(alts,a)
        add_alt(alts,a.replace("-",""))

    add_greek_alt(alts,term)
    for delimiter in [",","#",";"]:
        [add_greek_alt(alts,c.strip()) for c in term.split(delimiter)]

    return alts

def remove_accents(input_str):
    if isinstance(input_str, bytes):
        input_str = input_str.decode("utf-8")
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def html_container_filter(container, charset="utf-8", bad_content=None):
    def tmp_func(fthread, data, uri):
        if data == None or len(data) < 2: return None
        encoded_str = data.decode(charset).encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(encoded_str, parser=parser))
        if len(doc(container)) == 0: return None
        elif bad_content != None and doc(container).text() == bad_content:
            return None
        else: return doc(container).html()
    return tmp_func

"""
The CancelableThread is a convenience class that all threads in dictmaster
are instances of. Apart from the cancel() method it provides convenient access
to a (cancelable and feedback providing) download method.
"""
class CancelableThread(threading.Thread):
    _canceled = False
    _download_status = ""

    def __init__(self):
        super(CancelableThread, self).__init__()
        self.daemon = True

    def progress(self):
        if self._canceled: return "Sleeping..."
        return "Active..."

    def cancel(self): self._canceled = True

    def _chunk_download(self, response, total_size):
        data, chunk_size = b"", 2**16
        while True:
            if self._canceled:
                data = None
                break
            chunk = response.read(chunk_size)
            if not chunk: break
            data += chunk
            self._download_status = "Downloading... {: 6d} of {: 6d} KB".format(
                int(len(data)/1000), int(total_size/1000)
            )
        self._download_status = ""
        return data

    def download_retry(self, url, params=None):
        if self._canceled: return None
        try:
            req = urllib2.Request(url, data=params, headers=URL_HEADER)
            try: response = urllib2.urlopen(req, timeout=60)
            except HTTPError as e:
                if e.code in [403,404]: return ""
                else: raise
            total_size = response.info()['Content-Length']
            if total_size != None: total_size = int(total_size.strip())
            else: total_size = 0
            if total_size > 5*2**16:
                print("\nDownloading large file ({:.2f} MB)!".format(total_size/1000000.0))
                data = self._chunk_download(response, total_size)
            else: data = response.read()
            return data
        except (URLError, httplib.BadStatusLine):
            warn_nl("Connection to %s failed. Retrying..." % url)
            time.sleep(random.uniform(1.0,3.0))
            return self.download_retry(url, params)
        except Exception as e:
            warn_nl("Error on %s: '%s'. Retrying..." % (url, e))
            time.sleep(random.uniform(1.0,3.0))
            return self.download_retry(url, params)

