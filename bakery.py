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
import toml
import subprocess
import os
import gettext
from time import sleep, monotonic
from pathlib import Path
import socket
from datetime import datetime
import requests
import json
from traceback import print_exception
from threading import Lock
from functools import wraps

from pyrunning import logging, LogMessage, LoggingHandler, Command, LoggingLevel
import gi

gi.require_version("NM", "1.0")
from gi.repository import GLib, NM

import config


# Config functions

# Config spec
#
# author = str | Author of the config
# title = str | A title for the config.
# config_version = int | Used to test if this config is compatible.
# uninstall_upon_completion = bool | Remove bakery on completion.
# headless = bool | Do not ask or wait for any user confirmation.
#
# [gui]
# logo = str | Used to override the BredOS logo
#
# [settings]
# lang = str | Main display language ex. "en_us"
# kb_lang = list | Languages to be added to the keyboard.
#
# region = str | Region identifier.
# timezone = str | Timezone identifier.
#
# use_ntp = bool | Use network provided time.
#
# user = false / str | The configured username. Pass false to ask for input.
# passwd = false / str | Pass an empty string to disable or false to ask for input.
# ssh_pub = false / str | Install a pubkey in the user's home and enable sshd key login.
#                       | If a key is installed, password entry via ssh is disabled.
# root_passwd = false / str | Pass an empty string to disable root login or false to ask for input.
#
# [apps]
# app_selection = list | Apps selected to be installed.
# greeter_enable = false / str | Which greeter to enable.
#                             | Use None to boot to tty.
# [postint]
# type = int | Type of post-installation script to run.
#            | 0 for none, 1 for local / remote script, 2 for a set of commands.
# data = false / str / list | For 0, 1, 2 respectively.


dryrun = False if "DO_DRYRUN" not in os.listdir() else True

defer = []


# Timer functions

_stimer = monotonic()


def reset_timer() -> None:
    global _stimer
    _stimer = monotonic()


def get_timer() -> float:
    return monotonic() - _stimer


# Translations


def setup_translations(lang: object = None) -> gettext.GNUTranslations:
    """
    Setup translations

        Does the following:
        - Loads the translations from the locale folder
        - Sets the translations for the gettext module

        Returns:  A gettext translation object
        :rtype: object
    """
    lang_path = os.path.join(os.path.dirname(__file__), "locale")
    # Load translations
    if lang is not None:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        translation = gettext.translation("bakery", lang_path, languages=[lang])
        translation.install()
        return translation.gettext  # type: ignore
    else:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        return gettext.gettext  # type: ignore


_ = None

# Logging

logging_handler = None
st_msgs = []


def populate_messages(lang=None) -> None:
    global _
    _ = setup_translations(lang=lang)
    global st_msgs
    st_msgs.clear()
    st_msgs += [
        [_("Preparing for installation"), 0],  # 0
        [_("Applying Locale Settings"), 10],  # 1
        [_("Applying Keyboard Settings"), 20],  # 2
        [_("Applying Timezone Settings"), 30],  # 3
        [_("Creating User account"), 40],  # 4
        [_("Setting Hostname"), 50],  # 5
        [_("Finalizing installation"), 90],  # 6
        [_("Cleaning up installation"), 100],  # 7
    ]


populate_messages()


def lp(message, mode="info") -> None:
    if mode == "info":
        LogMessage.Info(message).write(logging_handler=logging_handler)
    elif mode == "debug":
        LogMessage.Debug(message).write(logging_handler=logging_handler)
    elif mode == "warn":
        LogMessage.Warning(message).write(logging_handler=logging_handler)
    elif mode == "crit":
        LogMessage.Critical(message).write(logging_handler=logging_handler)
    elif mode == "error":
        LogMessage.Error(message).write(logging_handler=logging_handler)
    elif mode == "exception":
        LogMessage.Exception(message).write(logging_handler=logging_handler)

    else:
        raise ValueError("Invalid mode.")


def st(msg_id: int) -> None:
    sleep(0.2)
    lp("%ST" + str(msg_id) + "%")
    sleep(0.2)


