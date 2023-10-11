#
# Copyright 2023 BredOS
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

import sys
import gi
import os
import gettext
import babel
import requests
import json
from datetime import date, datetime, time
from babel import dates, numbers
from pyrunning import Command
import config

# from bakery import kb_langs

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Gettext
gettext.bindtextdomain("bakery", "./po")
gettext.textdomain("bakery")
gettext.install("bakery", "./po")
# py file path
script_dir = os.path.dirname(os.path.realpath(__file__))


def kb_langs() -> dict:
    return {
        "Afrikaans": [["fa-olpc", "ps", "ps-olpc", "uz", "uz-olpc"]],
        "Albanian": [["plisi", "veqilharxhi"]],
        "Amharic": [["eastern", "eastern-alt", "phonetic", "phonetic-alt", "western"]],
        "Arabic": [
            [
                "azerty",
                "azerty_digits",
                "buckwalter",
                "digits",
                "mac",
                "olpc",
                "qwerty",
                "qwerty_digits",
            ]
        ],
        "Austrian German": [["mac", "nodeadkeys"]],
        "Australian English": [None],
        "Azerbaijani": [["cyrillic"]],
        "Bosnian": [["alternatequotes", "unicode", "unicodeus", "us"]],
        "Bangla": [["probhat"]],
        "Belgian Dutch": [["iso-alternate", "nodeadkeys", "oss", "oss_latin9", "wang"]],
        "Bulgarian": [["bas_phonetic", "bekl", "phonetic"]],
        "Portuguese (Brazil)": [
            [
                "dvorak",
                "nativo",
                "nativo-epo",
                "nativo-us",
                "nodeadkeys",
                "rus",
                "thinkpad",
            ]
        ],
        "Braille": [
            ["left_hand", "left_hand_invert", "right_hand", "right_hand_invert"]
        ],
        "Bhutanese": [None],
        "Tswana": [None],
        "Belarusian": [["intl", "latin", "legacy", "phonetic", "ru"]],
        "Canadian English": [["eng", "fr-dvorak", "fr-legacy", "ike", "multix"]],
        "Congolese": [None],
        "Swiss German": [
            ["de_mac", "de_nodeadkeys", "fr", "fr_mac", "fr_nodeadkeys", "legacy"]
        ],
        "Cameroonian": [["azerty", "dvorak", "french", "mmuock", "qwerty"]],
        "Chinese": [
            [
                "altgr-pinyin",
                "mon_manchu_galik",
                "mon_todo_galik",
                "mon_trad",
                "mon_trad_galik",
                "mon_trad_manchu",
                "mon_trad_todo",
                "mon_trad_xibe",
                "tib",
                "tib_asciinum",
                "ug",
            ]
        ],
        "Czech": [
            [
                "bksl",
                "dvorak-ucw",
                "qwerty",
                "qwerty-mac",
                "qwerty_bksl",
                "rus",
                "ucw",
                "winkeys",
                "winkeys-qwerty",
            ]
        ],
        "German": [
            [
                "T3",
                "deadacute",
                "deadgraveacute",
                "deadtilde",
                "dsb",
                "dsb_qwertz",
                "dvorak",
                "e1",
                "e2",
                "mac",
                "mac_nodeadkeys",
                "neo",
                "nodeadkeys",
                "qwerty",
                "ro",
                "ro_nodeadkeys",
                "ru",
                "tr",
                "us",
            ]
        ],
        "Danish": [["dvorak", "mac", "mac_nodeadkeys", "nodeadkeys", "winkeys"]],
        "Algerian Arabic": [
            ["ar", "azerty-deadkeys", "ber", "qwerty-gb-deadkeys", "qwerty-us-deadkeys"]
        ],
        "Estonian": [None],
        "Esperanto": [["legacy"]],
        "Spanish": [["ast", "cat", "deadtilde", "dvorak", "nodeadkeys", "winkeys"]],
        "Finnish": [["classic", "mac", "nodeadkeys", "smi", "winkeys"]],
        "Faroese": [["nodeadkeys"]],
        "French": [
            [
                "afnor",
                "azerty",
                "bepo",
                "bepo_afnor",
                "bepo_latin9",
                "bre",
                "dvorak",
                "geo",
                "latin9",
                "latin9_nodeadkeys",
                "mac",
                "nodeadkeys",
                "oci",
                "oss",
                "oss_latin9",
                "oss_nodeadkeys",
                "us",
            ]
        ],
        "British English": [
            [
                "colemak",
                "colemak_dh",
                "dvorak",
                "dvorakukp",
                "extd",
                "gla",
                "intl",
                "mac",
                "mac_intl",
                "pl",
            ]
        ],
        "Georgian": [["ergonomic", "mess", "os", "ru"]],
        "Ghanaian": [
            ["akan", "avn", "ewe", "fula", "ga", "generic", "gillbt", "hausa"]
        ],
        "Guinean": [None],
        "Greek": [["extended", "nodeadkeys", "polytonic", "simple"]],
        "Croatian": [["alternatequotes", "unicode", "unicodeus", "us"]],
        "Hungarian": [
            [
                "101_qwerty_comma_dead",
                "101_qwerty_comma_nodead",
                "101_qwerty_dot_dead",
                "101_qwerty_dot_nodead",
                "101_qwertz_comma_dead",
                "101_qwertz_comma_nodead",
                "101_qwertz_dot_dead",
                "101_qwertz_dot_nodead",
                "102_qwerty_comma_dead",
                "102_qwerty_comma_nodead",
                "102_qwerty_dot_dead",
                "102_qwerty_dot_nodead",
                "102_qwertz_comma_dead",
                "102_qwertz_comma_nodead",
                "102_qwertz_dot_dead",
                "102_qwertz_dot_nodead",
                "nodeadkeys",
                "qwerty",
                "standard",
            ]
        ],
        "Indonesian": [
            ["javanese", "melayu-phonetic", "melayu-phoneticx", "pegon-phonetic"]
        ],
        "Irish": [["CloGaelach", "UnicodeExpert", "ogam", "ogam_is434"]],
        "Hebrew": [["biblical", "lyx", "phonetic"]],
        "Indian English": [
            [
                "ben",
                "ben_baishakhi",
                "ben_bornona",
                "ben_gitanjali",
                "ben_inscript",
                "ben_probhat",
                "bolnagri",
                "eeyek",
                "eng",
                "guj",
                "guj-kagapa",
                "guru",
                "hin-kagapa",
                "hin-wx",
                "iipa",
                "jhelum",
                "kan",
                "kan-kagapa",
                "mal",
                "mal_enhanced",
                "mal_lalitha",
                "mal_poorna",
                "mar-kagapa",
                "marathi",
                "olck",
                "ori",
                "ori-bolnagri",
                "ori-wx",
                "san-kagapa",
                "tam",
                "tam_tamilnumbers",
                "tamilnet",
                "tamilnet_TAB",
                "tamilnet_TSCII",
                "tamilnet_tamilnumbers",
                "tel",
                "tel-kagapa",
                "tel-sarala",
                "urd-phonetic",
                "urd-phonetic3",
                "urd-winkeys",
            ]
        ],
        "Iraqi Arabic": [["ku", "ku_alt", "ku_ara", "ku_f"]],
        "Persian": [["azb", "ku", "ku_alt", "ku_ara", "ku_f", "pes_keypad", "winkeys"]],
        "Icelandic": [["dvorak", "mac", "mac_legacy"]],
        "Italian": [
            ["fur", "geo", "ibm", "intl", "mac", "nodeadkeys", "scn", "us", "winkeys"]
        ],
        "Japanese": [["OADG109A", "dvorak", "kana", "kana86", "mac"]],
        "Kenyan": [["kik"]],
        "Kyrgyz": [["phonetic"]],
        "Khmer": [None],
        "Korean": [["kr104"]],
        "Kazakh": [["ext", "kazrus", "latin", "ruskaz"]],
        "Lao": [["stea"]],
        "Latin American Spanish": [["colemak", "deadtilde", "dvorak", "nodeadkeys"]],
        "Sinhala": [["tam_TAB", "tam_unicode", "us"]],
        "Lithuanian": [["ibm", "lekp", "lekpa", "ratise", "sgs", "std", "us"]],
        "Latvian": [
            [
                "adapted",
                "apostrophe",
                "ergonomic",
                "fkey",
                "modern",
                "modern-cyr",
                "tilde",
            ]
        ],
        "Moroccan Arabic": [
            [
                "french",
                "rif",
                "tifinagh",
                "tifinagh-alt",
                "tifinagh-alt-phonetic",
                "tifinagh-extended",
                "tifinagh-extended-phonetic",
                "tifinagh-phonetic",
            ]
        ],
        "Māori": [None],
        "Moldovan": [["gag"]],
        "Montenegrin": [
            [
                "cyrillic",
                "cyrillicalternatequotes",
                "cyrillicyz",
                "latinalternatequotes",
                "latinunicode",
                "latinunicodeyz",
                "latinyz",
            ]
        ],
        "Macedonian": [["nodeadkeys"]],
        "Malian": [["fr-oss", "us-intl", "us-mac"]],
        "Myanmar": [["mnw", "mnw-a1", "shn", "zawgyi", "zgt"]],
        "Mongolian": [None],
        "Maltese": [["alt-gb", "alt-us", "us"]],
        "Dhivehi": [None],
        "Malay": [["phonetic"]],
        "Nigerian Pidgin": [["hausa", "igbo", "yoruba"]],
        "Dutch": [["mac", "std", "us"]],
        "Norwegian": [
            [
                "colemak",
                "colemak_dh",
                "colemak_dh_wide",
                "dvorak",
                "mac",
                "mac_nodeadkeys",
                "nodeadkeys",
                "smi",
                "smi_nodeadkeys",
                "winkeys",
            ]
        ],
        "Nepali": [None],
        "Filipino": [
            [
                "capewell-dvorak",
                "capewell-dvorak-bay",
                "capewell-qwerf2k6",
                "capewell-qwerf2k6-bay",
                "colemak",
                "colemak-bay",
                "dvorak",
                "dvorak-bay",
                "qwerty-bay",
            ]
        ],
        "Pakistani": [["ara", "snd", "urd-crulp", "urd-nla"]],
        "Polish": [
            [
                "csb",
                "dvorak",
                "dvorak_altquotes",
                "dvorak_quotes",
                "dvp",
                "legacy",
                "qwertz",
                "ru_phonetic_dvorak",
                "szl",
            ]
        ],
        "Portuguese": [
            ["mac", "mac_nodeadkeys", "nativo", "nativo-epo", "nativo-us", "nodeadkeys"]
        ],
        "Romanian": [["std", "winkeys"]],
        "Serbian": [
            [
                "alternatequotes",
                "latin",
                "latinalternatequotes",
                "latinunicode",
                "latinunicodeyz",
                "latinyz",
                "rue",
                "yz",
            ]
        ],
        "Russian": [
            [
                "ab",
                "bak",
                "chm",
                "cv",
                "cv_latin",
                "dos",
                "kom",
                "legacy",
                "mac",
                "os_legacy",
                "os_winkeys",
                "phonetic",
                "phonetic_YAZHERTY",
                "phonetic_azerty",
                "phonetic_dvorak",
                "phonetic_fr",
                "phonetic_winkeys",
                "ruchey_en",
                "ruchey_ru",
                "sah",
                "srp",
                "tt",
                "typewriter",
                "typewriter-legacy",
                "udm",
                "xal",
            ]
        ],
        "Swedish": [
            [
                "dvorak",
                "mac",
                "nodeadkeys",
                "rus",
                "rus_nodeadkeys",
                "smi",
                "svdvorak",
                "swl",
                "us",
                "us_dvorak",
            ]
        ],
        "Slovenian": [["alternatequotes", "us"]],
        "Slovak": [["bksl", "qwerty", "qwerty_bksl"]],
        "Senegalese": [None],
        "Syrian Arabic": [["ku", "ku_alt", "ku_f", "syc", "syc_phonetic"]],
        "Tajik": [["legacy"]],
        "Thai": [["pat", "tis"]],
        "Turkmen": [["alt"]],
        "Turkish": [
            [
                "alt",
                "e",
                "f",
                "intl",
                "ku",
                "ku_alt",
                "ku_f",
                "ot",
                "otf",
                "otk",
                "otkf",
            ]
        ],
        "Taiwanese": [["indigenous", "saisiyat"]],
        "Tanzanian": [None],
        "Ukrainian": [
            [
                "crh",
                "crh_alt",
                "crh_f",
                "homophonic",
                "legacy",
                "macOS",
                "phonetic",
                "typewriter",
                "winkeys",
            ]
        ],
        "American English": [
            [
                "alt-intl",
                "altgr-intl",
                "chr",
                "colemak",
                "colemak_dh",
                "colemak_dh_iso",
                "colemak_dh_ortho",
                "colemak_dh_wide",
                "colemak_dh_wide_iso",
                "dvorak",
                "dvorak-alt-intl",
                "dvorak-classic",
                "dvorak-intl",
                "dvorak-l",
                "dvorak-mac",
                "dvorak-r",
                "dvp",
                "euro",
                "haw",
                "hbs",
                "intl",
                "mac",
                "norman",
                "olpc2",
                "rus",
                "symbolic",
                "workman",
                "workman-intl",
            ]
        ],
        "Uzbek": [["latin"]],
        "Vietnamese": [["fr", "us"]],
        "South African English": [None],
    }


