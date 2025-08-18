#!/usr/bin/env python
#
# Copyright 2025 BredOS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
from bredos.utilities import catch_exceptions
from bakery import lrun, lp, _

_kbmodelmap = {
    "armada": "Laptop/notebook Compaq (eg. Armada) Laptop Keyboard",
    "apex300": "Apex 300 Gaming Keyboard",
    "chromebook": "Chromebook Laptop Keyboard",
    "pc101": "Generic 101-key PC",
    "pc102": "Generic 102-key (Intl) PC",
    "pc104": "Generic 104-key PC",
    "pc105": "Generic 105-key (Intl) PC",
    "pc104alt": "Generic 104-key PC (Alternative)",
    "pc86": "Generic 86-key PC",
    "ppkb": "PinePhone Keyboard",
    "dell101": "Dell 101-key PC",
    "latitude": "Dell Latitude series laptop",
    "dellm65": "Dell Precision M65",
    "everex": "Everex STEPnote",
    "flexpro": "Keytronic FlexPro",
    "microsoft": "Microsoft Natural",
    "omnikey101": "Northgate OmniKey 101",
    "winbook": "Winbook Model XP5",
    "pc98": "PC-98xx Series",
    "a4techKB21": "A4Tech KB-21",
    "a4techKBS8": "A4Tech KBS-8",
    "a4_rfkb23": "A4Tech Wireless Desktop RFKB-23",
    "airkey": "Acer AirKey V",
    "azonaRF2300": "Azona RF2300 wireless Internet Keyboard",
    "scorpius": "Advance Scorpius KI",
    "brother": "Brother Internet Keyboard",
    "btc5113rf": "BTC 5113RF Multimedia",
    "btc5126t": "BTC 5126T",
    "btc6301urf": "BTC 6301URF",
    "btc9000": "BTC 9000",
    "btc9000a": "BTC 9000A",
    "btc9001ah": "BTC 9001AH",
    "btc5090": "BTC 5090",
    "btc9019u": "BTC 9019U",
    "btc9116u": "BTC 9116U Mini Wireless Internet and Gaming",
    "cherryblue": "Cherry Blue Line CyBo@rd",
    "cherryblueb": "Cherry CyMotion Master XPress",
    "cherrybluea": "Cherry Blue Line CyBo@rd (alternate option)",
    "cherrycyboard": "Cherry CyBo@rd USB-Hub",
    "cherrycmexpert": "Cherry CyMotion Expert",
    "cherrybunlim": "Cherry B.UNLIMITED",
    "chicony": "Chicony Internet Keyboard",
    "chicony0108": "Chicony KU-0108",
    "chicony0420": "Chicony KU-0420",
    "chicony9885": "Chicony KB-9885",
    "compaqeak8": "Compaq Easy Access Keyboard",
    "compaqik7": "Compaq Internet Keyboard (7 keys)",
    "compaqik13": "Compaq Internet Keyboard (13 keys)",
    "compaqik18": "Compaq Internet Keyboard (18 keys)",
    "cymotionlinux": "Cherry CyMotion Master Linux",
    "armada": "Laptop/notebook Compaq (eg. Armada) Laptop Keyboard",
    "presario": "Laptop/notebook Compaq (eg. Presario) Internet Keyboard",
    "ipaq": "Compaq iPaq Keyboard",
    "dell": "Dell",
    "dellsk8125": "Dell SK-8125",
    "dellsk8135": "Dell SK-8135",
    "dellusbmm": "Dell USB Multimedia Keyboard",
    "inspiron": "Dell Laptop/notebook Inspiron 6xxx/8xxx",
    "precision_m": "Dell Laptop/notebook Precision M series",
    "dexxa": "Dexxa Wireless Desktop Keyboard",
    "diamond": "Diamond 9801 / 9802 series",
    "dtk2000": "DTK2000",
    "ennyah_dkb1008": "Ennyah DKB-1008",
    "fscaa1667g": "Fujitsu-Siemens Computers AMILO laptop",
    "genius": "Genius Comfy KB-16M / Genius MM Keyboard KWD-910",
    "geniuscomfy": "Genius Comfy KB-12e",
    "geniuscomfy2": "Genius Comfy KB-21e-Scroll",
    "geniuskb19e": "Genius KB-19e NB",
    "geniuskkb2050hs": "Genius KKB-2050HS",
    "gyration": "Gyration",
    "htcdream": "HTC Dream",
    "kinesis": "Kinesis",
    "logitech_base": "Logitech Generic Keyboard",
    "logitech_g15": "Logitech G15 extra keys via G15daemon",
    "hpi6": "Hewlett-Packard Internet Keyboard",
    "hp250x": "Hewlett-Packard SK-250x Multimedia Keyboard",
    "hpxe3gc": "Hewlett-Packard Omnibook XE3 GC",
    "hpxe3gf": "Hewlett-Packard Omnibook XE3 GF",
    "hpxt1000": "Hewlett-Packard Omnibook XT1000",
    "hpdv5": "Hewlett-Packard Pavilion dv5",
    "hpzt11xx": "Hewlett-Packard Pavilion ZT11xx",
    "hp500fa": "Hewlett-Packard Omnibook 500 FA",
    "hp5xx": "Hewlett-Packard Omnibook 5xx",
    "hpnx9020": "Hewlett-Packard nx9020",
    "hp6000": "Hewlett-Packard Omnibook 6000/6100",
    "honeywell_euroboard": "Honeywell Euroboard",
    "hpmini110": "Hewlett-Packard Mini 110 Notebook",
    "rapidaccess": "IBM Rapid Access",
    "rapidaccess2": "IBM Rapid Access II",
    "thinkpad": "IBM ThinkPad 560Z/600/600E/A22E",
    "thinkpad60": "IBM ThinkPad R60/T60/R61/T61",
    "thinkpadz60": "IBM ThinkPad Z60m/Z60t/Z61m/Z61t",
    "ibm_spacesaver": "IBM Space Saver",
    "logiaccess": "Logitech Access Keyboard",
    "logiclx300": "Logitech Cordless Desktop LX-300",
    "logii350": "Logitech Internet 350 Keyboard",
    "logimel": "Logitech Media Elite Keyboard",
    "logicd": "Logitech Cordless Desktop",
    "logicd_it": "Logitech Cordless Desktop iTouch",
    "logicd_nav": "Logitech Cordless Desktop Navigator",
    "logicd_opt": "Logitech Cordless Desktop Optical",
    "logicda": "Logitech Cordless Desktop (alternate option)",
    "logicdpa2": "Logitech Cordless Desktop Pro (alternate option 2)",
    "logicfn": "Logitech Cordless Freedom/Desktop Navigator",
    "logicdn": "Logitech Cordless Desktop Navigator",
    "logiitc": "Logitech iTouch Cordless Keyboard (model Y-RB6)",
    "logiik": "Logitech Internet Keyboard",
    "itouch": "Logitech iTouch",
    "logicink": "Logitech Internet Navigator Keyboard",
    "logiex110": "Logitech Cordless Desktop EX110",
    "logiinkse": "Logitech iTouch Internet Navigator Keyboard SE",
    "logiinkseusb": "Logitech iTouch Internet Navigator Keyboard SE (USB)",
    "logiultrax": "Logitech Ultra-X Keyboard",
    "logiultraxc": "Logitech Ultra-X Cordless Media Desktop Keyboard",
    "logidinovo": "Logitech diNovo Keyboard",
    "logidinovoedge": "Logitech diNovo Edge Keyboard",
    "mx1998": "Memorex MX1998",
    "mx2500": "Memorex MX2500 EZ-Access Keyboard",
    "mx2750": "Memorex MX2750",
    "microsoft4000": "Microsoft Natural Ergonomic Keyboard 4000",
    "microsoft7000": "Microsoft Natural Wireless Ergonomic Keyboard 7000",
    "microsoftinet": "Microsoft Internet Keyboard",
    "microsoftpro": "Microsoft Natural Keyboard Pro / Microsoft Internet Keyboard Pro",
    "microsoftprousb": "Microsoft Natural Keyboard Pro USB / Microsoft Internet Keyboard Pro",
    "microsoftprooem": "Microsoft Natural Keyboard Pro OEM",
    "vsonku306": "ViewSonic KU-306 Internet Keyboard",
    "microsoftprose": "Microsoft Internet Keyboard Pro, Swedish",
    "microsoftoffice": "Microsoft Office Keyboard",
    "microsoftmult": "Microsoft Wireless Multimedia Keyboard 1.0A",
    "microsoftelite": "Microsoft Natural Keyboard Elite",
    "microsoftccurve2k": "Microsoft Comfort Curve Keyboard 2000",
    "microsoftsurface": "Microsoft Surface Keyboard",
    "oretec": "Ortek MCK-800 MM/Internet keyboard",
    "propeller": "Propeller Voyager (KTEZ-1000)",
    "qtronix": "QTronix Scorpius 98N+",
    "samsung4500": "Samsung SDM 4500P",
    "samsung4510": "Samsung SDM 4510P",
    "sanwaskbkg3": "Sanwa Supply SKB-KG3",
    "sk1300": "SK-1300",
    "sk2500": "SK-2500",
    "sk6200": "SK-6200",
    "sk7100": "SK-7100",
    "sp_inet": "Super Power Multimedia Keyboard",
    "sven": "SVEN Ergonomic 2500",
    "sven303": "SVEN Slim 303",
    "symplon": "Symplon PaceBook (tablet PC)",
    "toshiba_s3000": "Toshiba Satellite S3000",
    "trust": "Trust Wireless Keyboard Classic",
    "trustda": "Trust Direct Access Keyboard",
    "trust_slimline": "Trust Slimline",
    "tm2020": "TypeMatrix EZ-Reach 2020",
    "tm2030PS2": "TypeMatrix EZ-Reach 2030 PS2",
    "tm2030USB": "TypeMatrix EZ-Reach 2030 USB",
    "tm2030USB-102": "TypeMatrix EZ-Reach 2030 USB (102/105:EU mode)",
    "tm2030USB-106": "TypeMatrix EZ-Reach 2030 USB (106:JP mode)",
    "yahoo": "Yahoo! Internet Keyboard",
    "macbook78": "MacBook/MacBook Pro",
    "macbook79": "MacBook/MacBook Pro (Intl)",
    "macintosh": "Macintosh",
    "macintosh_old": "Macintosh Old",
    "macintosh_hhk": "Happy Hacking Keyboard for Mac",
    "acer_c300": "Acer C300",
    "acer_ferrari4k": "Acer Ferrari 4000",
    "acer_laptop": "Acer Laptop",
    "asus_laptop": "Asus Laptop",
    "apple": "Apple",
    "apple_laptop": "Apple Laptop",
    "applealu_ansi": "Apple Aluminium Keyboard (ANSI)",
    "applealu_iso": "Apple Aluminium Keyboard (ISO)",
    "applealu_jis": "Apple Aluminium Keyboard (JIS)",
    "silvercrest": "SILVERCREST Multimedia Wireless Keyboard",
    "emachines": "Laptop/notebook eMachines m68xx",
    "benqx": "BenQ X-Touch",
    "benqx730": "BenQ X-Touch 730",
    "benqx800": "BenQ X-Touch 800",
    "hhk": "Happy Hacking Keyboard",
    "classmate": "Classmate PC",
    "olpc": "OLPC",
    "sun_type7_usb": "Sun Type 7 USB",
    "sun_type7_euro_usb": "Sun Type 7 USB (European layout)",
    "sun_type7_unix_usb": "Sun Type 7 USB (Unix layout)",
    "sun_type7_jp_usb": "Sun Type 7 USB (Japanese layout) / Japanese 106-key",
    "sun_type6_usb": "Sun Type 6/7 USB",
    "sun_type6_euro_usb": "Sun Type 6/7 USB (European layout)",
    "sun_type6_unix_usb": "Sun Type 6 USB (Unix layout)",
    "sun_type6_jp_usb": "Sun Type 6 USB (Japanese layout)",
    "sun_type6_jp": "Sun Type 6 (Japanese layout)",
    "targa_v811": "Targa Visionary 811",
    "unitekkb1925": "Unitek KB-1925",
    "compalfl90": "FL90",
    "creativedw7000": "Creative Desktop Wireless 7000",
    "htcdream": "Htc Dream phone",
    "teck227": "Truly Ergonomic Computer Keyboard Model 227 (Wide Alt keys)",
    "teck229": (
        "Truly Ergonomic Computer Keyboard Model 229 (Standard sized Alt keys, additional "
        + "Super and Menu key)"
    ),
}