def console_logging(
    logging_level: int,
    message: str,
    *args,
    loginfo_filename="",
    loginfo_line_number=-1,
    loginfo_function_name="",
    loginfo_stack_info=None,
    **kwargs,
) -> None:
    logging_level_name = LoggingLevel(logging_level).name
    pos = message.find("%ST")
    if pos != -1:
        prs = message.rfind("%")
        stm = st_msgs[int(message[pos + 3 : prs])]
        lp("STATUS  : " + stm[0])
        lp("PROGRESS: " + str(stm[1]) + "%")


log_path = None


def setup_logging() -> logging.Logger:
    """
    Setup logging

        Does the following:
        - Creates a logger with a name
        - Sets the format for the logs
        - Sets up logging to a file and future console
    """

    logger = logging.getLogger("bredos-bakery")
    logger.setLevel(logging.DEBUG)
    if dryrun:
        log_dir = os.path.abspath(os.path.join("."))
        log_file = os.path.abspath(os.path.join(log_dir, "DRYRUN.log"))
    else:
        log_dir = os.path.join(os.path.expanduser("~"), ".bredos", "bakery", "logs")
        log_file = os.path.join(
            log_dir, datetime.now().strftime("BAKERY-%Y-%m-%d-%H-%M-%S.log")
        )
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.isdir(log_dir):
            raise FileNotFoundError("The directory {} does not exist".format(log_dir))
        # get write perms
        elif not os.access(log_dir, os.W_OK):
            raise PermissionError(
                "You do not have permission to write to {}".format(log_dir)
            )
    except Exception as e:
        print_exception(type(e), e, e.__traceback__)
        exit(1)

    print("Logging to:", log_file)
    global log_path
    log_path = log_file
    rm_old_logs(log_dir, keep=5)

    log_file_handler = logging.FileHandler(log_file)
    log_file_handler.setLevel(logging.DEBUG)
    log_file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)8s] %(message)s",
    )
    log_file_handler.setFormatter(log_file_formatter)
    logger.addHandler(log_file_handler)

    log_error_handler = logging.StreamHandler()
    log_error_handler.setLevel(logging.INFO)
    log_error_formatter = logging.Formatter("%(levelname)8s: %(message)s")
    log_error_handler.setFormatter(log_error_formatter)
    logger.addHandler(log_error_handler)
    return logger


def rm_old_logs(log_dir_path: str, keep: int) -> None:
    for i in os.listdir(log_dir_path):
        if i.startswith("BAKERY" if not dryrun else "DRYRUN"):
            os.remove(f"{log_dir_path}/{i}")


def copy_logs(new_usern: str) -> None:
    if dryrun:
        lp("Would have synced and copied logs.")
        return
    subprocess.run("sync")
    subprocess.run(
        [
            "sudo",
            "cp",
            "-vr",
            "/home/bred/.bredos",
            "/home/" + new_usern + "/.bredos",
        ]
    )
    subprocess.run(
        [
            "sudo",
            "chown",
            "-R",
            new_usern + ":" + new_usern,
            "/home/" + new_usern + "/.bredos",
        ]
    )


# Logger config


print("Starting logger..")
logger = setup_logging()
logging_handler = LoggingHandler(
    logger=logger,
    logging_functions=[console_logging],
)


def lrun(cmd: list, force: bool = False, silent: bool = False) -> None:
    if dryrun and not force:
        lp("Would have run: " + " ".join(cmd))
    else:
        if not silent:
            Command(cmd).run_log_and_wait(logging_handler=logging_handler)
        else:
            Command(cmd).run_and_wait()


lp("Logger initialized.")
lp("Dry run = " + str(dryrun))


# TOML


def check_override_config() -> bool:
    # check if a /boot/override.toml exists.
    try:
        with open("/boot/override.toml"):
            pass
        return True
    except:
        return False


def load_config(file_path: str = "/bakery/config.toml") -> dict:
    # Load a config file as a dict.
    lp("Loaded config: " + file_path)
    return toml.load(file_path)


def export_config(config: dict, file_path: str = "/bakery/output.toml") -> bool:
    # Export a config file from a stored config dict.
    try:
        with open(file_path, "w") as f:
            lp("Exporting config to: " + file_path)
            f.write(toml.dumps(config))
    except:
        return False
    return True


# Networking functions


def test_up(hostport: tuple) -> bool:
    if not networking_up():
        return False
    try:
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(hostport)
        return True
    except:
        return False