def langs() -> dict:
    return {
        "English": [
            "en_US.UTF-8 UTF-8",
            "en_AG UTF-8",
            "en_AU.UTF-8 UTF-8",
            "en_AU ISO-8859-1",
            "en_BW.UTF-8 UTF-8",
            "en_BW ISO-8859-1",
            "en_CA.UTF-8 UTF-8",
            "en_CA ISO-8859-1",
            "en_DK.UTF-8 UTF-8",
            "en_DK ISO-8859-1",
            "en_GB.UTF-8 UTF-8",
            "en_GB ISO-8859-1",
            "en_HK.UTF-8 UTF-8",
            "en_HK ISO-8859-1",
            "en_IE.UTF-8 UTF-8",
            "en_IE ISO-8859-1",
            "en_IE@euro ISO-8859-15",
            "en_IL UTF-8",
            "en_IN UTF-8",
            "en_NG UTF-8",
            "en_NZ.UTF-8 UTF-8",
            "en_NZ ISO-8859-1",
            "en_PH.UTF-8 UTF-8",
            "en_PH ISO-8859-1",
            "en_SC.UTF-8 UTF-8",
            "en_SG.UTF-8 UTF-8",
            "en_SG ISO-8859-1",
            "en_US.UTF-8 UTF-8",
            "en_US ISO-8859-1",
            "en_ZA.UTF-8 UTF-8",
            "en_ZA ISO-8859-1",
            "en_ZM UTF-8",
            "en_ZW.UTF-8 UTF-8",
            "en_ZW ISO-8859-1",
        ],
        "Afar": [
            "aa_DJ.UTF-8 UTF-8",
            "aa_DJ ISO-8859-1",
            "aa_ER UTF-8",
            "aa_ER@saaho UTF-8",
            "aa_ET UTF-8",
        ],
        "Afrikaans": ["af_ZA.UTF-8 UTF-8", "af_ZA ISO-8859-1"],
        "Akan": ["ak_GH UTF-8"],
        "Amharic": ["am_ET UTF-8"],
        "Aragonese": ["an_ES.UTF-8 UTF-8", "an_ES ISO-8859-15"],
        "Arabic": [
            "ar_AE.UTF-8 UTF-8",
            "ar_AE ISO-8859-6",
            "ar_BH.UTF-8 UTF-8",
            "ar_BH ISO-8859-6",
            "ar_DZ.UTF-8 UTF-8",
            "ar_DZ ISO-8859-6",
            "ar_EG.UTF-8 UTF-8",
            "ar_EG ISO-8859-6",
            "ar_IN UTF-8",
            "ar_IQ.UTF-8 UTF-8",
            "ar_IQ ISO-8859-6",
            "ar_JO.UTF-8 UTF-8",
            "ar_JO ISO-8859-6",
            "ar_KW.UTF-8 UTF-8",
            "ar_KW ISO-8859-6",
            "ar_LB.UTF-8 UTF-8",
            "ar_LB ISO-8859-6",
            "ar_LY.UTF-8 UTF-8",
            "ar_LY ISO-8859-6",
            "ar_MA.UTF-8 UTF-8",
            "ar_MA ISO-8859-6",
            "ar_OM.UTF-8 UTF-8",
            "ar_OM ISO-8859-6",
            "ar_QA.UTF-8 UTF-8",
            "ar_QA ISO-8859-6",
            "ar_SA.UTF-8 UTF-8",
            "ar_SA ISO-8859-6",
            "ar_SD.UTF-8 UTF-8",
            "ar_SD ISO-8859-6",
            "ar_SS UTF-8",
            "ar_SY.UTF-8 UTF-8",
            "ar_SY ISO-8859-6",
            "ar_TN.UTF-8 UTF-8",
            "ar_TN ISO-8859-6",
            "ar_YE.UTF-8 UTF-8",
            "ar_YE ISO-8859-6",
        ],
        "Azerbaijani": ["az_AZ UTF-8", "az_IR UTF-8"],
        "Assamese": ["as_IN UTF-8"],
        "Belarusian": ["be_BY.UTF-8 UTF-8", "be_BY CP1251", "be_BY@latin UTF-8"],
        "Bulgarian": ["bg_BG.UTF-8 UTF-8", "bg_BG CP1251"],
        "Bislama": ["bi_VU UTF-8"],
        "Bengali": ["bn_BD UTF-8", "bn_IN UTF-8"],
        "Tibetan": ["bo_CN UTF-8", "bo_IN UTF-8"],
        "Breton": ["br_FR.UTF-8 UTF-8", "br_FR ISO-8859-1", "br_FR@euro ISO-8859-15"],
        "Bosnian": ["bs_BA.UTF-8 UTF-8", "bs_BA ISO-8859-2"],
        "Catalan": [
            "ca_AD.UTF-8 UTF-8",
            "ca_AD ISO-8859-15",
            "ca_ES.UTF-8 UTF-8",
            "ca_ES ISO-8859-1",
            "ca_ES@euro ISO-8859-15",
            "ca_ES@valencia UTF-8",
            "ca_FR.UTF-8 UTF-8",
            "ca_FR ISO-8859-15",
            "ca_IT.UTF-8 UTF-8",
            "ca_IT ISO-8859-15",
        ],
        "Chechen": ["ce_RU UTF-8"],
        "Czech": ["cs_CZ.UTF-8 UTF-8", "cs_CZ ISO-8859-2"],
        "Chuvash": ["cv_RU UTF-8"],
        "Welsh": ["cy_GB.UTF-8 UTF-8", "cy_GB ISO-8859-14"],
        "Danish": ["da_DK.UTF-8 UTF-8", "da_DK ISO-8859-1"],
        "German": [
            "de_AT.UTF-8 UTF-8",
            "de_AT ISO-8859-1",
            "de_AT@euro ISO-8859-15",
            "de_BE.UTF-8 UTF-8",
            "de_BE ISO-8859-1",
            "de_BE@euro ISO-8859-15",
            "de_CH.UTF-8 UTF-8",
            "de_CH ISO-8859-1",
            "de_DE.UTF-8 UTF-8",
            "de_DE ISO-8859-1",
            "de_DE@euro ISO-8859-15",
            "de_IT.UTF-8 UTF-8",
            "de_IT ISO-8859-1",
            "de_LI.UTF-8 UTF-8",
            "de_LU.UTF-8 UTF-8",
            "de_LU ISO-8859-1",
            "de_LU@euro ISO-8859-15",
        ],
        "Divehi": ["dv_MV UTF-8"],
        "Dzongkha": ["dz_BT UTF-8"],
        "Greek": [
            "el_GR.UTF-8 UTF-8",
            "el_GR ISO-8859-7",
            "el_GR@euro ISO-8859-7",
            "el_CY.UTF-8 UTF-8",
            "el_CY ISO-8859-7",
        ],
        "Spanish": [
            "es_AR.UTF-8 UTF-8",
            "es_AR ISO-8859-1",
            "es_BO.UTF-8 UTF-8",
            "es_BO ISO-8859-1",
            "es_CL.UTF-8 UTF-8",
            "es_CL ISO-8859-1",
            "es_CO.UTF-8 UTF-8",
            "es_CO ISO-8859-1",
            "es_CR.UTF-8 UTF-8",
            "es_CR ISO-8859-1",
            "es_CU UTF-8",
            "es_DO.UTF-8 UTF-8",
            "es_DO ISO-8859-1",
            "es_EC.UTF-8 UTF-8",
            "es_EC ISO-8859-1",
            "es_ES.UTF-8 UTF-8",
            "es_ES ISO-8859-1",
            "es_ES@euro ISO-8859-15",
            "es_GT.UTF-8 UTF-8",
            "es_GT ISO-8859-1",
            "es_HN.UTF-8 UTF-8",
            "es_HN ISO-8859-1",
            "es_MX.UTF-8 UTF-8",
            "es_MX ISO-8859-1",
            "es_NI.UTF-8 UTF-8",
            "es_NI ISO-8859-1",
            "es_PA.UTF-8 UTF-8",
            "es_PA ISO-8859-1",
            "es_PE.UTF-8 UTF-8",
            "es_PE ISO-8859-1",
            "es_PR.UTF-8 UTF-8",
            "es_PR ISO-8859-1",
            "es_PY.UTF-8 UTF-8",
            "es_PY ISO-8859-1",
            "es_SV.UTF-8 UTF-8",
            "es_SV ISO-8859-1",
            "es_US.UTF-8 UTF-8",
            "es_US ISO-8859-1",
            "es_UY.UTF-8 UTF-8",
            "es_UY ISO-8859-1",
            "es_VE.UTF-8 UTF-8",
            "es_VE ISO-8859-1",
        ],
        "Estonian": [
            "et_EE.UTF-8 UTF-8",
            "et_EE ISO-8859-1",
            "et_EE.ISO-8859-15 ISO-8859-15",
        ],
        "Basque": ["eu_ES.UTF-8 UTF-8", "eu_ES ISO-8859-1", "eu_ES@euro ISO-8859-15"],
        "Persian": ["fa_IR UTF-8"],
        "Fulah": ["ff_SN UTF-8"],
        "Finnish": ["fi_FI.UTF-8 UTF-8", "fi_FI ISO-8859-1", "fi_FI@euro ISO-8859-15"],
        "Faroese": ["fo_FO.UTF-8 UTF-8", "fo_FO ISO-8859-1"],
        "French": [
            "fr_BE.UTF-8 UTF-8",
            "fr_BE ISO-8859-1",
            "fr_BE@euro ISO-8859-15",
            "fr_CA.UTF-8 UTF-8",
            "fr_CA ISO-8859-1",
            "fr_CH.UTF-8 UTF-8",
            "fr_CH ISO-8859-1",
            "fr_FR.UTF-8 UTF-8",
            "fr_FR ISO-8859-1",
            "fr_FR@euro ISO-8859-15",
            "fr_LU.UTF-8 UTF-8",
            "fr_LU ISO-8859-1",
            "fr_LU@euro ISO-8859-15",
        ],
        "Western Frisian": ["fy_NL UTF-8", "fy_DE UTF-8"],
        "Irish": ["ga_IE.UTF-8 UTF-8", "ga_IE ISO-8859-1", "ga_IE@euro ISO-8859-15"],
        "Scottish Gaelic": ["gd_GB.UTF-8 UTF-8", "gd_GB ISO-8859-15"],
        "Galician": ["gl_ES.UTF-8 UTF-8", "gl_ES ISO-8859-1", "gl_ES@euro ISO-8859-15"],
        "Gujarati": ["gu_IN UTF-8"],
        "Manx": ["gv_GB.UTF-8 UTF-8", "gv_GB ISO-8859-1"],
        "Hausa": ["ha_NG UTF-8"],
        "Hebrew": ["he_IL.UTF-8 UTF-8", "he_IL ISO-8859-8"],
        "Hindi": ["hi_IN UTF-8"],
        "Croatian": ["hr_HR.UTF-8 UTF-8", "hr_HR ISO-8859-2"],
        "Haitian Creole": ["ht_HT UTF-8"],
        "Hungarian": ["hu_HU.UTF-8 UTF-8", "hu_HU ISO-8859-2"],
        "Armenian": ["hy_AM UTF-8", "hy_AM.ARMSCII-8 ARMSCII-8"],
        "Interlingua": ["ia_FR UTF-8"],
        "Indonesian": ["id_ID.UTF-8 UTF-8", "id_ID ISO-8859-1"],
        "Igbo": ["ig_NG UTF-8"],
        "Inupiaq": ["ik_CA UTF-8"],
        "Icelandic": ["is_IS.UTF-8 UTF-8", "is_IS ISO-8859-1"],
        "Italian": [
            "it_CH.UTF-8 UTF-8",
            "it_CH ISO-8859-1",
            "it_IT.UTF-8 UTF-8",
            "it_IT ISO-8859-1",
            "it_IT@euro ISO-8859-15",
        ],
        "Inuktitut": ["iu_CA UTF-8"],
        "Japanese": ["ja_JP.EUC-JP EUC-JP", "ja_JP.UTF-8 UTF-8"],
        "Georgian": ["ka_GE.UTF-8 UTF-8", "ka_GE GEORGIAN-PS"],
        "Kazakh": ["kk_KZ.UTF-8 UTF-8", "kk_KZ PT154"],
        "Kalaallisut": ["kl_GL.UTF-8 UTF-8", "kl_GL ISO-8859-1"],
        "Khmer": ["km_KH UTF-8"],
        "Kannada": ["kn_IN UTF-8"],
        "Korean": ["ko_KR.EUC-KR EUC-KR", "ko_KR.UTF-8 UTF-8"],
        "Kashmiri": ["ks_IN UTF-8", "ks_IN@devanagari UTF-8"],
        "Kurdish": ["ku_TR.UTF-8 UTF-8", "ku_TR ISO-8859-9"],
        "Cornish": ["kw_GB.UTF-8 UTF-8", "kw_GB ISO-8859-1"],
        "Kyrgyz": ["ky_KG UTF-8"],
        "Luxembourgish": ["lb_LU UTF-8"],
        "Ganda": ["lg_UG.UTF-8 UTF-8", "lg_UG ISO-8859-10"],
        "Limburgish": ["li_BE UTF-8", "li_NL UTF-8"],
        "Lingala": ["ln_CD UTF-8"],
        "Lao": ["lo_LA UTF-8"],
        "Lithuanian": ["lt_LT.UTF-8 UTF-8", "lt_LT ISO-8859-13"],
        "Latvian": ["lv_LV.UTF-8 UTF-8", "lv_LV ISO-8859-13"],
        "Malagasy": ["mg_MG.UTF-8 UTF-8", "mg_MG ISO-8859-15"],
        "Maori": ["mi_NZ.UTF-8 UTF-8", "mi_NZ ISO-8859-13"],
        "Macedonian": ["mk_MK.UTF-8 UTF-8", "mk_MK ISO-8859-5"],
        "Malayalam": ["ml_IN UTF-8"],
        "Mongolian": ["mn_MN UTF-8"],
        "Marathi": ["mr_IN UTF-8"],
        "Malay": ["ms_MY.UTF-8 UTF-8", "ms_MY ISO-8859-1"],
        "Maltese": ["mt_MT.UTF-8 UTF-8", "mt_MT ISO-8859-3"],
        "Burmese": ["my_MM UTF-8"],
        "Norwegian Bokmål": ["nb_NO.UTF-8 UTF-8", "nb_NO ISO-8859-1"],
        "Nepali": ["ne_NP UTF-8"],
        "Dutch": [
            "nl_AW UTF-8",
            "nl_BE.UTF-8 UTF-8",
            "nl_BE ISO-8859-1",
            "nl_BE@euro ISO-8859-15",
            "nl_NL.UTF-8 UTF-8",
            "nl_NL ISO-8859-1",
            "nl_NL@euro ISO-8859-15",
        ],
        "Norwegian Nynorsk": ["nn_NO.UTF-8 UTF-8", "nn_NO ISO-8859-1"],
        "Southern Ndebele": ["nr_ZA UTF-8"],
        "Occitan": ["oc_FR.UTF-8 UTF-8", "oc_FR ISO-8859-1"],
        "Oromo": ["om_ET UTF-8", "om_KE.UTF-8 UTF-8", "om_KE ISO-8859-1"],
        "Oriya": ["or_IN UTF-8"],
        "Ossetic": ["os_RU UTF-8"],
        "Punjabi": ["pa_IN UTF-8", "pa_PK UTF-8"],
        "Polish": ["pl_PL.UTF-8 UTF-8", "pl_PL ISO-8859-2"],
        "Pashto": ["ps_AF UTF-8"],
        "Portuguese": [
            "pt_BR.UTF-8 UTF-8",
            "pt_BR ISO-8859-1",
            "pt_PT.UTF-8 UTF-8",
            "pt_PT ISO-8859-1",
            "pt_PT@euro ISO-8859-15",
        ],
        "Romanian": ["ro_RO.UTF-8 UTF-8", "ro_RO ISO-8859-2"],
        "Russian": [
            "ru_RU.KOI8-R KOI8-R",
            "ru_RU.UTF-8 UTF-8",
            "ru_RU ISO-8859-5",
            "ru_UA.UTF-8 UTF-8",
            "ru_UA KOI8-U",
        ],
        "Kinyarwanda": ["rw_RW UTF-8"],
        "Sanskrit": ["sa_IN UTF-8"],
        "Sardinian": ["sc_IT UTF-8"],
        "Sindhi": ["sd_IN UTF-8", "sd_IN@devanagari UTF-8"],
        "Northern Sami": ["se_NO UTF-8"],
        "Sinhala": ["si_LK UTF-8"],
        "Slovak": ["sk_SK.UTF-8 UTF-8", "sk_SK ISO-8859-2"],
        "Slovenian": ["sl_SI.UTF-8 UTF-8", "sl_SI ISO-8859-2"],
        "Samoan": ["sm_WS UTF-8"],
        "Somali": [
            "so_DJ.UTF-8 UTF-8",
            "so_DJ ISO-8859-1",
            "so_ET UTF-8",
            "so_KE.UTF-8 UTF-8",
            "so_KE ISO-8859-1",
            "so_SO.UTF-8 UTF-8",
            "so_SO ISO-8859-1",
        ],
        "Albanian": ["sq_AL.UTF-8 UTF-8", "sq_AL ISO-8859-1", "sq_MK UTF-8"],
        "Serbian": ["sr_ME UTF-8", "sr_RS UTF-8", "sr_RS@latin UTF-8"],
        "Swati": ["ss_ZA UTF-8"],
        "Southern Sotho": ["st_ZA.UTF-8 UTF-8", "st_ZA ISO-8859-1"],
        "Swedish": [
            "sv_FI.UTF-8 UTF-8",
            "sv_FI ISO-8859-1",
            "sv_FI@euro ISO-8859-15",
            "sv_SE.UTF-8 UTF-8",
            "sv_SE ISO-8859-1",
        ],
        "Swahili": ["sw_KE UTF-8", "sw_TZ UTF-8"],
        "Tamil": ["ta_IN UTF-8", "ta_LK UTF-8"],
        "Telugu": ["te_IN UTF-8"],
        "Tajik": ["tg_TJ.UTF-8 UTF-8", "tg_TJ KOI8-T"],
        "Thai": ["th_TH.UTF-8 UTF-8", "th_TH TIS-620"],
        "Tigrinya": ["ti_ER UTF-8", "ti_ET UTF-8"],
        "Turkmen": ["tk_TM UTF-8"],
        "Tagalog": ["tl_PH.UTF-8 UTF-8", "tl_PH ISO-8859-1"],
        "Tswana": ["tn_ZA UTF-8"],
        "Tongan": ["to_TO UTF-8"],
        "Turkish": [
            "tr_CY.UTF-8 UTF-8",
            "tr_CY ISO-8859-9",
            "tr_TR.UTF-8 UTF-8",
            "tr_TR ISO-8859-9",
        ],
        "Tsonga": ["ts_ZA UTF-8"],
        "Tatar": ["tt_RU UTF-8", "tt_RU@iqtelif UTF-8"],
        "Uighur": ["ug_CN UTF-8"],
        "Ukrainian": ["uk_UA.UTF-8 UTF-8", "uk_UA KOI8-U"],
        "Urdu": ["ur_IN UTF-8", "ur_PK UTF-8"],
        "Uzbek": ["uz_UZ.UTF-8 UTF-8", "uz_UZ ISO-8859-1", "uz_UZ@cyrillic UTF-8"],
        "Venda": ["ve_ZA UTF-8"],
        "Vietnamese": ["vi_VN UTF-8"],
        "Walloon": ["wa_BE ISO-8859-1", "wa_BE@euro ISO-8859-15", "wa_BE.UTF-8 UTF-8"],
        "Wolof": ["wo_SN UTF-8"],
        "Xhosa": ["xh_ZA.UTF-8 UTF-8", "xh_ZA ISO-8859-1"],
        "Yiddish": ["yi_US.UTF-8 UTF-8", "yi_US CP1255"],
        "Yoruba": ["yo_NG UTF-8"],
        "Chinese": [
            "zh_CN.GB18030 GB18030",
            "zh_CN.GBK GBK",
            "zh_CN.UTF-8 UTF-8",
            "zh_CN GB2312",
            "zh_HK.UTF-8 UTF-8",
            "zh_HK BIG5-HKSCS",
            "zh_SG.UTF-8 UTF-8",
            "zh_SG.GBK GBK",
            "zh_SG GB2312",
            "zh_TW.EUC-TW EUC-TW",
            "zh_TW.UTF-8 UTF-8",
            "zh_TW BIG5",
        ],
        "Zulu": ["zu_ZA.UTF-8 UTF-8", "zu_ZA ISO-8859-1"],
    }


