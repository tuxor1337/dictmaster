#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import signal

from dictmaster.util import load_plugin

last_broadcast_msg = " "
def broadcast(msg, overwrite=False):
    global last_broadcast_msg
    if overwrite:
        sys.stdout.write("\r{}".format(" "*len(last_broadcast_msg.strip())))
        msg = "\r"+msg
    else:
        if last_broadcast_msg[0] == "\r":
            msg = "\n"+msg
        msg += "\n"
    last_broadcast_msg = msg
    sys.stdout.write(msg)
    sys.stdout.flush()

def main(args):
    plugin = load_plugin(args.plugin, args.popts, args.output)
    if plugin == None: sys.exit("Plugin not found or plugin broken.")

    if args.reset:
        broadcast("Resetting plugin data in '{}'.".format(plugin.output_directory))
        plugin.reset()
    
    broadcast("Running plugin '{}'.".format(args.plugin))
    broadcast("Output is written to '{}'.".format(plugin.output_directory))
    plugin.start()

    def ctrl_c(signal, frame):
        broadcast("User interrupt. Stopping the plugin...")
        plugin.cancel()
    signal.signal(signal.SIGINT, ctrl_c)

    while plugin.is_alive():
        broadcast(plugin.progress(), True)
        plugin.join(1)
    broadcast("Plugin '{}' quit.".format(args.plugin))

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

