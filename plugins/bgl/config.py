# -*- coding: utf-8 -*-

import os

cfg = {
    "format" :  {
        "bgl" : {
            "definition": {
                "regex": [
                    [r"(?i)^[^<]+<br>\n<div[^>]+></div>", ""]
                ],
                "no_font_tags": ""
            }
        }
    },
    "editor": {
        "dups": "enumerate"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
