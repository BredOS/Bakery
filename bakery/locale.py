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

from bredos.utilities import catch_exceptions
from bakery import lrun, lp, _, dryrun
from .iso import run_chroot_cmd

_langmap = {
    "aa": "Afar",
    "af": "Afrikaans",
    "am": "Amharic",
    "an": "Aragonese",
    "ak": "Akan",
    "ar": "Arabic",
    "as": "Assamese",
    "ast": "Asturian",
    "az": "Azerbaijani",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bi": "Bislama",
    "bn": "Bengali",
    "bo": "Tibetan",
    "br": "Breton",
    "bs": "Bosnian",
    "ca": "Catalan",
    "ce": "Chechen",
    "cs": "Czech",
    "cv": "Chuvash",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "dv": "Divehi",
    "dz": "Dzongkha",
    "el": "Greek",
    "en": "English",
    "eo": "Esperanto",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "ff": "Fulah",
    "fil": "Filipino",
    "fo": "Faroese",
    "fr": "French",
    "fy": "Western Frisian",
    "ga": "Irish",
    "gd": "Scottish Gaelic",
    "gl": "Galician",
    "gu": "Gujarati",
    "gv": "Manx",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "ht": "Haitian Creole",
    "hu": "Hungarian",
    "hy": "Armenian",
    "ia": "Interlingua",
    "id": "Indonesian",
    "ig": "Igbo",
    "ik": "Inupiaq",
    "is": "Icelandic",
    "it": "Italian",
    "iu": "Inuktitut",
    "ja": "Japanese",
    "ka": "Georgian",
    "kab": "Kabyle",
    "kl": "Kalaallisut",
    "kk": "Kazakh",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "kok": "Konkani",
    "ks": "Kashmiri",
    "ku": "Kurdish",
    "kw": "Cornish",
    "kv": "Komi",
    "ky": "Kyrgyz",
    "lb": "Luxembourgish",
    "ln": "Lingala",
    "lo": "Lao",
    "lg": "Ganda",
    "li": "Limburgish",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mai": "Maithili",
    "mg": "Malagasy",
    "mhr": "Eastern Mari",
    "mi": "Maori",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "my": "Burmese",
    "nb": "Norwegian Bokmål",
    "nds": "Low German",
    "ne": "Nepali",
    "nl": "Dutch",
    "nn": "Norwegian Nynorsk",
    "nr": "Southern Ndebele",
    "nso": "Northern Sotho",
    "oc": "Occitan",
    "om": "Oromo",
    "or": "Oriya",
    "os": "Ossetic",
    "pa": "Punjabi",
    "pl": "Polish",
    "ps": "Pashto",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "rw": "Kinyarwanda",
    "sa": "Sanskrit",
    "sc": "Sardinian",
    "sd": "Sindhi",
    "se": "Northern Sami",
    "sm": "Samoan",
    "so": "Somali",
    "shs": "Shuswap",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian",
    "ss": "Swati",
    "su": "Basa Sunda",
    "st": "Southern Sotho",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "ti": "Tigrinya",
    "to": "Tongan",
    "te": "Telugu",
    "tg": "Tajik",
    "th": "Thai",
    "tk": "Turkmen",
    "tl": "Tagalog",
    "tn": "Tswana",
    "tr": "Turkish",
    "ts": "Tsonga",
    "tt": "Tatar",
    "ug": "Uighur",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "ve": "Venda",
    "vi": "Vietnamese",
    "wa": "Walloon",
    "wae": "Walser",
    "wo": "Wolof",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "yue": "Yue Chinese",
    "zh": "Chinese",
    "zu": "Zulu",
}


@catch_exceptions
def locales(
    only_enabled: bool = False, chroot: bool = False, mnt_dir: str = None
) -> list:
    """
    Returns all possible locales.

    Uses /etc/locale.gen since there is no standard on arm.
    """
    if chroot:
        file = mnt_dir + "/etc/locale.gen"
    else:
        file = "/etc/locale.gen"
    with open(file) as localef:
        data = localef.read().split("\n")
        for i in range(len(data) - 1, -1, -1):
            if (
                len(data[i]) < 4
                or (data[i][2] != "_" and data[i][3] != "_")
                or (only_enabled and data[i][0] == "#")
                or "@" in data[i]
                or "UTF-8" not in data[i]
            ):
                data.pop(i)  # remove non-locale / disabled locale on only_enabled
        for i in range(len(data)):
            data[i] = data[i].replace("#", "").replace("  ", "")  # cleanup
        return set(data)


@catch_exceptions
def enable_locales(to_en: list, chroot: bool = False, mnt_dir: str = None) -> None:
    to_add = set()
    enabled = locales(True, chroot, mnt_dir)
    all_loc = locales(chroot=chroot, mnt_dir=mnt_dir)
    for locale in to_en:
        if locale not in enabled:
            if locale in all_loc:
                to_add.add(locale)
            else:
                raise OSError("Invalid locale: " + locale)
        else:
            lp("Locale " + locale + " already enabled")
    if len(to_add):
        for i in to_add:  # Why fumble with stacked \\n? Just spam a bit.
            lp("Enabling locale: " + i)
            if chroot:
                run_chroot_cmd(
                    mnt_dir, ["bash", "-c", "echo " + i + ">> /etc/locale.gen"]
                )
            else:
                lrun(["bash", "-c", "echo " + i + ">> /etc/locale.gen"])
        lp("Generating locales")
        if chroot:
            run_chroot_cmd(mnt_dir, ["locale-gen"])
        else:
            lrun(["locale-gen"])
    else:
        lp("No locales were enabled, not regenerating locale database.")


@catch_exceptions
def set_locale(locale: str, chroot: bool = False, mnt_dir: str = None) -> None:
    if locale not in locales(True, chroot, mnt_dir):
        if dryrun:
            lp("The locale " + locale + " is not enabled, but this is a dryrun.")
        else:
            raise OSError("Locale " + locale + " not enabled!")
    lc = locale.split(" ")[0]
    lp("Setting locale to: " + lc)
    if chroot:
        run_chroot_cmd(
            mnt_dir,
            [
                "bash",
                "-c",
                "echo LANG=" + lc + " > /etc/locale.conf",
            ],
        )
    else:
        lrun(["localectl", "set-locale", "LANG=" + lc])
        lrun(
            [
                "bash",
                "-c",
                "echo LANG=" + lc + " > /etc/locale.conf",
            ]
        )


@catch_exceptions
def langs(only_enabled: bool = False) -> dict:
    """
    A formatted dict of languages and locales

    {language: [locale1, locale2], ...}
    """
    data = locales(only_enabled)
    res = {}
    for i in data:
        lang = _langmap[i[: i.find("_")]]
        if lang in res.keys():
            res[lang].append(i)
        else:
            res[lang] = [i]
    return res
