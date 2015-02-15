#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import signal

from dictmaster.util import load_plugin

def main(args):
    plugin = load_plugin(args.plugin, args.popts, args.output)
    if plugin == None: sys.exit("Plugin not found or plugin broken.")

    if args.reset: plugin.reset()
    plugin.start()

    def ctrl_c(signal, frame):
        print("\nUser interrupt. Stopping the plugin...")
        plugin.cancel()
    signal.signal(signal.SIGINT, ctrl_c)

    while plugin.is_alive():
        prog = plugin.progress()
        sys.stdout.write("\r{}".format(" "*len(prog)))
        sys.stdout.write("\r{}".format(plugin.progress()))
        sys.stdout.flush()
        plugin.join(1)
    print

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Download and convert dictionaries.')
    parser.add_argument('plugin', metavar='FILE', type=str, help='The plugin to use.')
    parser.add_argument('--popts', action="store", default="", type=str,
                    help=("Option string passed to the plugin."))
    parser.add_argument('--reset', action="store_true", default=False,
                    help=("Discard data from last time."))
    parser.add_argument('-o', '--output', action="store", default="", type=str,
                    help=("Work and output directory."))
    main(parser.parse_args())
