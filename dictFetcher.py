#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import argparse, importlib, sys
    import fetcher, postprocessor, editor
    from postprocessor import Postprocessor

    from pyglossary.glossary import Glossary

    parser = argparse.ArgumentParser(description='Download and convert dictionaries.')
    parser.add_argument('plugin', metavar='FILE', type=str,
                            help='The plugin to use.')
    parser.add_argument('-o','--output', metavar='FILE', type=str,
                            help='Output file for conversion/changes.')
    parser.add_argument('--use-raw', action="store_true", default=False,
                    help=("Don't download anything. Use provided data."))
    parser.add_argument('--use-sqlite', action="store_true", default=False,
                    help=("Use preprocessed data in sqlite DB."))
    args = parser.parse_args()

    try:
        plugin_config = importlib.import_module("plugins.%s.config" % args.plugin)
        plugin = plugin_config.cfg
    except:
        sys.exit("Plugin not found or plugin broken.")

    ed = None
    if not args.use_sqlite:
        if not args.use_raw and "url" in plugin:
            fetcher.fetch(plugin)
        proc = Postprocessor(plugin)
        print("Postprocessing...")
        proc.run()
        print("...postprocessing done.")
        ed = proc.editor()

    if ed == None:
        g = Glossary()
        g.setInfo("bookname", plugin["dictname"])
        ed = editor.glossEditor(gloss=g, db="data/%s/db.sqlite")

    if ed != None:
        ed.write("data/%s/stardict.ifo" % plugin["name"])