def networking_up() -> bool:
    # Tests if an interface is connected.
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() in ["wifi", "ethernet"]
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False


def internet_up() -> bool:
    res = False
    for i in [
        ("8.8.8.8", 53),
        ("9.9.9.9", 53),
        ("1.1.1.1", 53),
        ("130.61.177.30", 443),
    ]:
        res = test_up(i)
        if res:
            break
    lp("Internet status: " + str(res))
    return res


def geoip() -> dict:
    try:
        if not internet_up():
            raise OSError
        tz_data = requests.get("https://geoip.kde.org/v1/timezone").json()
        region, zone = tz_data["time_zone"].split("/")
        return {"region": region, "zone": zone}
    except:
        return config.timezone


def ethernet_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "ethernet":
            return True
    return False


def ethernet_connected() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() == "ethernet"
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False


def wifi_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "wifi":
            return True
    return False


def wifi_connected() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if (
            device.get_type_description() == "wifi"
            and device.get_state().value_nick == "activated"
        ):
            return True
    return False


def open_nm_settings() -> None:
    # Opens whichever gui for network settings is found.
    pass


def check_updated() -> bool:
    # Check if bakery version has chanced in pacman.
    return False


def nmtui() -> None:
    # Opens nmtui for network settings configurations.
    st = True
    while st:
        subprocess.run(["nmtui"])
        while st:
            try:
                if not internet_up():
                    print("\nWARNING: The internet is still unreachable.")
                res = input("Do you want to run nmtui again? (Y/N): ")
                if res in ["n", "N"]:
                    st = False
                elif res in ["y", "Y"]:
                    break
            except:
                pass


# Locale functions

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


def locales(only_enabled: bool = False) -> list:
    """
    Returns all possible locales.

    Uses /etc/locale.gen since there is no standard on arm.
    """
    with open("/etc/locale.gen") as localef:
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


def enable_locales(to_en: list) -> None:
    to_add = set()
    enabled = locales(True)
    all_loc = locales()
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
            lrun(["sudo", "bash", "-c", "echo " + i + ">> /etc/locale.gen"])
        lp("Generating locales")
        lrun(["sudo", "locale-gen"])
    else:
        lp("No locales were enabled, not regenerating locale database.")


def set_locale(locale: str) -> None:
    if locale not in locales(True):
        if dryrun:
            lp("The locale " + locale + " is not enabled, but this is a dryrun.")
        else:
            raise OSError("Locale " + locale + " not enabled!")
    lc = locale.split(" ")[0]
    lp("Setting locale to: " + lc)
    lrun(["sudo", "localectl", "set-locale", "LANG=" + lc])
    lrun(
        [
            "sudo",
            "bash",
            "-c",
            "echo LANG=" + lc + " > /etc/locale.conf",
        ]
    )


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


def kb_set(model: str, layout: str, variant) -> None:
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
    cmd = ["sudo", "localectl", "set-x11-keymap", layout, model]
    if variant not in [None, "normal"]:
        cmd.append(variant)
    lrun(cmd)


def tz_list() -> dict:
    res = {}
    data = (
        subprocess.check_output(["timedatectl", "list-timezones"])
        .decode("UTF-8")
        .split()
    )
    for i in data:
        if "/" in i:
            cont = i[: i.find("/")]
            if cont not in res.keys():
                res[cont] = []
            res[cont].append(i[i.find("/") + 1 :])
    return res


def tz_set(region: str, zone: str) -> None:
    tzs = tz_list()
    if region in tzs.keys() and zone in tzs[region]:
        lrun(["sudo", "timedatectl", "set-timezone", region + "/" + zone])
    else:
        lp("Timezone " + region + "/" + zone + " not a valid timezone!")
        raise TypeError("Timezone " + region + "/" + zone + " not a valid timezone!")


def tz_ntp(ntp: bool) -> None:
    lp("Setting ntp to " + str(ntp))
    lrun(["sudo", "timedatectl", "set-ntp", str(int(ntp))])


# Package functions


