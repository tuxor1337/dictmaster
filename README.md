dictmaster
==========

A simple tool that automatically fetches dictionary data from
different offline and online sources.
The dictionaries are prettified and automatically converted to stardict
format.
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
* Dictionnaire de l'Académie Française (http://atilf.atilf.fr/academie.htm)
* Diccionario de la lengua española (http://lema.rae.es/drae/)
* GNU Collaborative International Dictionary of English (http://gcide.gnu.org.ua/)
* Online Etymology Dictionary (http://etymonline.com)
* American Heritage Dictionary (https://ahdictionary.com)
* Oxford Dictionaries Online (http://oxforddictionaries.com)
* Ó Dónaill’s Irish-English Dictionary (https://www.teanglann.ie/en/fgb/)
* CIA World Factbook (https://www.cia.gov/library/publications/the-world-factbook/)
* There is basic support for BEOLINGUS (http://dict.tu-chemnitz.de/) and dict.cc
(http://www.dict.cc/), but the algorithms used in dictmaster don't perform well
with the csv-like file structure and the Stardict output format is not really
suitable for this kind of dictionary structure.

Dictionaries that are easily accessible and might be integrated in future versions are
listed in the following blog post: http://tovotu.de/blog/536-Kostenlose-Wrterbcher-fr-die-Offlinenutzung/

How to get started
------------------

First, clone this repository and make sure you execute the following
commands from the root directory of the repository:

    git clone https://framagit.org/tuxor1337/dictmaster
    cd ./dictmaster

All the conversion to stardict is done with the help of pyglossary
(https://github.com/ilius/pyglossary). Therefore, before you start you have
to pull in the third party code with

    git submodule update --init

and install using

    pip3 install -e ./

Running `dictmaster` then starts a graphical user interface.
However, many features are exclusively available through the command line:

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
the help of dictmaster. I'm not even sure whether this kind of data aggregation itself is legal.
However, the stardict dictionaries created with dictmaster won't be freely distributable
in most cases - personal use should be okay though.
