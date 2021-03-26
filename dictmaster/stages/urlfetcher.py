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

import sqlite3

from dictmaster.util import FLAGS
from dictmaster.stages.fetcher import Fetcher

class UrlFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        _output_flag = FLAGS["RAW_FETCHER"]
        def fetch_uri(self, rawid, uri):
            self._i += 1
            data = self.download_retry(self.parse_uri(uri), self.postdata,
                                       sleep=self.sleep)
            if self._canceled: return
            for url in self.filter_data(data, uri):
                self._queue.put((None, url, None, self._output_flag))
            self._queue.put((rawid, uri, None, self._flag))

    def __init__(self, *args, **kwargs):
        super(UrlFetcher, self).__init__(*args, **kwargs)
        self._flag = FLAGS["URL_FETCHER"]

    def progress(self):
        return Fetcher.progress(self).replace("Fetching","Fetching URLs")

    def reset(self):
        conn = sqlite3.connect(self.plugin.output_db)
        c = conn.cursor()
        c.execute('''
            DELETE FROM raw WHERE flag & ? == 0
        ''', (FLAGS["URL_FETCHER"],))
        c.execute('''
            UPDATE raw SET flag = flag & ~?
            WHERE flag & ? > 0
        ''', (FLAGS["FETCHED"], FLAGS["URL_FETCHER"]))
        conn.commit()
        conn.close()

