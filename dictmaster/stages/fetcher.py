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
import random
import sqlite3
import time

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

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

    def __init__(self, no, uris, queue, flag, postdata=None,
                 pause=None, **kwargs):
        super().__init__(**kwargs)
        self.uris, self.postdata = uris, postdata
        self.no = no
        self.pause = pause
        self._queue = queue
        self._flag = flag | FLAGS["FETCHED"]
        self._canceled = len(self.uris) == 0

    def filter_data(self, data, uri): return data
    def parse_uri(self, uri): return uri

    def fetch_uri(self, rawid, uri):
        data = self.download_retry(self.parse_uri(uri), self.postdata)
        if self._canceled: return
        data = self.filter_data(data, uri)
        self._queue.put((rawid, uri, data, self._flag))
        self._i += 1

    def run(self):
        for rawid, uri in self.uris:
            if self._canceled:
                break
            self.fetch_uri(rawid, uri)
            if self.pause is not None:
                sleep_time = random.uniform(*self.pause)
                while sleep_time > 0:
                    if self._canceled:
                        break
                    time.sleep(min(sleep_time, 1))
                    sleep_time -= 1

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
        postdata=None,
        pause=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._subthreads = [None]*threadcnt
        self.pause = pause
        self.plugin = plugin
        self.postdata = postdata

    def init_queue(self):
        self._queue = RawDbQueue(self.plugin.output_db)

    def init_subthreads(self, uris):
        self.init_queue()
        self._subthreads = self._subthreads[:len(uris)]
        for i in range(len(self._subthreads)):
            uri_portion = uris[i::len(self._subthreads)]
            self._subthreads[i] = self.FetcherThread(
                no=i,
                uris=uri_portion,
                queue=self._queue,
                flag=self._flag,
                postdata=self.postdata,
                pause=self.pause,
                sleep=self.sleep
            )

    def progress(self):
        if None in self._subthreads: return "Initializing threads..."
        if self._canceled: return self._queue.progress()
        prog = "Fetching... "
        sub_p = [s.progress() for s in self._subthreads]
        if all(type(p) == float for p in sub_p):
            percentage = 100*self._fetched
            percentage += (1-self._fetched)*float(sum(sub_p))/len(sub_p)
            prog += "{:.2f}%".format(percentage)
        elif any(type(p) == str and p[:11] == "Downloading" for p in sub_p):
            for p in sub_p:
                if type(p) == str and p[:11] == "Downloading":
                    prog = p
                    break
        else:
            for i,p in enumerate(sub_p):
                prog += "{}:{} ".format(i, p[:13])
        return prog

    def get_unfetched_uris(self):
        conn = sqlite3.connect(self.plugin.output_db)
        curs = conn.cursor()
        n_fetched = curs.execute('''
            SELECT COUNT(*) FROM raw WHERE flag & :0 == :0
        ''', [FLAGS["FETCHED"] | self._flag]).fetchone()[0]
        uris = curs.execute('''
            SELECT id, uri FROM raw
            WHERE flag & ? == 0
            AND flag & ? > 0
        ''', (FLAGS["FETCHED"], self._flag)).fetchall()
        conn.close()
        return n_fetched, uris

    def run(self):
        self._fetched, uris = self.get_unfetched_uris()
        self._fetched = float(self._fetched) / (len(uris) + self._fetched)
        if self._canceled or len(uris) == 0: return
        self.init_subthreads(uris)
        self._queue.start()
        [s.start() for s in self._subthreads]
        [s.join() for s in self._subthreads]
        self._queue.cancel()
        self._queue.join()
        if self._canceled: return
        # restart in case some uris couldn't be fetched due to problems
        self.run()

    def reset(self):
        conn = sqlite3.connect(self.plugin.output_db)
        c = conn.cursor()
        c.execute('''
            UPDATE raw SET flag = flag & ~?
            WHERE flag & ? == 0
        ''', (FLAGS["FETCHED"], FLAGS["URL_FETCHER"]))
        conn.commit()
        conn.close()

    def cancel(self):
        CancelableThread.cancel(self)
        [s.cancel() for s in self._subthreads]
        self._queue.cancel()

class ZipFetcher(Fetcher):
    class FetcherThread(FetcherThread):
        def fetch_uri(self, rawid, uri):
            data = self.download_retry(self.parse_uri(uri), self.postdata)
            if self._canceled: return
            path = self.to_file(data)
            self._queue.put((rawid, uri, path, self._flag))
            self._i += 1

    def __init__(self, plugin, postdata=None):
        super().__init__(plugin,threadcnt=1,postdata=postdata)
        self._flag = FLAGS["ZIP_FETCHER"]
        def to_file(fthread, data):
            zdirname = os.path.join(self.plugin.output_directory, "zip")
            path = os.path.join(zdirname, "{}_{}".format(fthread.no, fthread._i))
            with open(path, "wb") as f: f.write(data)
            return path
        self.FetcherThread.to_file = to_file