def tz_list() -> dict:
    return {
        "Africa": [
            "Abidjan",
            "Accra",
            "Addis_Ababa",
            "Algiers",
            "Asmara",
            "Asmera",
            "Bamako",
            "Bangui",
            "Banjul",
            "Bissau",
            "Blantyre",
            "Brazzaville",
            "Bujumbura",
            "Cairo",
            "Casablanca",
            "Ceuta",
            "Conakry",
            "Dakar",
            "Dar_es_Salaam",
            "Djibouti",
            "Douala",
            "El_Aaiun",
            "Freetown",
            "Gaborone",
            "Harare",
            "Johannesburg",
            "Juba",
            "Kampala",
            "Khartoum",
            "Kigali",
            "Kinshasa",
            "Lagos",
            "Libreville",
            "Lome",
            "Luanda",
            "Lubumbashi",
            "Lusaka",
            "Malabo",
            "Maputo",
            "Maseru",
            "Mbabane",
            "Mogadishu",
            "Monrovia",
            "Nairobi",
            "Ndjamena",
            "Niamey",
            "Nouakchott",
            "Ouagadougou",
            "Porto-Novo",
            "Sao_Tome",
            "Timbuktu",
            "Tripoli",
            "Tunis",
            "Windhoek",
        ],
        "America": [
            "Adak",
            "Anchorage",
            "Anguilla",
            "Antigua",
            "Araguaina",
            "Argentina/Buenos_Aires",
            "Argentina/Catamarca",
            "Argentina/ComodRivadavia",
            "Argentina/Cordoba",
            "Argentina/Jujuy",
            "Argentina/La_Rioja",
            "Argentina/Mendoza",
            "Argentina/Rio_Gallegos",
            "Argentina/Salta",
            "Argentina/San_Juan",
            "Argentina/San_Luis",
            "Argentina/Tucuman",
            "Argentina/Ushuaia",
            "Aruba",
            "Asuncion",
            "Atikokan",
            "Atka",
            "Bahia",
            "Bahia_Banderas",
            "Barbados",
            "Belem",
            "Belize",
            "Blanc-Sablon",
            "Boa_Vista",
            "Bogota",
            "Boise",
            "Buenos_Aires",
            "Cambridge_Bay",
            "Campo_Grande",
            "Cancun",
            "Caracas",
            "Catamarca",
            "Cayenne",
            "Cayman",
            "Chicago",
            "Chihuahua",
            "Ciudad_Juarez",
            "Coral_Harbour",
            "Cordoba",
            "Costa_Rica",
            "Creston",
            "Cuiaba",
            "Curacao",
            "Danmarkshavn",
            "Dawson",
            "Dawson_Creek",
            "Denver",
            "Detroit",
            "Dominica",
            "Edmonton",
            "Eirunepe",
            "El_Salvador",
            "Ensenada",
            "Fort_Nelson",
            "Fort_Wayne",
            "Fortaleza",
            "Glace_Bay",
            "Godthab",
            "Goose_Bay",
            "Grand_Turk",
            "Grenada",
            "Guadeloupe",
            "Guatemala",
            "Guayaquil",
            "Guyana",
            "Halifax",
            "Havana",
            "Hermosillo",
            "Indiana/Indianapolis",
            "Indiana/Knox",
            "Indiana/Marengo",
            "Indiana/Petersburg",
            "Indiana/Tell_City",
            "Indiana/Vevay",
            "Indiana/Vincennes",
            "Indiana/Winamac",
            "Indianapolis",
            "Inuvik",
            "Iqaluit",
            "Jamaica",
            "Jujuy",
            "Juneau",
            "Kentucky/Louisville",
            "Kentucky/Monticello",
            "Knox_IN",
            "Kralendijk",
            "La_Paz",
            "Lima",
            "Los_Angeles",
            "Louisville",
            "Lower_Princes",
            "Maceio",
            "Managua",
            "Manaus",
            "Marigot",
            "Martinique",
            "Matamoros",
            "Mazatlan",
            "Mendoza",
            "Menominee",
            "Merida",
            "Metlakatla",
            "Mexico_City",
            "Miquelon",
            "Moncton",
            "Monterrey",
            "Montevideo",
            "Montreal",
            "Montserrat",
            "Nassau",
            "New_York",
            "Nipigon",
            "Nome",
            "Noronha",
            "North_Dakota/Beulah",
            "North_Dakota/Center",
            "North_Dakota/New_Salem",
            "Nuuk",
            "Ojinaga",
            "Panama",
            "Pangnirtung",
            "Paramaribo",
            "Phoenix",
            "Port-au-Prince",
            "Port_of_Spain",
            "Porto_Acre",
            "Porto_Velho",
            "Puerto_Rico",
            "Punta_Arenas",
            "Rainy_River",
            "Rankin_Inlet",
            "Recife",
            "Regina",
            "Resolute",
            "Rio_Branco",
            "Rosario",
            "Santa_Isabel",
            "Santarem",
            "Santiago",
            "Santo_Domingo",
            "Sao_Paulo",
            "Scoresbysund",
            "Shiprock",
            "Sitka",
            "St_Barthelemy",
            "St_Johns",
            "St_Kitts",
            "St_Lucia",
            "St_Thomas",
            "St_Vincent",
            "Swift_Current",
            "Tegucigalpa",
            "Thule",
            "Thunder_Bay",
            "Tijuana",
            "Toronto",
            "Tortola",
            "Vancouver",
            "Virgin",
            "Whitehorse",
            "Winnipeg",
            "Yakutat",
            "Yellowknife",
        ],
        "Antarctica": [
            "Casey",
            "Davis",
            "DumontDUrville",
            "Macquarie",
            "Mawson",
            "McMurdo",
            "Palmer",
            "Rothera",
            "South_Pole",
            "Syowa",
            "Troll",
            "Vostok",
        ],
        "Arctic": ["Longyearbyen"],
        "Asia": [
            "Aden",
            "Almaty",
            "Amman",
            "Anadyr",
            "Aqtau",
            "Aqtobe",
            "Ashgabat",
            "Ashkhabad",
            "Atyrau",
            "Baghdad",
            "Bahrain",
            "Baku",
            "Bangkok",
            "Barnaul",
            "Beirut",
            "Bishkek",
            "Brunei",
            "Calcutta",
            "Chita",
            "Choibalsan",
            "Chongqing",
            "Chungking",
            "Colombo",
            "Dacca",
            "Damascus",
            "Dhaka",
            "Dili",
            "Dubai",
            "Dushanbe",
            "Famagusta",
            "Gaza",
            "Harbin",
            "Hebron",
            "Ho_Chi_Minh",
            "Hong_Kong",
            "Hovd",
            "Irkutsk",
            "Istanbul",
            "Jakarta",
            "Jayapura",
            "Jerusalem",
            "Kabul",
            "Kamchatka",
            "Karachi",
            "Kashgar",
            "Kathmandu",
            "Katmandu",
            "Khandyga",
            "Kolkata",
            "Krasnoyarsk",
            "Kuala_Lumpur",
            "Kuching",
            "Kuwait",
            "Macao",
            "Macau",
            "Magadan",
            "Makassar",
            "Manila",
            "Muscat",
            "Nicosia",
            "Novokuznetsk",
            "Novosibirsk",
            "Omsk",
            "Oral",
            "Phnom_Penh",
            "Pontianak",
            "Pyongyang",
            "Qatar",
            "Qostanay",
            "Qyzylorda",
            "Rangoon",
            "Riyadh",
            "Saigon",
            "Sakhalin",
            "Samarkand",
            "Seoul",
            "Shanghai",
            "Singapore",
            "Srednekolymsk",
            "Taipei",
            "Tashkent",
            "Tbilisi",
            "Tehran",
            "Tel_Aviv",
            "Thimbu",
            "Thimphu",
            "Tokyo",
            "Tomsk",
            "Ujung_Pandang",
            "Ulaanbaatar",
            "Ulan_Bator",
            "Urumqi",
            "Ust-Nera",
            "Vientiane",
            "Vladivostok",
            "Yakutsk",
            "Yangon",
            "Yekaterinburg",
            "Yerevan",
        ],
        "Atlantic": [
            "Azores",
            "Bermuda",
            "Canary",
            "Cape_Verde",
            "Faeroe",
            "Faroe",
            "Jan_Mayen",
            "Madeira",
            "Reykjavik",
            "South_Georgia",
            "St_Helena",
            "Stanley",
        ],
        "Australia": [
            "ACT",
            "Adelaide",
            "Brisbane",
            "Broken_Hill",
            "Canberra",
            "Currie",
            "Darwin",
            "Eucla",
            "Hobart",
            "LHI",
            "Lindeman",
            "Lord_Howe",
            "Melbourne",
            "NSW",
            "North",
            "Perth",
            "Queensland",
            "South",
            "Sydney",
            "Tasmania",
            "Victoria",
            "West",
            "Yancowinna",
        ],
        "Brazil": ["Acre", "DeNoronha", "East", "West"],
        "Canada": [
            "Atlantic",
            "Central",
            "Eastern",
            "Mountain",
            "Newfoundland",
            "Pacific",
            "Saskatchewan",
            "Yukon",
        ],
        "Chile": ["Continental", "EasterIsland"],
        "Etc": [
            "GMT",
            "GMT+0",
            "GMT+1",
            "GMT+10",
            "GMT+11",
            "GMT+12",
            "GMT+2",
            "GMT+3",
            "GMT+4",
            "GMT+5",
            "GMT+6",
            "GMT+7",
            "GMT+8",
            "GMT+9",
            "GMT-0",
            "GMT-1",
            "GMT-10",
            "GMT-11",
            "GMT-12",
            "GMT-13",
            "GMT-14",
            "GMT-2",
            "GMT-3",
            "GMT-4",
            "GMT-5",
            "GMT-6",
            "GMT-7",
            "GMT-8",
            "GMT-9",
            "GMT0",
            "Greenwich",
            "UCT",
            "UTC",
            "Universal",
            "Zulu",
        ],
        "Europe": [
            "Amsterdam",
            "Andorra",
            "Astrakhan",
            "Athens",
            "Belfast",
            "Belgrade",
            "Berlin",
            "Bratislava",
            "Brussels",
            "Bucharest",
            "Budapest",
            "Busingen",
            "Chisinau",
            "Copenhagen",
            "Dublin",
            "Gibraltar",
            "Guernsey",
            "Helsinki",
            "Isle_of_Man",
            "Istanbul",
            "Jersey",
            "Kaliningrad",
            "Kiev",
            "Kirov",
            "Kyiv",
            "Lisbon",
            "Ljubljana",
            "London",
            "Luxembourg",
            "Madrid",
            "Malta",
            "Mariehamn",
            "Minsk",
            "Monaco",
            "Moscow",
            "Nicosia",
            "Oslo",
            "Paris",
            "Podgorica",
            "Prague",
            "Riga",
            "Rome",
            "Samara",
            "San_Marino",
            "Sarajevo",
            "Saratov",
            "Simferopol",
            "Skopje",
            "Sofia",
            "Stockholm",
            "Tallinn",
            "Tirane",
            "Tiraspol",
            "Ulyanovsk",
            "Uzhgorod",
            "Vaduz",
            "Vatican",
            "Vienna",
            "Vilnius",
            "Volgograd",
            "Warsaw",
            "Zagreb",
            "Zaporozhye",
            "Zurich",
        ],
        "Indian": [
            "Antananarivo",
            "Chagos",
            "Christmas",
            "Cocos",
            "Comoro",
            "Kerguelen",
            "Mahe",
            "Maldives",
            "Mauritius",
            "Mayotte",
            "Reunion",
        ],
        "Mexico": ["BajaNorte", "BajaSur", "General"],
        "Pacific": [
            "Apia",
            "Auckland",
            "Bougainville",
            "Chatham",
            "Chuuk",
            "Easter",
            "Efate",
            "Enderbury",
            "Fakaofo",
            "Fiji",
            "Funafuti",
            "Galapagos",
            "Gambier",
            "Guadalcanal",
            "Guam",
            "Honolulu",
            "Johnston",
            "Kanton",
            "Kiritimati",
            "Kosrae",
            "Kwajalein",
            "Majuro",
            "Marquesas",
            "Midway",
            "Nauru",
            "Niue",
            "Norfolk",
            "Noumea",
            "Pago_Pago",
            "Palau",
            "Pitcairn",
            "Pohnpei",
            "Ponape",
            "Port_Moresby",
            "Rarotonga",
            "Saipan",
            "Samoa",
            "Tahiti",
            "Tarawa",
            "Tongatapu",
            "Truk",
            "Wake",
            "Wallis",
            "Yap",
        ],
        "US": [
            "Alaska",
            "Aleutian",
            "Arizona",
            "Central",
            "East-Indiana",
            "Eastern",
            "Hawaii",
            "Indiana-Starke",
            "Michigan",
            "Mountain",
            "Pacific",
            "Samoa",
        ],
    }