def ensure_localdb(retries: int = 3) -> None:
    if not internet_up():
        raise OSError("Internet Unavailable.")
    tried = 0
    while tried < retries:
        lrun(["sudo", "pacman", "-Sy"], force=True)
        if len(os.listdir("/var/lib/pacman/sync/")):
            break
        tried += 1
    if not len(os.listdir("/var/lib/pacman/sync/")):
        raise OSError("Could not update databases.")


def package_desc(packages: list) -> dict:
    ensure_localdb()
    res = {}
    if len(packages):
        outp = (
            subprocess.check_output(["pacman", "-Si"] + packages)
            .decode("UTF-8")
            .split()
        )
        cindex = 0
        cur_desc = ""
        cur_pkg = None
        in_desc = False
        while cindex < len(outp):
            if (not in_desc) and outp[cindex] == "Name" and outp[cindex + 1] == ":":
                cur_pkg = outp[cindex + 2]
                cindex += 3
            if (
                (not in_desc)
                and outp[cindex] == "Description"
                and outp[cindex + 1] == ":"
            ):
                cindex += 1
                in_desc = True
            elif in_desc:
                if outp[cindex] == "Architecture" and outp[cindex + 1] == ":":
                    if cur_pkg in packages:
                        res[cur_pkg] = cur_desc
                    in_desc = False
                    cur_desc = ""
                else:
                    cur_desc += (" " if len(cur_desc) else "") + outp[cindex]
            cindex += 1
    return res


# Device functions


def detect_install_source() -> str:
    with open("/proc/cmdline", "r") as cmdline_file:
        cmdline = cmdline_file.read()
        if "archisobasedir" in cmdline or "archisolabel" in cmdline:
            return "from_iso"
        else:
            return "on_device"


def detect_install_device() -> str:
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as model_file:
            return model_file.read().rstrip("\n")
    except FileNotFoundError:
        try:
            with open("/sys/class/dmi/id/product_name", "r") as product_name_file:
                return product_name_file.read().rstrip("\n")
        except FileNotFoundError:
            return "unknown"


def enable_services(services: list) -> None:
    try:
        for i in services:
            lrun(["sudo", "systemctl", "enable", i], silent=True)
    except:
        pass


def final_setup() -> None:
    lrun(["sudo", "systemctl", "disable", "resizefs.service"], silent=True)
    enable_services(
        ["bluetooth.service", "fstrim.timer", "oemcleanup.service", "cups.socket"],
    )
    global defer
    defer.append(
        [
            "sudo",
            "rm",
            "-f",
            "/etc/sudoers.d/g_wheel",
            "/etc/polkit-1/rules.d/49-nopasswd_global.rules",
        ]
    )


dms = {
    "sddm": "sddm.service",
    "lightdm": "lightdm.service",
    "gdm": "gdm.service",
    "lxdm": "lxdm.service",
    "tdm": "tdm.service",
    "kdm": "kdm.service",
    "mdm": "mdm.service",
    "slim": "slim.service",
    "entrance": "entrance.service",
}


# Verification functions


def validate_username(username) -> str:
    if len(username) > 30:
        return "Cannot be longer than 30 characters"
    elif not len(username):
        return "Cannot be empty"
    if len(username) and username[0] in ["-", "_", "."]:
        return "Cannot start with special characters"
    for i in range(len(username)):
        if not (
            (
                username[i].isdigit()
                or username[i].islower()
                or username[i] in ["-", "_", "."]
            )
            and username[i].isascii()
        ):
            return "Invalid characters (Use lowercase latin characters, numbers and '-' '_' '.')"
    return ""


def validate_fullname(fullname) -> str:
    if len(fullname) > 30:
        return "Cannot be longer than 30 characters"
    elif not len(fullname):
        return "Cannot be empty"
    for i in range(len(fullname)):
        if not (
            fullname[i].isdigit()
            or fullname[i].islower()
            or fullname[i].isupper()
            or fullname[i].isspace()
            or fullname[i] in ["'", "-"]
        ):
            return 'Invalid characters (Use characters, numbers and "\'")'
    return ""


def validate_hostname(hostname) -> str:
    if len(hostname) > 63:
        return "Cannot be longer than 30 characters"
    elif not len(hostname):
        return "Cannot be empty"
    if len(hostname) and hostname[0] == "_":
        return "Cannot start with '_'"
    for i in range(len(hostname)):
        if not (
            (
                hostname[i].isdigit()
                or hostname[i].islower()
                or hostname[i].isupper()
                or hostname[i] in ["-"]
            )
            and hostname[i].isascii()
        ):
            return 'Invalid characters (Use characters, numbers and "\'")'
    return ""


