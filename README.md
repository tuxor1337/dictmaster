dictmaster
==========

Fetch dictionary data from several offline and online sources.

The dictionaries are prettified and automatically converted to stardict format.
The input format might be some XML or HTML format.
Zipped data is also supported and there is basic support for Babylon dictionaries.

Supported dictionary sources
----------------------------

At the moment you can extract dictionary data from any Babylon dictionary (`*.bgl`)
available on your computer.
Furthermore `dictmaster` is able to retrieve data from the following online sources:

* Digitales Wörterbuch der deutschen Sprache (http://www.dwds.de)
* Georges, Pape (http://www.zeno.org)
* Folkets Lexikon (http://folkets-lexikon.csc.kth.se/folkets/)
* XMLittré (http://www.littre.org)
* Dictionnaire de l'Académie Française (https://academie.atilf.fr/, **plugin broken**)
* Diccionario de la lengua española (http://lema.rae.es/drae/)
* GNU Collaborative International Dictionary of English (http://gcide.gnu.org.ua/)
* Online Etymology Dictionary (http://etymonline.com)
* American Heritage Dictionary (https://ahdictionary.com)
* Oxford Lexico English Dictionary Online (http://lexico.com)
* Ó Dónaill’s Irish-English Dictionary (https://www.teanglann.ie/en/fgb/)
* CIA World Factbook (https://www.cia.gov/the-world-factbook/about/archives/)
* There is basic support for BEOLINGUS (http://dict.tu-chemnitz.de/) and dict.cc
(http://www.dict.cc/), but the algorithms used in dictmaster don't perform well
with the csv-like file structure and the Stardict output format is not really
suitable for this kind of dictionary structure.

Dictionaries that are easily accessible and might be integrated in future versions are
listed in the following blog post: http://tovotu.de/blog/536-Kostenlose-Wrterbcher-fr-die-Offlinenutzung/

How to get started
------------------

Note that, since 2021, `dictmaster` requires Python 3.7 or higher (due to third-party dependencies).

First, clone this repository and make sure you execute the following
commands from the root directory of the repository:

    git clone https://framagit.org/tuxor1337/dictmaster
    cd ./dictmaster
    pip3 install --user wheel
    pip3 install --user -e ./

Running `dictmaster` then starts a graphical user interface if your operating system comes with GTK3 and `PyGObject`.
Otherwise, the software will fall back to using the command line interface.
Actually, many features are exclusively available through the command line which is used as follows:

    dictmaster PLUGIN_NAME

You find available plugins in the `dictmaster/plugins` directory.
Some plugins need additional plugin-specific option strings that you can provide
with the `--popts OPTIONS` parameter, e.g.:

    dictmaster zeno --popts "Pape-1880"

If a plugin asks for a word list file have a look into the `thirdparty`
directory where some lists are provided.

Your dictionary data will be saved (by default) to `data/PLUGIN_NAME/stardict.*`
in stardict format.
(Note that for some dictionaries the directory `data/PLUGIN_NAME/res` is also needed.)

Interrupting the running process with Ctrl+C should gracefully cancel the process.
From most parts of the download stage, dictmaster is able to recover and continue
at a later time from where it stopped last time.
If you want to force redownloading the data add the parameter `--reset` to
your command line.

Troubleshooting
---------------

### Setup fails with `Not Found for url: https://pypi.org/simple/pyglossary/`

Please make sure you use the most recent version of `pip3`, e.g., by running

    sudo pip3 install --upgrade pip
    hash -r

Then, follow the setup instructions given above.

### In the console, there is output `Invalid plugin directory: ...`

This is not an error message, but verbose debugging output by the module
PyGlossary that we cannot suppress. Please ignore this.

### The plugin XY doesn't work (returns empty result or gibberish).

Since downloading of the dictionary data is discouraged by most dictionary
services, they change their format from time to time and we can't keep track
of all the changes. That's why many of dictmaster's plugins are defunct by now.

We don't remove broken plugins from the repository because, in many cases,
functionality can be easily restored with minor changes to the code.

Plugins that are known to be broken: `dwds` (please use `dwds-panel` instead), `acadfran`

Limitations
-----------

If you want to write a new plugin, try to start from one of the existing ones.
Of course, it is mandatory to have basic understanding of Python code and probably
HTML (since most online dictionaries come in HTML format). But apart from that I can
just encourage you to start fiddling around. It's not that hard. Open an issue
or contact me directly if you run into problems.

Todo list
---------

- GUI: Choose popts and output directory
- GUI: Edit existing dictionary data or customize post-processing

Legal issues
------------

Keep in mind that you might not be the copyright holder for the data you download with
the help of dictmaster. While dictmaster does not circumvent any copyright protection or
digital rights management, some kinds of massive data aggregation itself might be illegal
in some jurisdictions. Therefore, the dictionaries created with dictmaster are not freely
distributable in most cases - personal use should be okay though.
