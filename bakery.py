import toml
import subprocess
import os
import gettext
from time import sleep
from pathlib import Path
import socket
from datetime import datetime

from pyrunning import logging, LogMessage, LoggingHandler, Command
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
    log_dir = os.path.join(os.path.expanduser("~"), ".bredos", "bakery", "logs")
    log_file = os.path.join(log_dir, datetime.now().strftime("%Y-%m-%d-%H-%M-%S.log"))
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
        import traceback

        traceback.print_exception(type(e), e, e.__traceback__)
        exit(1)

    print("Logging to:" + str(log_file))
    rm_old_logs(log_dir, keep=5)

    log_file_handler = logging.FileHandler(log_file)
    log_file_handler.setLevel(logging.DEBUG)
    log_file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)8s] %(message)s (%(pathname)s > %(funcName)s; Line %(lineno)d)",
        "%Y-%m-%d %H:%M:%S",
    )
    log_file_handler.setFormatter(log_file_formatter)

    # # For console (when installing)
    # log_error_handler = logging.StreamHandler()
    # log_error_handler.setLevel(logging.INFO)
    # log_error_formatter = logging.Formatter('%(levelname)8s: %(message)s')
    # log_error_handler.setFormatter(log_error_formatter)
    # logger.addHandler(log_error_handler)
    return logger


def rm_old_logs(log_dir_path: str, keep: int) -> None:
    subprocess.Popen(
        "ls -tp * | grep -v '/$' | tail -n +"
        + str(keep + 1)
        + " | xargs -I {} rm -- {}",
        shell=True,
        cwd=log_dir_path,
    )


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
    return toml.load(file_path)


def export_config(config: dict, file_path: str = "/bakery/output.toml") -> bool:
    # Export a config file from a stored config dict.
    try:
        with open(file_path, "w") as f:
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
    return res


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


def nmcli_connection(connection_name=None) -> None:
    # Opens nmcli network settings.
    try:
        if connection_name is None:
            subprocess.run(["nmcli", "con", "edit"])
        else:
            subprocess.run(["nmcli", "con", "edit", connection_name])
    except KeyboardInterrupt:
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

_kblangmap = {
    "al": "Albanian",
    "at": "Austrian German",
    "ara": "Arabic",
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
            ):
                data.pop(i)  # remove non-locale / disabled locale on only_enabled
        for i in range(len(data)):
            data[i] = data[i].replace("#", "").replace("  ", "")  # cleanup
        return data


def langs(only_enabled: bool = False) -> list:
    """
    A formatted dict of languages and locales

    {language: [locale1, locale2], ...}
    """
    data = locales(only_enabled)
    res = dict()
    for i in range(len(data)):
        lang = _langmap[data[i][: data[i].find("_")]]
        if lang in res.keys():
            res[lang].append(data[i])
        else:
            res.update({lang: [data[i]]})
    return res


def kb_langs(only_enabled: bool = False) -> list:
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
    res = {}
    for i in layouts:
        lang = _kblangmap[i]
        if lang in res.keys():
            res[lang].append(i)
        else:
            res.update({lang: [i]})
    return layouts
