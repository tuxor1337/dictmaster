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
import shutil
import sqlite3
import zipfile
import glob

from dictmaster.util import mkdir_p, CancelableThread, FLAGS

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
                        with open(dest, 'wb') as f: f.write(z.read(n))
                    c.execute('''
                        INSERT INTO raw (uri, flag)
                        VALUES (?,?)
                    ''', (dest, FLAGS["FILE"]))
                for n in filter(self.zfile_resfilter, z.namelist()):
                    dest = os.path.join(resdirname, os.path.basename(n))
                    with open(dest, 'wb') as f: f.write(z.read(n))
            c.execute('''
                UPDATE raw
                SET flag=?
                WHERE id=?
            ''', (flag | FLAGS["PROCESSED"], rawid))
            if self._canceled: break
        conn.commit()
        conn.close()

    def reset(self):
        uzdirname = os.path.join(self.plugin.output_directory, "raw")
        resdirname = os.path.join(self.plugin.output_directory, "res")
        for dn in [uzdirname,resdirname]:
            if os.path.exists(dn):
                shutil.rmtree(dn)
            mkdir_p(dn)

        conn = sqlite3.connect(self.plugin.output_db)
        c = conn.cursor()
        c.execute('''
            DELETE FROM raw WHERE flag & ? > 0
        ''', (FLAGS["FILE"],))
        c.execute('''
            UPDATE raw SET flag = flag & ~:nonflag
            WHERE flag & :flag == :flag
        ''', {
            "flag": FLAGS["ZIP_FETCHER"] | FLAGS["FETCHED"],
            "nonflag": FLAGS["PROCESSED"]
        })
        conn.commit()
        conn.close()