# User configuration functions.


def gidc(gid) -> bool:
    if gid is False:
        return True
    elif isinstance(gid, int):
        gid = str(gid)
    elif not gid.isdigit():
        raise TypeError("GID not a number!")
    with open("/etc/group") as gr:
        data = gr.read().split("\n")
        for i in data:
            try:
                if i.split(":")[-2] == gid:
                    return True
            except IndexError:
                pass
    return False


def uidc(uid: str) -> bool:
    if uid is False:
        return True
    if isinstance(uid, int):
        uid = str(uid)
    elif not uid.isdigit():
        raise TypeError("UID not a number!")
    with open("/etc/passwd") as pw:
        data = pw.read().split("\n")
        for i in data:
            try:
                if i.split(":")[2] == uid:
                    return True
            except IndexError:
                pass
    return False


def shells() -> set:
    res = set()
    with open("/etc/shells") as sh:
        data = sh.read().split("\n")
        for i in data:
            if i.startswith("/"):
                res.add(i)
    return res


def adduser(username: str, password: str, uid, gid, shell: str, groups: list) -> None:
    if isinstance(uid, int):
        uid = str(uid)
    elif not uid.isdigit():
        raise TypeError("UID not a number!")
    if gid is False:
        gid = uid
    elif isinstance(gid, int):
        gid = str(gid)
    elif not gid.isdigit():
        raise TypeError("GID not a number!")
    if shell not in shells():
        raise OSError("Invalid shell")
    if uidc(uid):
        raise OSError("Used UID")
    if gidc(gid):
        raise OSError("Used GID")
    lp("Making group " + username + " on gid " + gid)
    lrun(["sudo", "groupadd", username, "-g", gid])  # May silently fail, which is fine.
    lp("Adding user " + username + " on " + uid + ":" + gid + " with shell " + shell)
    lrun(["sudo", "useradd", "-N", username, "-u", uid, "-g", gid, "-m", "-s", shell])
    for i in groups:
        groupadd(username, i)
    passwd(username, password)


def groupadd(username: str, group: str) -> None:
    lp("Adding " + username + " to group " + group)
    lrun(["sudo", "usermod", "-aG", group, username])


def passwd(username: str, password: str) -> None:
    lp("Setting user " + username + " password")
    cmd = ["sudo", "passwd", username]
    if dryrun:
        lp("Would have run: " + str(cmd) + ", with the password via stdin.")
    else:
        subprocess.run(cmd, input=f"{password}\n{password}", text=True)


def sudo_nopasswd(no_passwd: bool) -> None:
    cmd = ["sudo", "sh", "-c", "echo '%wheel ALL=(ALL) "]
    if no_passwd:
        cmd[-1] += "NOPASSWD: "
    cmd[-1] += "ALL' > /etc/sudoers.d/10-installer"
    lrun(cmd)


def enable_autologin(username: str, de: str, dm: str, install_type: dict) -> None:
    if dm == "lightdm":
        lp("Enabling autologin for " + username + " in " + dm)
        if (install_type["source"] == "on_device") or (
            install_type["source"] == "from_iso" and install_type["type"] == "offline"
        ):
            lrun(
                [
                    "sudo",
                    "cp",
                    "/etc/lightdm/lightdm.conf.bak",
                    "/etc/lightdm/lightdm.conf",
                ]
            )
        lrun(
            [
                "sudo",
                "sh",
                "-c",
                f"sed -i '/^\[Seat:\*\]$/a autologin-user={username}\\nuser-session={de}\\n"
                + "greeter-session=lightdm-slick-greeter\\nautologin-user-timeout=0\\nautologin-guest=false'"
                + " /etc/lightdm/lightdm.conf",
            ]
        )
        groupadd(username, "autologin")


def enable_autologin_tty(username: str) -> None:
    # sudo mkdir -p /etc/systemd/system/getty@tty1.service.d/
    lrun(["sudo", "mkdir", "-p", "/etc/systemd/system/getty@tty1.service.d/"])
    overrideconf = f"""[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin {username} --noclear %I $TERM
"""
    cmd = f'echo "{overrideconf}" | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf'
    lrun(["sudo", "sh", "-c", cmd])


