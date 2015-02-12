# -*- coding: utf-8 -*-

import os, glob, shutil, re, sys
from pyquery import PyQuery as pq

def post_unzip(dirname):
    repodir = os.listdir(dirname)[0]
    path = os.path.join(dirname, repodir)
    for filename in glob.glob("%s/CIDE.*" % path):
        filename = os.path.basename(filename)
        src = os.path.join(path, filename)
        dest = os.path.join(dirname, filename)
        os.rename(src, dest)
    shutil.rmtree(path)

"""
Format information from dico source code (c and lex files)
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/ent.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/grk.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/idxgcide.l
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/markup.l
"""

entities = {
    u"Cced":   u"Ç",
    u"uum":    u"ü",
    u"eacute": u"é",
    u"acir":   u"â",
    u"aum":    u"ä",
    u"agrave": u"à",
    u"aring":  u"å",
    u"ccedil": u"ç",
    u"cced":   u"ç",
    u"ecir":   u"ê",
    u"eum":    u"ë",
    u"egrave": u"è",
    u"ium":    u"ï",
    u"icir":   u"î",
    u"igrave": u"ì",
    u"Aum":    u"Ä",
    u"Aring":  u"Å",
    u"Eacute": u"È",
    u"ae":     u"æ",
    u"AE":     u"Æ",
    u"ocir":   u"ô",
    u"oum":    u"ö",
    u"ograve": u"ò",
    u"oacute": u"ó",
    u"Oacute": u"Ó",
    u"ucir":   u"û",
    u"ugrave": u"ù",
    u"uacute": u"ú",
    u"yum":    u"ÿ",
    u"Oum":    u"Ö",
    u"Uum":    u"Ü",
    u"pound":  u"£",
    u"aacute": u"á",
    u"iacute": u"í",
    u"frac23": u"⅔",
    u"frac13": u"⅓",
    u"frac12": u"½",
    u"frac14": u"¼",
    u"?":      u"<?>", # Place-holder for unknown or illegible character.
    u"hand":   u"☞",   # pointing hand (printer's u"fist")
    u"sect":   u"§",
    u"amac":   u"ā",
    u"nsm":    u"ṉ",   # u"n sub-macron"
    u"sharp":  u"♯",
    u"flat":   u"♭",
    u"th":     u"th",
    u"imac":   u"ī",
    u"emac":   u"ē",
    u"dsdot":  u"ḍ",   # Sanskrit/Tamil d dot
    u"nsdot":  u"ṇ",   # Sanskrit/Tamil n dot
    u"tsdot":  u"ṭ",   # Sanskrit/Tamil t dot
    u"ecr":    u"ĕ",
    u"icr":    u"ĭ",
    u"ocr":    u"ŏ",
    u"OE":     u"Œ",
    u"oe":     u"œ",
    u"omac":   u"ō",
    u"umac":   u"ū",
    u"ocar":   u"ǒ",
    u"aemac":  u"ǣ",
    u"ucr":    u"ŭ",
    u"acr":    u"ă",
    u"ymac":   u"ȳ",
    u"asl":    u"a",   # FIXME: a u"semilong" (has a macron above with a short
    u"esl":    u"e",   # FIXME: e u"semilong"
    u"isl":    u"i",   # FIXME: i u"semilong"
    u"osl":    u"o",   # FIXME: o u"semilong"
    u"usl":    u"u",   # FIXME: u u"semilong"
    u"adot":   u"ȧ",   # a with dot above
    u"edh":    u"ð",
    u"thorn":  u"þ",
    u"atil":   u"ã",
    u"etil":   u"ẽ",
    u"itil":   u"ĩ",
    u"otil":   u"õ",
    u"util":   u"ũ",
    u"ntil":   u"ñ",
    u"Atil":   u"Ã",
    u"Etil":   u"Ẽ",
    u"Itil":   u"Ĩ",
    u"Otil":   u"Õ",
    u"Util":   u"Ũ",
    u"Ntil":   u"Ñ",
    u"ndot":   u"ṅ",
    u"rsdot":  u"ṛ",
    u"yogh":   u"ȝ",
    u"deg":    u"°",
    u"middot": u"•",
    u"root":   u"√",
# Greek alphabet
    u"alpha":    u"α",
    u"beta":     u"β",
    u"gamma":    u"γ",
    u"delta":    u"δ",
    u"epsilon":  u"ε",
    u"zeta":     u"ζ",
    u"eta":      u"η",
    u"theta":    u"θ",
    u"iota":     u"ι",
    u"kappa":    u"κ",
    u"lambda":   u"λ",
    u"mu":       u"μ",
    u"nu":       u"ν",
    u"xi":       u"ξ",
    u"omicron":  u"ο",
    u"pi":       u"π",
    u"rho":      u"ρ",
    u"sigma":    u"σ",
    u"sigmat":   u"ς",
    u"tau":      u"τ",
    u"upsilon":  u"υ",
    u"phi":      u"φ",
    u"chi":      u"χ",
    u"psi":      u"ψ",
    u"omega":    u"ω",
    u"digamma":  u"ϝ",
    u"ALPHA":    u"Α",
    u"BETA":     u"Β",
    u"GAMMA":    u"Γ",
    u"DELTA":    u"Δ",
    u"EPSILON":  u"Ε",
    u"ZETA":     u"Ζ",
    u"ETA":      u"Η",
    u"THETA":    u"Θ",
    u"IOTA":     u"Ι",
    u"KAPPA":    u"Κ",
    u"LAMBDA":   u"Λ",
    u"MU":       u"Μ",
    u"NU":       u"Ν",
    u"XI":       u"Ξ",
    u"OMICRON":  u"Ο",
    u"PI":       u"Π",
    u"RHO":      u"Ρ",
    u"SIGMA":    u"Σ",
    u"TAU":      u"Τ",
    u"UPSILON":  u"Υ",
    u"PHI":      u"Φ",
    u"CHI":      u"Χ",
    u"PSI":      u"Ψ",
    u"OMEGA":    u"Ω",
# Italic letters
    u"AIT":      u"A",
    u"BIT":      u"B",
    u"CIT":      u"C",
    u"DIT":      u"D",
    u"EIT":      u"E",
    u"FIT":      u"F",
    u"GIT":      u"G",
    u"HIT":      u"H",
    u"IIT":      u"I",
    u"JIT":      u"J",
    u"KIT":      u"K",
    u"LIT":      u"L",
    u"MIT":      u"M",
    u"NOT":      u"N",
    u"OIT":      u"O",
    u"PIT":      u"P",
    u"QIT":      u"Q",
    u"RIT":      u"R",
    u"SIT":      u"S",
    u"TIT":      u"T",
    u"UIT":      u"U",
    u"VIT":      u"V",
    u"WIT":      u"W",
    u"XIT":      u"X",
    u"YIT":      u"Y",
    u"ZIT":      u"Z",
    u"ait":      u"a",
    u"bit":      u"b",
    u"cit":      u"c",
    u"dit":      u"d",
    u"eit":      u"e",
    u"fit":      u"f",
    u"git":      u"g",
    u"hit":      u"h",
    u"iit":      u"i",
    u"jit":      u"j",
    u"kit":      u"k",
    u"lit":      u"l",
    u"mit":      u"m",
    u"not":      u"n",
    u"oit":      u"o",
    u"pit":      u"p",
    u"qit":      u"q",
    u"rit":      u"r",
    u"sit":      u"s",
    u"tit":      u"t",
    u"uit":      u"u",
    u"vit":      u"v",
    u"wit":      u"w",
    u"xit":      u"x",
    u"yit":      u"y",
    u"zit":      u"z",
# FIXME: Vowels with a double dot below. There`s nothing suitable in the Unicode
    u"add":      u"a",
    u"udd":      u"u",
    u"ADD":      u"A",
    u"UDD":      u"U",
# Accents
    u"prime":    u"´",
    u"bprime":   u"˝",
    u"mdash":    u"—",
    u"divide":   u"÷",
# Quotes
    u"lsquo":    u"‘",
    u"ldquo":    u"“",
    u"rdquo":    u"”",
    u"dagger":   u"†",
    u"dag":      u"†",
    u"Dagger":   u"‡",
    u"ddag":     u"‡",
    u"para":     u"§",
    u"gt":       u">",
    u"lt":       u"<",
    u"rarr":     u"→",
    u"larr":     u"←",
    u"schwa":    u"ə",
    u"br":       u"\n",
    u"and":      u"and",
    u"or":       u"or",
    u"sec":      u"˝"
}

