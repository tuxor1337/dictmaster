# -*- coding: utf-8 -*-

import os

# webster alternatives:
#
# http://machaut.uchicago.edu/?resource=Webster%27s&word=.*&use1913=on
# the regex .* will give all entries separated by <hr />
#
# http://www.gutenberg.org/ebooks/673
# very similar to the artfl version

preregex = [
    [r"<!",r"<!--"],
    [r"!>",r"-->"],
    [r"<--",r"<!--"],
    [r"<([a-zA-Z?][a-zA-Z0-9]*)/", r"<entity>\1</entity>"],
    [r"\\'([0-9a-f][0-9a-f])", r"<unicode>\1</unicode>"]
]

cfg = {
    "dictname" : "GNU Collaborative International Dictionary of English",
    "url" : {
        "singleton" : "ftp://ftp.gnu.org/gnu/gcide/gcide-0.51.zip"
    },
    "threadcnt" : 1,
    "format" :  {
        "zip" : {
            "userscript" : ""
        },
        "html" : {
            "pre_parser": {
                "regex": preregex
            },
            "container_iter" : "p",
            "greedy": True,
            "term" : {
                "text_content": "hw",
                "regex": [
                    [r"[\"`\*']",""]
                ]
            },
            "definition" : {
                "userscript" : ""
            }
        }
    },
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
