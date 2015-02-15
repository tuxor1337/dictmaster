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

At the moment you can fetch dictionary data from any Babylon dictionary (`*.bgl`)
available on your computer.
Furthermore `dictmaster` is able to retrieve data from the following online sources:

* Online Etymology Dictionary (http://etymonline.com)
* Georges, Pape (http://wwww.zeno.org)
* Dictionnaire de l'Académie Française (http://atilf.atilf.fr/academie.htm),
* Folkets Lexikon (http://folkets-lexikon.csc.kth.se/folkets/)
* XMLittré (http://www.littre.org)
* American Heritage Dictionary (https://ahdictionary.com)
* Diccionario de la lengua española (http://lema.rae.es/drae/)
* GNU Collaborative International Dictionary of English (http://gcide.gnu.org.ua/)
* CIA World Factbook (https://www.cia.gov/library/publications/the-world-factbook/)
* There is basic support for BEOLINGUS (http://dict.tu-chemnitz.de/) and dict.cc
(http://www.dict.cc/), but the algorithms used in dictmaster don't perform well
with the csv-like file structure and the Stardict output format is not really
suitable for this kind of dictionary structure.

Dictionaries that are easily accessible and might be integrated in future versions are
listed in the following blog post: http://tovotu.de/blog/536-Kostenlose-Wrterbcher-fr-die-Offlinenutzung/

How to get started
------------------

All the conversion to stardict is done with the help of pyglossary
(https://github.com/ilius/pyglossary). Before you start you have
to pull in the third party code with

    git submodule update --init

Start the tool with:

    ./dictmaster.py PLUGIN_NAME

You find available plugins in the `dictmaster/plugins` directory.
Some plugins need addition plugin-specific option string that you can provide
with the `--popts OPTION` parameter, e.g.:

    ./dictmaster.py zeno --popts "Pape-1880"

If a plugin asks for a word list file have a look into the `thirdparty` 
directory where some lists are provided.

Your dictionary data will be saved (by default) to `data/PLUGIN_NAME/stardict.*`
in stardict format.
(Note that for some dictionaries the directory `data/PLUGIN_NAME/res` is also needed.)

Interrupting the running process with Ctrl+C should gracely cancel the process.
From most parts of the download stage, dictmaster is able to recover and continue
at a later time from where it stopped last time.
If you want to force redownloading the data add the parameter `--reset` to
you command line.

Limitations
-----------

Even though this projects looks pretty modularized and extendible at first
glance, let me tell you that this is unfortunately not the case - yet.
For now, you really have to go through the code and understand what's happening
in order to write new plugins because there is no API documentation.
But if you still want to write a new plugin, try to start from one of the
existing ones.

Todo list
---------

- Extendibility: Implement some kind of standard procedure for adding new plugins or at
least provide plugin templates that you can use if you wish to add new ones.
- Usability: A graphical user interface that guides you through the process.
- A way to edit existing (ready converted) dictionary data using some kind
of user interface.

Legal issues
------------

Keep in mind that you might not be the copyright holder for the data you download with
the help of dictmaster. I'm not even sure whether this kind of data aggregation itself is legal.
However, the stardict dictionaries created with dictmaster won't be freely distributable
in most cases - personal use should be okay though.