xlit = [
    [ u"'A", u"Ἀ" ],
    [ u"'A,", u"ᾈ" ],
    [ u"'A^", u"Ἆ" ],
    [ u"'A`", u"Ἄ" ],
    [ u"'A~", u"Ἂ" ],
    [ u"'A~,", u"ᾊ" ],
    [ u"'A~,", u"ᾌ" ],
    [ u"'A~,", u"ᾎ" ],
    [ u"'E", u"Ἐ" ],
    [ u"'E`", u"Ἔ" ],
    [ u"'E~", u"Ἒ" ],
    [ u"'H", u"Ἠ" ],
    [ u"'H,", u"ᾘ" ],
    [ u"'H^", u"Ἦ" ],
    [ u"'H`", u"Ἤ" ],
    [ u"'H~", u"Ἢ" ],
    [ u"'H~,", u"ᾚ" ],
    [ u"'H~,", u"ᾜ" ],
    [ u"'H~,", u"ᾞ" ],
    [ u"'I", u"Ἰ" ],
    [ u"'I^", u"Ἶ" ],
    [ u"'I`", u"Ἴ" ],
    [ u"'I~", u"Ἲ" ],
    [ u"'O", u"Ὀ" ],
    [ u"'O`", u"Ὄ" ],
    [ u"'O~", u"Ὂ" ],
    [ u"'W", u"Ὠ" ],
    [ u"'W,", u"ᾨ" ],
    [ u"'W^", u"Ὦ" ],
    [ u"'W`", u"Ὤ" ],
    [ u"'W~", u"Ὢ" ],
    [ u"'W~,", u"ᾪ" ],
    [ u"'W~,", u"ᾬ" ],
    [ u"'W~,", u"ᾮ" ],
    [ u"'`O", u"Ὄ" ],
    [ u"'a", u"ἀ" ],
    [ u"'a,", u"ᾀ" ],
    [ u"'a^", u"ἆ" ],
    [ u"'a^,", u"ᾆ" ],
    [ u"'a`", u"ἄ" ],
    [ u"'a`,", u"ᾄ" ],
    [ u"'a~", u"ἂ" ],
    [ u"'a~,", u"ᾂ" ],
    [ u"'e", u"ἐ" ],
    [ u"'e`", u"ἔ" ],
    [ u"'e~", u"ἒ" ],
    [ u"'h", u"ἠ" ],
    [ u"'h,", u"ᾐ" ],
    [ u"'h^", u"ἦ" ],
    [ u"'h^,", u"ᾖ" ],
    [ u"'h`", u"῎η" ],
    [ u"'h`,", u"ᾔ" ],
    [ u"'h~", u"ἢ" ],
    [ u"'h~,", u"ᾒ" ],
    [ u"'i", u"ἰ" ],
    [ u"'i^", u"ἶ" ],
    [ u"'i`", u"ἴ" ],
    [ u"'i~", u"ἲ" ],
    [ u"'o", u"ὀ" ],
    [ u"'o`", u"ὄ" ],
    [ u"'o~", u"ὂ" ],
    [ u"'r", u"ῤ" ],
    [ u"'u", u"ὐ" ],
    [ u"'u^", u"ὖ" ],
    [ u"'u`", u"ὔ" ],
    [ u"'u~", u"ὒ" ],
    [ u"'w", u"ὠ" ],
    [ u"'w,", u"ᾠ" ],
    [ u"'w^", u"ὦ" ],
    [ u"'w^,", u"ᾦ" ],
    [ u"'w`", u"ὤ" ],
    [ u"'w`,", u"ᾤ" ],
    [ u"'w~", u"ὢ" ],
    [ u"'w~,", u"ᾢ" ],
    [ u"'y", u"ὐ" ],
    [ u"'y^", u"ὖ" ],
    [ u"'y`", u"ὔ" ],
    [ u"'y~", u"ὒ" ],
    [ u"A", u"Α" ],
    [ u"A", u"Α" ],
    [ u"A,", u"ᾼ" ],
    [ u"A`", u"Ά" ],
    [ u"A~", u"Ἁ" ],
    [ u"B", u"Β" ],
    [ u"CH", u"Χ" ],
    [ u"Ch", u"Χ" ],
    [ u"D", u"Δ" ],
    [ u"E", u"Ε" ],
    [ u"E", u"Ε" ],
    [ u"E`", u"Έ" ],
    [ u"E~", u"Ἑ" ],
    [ u"F", u"Φ" ],
    [ u"G", u"Γ" ],
    [ u"H", u"Η" ],
    [ u"H", u"Η" ],
    [ u"H,", u"ῌ" ],
    [ u"H`", u"Ή" ],
    [ u"H~", u"Ἡ" ],
    [ u"I", u"Ι" ],
    [ u"I", u"Ι" ],
    [ u"I`", u"Ί" ],
    [ u"I~", u"Ἱ" ],
    [ u"K", u"Κ" ],
    [ u"L", u"Λ" ],
    [ u"M", u"Μ" ],
    [ u"N", u"Ν" ],
    [ u"O", u"Ο" ],
    [ u"O", u"Ο" ],
    [ u"O`", u"Ό" ],
    [ u"O~", u"Ὁ" ],
    [ u"P", u"Π" ],
    [ u"PS", u"Ψ" ],
    [ u"Ps", u"Ψ" ],
    [ u"Q", u"Θ" ],
    [ u"R", u"Ρ" ],
    [ u"S", u"Σ" ],
    [ u"T", u"Τ" ],
    [ u"U", u"Υ" ],
    [ u"U", u"Υ" ],
    [ u"U`", u"Ύ" ],
    [ u"U~", u"Ὑ" ],
    [ u"W", u"Ω" ],
    [ u"W", u"Ω" ],
    [ u"W,", u"ῼ" ],
    [ u"W`", u"Ώ" ],
    [ u"W~", u"Ὡ" ],
    [ u"X", u"Ξ" ],
    [ u"Y", u"Υ" ],
    [ u"Y", u"Υ" ],
    [ u"Y`", u"Ύ" ],
    [ u"Y~", u"Ὑ" ],
    [ u"Z", u"Ζ" ],
    [ u"\"A", u"Ὰ" ],
    [ u"\"A,", u"ᾉ" ],
    [ u"\"A^", u"Ἇ" ],
    [ u"\"A^,", u"ᾏ" ],
    [ u"\"A`", u"Ἅ" ],
    [ u"\"A`,", u"ᾍ" ],
    [ u"\"A~", u"Ἃ" ],
    [ u"\"A~,", u"ᾋ" ],
    [ u"\"E", u"Ὲ" ],
    [ u"\"E`", u"Ἕ" ],
    [ u"\"E~", u"Ἓ" ],
    [ u"\"H", u"Ὴ" ],
    [ u"\"H,", u"ᾙ" ],
    [ u"\"H^", u"Ἧ" ],
    [ u"\"H^,", u"ᾟ" ],
    [ u"\"H`", u"Ἥ" ],
    [ u"\"H`,", u"ᾝ" ],
    [ u"\"H~", u"Ἣ" ],
    [ u"\"H~,", u"ᾛ" ],
    [ u"\"I", u"Ὶ" ],
    [ u"\"I^", u"Ἷ" ],
    [ u"\"I`", u"Ἵ" ],
    [ u"\"I~", u"Ἳ" ],
    [ u"\"O", u"Ὸ" ],
    [ u"\"O`", u"Ὅ" ],
    [ u"\"O~", u"Ὃ" ],
    [ u"\"R", u"Ῥ" ],
    [ u"\"U", u"Ὺ" ],
    [ u"\"U^", u"Ὗ" ],
    [ u"\"U`", u"Ὕ" ],
    [ u"\"U~", u"Ὓ" ],
    [ u"\"W", u"Ὼ" ],
    [ u"\"W,", u"ᾩ" ],
    [ u"\"W^", u"Ὧ" ],
    [ u"\"W^,", u"ᾯ" ],
    [ u"\"W`", u"Ὥ" ],
    [ u"\"W`,", u"ᾭ" ],
    [ u"\"W~", u"Ὣ" ],
    [ u"\"W~,", u"ᾫ" ],
    [ u"\"Y", u"Ὺ" ],
    [ u"\"Y^", u"Ὗ" ],
    [ u"\"Y`", u"Ὕ" ],
    [ u"\"Y~", u"Ὓ" ],
    [ u"\"a", u"ἁ" ],
    [ u"\"a,", u"ᾁ" ],
    [ u"\"a^", u"ἇ" ],
    [ u"\"a^,", u"ᾇ" ],
    [ u"\"a`", u"ἄ" ],
    [ u"\"a`", u"ἅ" ],
    [ u"\"a`,", u"ᾅ" ],
    [ u"\"a~", u"ἂ" ],
    [ u"\"a~", u"ἃ" ],
    [ u"\"a~,", u"ᾃ" ],
    [ u"\"e", u"ἑ" ],
    [ u"\"e`", u"ἕ" ],
    [ u"\"e~", u"ἓ" ],
    [ u"\"h", u"ἡ" ],
    [ u"\"h,", u"ᾑ" ],
    [ u"\"h^", u"ἧ" ],
    [ u"\"h^,", u"ᾗ" ],
    [ u"\"h`", u"ἤ" ],
    [ u"\"h`", u"ἥ" ],
    [ u"\"h`,", u"ᾕ" ],
    [ u"\"h~", u"ἣ" ],
    [ u"\"h~,", u"ᾓ" ],
    [ u"\"i", u"ἱ" ],
    [ u"\"i^", u"ἷ" ],
    [ u"\"i`", u"ἵ" ],
    [ u"\"i~", u"ἳ" ],
    [ u"\"o", u"ὁ" ],
    [ u"\"o`", u"ὅ" ],
    [ u"\"o~", u"ὃ" ],
    [ u"\"r", u"ῥ" ],
    [ u"\"u", u"ὑ" ],
    [ u"\"u^", u"ὗ" ],
    [ u"\"u`", u"ὕ" ],
    [ u"\"u~", u"ὓ" ],
    [ u"\"w", u"ὡ" ],
    [ u"\"w,", u"ᾡ" ],
    [ u"\"w^", u"ὣ" ],
    [ u"\"w^", u"ὧ" ],
    [ u"\"w^,", u"ᾧ" ],
    [ u"\"w`", u"ὥ" ],
    [ u"\"w`,", u"ᾥ" ],
    [ u"\"w~,", u"ᾣ" ],
    [ u"\"y", u"ὑ" ],
    [ u"\"y^", u"ὗ" ],
    [ u"\"y`", u"ὕ" ],
    [ u"\"y~", u"ὓ" ],
    [ u"a", u"α" ],
    [ u"a,", u"ᾳ" ],
    [ u"a^", u"ᾶ" ],
    [ u"a^,", u"ᾷ" ],
    [ u"a`", u"ά" ],
    [ u"a`,", u"ᾴ" ],
    [ u"a~", u"ὰ" ],
    [ u"a~,", u"ᾲ" ],
    [ u"b", u"β" ],
    [ u"ch", u"χ" ],
    [ u"d", u"δ" ],
    [ u"e", u"ε" ],
    [ u"e`", u"έ" ],
    [ u"e~", u"ὲ" ],
    [ u"f", u"φ" ],
    [ u"g", u"γ" ],
    [ u"h", u"η" ],
    [ u"h,", u"ῃ" ],
    [ u"h^", u"ῆ" ],
    [ u"h^,", u"ῇ" ],
    [ u"h`", u"ή" ],
    [ u"h`,", u"ῄ" ],
    [ u"h~", u"ὴ" ],
    [ u"h~,", u"ῂ" ],
    [ u"i", u"ι" ],
    [ u"i:", u"ϊ" ],
    [ u"i:^", u"ῗ" ],
    [ u"i:`", u"ῒ" ],
    [ u"i:`", u"ΐ" ],
    [ u"i^", u"ῖ" ],
    [ u"i^:", u"ῗ" ],
    [ u"i`", u"ί" ],
    [ u"i`:", u"ῒ" ],
    [ u"i`:", u"ΐ" ],
    [ u"i~", u"ὶ" ],
    [ u"k", u"κ" ],
    [ u"l", u"λ" ],
    [ u"m", u"μ" ],
    [ u"n", u"ν" ],
    [ u"o", u"ο" ],
    [ u"o`", u"ό" ],
    [ u"o~", u"ὸ" ],
    [ u"p", u"π" ],
    [ u"ps", u"ψ" ],
    [ u"q", u"θ" ],
    [ u"r", u"ρ" ],
    [ u"s", u"σ" ],
    [ u"t", u"τ" ],
    [ u"u", u"υ" ],
    [ u"u:", u"ϋ" ],
    [ u"u:^", u"ῧ" ],
    [ u"u:`", u"ΰ" ],
    [ u"u:~", u"ῢ" ],
    [ u"u^", u"ῦ" ],
    [ u"u^:", u"ῧ" ],
    [ u"u`", u"ύ" ],
    [ u"u`:", u"ΰ" ],
    [ u"u~", u"ὺ" ],
    [ u"u~:", u"ῢ" ],
    [ u"w", u"ω" ],
    [ u"w,", u"ῳ" ],
    [ u"w^", u"ῶ" ],
    [ u"w^,", u"ῷ" ],
    [ u"w`", u"ώ" ],
    [ u"w`,", u"ῴ" ],
    [ u"w~", u"ὼ" ],
    [ u"w~,", u"ῲ" ],
    [ u"x", u"ξ" ],
    [ u"y", u"υ" ],
    [ u"y:", u"ϋ" ],
    [ u"y:^", u"ῧ" ],
    [ u"y:`", u"ΰ" ],
    [ u"y:~", u"ῢ" ],
    [ u"y^", u"ῦ" ],
    [ u"y^:", u"ῧ" ],
    [ u"y`", u"ύ" ],
    [ u"y`:", u"ΰ" ],
    [ u"y~", u"ὺ" ],
    [ u"y~:", u"ῢ" ],
    [ u"z", u"ζ" ]
]

