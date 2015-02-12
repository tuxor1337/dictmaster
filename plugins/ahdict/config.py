# -*- coding: utf-8 -*-

import os

# TODO: get full word list

cfg = {
    "dictname" : "The American Heritage Dictionary of the English Language, Fifth Edition",
    "url" : {
        "pattern" : "https://ahdictionary.com/word/search.html?q={word}",
        "itermode" : {
            "wordlist" : {
                "from_file" : "words.txt",
                "decode": "iso-8859-1", # for UKACD17
                #"decode": "ascii", # for ENABLE
                #"decode" : "utf-8", # for EOWL (basically UKACD16)
                "encode" : "utf-8"
            }
        },
        "count_condition" : {
            "always_continue": True
        },
        "charset": "utf-8"
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "#results" },
    "format" :  {
        "html" : {
            "container_iter" : "td",
            "pre_parser": {
                "regex": [
                    # pronunciation
                    [r"","′"],
                    [r"","o͞o"],
                    [r"</?font[^>]*>",""]
                ]
            },
            "term" : {
                "text_content" : "b",
                "regex": [
                    [r"\xb7",""], # the centered dot
                    [r" ([0-9]+)$",r"(\1)"]
                ]
            },
            "definition" : {
                "userscript" : ""
            },
            "codec": "utf-8"
        }
    },
    "editor": {
        "dups": "enumerate"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