def set_hostname(hostname: str) -> None:
    lrun(["sudo", "bash", "-c", "echo " + hostname + " > /etc/hostname"])


# Support functions


def upload_log() -> str:
    command = f"cat {log_path} | nc termbin.com 9999"
    lp("Uploading log to termbin.com")
    try:
        result = subprocess.run(
            command, shell=True, check=True, text=True, capture_output=True
        )
        lp("Log uploaded to " + result.stdout.strip().split("\n")[0])
        return result.stdout.strip().split("\n")[0]
    except subprocess.CalledProcessError:
        lp("Error uploading log to termbin.com", mode="error")
        return "error"


def debounce(wait):
    """
    Decorator that will postpone a function's
    execution until after wait seconds
    have elapsed since the last time it was invoked.
    """

    def decorator(func):
        last_time_called = 0
        lock = Lock()

        @wraps(func)
        def debounced(*args, **kwargs):
            nonlocal last_time_called
            with lock:
                elapsed = monotonic() - last_time_called
                remaining = wait - elapsed
                if remaining <= 0:
                    last_time_called = monotonic()
                    return func(*args, **kwargs)
                else:
                    return None

        return debounced

    return decorator


def reboot(time: int = 5) -> None:
    if time < 0:
        raise ValueError("Time cannot be lower than 0")
    if not dryrun:
        subprocess.run(["sudo", "sh", "-c", f"sleep {time} && shutdown -r now &"])
    else:
        print("Skipping reboot during dryrun.")


def run_deferred():
    global defer
    if len(defer):
        lp("Running deferred commands..")
        sleep(0.15)
        for i in defer:
            lrun(i)
        defer.clear()


# Main functions