_kblangmap = {
    "af": "Afrikaans",
    "al": "Albanian",
    "am": "Amharic",
    "ara": "Arabic",
    "at": "Austrian German",
    "au": "Australian English",
    "az": "Azerbaijani",
    "ba": "Bosnian",
    "bd": "Bangla",
    "be": "Belgian Dutch",
    "bg": "Bulgarian",
    "br": "Portuguese (Brazil)",
    "brai": "Braille",
    "bt": "Bhutanese",
    "bw": "Tswana",
    "by": "Belarusian",
    "ca": "Canadian English",
    "cd": "Congolese",
    "ch": "Swiss German",
    "cm": "Cameroonian",
    "cn": "Chinese",
    "cz": "Czech",
    "de": "German",
    "dk": "Danish",
    "dz": "Algerian Arabic",
    "ee": "Estonian",
    "epo": "Esperanto",
    "es": "Spanish",
    "eg": "Egyptian",
    "et": "Estonian",
    "fi": "Finnish",
    "fo": "Faroese",
    "fr": "French",
    "gb": "British English",
    "ge": "Georgian",
    "gh": "Ghanaian",
    "gn": "Guinean",
    "gr": "Greek",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "ie": "Irish",
    "il": "Hebrew",
    "in": "Indian English",
    "iq": "Iraqi Arabic",
    "ir": "Persian",
    "is": "Icelandic",
    "it": "Italian",
    "jp": "Japanese",
    "ke": "Kenyan",
    "kg": "Kyrgyz",
    "kh": "Khmer",
    "kr": "Korean",
    "kz": "Kazakh",
    "la": "Lao",
    "latam": "Latin American Spanish",
    "lk": "Sinhala",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ma": "Moroccan Arabic",
    "mao": "Māori",
    "md": "Moldovan",
    "me": "Montenegrin",
    "mk": "Macedonian",
    "ml": "Malian",
    "mm": "Myanmar",
    "mn": "Mongolian",
    "mt": "Maltese",
    "mv": "Dhivehi",
    "my": "Malay",
    "ng": "Nigerian Pidgin",
    "nl": "Dutch",
    "no": "Norwegian",
    "np": "Nepali",
    "nz": "New Zealand",
    "ph": "Filipino",
    "pk": "Pakistani",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "rs": "Serbian",
    "ru": "Russian",
    "se": "Swedish",
    "si": "Slovenian",
    "sk": "Slovak",
    "sn": "Senegalese",
    "sy": "Syrian Arabic",
    "tg": "Tajik",
    "th": "Thai",
    "tj": "Tajik",
    "tm": "Turkmen",
    "tr": "Turkish",
    "tw": "Taiwanese",
    "tz": "Tanzanian",
    "ua": "Ukrainian",
    "us": "American English",
    "uz": "Uzbek",
    "vn": "Vietnamese",
    "za": "South African English",
}