def geoip() -> dict:
    if True:
        tz_data = requests.get("https://geoip.kde.org/v1/timezone").json()
        region, zone = tz_data["time_zone"].split("/")
        return {"region": region, "zone": zone}
    else:
        return config.timezone


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app) -> None:
        self.create_action("about", self.on_about_action)

    def do_activate(self) -> None:
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = BakeryWindow(application=self)
        win.present()

    def on_preferences_action(self, widget, _) -> None:
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, _) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="BredOS Installer",
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            version="0.1.0",
            developers=["Panda", "bill88t"],
            copyright="© 2023 BredOS",
            comments="BredOS Installer is a simple installer for BredOS.",
            license_type=Gtk.License.GPL_3_0,
            website="https://BredOS.org",
        )
        about.present()
        print(BakeryWindow.collect_data())

    def create_action(self, name, callback, shortcuts=None) -> None:
        """Add an application action.
        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


@Gtk.Template.from_file(script_dir + "/data/window.ui")
class BakeryWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BakeryWindow"

    stack1 = Gtk.Template.Child()
    stack1_sidebar = Gtk.Template.Child()
    cancel_btn = Gtk.Template.Child()
    back_btn = Gtk.Template.Child()
    next_btn = Gtk.Template.Child()

    main_stk = Gtk.Template.Child()
    offline_install = Gtk.Template.Child()
    online_install = Gtk.Template.Child()
    custom_install = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # go to the first page of main stack
        self.main_stk.set_visible_child_name("main_page")

        self.online_install.connect("clicked", self.main_button_clicked)
        self.offline_install.connect("clicked", self.main_button_clicked)
        self.custom_install.connect("clicked", self.main_button_clicked)

        self.next_btn.connect("clicked", self.on_next_clicked)
        self.back_btn.connect("clicked", self.on_back_clicked)
        self.cancel_btn.connect("clicked", self.on_cancel_clicked)

    def main_button_clicked(self, button) -> None:
        if button == self.online_install:
            print("online install")
            self.init_screens("online")
        elif button == self.offline_install:
            print("offline install")
            self.init_screens("offline")
        elif button == self.custom_install:
            print("custom install")
            self.init_screens("custom")

    def on_next_clicked(self, button) -> None:
        num_pages = len(self.pages)
        if self.current_page < num_pages - 1:
            self.current_page += 1
            page_name = self.pages[self.current_page]
            page_id = self.get_page_id(page_name)
            self.stack1.set_visible_child_name(page_id)
            self.update_buttons()

    def on_back_clicked(self, button) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            page_name = self.pages[self.current_page]
            page_id = self.get_page_id(page_name)
            self.stack1.set_visible_child_name(page_id)
            self.update_buttons()

    def update_buttons(self) -> None:
        num_pages = len(self.pages)
        self.next_btn.set_sensitive(self.current_page < num_pages - 1)
        self.back_btn.set_sensitive(self.current_page > 0)

    def on_cancel_clicked(self, button) -> None:
        self.main_stk.set_visible_child_name("main_page")
        # remove all pages from stack1
        for page in self.pages:
            page_id = self.get_page_id(page)
            self.stack1.remove(self.stack1.get_child_by_name(page_id))

    def get_page_id(self, page_name) -> str:
        return config.pages[page_name]

    @staticmethod
    def collect_data() -> dict:
        data = {}
        # From kb_screen
        data["layout"] = layout
        data["locale"] = locale
        data["user"] = user_screen.collect_data(user_screen)
        print(data)
        return data

    def set_list_text(list, string) -> None:
        n = list.get_n_items()
        if n > 0:
            list.splice(0, n, [string])
        else:
            list.append(string)

    def add_page(self, stack, page) -> None:
        stack.add_titled(
            globals()[config.pages[page]](window=self), config.pages[page], page
        )

    def init_screens(self, install_type) -> None:
        if install_type == "online":
            self.pages = config.online_pages
            for page in self.pages:
                self.add_page(self.stack1, page)

        elif install_type == "offline":
            for page in config.offline_pages:
                self.pages = config.offline_pages
                self.add_page(self.stack1, page)

        self.current_page = 0
        self.update_buttons()
        self.install_type = install_type
        self.main_stk.set_visible_child_name("install_page")
        # for testing


@Gtk.Template.from_file(script_dir + "/data/kb_screen.ui")
class kb_screen(Adw.Bin):
    __gtype_name__ = "kb_screen"

    event_controller = Gtk.EventControllerKey.new()
    langs_list = Gtk.Template.Child()  # GtkListBox

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.kb_data = kb_langs()  # {country: layouts in a list]}
        global layout
        layout = None
        builder = Gtk.Builder.new_from_file(script_dir + "/data/kb_dialog.ui")

        self.variant_dialog = builder.get_object("variant_dialog")

        self.variant_dialog.set_transient_for(self.window)
        self.variant_dialog.set_modal(self.window)

        self.select_variant_btn = builder.get_object("select_variant_btn")
        self.variant_list = builder.get_object("variant_list")  # GtkListBox

        self.select_variant_btn.connect("clicked", self.confirm_selection)
        self.populate_layout_list()

    def populate_layout_list(self) -> None:
        for lang in self.kb_data:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

    def confirm_selection(self, *_) -> None:
        self.variant_dialog.hide()

    def set_layout(self, layout) -> None:
        raise NotImplementedError

    def show_dialog(self, *_) -> None:
        self.variant_dialog.present()

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            layouts = self.kb_data[lang]
            if layouts[0] is None:
                print("no layouts")
            else:
                # clear the listbox
                self.variant_list.remove_all()
                for layout_ in layouts[0]:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    layout_label = Gtk.Label(label=f"{lang} - {layout_}")
                    newrow.set_child(layout_label)

                    self.variant_list.append(newrow)
                    self.variant_list.connect("row-activated", self.selected_layout)
                    self.last_selected_layout = None

                self.show_dialog()

    def selected_layout(self, widget, row) -> None:
        if row != self.last_selected_layout:
            self.last_selected_layout = row
            layout = row.get_child().get_label()


@Gtk.Template.from_file(script_dir + "/data/locale_screen.ui")
class locale_screen(Adw.Bin):
    __gtype_name__ = "locale_screen"

    langs_list = Gtk.Template.Child()
    date_preview = Gtk.Template.Child()
    currency_preview = Gtk.Template.Child()

    locale_dialog = Gtk.Template.Child()
    locales_list = Gtk.Template.Child()
    select_locale_btn = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.lang_data = langs()  # {country: layouts in a list]}

        self.update_previews("en_US")
        self.populate_locales_list()
        self.select_locale_btn.connect("clicked", self.hide_dialog)

    def populate_locales_list(self) -> None:
        for lang in self.lang_data:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            print(lang)
            if len(self.lang_data[lang]) == 1:
                self.update_previews(self.lang_data[lang][0])
            else:
                # clear the listbox
                self.locales_list.remove_all()
                for locale in langs()[lang]:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    locale_label = Gtk.Label(label=locale)
                    newrow.set_child(locale_label)

                    self.locales_list.append(newrow)
                    self.locales_list.connect("row-activated", self.selected_locale)
                    self.show_dialog()
                    self.last_selected_locale = None

    def selected_locale(self, widget, row) -> None:
        if row != self.last_selected_locale:
            self.last_selected_locale = row
            self.update_previews(row.get_child().get_label())

    def update_previews(self, selected_locale) -> None:
        try:
            the_locale, encoding = selected_locale.split(" ")
            if not encoding == "UTF-8":
                the_locale += "." + encoding
        except ValueError:
            the_locale = selected_locale
        global locale
        locale = the_locale
        locale_ = babel.Locale.parse(the_locale)
        date = dates.format_date(date=datetime.utcnow(), format="full", locale=locale_)
        time = dates.format_time(time=datetime.utcnow(), format="full", locale=locale_)
        currency = numbers.get_territory_currencies(locale_.territory)[0]
        currency_format = numbers.format_currency(1234.56, currency, locale=locale_)
        number_format = numbers.format_decimal(1234567.89, locale=locale_)
        self.date_preview.set_label(time + "  -  " + date)
        self.currency_preview.set_label(number_format + "  -  " + currency_format)

    def hide_dialog(self, *_) -> None:
        self.locale_dialog.hide()

    def show_dialog(self, *_) -> None:
        self.locale_dialog.present()


@Gtk.Template.from_file(script_dir + "/data/user_screen.ui")
class user_screen(Adw.Bin):
    __gtype_name__ = "user_screen"

    user_entry = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    pass_entry = Gtk.Template.Child()
    confirm_pass_entry = Gtk.Template.Child()
    pass_match = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        self.username = None
        self.hostname = None
        self.password = None

        self.confirm_pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.pass_match_is_visible = False

    def on_confirm_pass_changed(self, entry):
        pass_text = self.pass_entry.get_text()
        confirm_pass_text = entry.get_text()
        if self.pass_match_is_visible == False:
            self.pass_match.set_visible(True)
            self.pass_match_is_visible = True

        if pass_text == confirm_pass_text:
            self.pass_match.set_label("✅ Passwords match")
        else:
            self.pass_match.set_label("❌ Passwords do not match")

    def get_username(self) -> str:
        try:
            return self.user_entry.get_text()
        except AttributeError:
            return None

    def get_hostname(self) -> str:
        try:
            return self.hostname_entry.get_text()
        except AttributeError:
            return None

    def get_password(self) -> str:
        try:
            return self.pass_entry.get_text()
        except AttributeError:
            return None

    def collect_data(self) -> dict:
        data = {}
        data["username"] = self.get_username()
        data["hostname"] = self.get_hostname()
        data["password"] = self.get_password()
        return data


# @Gtk.Template.from_file(script_dir + "/data/de_screen.ui")
# class de_screen(Adw.Bin):
#     __gtype_name__ = "de_screen"

#     def __init(self, window, **kwargs) -> None:
#         super().__init__(**kwargs)
#         self.window = window


@Gtk.Template.from_file(script_dir + "/data/timezone_screen.ui")
class timezone_screen(Adw.Bin):
    __gtype_name__ = "timezone_screen"

    regions_list = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        current_timezone = geoip()

    # def populate_regions_list(self) -> None:
    #     self.


app = BakeryApp(application_id="org.bredos.bakery")
app.run(sys.argv)