def install(settings=None, do_deferred: bool = True) -> int:
    """
    The main install function.

    Returns 0 on success,
            1 on general error,
            2 on invalid settings,
            3 on implementation missing.
    """
    start_time = monotonic()
    if settings is None:
        if dryrun:
            settings = {
                "install_type": {
                    "type": "offline",
                    "source": "on_device",
                    "device": "rpi4",
                },
                "layout": {"model": "pc105", "layout": "us", "variant": "alt-intl"},
                "locale": "en_US.UTF-8 UTF-8",
                "timezone": {"region": "Europe", "zone": "Sofia", "ntp": True},
                "hostname": "breborb",
                "user": {
                    "fullname": "Bred guy",
                    "username": "Panda",
                    "password": "123",
                    "uid": 1005,
                    "gid": False,
                    "shell": "/bin/bash",
                    "groups": ["wheel", "network", "video", "audio", "storage", "uucp"],
                    "sudo_nopasswd": False,
                    "autologin": True,
                },
                "root_password": False,
                "installer": {
                    "shown_pages": ["Keyboard", "Timezone", "User", "Locale"],
                    "installer_version": "0.1.0",
                    "ui": "tui",
                },
                "packages": [],
                "de_packages": [],
            }
        else:
            raise ValueError("No data passed with dryrun disabled.")

    if settings["install_type"]["type"] == "online":
        lp("Online mode not yet implemented!", mode="error")
        return 3
    elif settings["install_type"]["type"] == "offline":
        lp("%ST0%")  # Preparing
        sleep(0.15)
        # Parse settings
        reset_timer()

        lp("Validating manifest")
        if "installer" in settings.keys():
            if "installer_version" in settings["installer"].keys():
                if (
                    settings["installer"]["installer_version"]
                    < config.installer_version
                ):
                    lp("Toml installer version lower than current.", mode="warn")
                else:
                    lp("Toml installer version matches.")
            else:
                lp("Did not find version specification, cannot continue.", mode="error")
                return 2
        else:
            lp("Not a bakery manifest", mode="error")
            return 2
        for i in [
            "install_type",
            "layout",
            "locale",
            "timezone",
            "hostname",
            "user",
            "root_password",
            "packages",
            "de_packages",
        ]:
            if i not in settings.keys():
                lp("Invalid manifest, does not contain " + i, mode="error")
                return 2
        for i in ["type", "source", "device"]:
            if i not in settings["install_type"].keys():
                lp("Invalid install_type manifest, does not contain " + i, mode="error")
                return 2
        for i in ["model", "layout", "variant"]:
            if i not in settings["layout"].keys():
                lp("Invalid layout manifest, does not contain " + i, mode="error")
                return 2
            if (not isinstance(settings["layout"][i], str)) and (
                settings["layout"][i] != False
            ):
                lp(i + " must be a string or False", mode="error")
                return 2
        for i in ["region", "zone", "ntp"]:
            if i not in settings["timezone"].keys():
                lp("Invalid timezone manifest, does not contain " + i, mode="error")
                return 2
        for i in [
            settings["timezone"]["region"],
            settings["timezone"]["zone"],
            settings["locale"],
        ]:
            if not isinstance(i, str):
                lp(i + " must be a string", mode="error")
                return 2
        if not isinstance(settings["timezone"]["ntp"], bool):
            lp("ntp must be a bool", mode="error")
            return 2
        for i in ["root_password"]:
            if (not isinstance(settings[i], str)) and (settings[i] != False):
                lp(i + " must be a string or False", mode="error")
                return 2
        for i in [
            "fullname",
            "username",
            "password",
            "uid",
            "gid",
            "shell",
            "groups",
            "sudo_nopasswd",
            "autologin",
        ]:
            if i not in settings["user"].keys():
                lp("Invalid user manifest, does not contain " + i, mode="error")
                return 2
        for i in ["shown_pages", "ui"]:
            if i not in settings["installer"].keys():
                lp("Invalid installer manifest, does not contain " + i, mode="error")
                return 2
        lp("Manifest validated")

        lp("Took {:.5f}".format(get_timer()))
        st(1)  # Locales
        reset_timer()

        enable_locales([settings["locale"]])
        set_locale(settings["locale"])

        lp("Took {:.5f}".format(get_timer()))
        st(2)  # keyboard
        reset_timer()

        kb_set(
            settings["layout"]["model"],
            settings["layout"]["layout"],
            settings["layout"]["variant"],
        )

        lp("Took {:.5f}".format(get_timer()))
        st(3)  # TZ
        reset_timer()

        tz_set(settings["timezone"]["region"], settings["timezone"]["zone"])
        tz_ntp(settings["timezone"]["ntp"])

        lp("Took {:.5f}".format(get_timer()))
        st(4)  # Configure users
        reset_timer()

        adduser(
            settings["user"]["username"],
            settings["user"]["password"],
            settings["user"]["uid"],
            settings["user"]["gid"],
            settings["user"]["shell"],
            settings["user"]["groups"],
        )
        sudo_nopasswd(settings["user"]["sudo_nopasswd"])
        # ideally, we should have a way to check which DM/DE is installed
        if settings["user"]["autologin"]:
            enable_autologin(
                settings["user"]["username"],
                "cinnamon",
                "lightdm",
                settings["install_type"],
            )

            enable_autologin_tty(settings["user"]["username"])

        lp("Took {:.5f}".format(get_timer()))
        st(5)  # Configure hostname
        reset_timer()

        set_hostname(settings["hostname"])

        lp("Took {:.5f}".format(get_timer()))
        st(6)  # finishing up
        reset_timer()

        final_setup()

        lp("Took {:.5f}".format(get_timer()))
        st(7)  # Cleanup
        reset_timer()

        # Done
        lp("Installation finished. Total time: {:.5f}".format(monotonic() - start_time))
        if len(defer):
            lp("There are still deferred commands:")
            for i in defer:
                lp(str(i))
            lp("These commands will NOT be logged.")
        sleep(0.15)
        copy_logs(settings["user"]["username"])
        sleep(0.15)
        if do_deferred:
            run_deferred()
            sleep(0.15)
        return 0
    elif settings["install_type"]["type"] == "custom":
        lp("Custom mode not yet implemented!", mode="error")
        return 3
    elif settings["install_type"]["source"] == "on_device":
        lp("On device mode not yet implemented!", mode="error")
        return 3
    elif settings["install_type"]["source"] == "from_iso":
        lp("From iso mode not yet implemented!", mode="error")
        return 3
