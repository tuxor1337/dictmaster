
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, Gdk, WebKit2

from pkg_resources import resource_filename

local_uri = 'webbrowser://'
initial_html = '''\
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>WebView Recipe</title>
</head>
<body>
<p>Some links:</a>
<ul>
    <li><a href="http://www.gtk.org/">Gtk+</a></li>
    <li><a href="https://glade.gnome.org/">Glade</a></li>
    <li><a href="http://www.python.org/">Python</a></li>
</ul>
</body>
</html>
'''

class gui_main(object):
    def __init__(self):
        self.ready    = False

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

        entries = builder.get_object("store_entries")
        entries.append([0,"abc"])
        entries.append([1,"def"])
        entries.append([2,"dbc"])
        entries.append([3,"eef"])
        entries.append([4,"gbc"])
        entries.append([5,"vef"])

        view = builder.get_object("dataview")
        self.dataview = WebKit2.WebView()
        view.add_with_viewport(self.dataview)
        self.dataview.load_html(initial_html, local_uri)

        self.win.show_all()
        Gtk.main()

    def destroy_cb(self, widget, data=None):
        Gtk.main_quit()
