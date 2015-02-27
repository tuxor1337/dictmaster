# -*- coding: utf-8 -*-

import os
import urllib2
import zipfile
import glob
import sqlite3

from dictmaster.util import mkdir_p, CancelableThread, FLAGS
from dictmaster.queue import RawDbQueue

DEFAULT_THREADCNT=6

class FetcherThread(CancelableThread):
    uris = []
    postdata = None
    no = 0

    _i = 0
    _flag = 0
    _queue = None

    def __init__(self, no, uris, queue, flag, postdata=None):
        super(FetcherThread, self).__init__()
        self.uris, self.postdata = uris, postdata
        self.no = no
        self._queue = queue
        self._flag = flag | FLAGS["FETCHED"]
        self._canceled = len(self.uris) == 0

    def filter_data(self, data): return data
    def parse_uri(self, uri): return uri

    def fetch_uri(self, rawid, uri):
        data = self.download_retry(self.parse_uri(uri), self.postdata)
        if self._canceled: return
        data = self.filter_data(data)
        self._queue.put((rawid, uri, data, self._flag))
        self._i += 1

    def run(self):
        for rawid, uri in self.uris:
            if self._canceled: break
            self.fetch_uri(rawid, uri)

    def progress(self):
        if self._download_status != "": return self._download_status
        if self._canceled: return ""
        return 100*self._i/float(len(self.uris))

class Fetcher(CancelableThread):
    class FetcherThread(FetcherThread): pass

    plugin = None
    postdata = None

    _subthreads = []
    _flag = FLAGS["RAW_FETCHER"]
    _queue = None
    _fetched = 0

    def __init__(self,
        plugin,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(Fetcher, self).__init__()
        self._subthreads = [None]*threadcnt
        self._queue = RawDbQueue(plugin.output_db)
        self.plugin = plugin
        self.postdata = postdata

    def init_subthreads(self, uris):
        self._subthreads = self._subthreads[:len(uris)]
        for i in range(len(self._subthreads)):
            uri_portion = uris[i::len(self._subthreads)]
            self._subthreads[i] = self.FetcherThread(
                no=i,
                uris=uri_portion,
                queue=self._queue,
                flag=self._flag,
                postdata=self.postdata
            )

    def progress(self):
        if None in self._subthreads: return "Initializing threads..."
        if self._canceled: return "Fetching... quit."
        prog = "Fetching... "
        sub_p = [s.progress() for s in self._subthreads]
        if all(type(p) == float for p in sub_p):
            percentage = 100*self._fetched
            percentage += (1-self._fetched)*float(sum(sub_p))/len(sub_p)
            prog += "{:.2f}%".format(percentage)
        elif any(p[:11] == "Downloading" for p in sub_p):
            for p in sub_p:
                if p[:11] == "Downloading": prog = p; break
        else:
            for i,p in enumerate(sub_p):
                prog += "{}:{} ".format(i, p[:13])
        return prog

    def run(self):
        conn = sqlite3.connect(self.plugin.output_db)
        curs = conn.cursor()
        self._fetched = curs.execute('''
            SELECT COUNT(*) FROM raw WHERE flag & :0 == :0
        ''', [FLAGS["FETCHED"] | self._flag]).fetchone()[0]
        uris = curs.execute('''
            SELECT id, uri FROM raw
            WHERE flag & ? == 0
            AND flag & ? > 0
        ''', (FLAGS["FETCHED"],self._flag)).fetchall()
        self._fetched = float(self._fetched)/(len(uris)+self._fetched)
        conn.close()
        if self._canceled or len(uris) == 0: return
        self.init_subthreads(uris)
        self._queue.start()
        [s.start() for s in self._subthreads]
        [s.join() for s in self._subthreads]
        self._queue.cancel()
        self._queue.join()

    def cancel(self):
        CancelableThread.cancel(self)
        [s.cancel() for s in self._subthreads]
        self._queue.cancel()

class UrlFetcher(Fetcher):
    class FetcherThread(FetcherThread):
        _output_flag = FLAGS["RAW_FETCHER"]
        def fetch_uri(self, rawid, uri):
            self._i += 1
            data = self.download_retry(self.parse_uri(uri), self.postdata)
            for url in self.filter_data(data):
                self._queue.put((None, url, None, self._output_flag))
            self._queue.put((rawid, uri, None, self._flag))

    def __init__(self,
        plugin,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(UrlFetcher, self).__init__(plugin,threadcnt,postdata)
        self._flag = FLAGS["URL_FETCHER"]

    def progress(self):
        return Fetcher.progress(self).replace("Fetching","Fetching URLs")

class ZipFetcher(Fetcher):
    class FetcherThread(FetcherThread):
        def fetch_uri(self, rawid, uri):
            data = self.download_retry(self.parse_uri(uri), self.postdata)
            if self._canceled: return
            path = self.to_file(data)
            self._queue.put((rawid, uri, path, self._flag))
            self._i += 1

    def __init__(self, plugin, postdata=None):
        super(ZipFetcher, self).__init__(plugin,threadcnt=1,postdata=postdata)
        self._flag = FLAGS["ZIP_FETCHER"]
        def to_file(fthread, data):
            zdirname = os.path.join(self.plugin.output_directory, "zip")
            path = os.path.join(zdirname, "{}_{}".format(fthread.no, fthread._i))
            with open(path, "w") as f: f.write(data)
            return path
        self.FetcherThread.to_file = to_file

class Unzipper(CancelableThread):
    plugin = None

    def __init__(self, plugin):
        super(Unzipper, self).__init__()
        self.plugin = plugin

    def progress(self):
        if self._canceled: return "Sleeping..."
        return "Unzipping..."

    def zfile_filter(self, zfilename): return True
    def zfile_resfilter(self, zfilename): return False

    def run(self):
        conn = sqlite3.connect(self.plugin.output_db)
        c = conn.cursor()
        zdirname = os.path.join(self.plugin.output_directory, "zip")
        uzdirname = os.path.join(self.plugin.output_directory, "raw")
        resdirname = os.path.join(self.plugin.output_directory, "res")
        read_cursor = conn.cursor()
        for rawid, zfile, flag in read_cursor.execute('''
            SELECT id, data, flag FROM raw
            WHERE flag & :flag == :flag
            AND flag & :nonflag == 0
        ''', {
            "flag": FLAGS["ZIP_FETCHER"] | FLAGS["FETCHED"],
            "nonflag": FLAGS["PROCESSED"]
        }):
            with zipfile.ZipFile(zfile) as z:
                for n in filter(self.zfile_filter, z.namelist()):
                    dest = os.path.join(uzdirname, n)
                    destdir = os.path.dirname(dest)
                    mkdir_p(destdir)
                    if not os.path.isdir(dest):
                        with open(dest, 'w') as f: f.write(z.read(n))
                    c.execute('''
                        INSERT INTO raw (uri, flag)
                        VALUES (?,?)
                    ''', (dest, FLAGS["FILE"]))
                for n in filter(self.zfile_resfilter, z.namelist()):
                    dest = os.path.join(resdirname, os.path.basename(n))
                    with open(dest, 'w') as f: f.write(z.read(n))
            c.execute('''
                UPDATE raw
                SET flag=?
                WHERE id=?
            ''', (flag | FLAGS["PROCESSED"], rawid))
            if self._canceled: break
        conn.commit()
        conn.close()