@catch_exceptions
def kb_variants(lang: str) -> list:
    try:
        variants = (
            subprocess.check_output(
                "localectl list-x11-keymap-variants " + lang,
                shell=True,
            )
            .decode("UTF-8")
            .split()
        )
        return variants
    except:
        return []


_kb_modcf = None
_kb_modct = None


@catch_exceptions
def kb_models(flip: bool = False) -> dict:
    res = {}
    global _kb_modcf, _kb_modct
    if (not flip) and _kb_modcf is not None:
        return _kb_modcf
    elif flip and _kb_modct is not None:
        return _kb_modct
    models = (
        subprocess.check_output(
            "localectl list-x11-keymap-models",
            shell=True,
        )
        .decode("UTF-8")
        .split()
    )
    for i in models:
        try:
            res[i] = _kbmodelmap[i]
        except:
            lp(i + " not in _kbmodelmap", mode="warn")
    if flip:
        res = {model: code for code, model in res.items()}
        _kb_modct = res
    else:
        _kb_modcf = res
    return res


_kb_laycf = None
_kb_layct = None


@catch_exceptions
def kb_layouts(flip: bool = False) -> dict:
    res = {}
    global _kb_laycf, _kb_layct
    if (not flip) and _kb_laycf is not None:
        return _kb_laycf
    elif flip and _kb_layct is not None:
        return _kb_layct
    layouts = (
        subprocess.check_output(
            "localectl list-x11-keymap-layouts",
            shell=True,
        )
        .decode("UTF-8")
        .split()
    )
    if "custom" in layouts:
        layouts.pop(layouts.index("custom"))

    for i in layouts:
        try:
            res[i] = _kblangmap[i]
        except:
            lp(i + " not in _kblangmap", mode="warn")
    if flip:
        res = {lang: code for code, lang in res.items()}
        _kb_layct = res
    else:
        _kb_laycf = res
    return res


