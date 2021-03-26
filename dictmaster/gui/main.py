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

def stringify_children(node):
    tostring = lambda x: etree.tostring(x, encoding="unicode", pretty_print=True)
    parts = ([node.text] + list(
                chain(*(
                    [c.text, tostring(c), c.tail] for c in node.getchildren()
                ))
            ) + [node.tail])
    # filter removes possible Nones in texts and tails
    return ''.join(filter(None, parts))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
gi.require_version('GtkSource', '3.0')
from gi.repository import Gtk, Gdk, WebKit2, GLib, GtkSource, GObject
GObject.type_register(GtkSource.View)
GObject.type_register(WebKit2.WebView)

from pkg_resources import resource_filename

from dictmaster.stages import STAGES
from dictmaster.util import load_plugin, PLUGINS, FLAGS

DB_DESCR = [
    ["info",    "key",  "value","value" ],
    ["raw",     "uri",  "flag", "data"  ],
    ["synonyms","syn",  "wid",  "syn"   ],
    ["dict",    "word", "rawid","def"   ]
]

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <style>
  img {
    max-width: 100%;
  }
  </style>
  <title>Dictionary entry</title>
</head>
<body>BODY</body>
</html>
"""

class gui_main(object):
    plugin = None

    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file(resource_filename("dictmaster.gui", "main.glade"))
        builder.connect_signals(self)

        self.win = builder.get_object("window1")
        screen = Gdk.Screen.get_default()
        self.geometry   = (screen.width()/640.0,screen.height()/480.0,\
                           int(screen.width()*0.5),int(screen.height()*0.5))
        width = int(600.0*max(1,self.geometry[0]))
        height = int(400.0*max(1,self.geometry[1]))
        self.win.set_size_request(width, height)

        self.views = {
            "empty": builder.get_object("emptyview"),
            "progress": builder.get_object("progressview"),
            "config": builder.get_object("configview")
        }

        self.db_cb_tables = builder.get_object("cb_tables")
        self.db_store = builder.get_object("store_entries")
        self.db_changing = False
        self.db_labels = [
            [builder.get_object("lb_db_%s" % k),
             builder.get_object("lb_db_%s_val" % k)]
            for k in ["id","key","flag"]
        ]
        self.db_dataview = builder.get_object("dataview")
        self.db_rawview = builder.get_object("rawview")
        self.db_srcview = builder.get_object("srcview")
        self.db_srcscrolled = builder.get_object("srcscrolled")
        self.db_htmlscrolled = builder.get_object("htmlscrolled")
        self.db_htmlview = builder.get_object("htmlview")
        for v in (self.db_srcview, self.db_rawview):
            buf = v.get_buffer()
            lm = GtkSource.LanguageManager.get_default()
            lang = lm.guess_language(None, "text/html")
            buf.set_language(lang)

        self.lb_path = builder.get_object("lb_config_path")
        self.ey_name = builder.get_object("ey_name")
        self.ck_enumerate = builder.get_object("ck_enumerate")
        self.cb_stages = builder.get_object("cb_stages")

        self.cb_plugins = builder.get_object("cb_plugins")
        for i,p in enumerate(PLUGINS):
            self.cb_plugins.append(str(i+1), p)

        self.console = builder.get_object("console")
        self.console_last = ""

        self.win.show_all()
        self.views["progress"].hide()
        self.views["config"].hide()
        Gtk.main()

    def broadcast(self, msg, overwrite=False):
        buf = self.console.get_buffer()
        if overwrite:
            pos = buf.props.cursor_position
            start = buf.get_iter_at_offset(pos - len(self.console_last))
            end = buf.get_iter_at_offset(pos)
            buf.delete(start, end)
        if msg[-1] != "\n":
            msg = msg + "\n"
        self.console_last = msg
        buf.insert_at_cursor(msg)

    def cb_plugins_changed_cb(self, widget, data=None):
        chosen = widget.get_active()
        if chosen > 0:
            self.plugin = load_plugin(PLUGINS[chosen-1])
            self.lb_path.set_text(self.plugin.output_directory)
            self.ey_name.set_text(self.plugin.dictname)
            self.views["progress"].hide()
            self.views["empty"].hide()
            self.views["config"].show()
            self.db_cb_tables.emit("changed")

    def bt_runstage_clicked_cb(self, widget, data=None):
        i = self.cb_stages.get_active()
        if i != 0:
            if self.plugin.stages[STAGES[i-1]] is None: return
            self.plugin.curr_stage = self.plugin.stages[STAGES[i-1]]
        self.views["progress"].show()
        self.views["config"].hide()
        buf = self.console.get_buffer()
        buf.set_text("")
        self.plugin.start()
        while self.plugin.is_alive():
            self.broadcast(self.plugin.progress(), True)
            while Gtk.events_pending():
                Gtk.main_iteration()
            self.plugin.join(0.1)
        self.cb_plugins.emit("changed")

    def bt_resetstage_clicked_cb(self, widget, data=None):
        i = self.cb_stages.get_active()
        if i == 0: # reset all
            self.plugin.reset()
        elif self.plugin.stages[STAGES[i-1]] is not None:
            self.plugin.stages[STAGES[i-1]].reset()
        self.cb_plugins.emit("changed")

    def bt_optimize_clicked_cb(self, widget, data=None):
        self.plugin.optimize_data(self.ck_enumerate.get_active())
        self.cb_plugins.emit("changed")
        self.db_cb_tables.emit("changed")

    def bt_export_clicked_cb(self, widget, data=None):
        self.plugin.export()

    def bt_interrupt_clicked_cb(self, widget, data=None):
        self.plugin.cancel()

    def cb_tables_changed_cb(self, widget, data=None):
        i = widget.get_active()
        for j in [1,2]:
            self.db_labels[j][0].set_text("%s:" % DB_DESCR[i][j])
            self.db_labels[j][1].set_text("")
        self.db_labels[0][1].set_text("")
        self.db_rawview.get_buffer().set_text("")

        self.db_changing = True
        self.db_store.clear()
        conn = sqlite3.connect(self.plugin.output_db)
        curs = conn.cursor()
        entries = curs.execute('''
            SELECT id, %s FROM %s
        ''' % (DB_DESCR[i][1],DB_DESCR[i][0])).fetchall()
        for e in entries:
            self.db_store.insert_with_valuesv(-1, [0,1],
                [e[0],GLib.markup_escape_text(e[1])])
        self.db_changing = False

        if i == 0:
            self.db_dataview.hide()
            self.db_htmlscrolled.hide()
        elif i == 1:
            self.db_dataview.show()
            self.db_srcscrolled.hide()
            self.db_htmlscrolled.hide()
        else:
            self.db_dataview.show()
            self.db_srcscrolled.show()
            self.db_htmlscrolled.show()

    def db_select_cb(self, sel, data=None):
        if self.db_changing: return
        i = self.db_cb_tables.get_active()
        rows = sel.get_selected_rows()
        if len(rows[1]) > 0:
            id = rows[0][rows[1][0]][0]
            conn = sqlite3.connect(self.plugin.output_db)
            curs = conn.cursor()
            entry = curs.execute('''
                SELECT %s,%s,%s FROM %s WHERE id=?
            ''' % (tuple(DB_DESCR[i][1:])+(DB_DESCR[i][0],)), (id,)).fetchone()
            self.db_labels[0][1].set_text(str(id))
            self.db_labels[1][1].set_text(entry[0])
            raw = ""
            src = ""
            if i == 0:
                self.db_labels[2][1].set_text(entry[1])
            elif i == 1:
                flags = []
                for name,flag in FLAGS.items():
                    if flag & entry[1] > 0:
                        flags.append(name)
                self.db_labels[2][1].set_text(", ".join(flags))
                raw = "" if entry[2] is None else entry[2]
            else:
                self.db_labels[2][1].set_text(str(entry[1]))
                if i == 2:
                    entry = curs.execute('''
                        SELECT %s,%s,%s FROM %s WHERE id=?
                    ''' % (tuple(DB_DESCR[3][1:])+(DB_DESCR[3][0],)),
                    (entry[1],)).fetchone()
                if entry is not None:
                    src = entry[2]
                    raw = curs.execute('''
                        SELECT %s FROM %s WHERE id=?
                    ''' % (DB_DESCR[1][3],DB_DESCR[1][0]),
                    (entry[1],)).fetchone()[0]
                    raw = "" if raw is None else raw
            raw = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            self.db_rawview.get_buffer().set_text(raw)
            self.db_srcview.get_buffer().set_text(src)
            resdir = os.path.join(self.plugin.output_directory, "res")
            resdir = "file://%s/" % os.path.abspath(resdir)
            self.db_htmlview.load_html(BASE_HTML.replace("BODY", src), resdir)

    def destroy_cb(self, widget, data=None):
        Gtk.main_quit()
