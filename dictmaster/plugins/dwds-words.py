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
from urllib.request import unquote

from pyquery import PyQuery as pq

from dictmaster.util import FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.urlfetcher import UrlFetcher

class Plugin(BasePlugin):
    dictname = "DWDS Wordlist"

    def __init__(self, dirname, popts=[]):
        super().__init__(dirname)
        self.stages['UrlFetcher'] = DwdsUrlFetcher(self)

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(a, FLAGS["URL_FETCHER"]) for a in range(7030)])

class DwdsUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data, uri):
            d = pq(data)
            links = d("div.container-fluid > ul > li > a")
            links = [d(l).attr("href") for l in links]
            prefix = "https://www.dwds.de/wb/"
            return [l[len(prefix):] for l in links]

        def parse_uri(self,uri):
            return "https://www.dwds.de/backlist?p=%s"%uri

    def run(self):
        UrlFetcher.run(self)
        conn = sqlite3.connect(self.plugin.output_db)
        curs = conn.cursor()
        uris = curs.execute('''
            SELECT uri FROM raw
            WHERE flag & ? > 0
        ''', (FLAGS["RAW_FETCHER"],)).fetchall()
        conn.close()
        path = os.path.join(self.plugin.output_directory, "wordlist.txt")
        with open(path,"w") as f:
            f.write("\n".join([unquote(u[0]) for u in uris]))