@catch_exceptions
def kb_set(
    model: str, layout: str, variant, chroot: bool = False, mnt_dir: str = None
) -> None:
    lp("Setting keyboard layout to: " + model + " - " + layout + " - " + variant)
    if model not in kb_models().keys():
        lp("Keyboard model " + model + " not found!")
        raise TypeError("Keyboard model " + model + " not found!")
    if layout not in kb_layouts().keys():
        lp("Keyboard layout " + layout + " not found!")
        raise TypeError("Keyboard layout " + layout + " not found!")
    if (variant not in [None, "normal"]) and variant not in kb_variants(layout):
        lp("Keyboard layout variant " + variant + " not found!")
        raise TypeError("Keyboard layout variant " + variant + " not found!")
    cmd = ["localectl", "set-x11-keymap", layout, model]
    if variant not in [None, "normal"]:
        cmd.append(variant)
    if chroot:
        kbconf = f"""# Written by systemd-localed(8), read by systemd-localed and Xorg. It's
# probably wise not to edit this file manually. Use localectl(1) to
# update this file.
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "{layout}"
        Option "XkbModel" "{model}"
        Option "XkbVariant" "{variant}"
EndSection
"""
        os.makedirs(mnt_dir + "/etc/X11/xorg.conf.d/", exist_ok=True)
        with open(mnt_dir + "/etc/X11/xorg.conf.d/00-keyboard.conf", "w") as f:
            f.write(kbconf)
    else:
        lrun(cmd)