def gcide_grk_to_utf8(grk_str):
    found_len = 0
    found_xlit = None

    if grk_str == u"s":
        return (1, u"ς")

    for p in xlit:
        i = 0
        while i < min(len(grk_str),len(p[0])) and p[0][i] == grk_str[i]:
            i += 1

        if i < len(p[0]):
            if found_len > 0 and i == 0:
                break
            continue

        if i > found_len:
            found_len = i
            found_xlit = p

    if found_len:
        return (found_len, found_xlit[1])
    return (None, None)


def greek_translit(grk_str):
    result = u""
    n = 0
    while len(grk_str) > n:
        gr_len, greek = gcide_grk_to_utf8(grk_str[n:])

        if greek:
            result += greek
            n += gr_len
        else:
            result += grk_str[n]
            n += 1
    return result

def process_html_element(html, term):
    if not html.html():
        return ""

    d = pq(html)
    for e in html.find("entity"):
        val = d(e).text()
        replace = ""
        if val in entities:
            replace = entities[val]
        d(e).replaceWith(replace)

    for u in html.find("unicode"):
        val = int(d(u).text(),16)
        replace = unichr(val)
        d(u).replaceWith(replace)

    for g in html.find("grk"):
        val = greek_translit(d(g).text())
        d(g).replaceWith(val)

    for hw in html.find("hw"):
        hw_html = re.sub(r"[\"`\*']","",d(hw).html())
        d(hw).replaceWith(
            d("<b/>").css("color", "#00b")
                .html(hw_html).outerHtml()
        )

    for wf in html.find("wf"):
        wf_html = re.sub(r"[\"`\*']","",d(wf).html())
        d(wf).replaceWith(
            d("<span/>").css("color", "#00b")
                .html(wf_html).outerHtml()
        )

    for pr in html.find("pr"):
        pr_html = re.sub(r"[\"`\*']","",d(pr).html())
        d(pr).replaceWith(
            d("<i/>").html(pr_html).outerHtml()
        )

    for q in html.find("q"):
        d(q).replaceWith(
            d("<i/>").css("color", "#33f")
                .html(d(q).html()).outerHtml()
        )

    for pos in html.find("pos,pluf"):
        d(pos).replaceWith(
            d("<i/>").css("color", "#a00")
                .html(d(pos).html()).outerHtml()
        )

    for m in html.find("mark,fld,conjf,plw,adjf,altname,sig,usedfor"):
        d(m).replaceWith(
            d("<span/>").css("color", "#00b")
                .html(d(m).html()).outerHtml()
        )

    for a in html.find("as"):
        d(a).replaceWith(
            d("<span/>").css("color", "33a")
                .html(d(a).html()).outerHtml()
        )

    for ets in html.find("ets,spn,gen,stype"):
        d(ets).replaceWith(
            d("<span/>").css("color", "#8B4513")
                .html(d(ets).html()).outerHtml()
        )

    for er in html.find("er"):
        href = d(er).text().strip()
        if href == "":
            d(er).replaceWith("")
        else:
            """
            Word groups are not indexed, hence it makes sense to link to the
            first part of a compound only.
            """
            href = href.split(" ")[0]
            d(er).replaceWith(
                d("<a/>").attr("href", "bword://%s" % href)
                    .html(d(er).html()).outerHtml()
            )

    for src in html.find("source"):
        """
        replacement = d("<p/>").css("text-align","right")
            .css("font-size","x-small")
            .html(d(src).html()).outerHtml()
        """
        "Including the sources unnecessarily blows up everything."
        replacement = ""
        d(src).replaceWith(replacement)

    output = "<p>%s</p>" % html.html().strip()
    return output

