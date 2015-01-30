# -*- coding: utf-8 -*-

import os, shutil, re, importlib, sys, codecs, zipfile
from pyquery import PyQuery as pq
    
from pyglossary.glossary import Glossary
from editor import glossEditor
from util import mkdir_p

def process(plugin):
    print("Postprocessing...")
    data = []
    dirname = "data/%s/raw" % plugin["name"]
    if "zip" in plugin["format"]:
        shutil.rmtree(dirname)
        zdirname = "data/%s/zip" % plugin["name"]
        for zfile in os.listdir(zdirname):
            z = zipfile.ZipFile("%s/%s" % (zdirname, zfile))
            for n in z.namelist():
                dest = os.path.join(dirname, n)
                destdir = os.path.dirname(dest)
                mkdir_p(destdir)
                if not os.path.isdir(dest):
                    zdata = z.read(n)
                    f = open(dest, 'w')
                    f.write(zdata)
                    f.close()
            z.close()
        if "userscript" in plugin["format"]["zip"]:
            userscript = importlib.import_module(plugin["format"]["zip"]["userscript"].replace("/",".").replace(".py",""))
            userscript.post_unzip(dirname)
    for i, f in enumerate(sorted(os.listdir(dirname))):
        sys.stdout.write("\r%s %04d" % (f, i))
        sys.stdout.write("\r\033[13C%06d" % len(data))
        sys.stdout.flush()
        complete_path = "%s/%s" % (dirname, f)
        if "html" in plugin["format"]:
            data += process_html(complete_path, plugin["format"]["html"])
        
    print("\r\n...postprocessing done.")
    
    g = Glossary()
    g.data = data
    g.setInfo("bookname", plugin["dictname"])
    ed = glossEditor(g)
    ed.write("data/%s/db.sqlite" % plugin["name"])
    return ed
            
def process_html(filename, html_structure):
    data = []
    with codecs.open(filename, "r", "utf-8") as html_file:
        doc = pq(html_file.read().encode("utf-8"))
        if "alternating" in html_structure:
            a = html_structure["alternating"]["a"]
            b = html_structure["alternating"]["b"]
            dt = doc(a)
            while len(dt) > 0:
                dt = dt.eq(0)
                dd = dt.nextAll(b).eq(0)
                term = process_html_element(dt, html_structure["term"])
                definition = process_html_element(dd, html_structure["definition"], term)
                if type(term) == "unicode":
                    term = term.encode("utf-8")
                if type(definition) == "unicode":
                    definition = definition.encode("utf-8")
                data.append((term, definition, None))
                dt = dt.nextAll(a)
                if len(data) % 50 == 0:
                    sys.stdout.write("\r\033[19C:%s" % u"{:<20}".format(term))
                    sys.stdout.flush()
        elif "container_iter" in html_structure:
            for container in doc(html_structure["container_iter"]):
                term = process_html_element(doc(container), html_structure["term"])
                definition = process_html_element(doc(container), html_structure["definition"], term)
                if type(term) == "unicode":
                    term = term.encode("utf-8")
                if type(definition) == "unicode":
                    definition = definition.encode("utf-8")
                data.append((term, definition, None))
                if len(data) % 50 == 0:
                    sys.stdout.write("\r\033[19C:%s" % u"{:<20}".format(term))
                    sys.stdout.flush()
    return data
            
def process_html_element(html, rule, term=""):
    result = ""
    
    if "attr" in rule:
        if "target" not in rule["attr"]:
            target = html
        else:
            try:
                target = html.find(rule["attr"]["target"])
            except:
                print html.html()
                sys.exit()
        result = target.attr(rule["attr"]["key"]).strip()
        
    if "text_content" in rule:
        if rule["text_content"] == "":
            target = html
        else:
            try:
                target = html.find(rule["text_content"])
            except:
                print html.html()
                sys.exit()
        result = target.text().strip()
        
    if "userscript" in rule:
        userscript = importlib.import_module(rule["userscript"].replace("/",".").replace(".py",""))
        result = userscript.process_html_element(html, term)
        
    if "regex" in rule:
        for regex in rule["regex"]:
            result = re.sub(regex[0], regex[1], result)
        
    if "lower" in rule:
        result = result.lower()
    
    return result

