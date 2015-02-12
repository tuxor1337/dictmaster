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
    [r"(?i)<([a-z?][a-z0-9]*)/", r"<entity>\1</entity>"],
    [r"(?i)\\'([0-9a-f]{2})", r"<unicode>\1</unicode>"],
    [r"(?i)(\[?)<(/?)source>(\]?)", r"\3<\2source>\1"],
    [r"(?i)( \})?<(/?)mhw>(\{ )?", r""],
    [r"(?i)<(/?)(def|rj|note|cs|mcol|col|syn|ety|cref|cd|vmorph|amorph|plu|ecol|specif|wordforms|usage)>", r""],
    [r"(?i)<(/?)(qex|sn|sd)>", r"<\1b>"],
    [r"(?i)<(/?)(qau|au)>", r"<\1small>"],
    [r"(?i)<(/?)(ex|xex|it|ptcl|contr|ant)>", r"<\1i>"],
    # Sorting out yet unknown tags
    #    [r"(?i)<(/?)()>", r"[\1\2]"],
    [r"(?i)<as>(as( in the phrases)?,? ?)", r"\1<as>"],
    [r"(?i)<ent>[^<]*</ent>", r""]
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
                ],
                "lower": True
            },
            "definition" : {
                "userscript" : ""
            },
            "alts": [
                ("hw", [[r"[\"`\*']",""]])
            ],
            "alts_lower": True
        }
    },
    "editor": {
        "dups": "cat"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
