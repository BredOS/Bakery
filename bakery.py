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
import platform
import toml, os, io, sys, re, time, json, tempfile, parted, psutil, subprocess, gettext, socket, requests, gi, yaml
from typing import Callable
from time import sleep, monotonic
from pathlib import Path
from datetime import datetime
from traceback import print_exception
from threading import Lock
from functools import partial, wraps

from pyrunning import logging, LogMessage, LoggingHandler, Command, LoggingLevel
import yaml

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


def populate_messages(
    lang=None,
    type: str = "on_device_offline",
) -> None:
    global _
    _ = setup_translations(lang=lang)
    global st_msgs
    st_msgs.clear()
    if type == "on_device_offline":
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
    elif type == "from_iso_offline":
        st_msgs += [
            [_("Preparing for installation"), 0],  # 0
            [_("Partitioning Disk"), 0],  # 1
            [_("Mounting Disk"), 15],  # 2
            [_("Copying Files from iso"), 20],  # 3
            [_("Regenerating initramfs"), 24],  # 4
            [_("Generating fstab"), 28],  # 5
            [_("Setting up bootloader"), 32],  # 6
            [_("Removing packages"), 40],  # 7
            [_("Applying Locale Settings"), 50],  # 8
            [_("Applying Keyboard Settings"), 60],  # 9
            [_("Applying Timezone Settings"), 70],  # 10
            [_("Creating User account"), 80],  # 11
            [_("Setting Hostname"), 85],  # 12
            [_("Finalizing installation"), 90],  # 13
            [_("Cleaning up installation"), 100],  # 14
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


def copy_logs(new_usern: str, chroot: bool = False, mnt_dir: str = None) -> None:
    if dryrun:
        lp("Would have synced and copied logs.")
        return
    subprocess.run("sync")
    if chroot:
        subprocess.run(
            [
                "cp",
                "-v",
                log_path,
                mnt_dir + "/home/" + new_usern + "/.bredos/bakery/logs",
            ]
        )
    else:
        subprocess.run(
            [
                "cp",
                "-vr",
                "/root/.bredos",
                "/home/" + new_usern + "/.bredos",
            ]
        )
        subprocess.run(
            [
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


def post_run_cmd(info, exitcode) -> None:
    if exitcode:
        lp(f"Command failed with exit code {exitcode}", mode="error")
        raise Exception(f"Command failed with exit code {exitcode}")


def expected_to_fail(info, exitcode) -> None:
    if exitcode:
        lp(f"Command failed with exit code {exitcode}", mode="error")


def lrun(
    cmd: list,
    force: bool = False,
    silent: bool = False,
    shell: bool = False,
    cwd: str = ".",
    postrunfn: Callable = post_run_cmd,
    wait=True,
) -> None:
    """
    Run a command and log the output

    Parameters:
    - cmd: The command to run
    - force: Whether to run the command even if dryrun is enabled. Default is False
    - silent: Whether to run the command silently. Default is False
    - shell: Whether to run the command in a shell. Default is False
    - cwd: The working directory to run the command in. Default is "."
    Returns: None
    """
    if dryrun and not force:
        lp("Would have run: " + " ".join(cmd))
    else:
        if shell and wait:
            new_cmd = " ".join(cmd)
            Command.Shell(
                new_cmd,
                is_silent=silent,
                working_directory=cwd,
                post_run_function=partial(postrunfn),
                do_send_output_to_post_run_function=True,
                do_send_exit_code_to_post_run_function=True,
            ).run_log_and_wait(logging_handler=logging_handler)
        elif shell and not wait:
            new_cmd = " ".join(cmd)
            Command.Shell(
                new_cmd,
                is_silent=silent,
                working_directory=cwd,
                post_run_function=partial(postrunfn),
                do_send_output_to_post_run_function=True,
                do_send_exit_code_to_post_run_function=True,
            ).run_and_log(logging_handler=logging_handler)
        elif not shell and wait:
            Command(
                cmd,
                is_silent=silent,
                working_directory=cwd,
                post_run_function=partial(postrunfn),
                do_send_output_to_post_run_function=True,
                do_send_exit_code_to_post_run_function=True,
            ).run_log_and_wait(logging_handler=logging_handler)
        elif not shell and not wait:
            Command(
                cmd,
                is_silent=silent,
                working_directory=cwd,
                post_run_function=partial(postrunfn),
                do_send_output_to_post_run_function=True,
                do_send_exit_code_to_post_run_function=True,
            ).run_and_log(logging_handler=logging_handler)


lp("Logger initialized.")
lp("Dry run = " + str(dryrun))


# Exception handling


def catch_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            lp(f"Exception in {func.__name__}: {e}", mode="error")
            raise e

    return wrapper


# CFG/Tweaks functions


@catch_exceptions
def resolve_placeholders(config, context=None):
    """
    Recursively resolves placeholders in the configuration using the context.
    Re-evaluates until no placeholders remain.
    """
    if context is None:
        context = config  # Use the entire configuration as the context

    def resolve_value(value, context):
        """Resolve a single value with placeholders."""
        if isinstance(value, str):
            # Keep resolving placeholders until none are left
            while True:
                placeholders = re.findall(r"{{\s*([\w.]+)\s*}}", value)
                if not placeholders:
                    break  # Stop if no placeholders are left
                for placeholder in placeholders:
                    keys = placeholder.split(".")
                    resolved = context
                    for key in keys:
                        resolved = resolved.get(
                            key, f"{{{{ {placeholder} }}}}"
                        )  # Leave unresolved if missing
                    value = value.replace(f"{{{{ {placeholder} }}}}", resolved)
        return value

    if isinstance(config, dict):
        return {
            key: resolve_placeholders(value, context) for key, value in config.items()
        }
    elif isinstance(config, list):
        return [resolve_placeholders(item, context) for item in config]
    else:
        return resolve_value(config, context)


@catch_exceptions
def check_tweaks_config() -> bool:
    # curr dir + tweaks.yaml or /usr/share/bakery/tweaks.yaml prefer curr dir
    if os.path.isfile("tweaks.yaml"):
        return True
    elif os.path.isfile("/usr/share/bakery/tweaks.yaml"):
        return True
    return False


@catch_exceptions
def load_config() -> dict:
    # curr dir + tweaks.yaml or /usr/share/bakery/tweaks.yaml prefer curr dir
    if os.path.isfile("tweaks.yaml"):
        with open("tweaks.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            return resolve_placeholders(cfg)
    elif os.path.isfile("/usr/share/bakery/tweaks.yaml"):
        with open("/usr/share/bakery/tweaks.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            return resolve_placeholders(cfg)


# Networking functions


@catch_exceptions
def test_up(hostport: tuple) -> bool:
    if not networking_up():
        return False
    try:
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(hostport)
        return True
    except:
        return False


@catch_exceptions
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


@catch_exceptions
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


@catch_exceptions
def geoip() -> dict:
    try:
        if not internet_up():
            raise OSError
        tz_data = requests.get("https://geoip.kde.org/v1/timezone").json()
        region, zone = tz_data["time_zone"].split("/")
        return {"region": region, "zone": zone}
    except:
        return config.timezone


@catch_exceptions
def ethernet_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "ethernet":
            return True
    return False


@catch_exceptions
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


@catch_exceptions
def wifi_available() -> bool:
    client = NM.Client.new(None)
    devices = client.get_devices()
    for device in devices:
        if device.get_type_description() == "wifi":
            return True
    return False


@catch_exceptions
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


@catch_exceptions
def open_nm_settings() -> None:
    # Opens whichever gui for network settings is found.
    pass


@catch_exceptions
def check_updated() -> bool:
    # Check if bakery version has chanced in pacman.
    return False


@catch_exceptions
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


@catch_exceptions
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


@catch_exceptions
def tz_set(region: str, zone: str, chroot: bool = False, mnt_dir: str = None) -> None:
    tzs = tz_list()
    if region in tzs.keys() and zone in tzs[region]:
        if chroot:
            # in chroot use symlink
            lrun(
                [
                    "ln",
                    "-sfv",
                    "/usr/share/zoneinfo/" + region + "/" + zone,
                    mnt_dir + "/etc/localtime",
                ]
            )
        else:
            lrun(["timedatectl", "set-timezone", region + "/" + zone])
    else:
        lp("Timezone " + region + "/" + zone + " not a valid timezone!")
        raise TypeError("Timezone " + region + "/" + zone + " not a valid timezone!")


@catch_exceptions
def tz_ntp(ntp: bool, chroot: bool = False, mnt_dir: str = None) -> None:
    lp("Setting ntp to " + str(ntp))
    if chroot:
        run_chroot_cmd(mnt_dir, ["systemctl", "enable", "systemd-timesyncd"])
    else:
        lrun(["timedatectl", "set-ntp", str(int(ntp))])


# Package functions


@catch_exceptions
def ensure_localdb(retries: int = 3) -> None:
    if not internet_up():
        raise OSError("Internet Unavailable.")
    tried = 0
    while tried < retries:
        lrun(["pacman", "-Sy"], force=True)
        if len(os.listdir("/var/lib/pacman/sync/")):
            break
        tried += 1
    if not len(os.listdir("/var/lib/pacman/sync/")):
        raise OSError("Could not update databases.")


@catch_exceptions
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


def detect_session_configuration() -> dict:
    # Check for the XDG_SESSION_TYPE environment variable
    try:
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE")
    except:
        xdg_session_type = None
    # Check for the XDG_CURRENT_DESKTOP environment variable and lowercase it
    try:
        xdg_current_desktop = os.environ.get("XDG_CURRENT_DESKTOP").lower()
    except:
        xdg_current_desktop = None
    # look at where display-manager.service is symlinked to
    try:
        display_manager = os.path.basename(
            os.path.realpath("/etc/systemd/system/display-manager.service")
        ).replace(".service", "")
    except:
        display_manager = None

    lp("Detected Display Manager: " + display_manager, mode="debug")
    lp("Detected Desktop Environment: " + xdg_current_desktop, mode="debug")
    if xdg_session_type == "wayland":
        lp("Detected Wayland session", mode="debug")
        return {"dm": display_manager, "de": xdg_current_desktop, "is_wayland": True}
    else:
        lp("Detected X11 session", mode="debug")
        return {"dm": display_manager, "de": xdg_current_desktop, "is_wayland": False}


@catch_exceptions
def detect_install_source() -> str:
    with open("/proc/cmdline", "r") as cmdline_file:
        cmdline = cmdline_file.read()
        if "archisobasedir" in cmdline or "archisolabel" in cmdline:
            lp("Installation source: from_iso", mode="debug")
            return "from_iso"
        else:
            lp("Installation source: on_device", mode="debug")
            return "on_device"


def detect_install_device() -> str:
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as model_file:
            device = model_file.read().rstrip("\n").rstrip("\x00")
            lp("Detected device: " + device, mode="debug")
            return device
    except FileNotFoundError:
        try:
            with open("/sys/class/dmi/id/product_name", "r") as product_name_file:
                device = product_name_file.read().rstrip("\n")
                lp("Detected device: " + device, mode="debug")
                return device
        except FileNotFoundError:
            lp("Device detection failed", mode="error")
            return "unknown"


def is_sbc(device: str) -> bool:
    if device in config.sbcs:
        return True
    return False


def enable_services(services: list, chroot: bool = False, mnt_dir: str = None) -> None:
    try:
        for i in services:
            cmd = ["systemctl", "enable", i]
            if chroot:
                run_chroot_cmd(mnt_dir, cmd)
            else:
                lrun(cmd)
    except:
        pass


# Partitioning functions


def check_efi() -> bool:
    try:
        with open("/proc/mounts", "r") as mounts_file:
            mounts = mounts_file.read().split("\n")
            for mount in mounts:
                if "efivarfs" in mount:
                    lp("System is EFI", mode="debug")
                    return True
    except FileNotFoundError:
        lp("System is MBR/BIOS", mode="debug")
        return False


def check_partition_table(disk: str) -> str:
    try:
        device = parted.getDevice(disk)
        disk_instance = parted.newDisk(device)
        lp(f"Found a {disk_instance.type} partition table on {disk}", mode="debug")
        return disk_instance.type
    except Exception as e:
        lp(f"Error while processing disk {disk}: {str(e)}", mode="error")
        return None


@catch_exceptions
def get_block_devices():
    disks = subprocess.check_output(["lsblk", "-d", "-o", "NAME"]).decode("UTF-8")
    disk_list = disks.strip().split("\n")[1:]  # Skip header line
    disk_list = [
        disk
        for disk in disk_list
        if not disk.startswith("loop") and not disk.startswith("zram")
    ]
    disk_list = ["/dev/" + disk for disk in disk_list]
    lp("Found block devices: " + str(disk_list), mode="debug")
    return disk_list


def list_drives() -> dict:
    device_names = get_block_devices()
    pretty_names = {}

    for device_name in device_names:
        try:
            device = parted.getDevice(device_name)
            model = device.model.strip() if device.model else "Unknown"
            if len(model) > 20:
                model = model[:17] + "..."
            pretty_names[device_name] = model
        except Exception as e:
            lp(f"Error retrieving device info for {device_name}: {e}", mode="error")

    return pretty_names


@catch_exceptions
def get_partitions() -> list:
    # Get the partitions from get_block_devices
    disk_list = get_block_devices()
    partitions_dict = {}
    for disk in disk_list:
        try:
            device = parted.getDevice(disk)
            disk_instance = parted.newDisk(device)

            partitions_info = []
            for partition in disk_instance.partitions:
                # if partition is extended, skip it
                if partition.type == 2:
                    continue
                partition_info = {
                    partition.path: [
                        int(partition.getSize()),  # Size in MB
                        partition.geometry.start,  # Start sector
                        partition.geometry.end,  # End sector
                        (
                            partition.fileSystem.type if partition.fileSystem else None
                        ),  # Filesystem type
                    ]
                }
                partitions_info.append(partition_info)

            # Get the free space regions and add them to the partitions_info
            free_space_regions = disk_instance.getFreeSpaceRegions()
            for free_space_region in free_space_regions:
                if free_space_region.getSize() < 4:
                    continue
                free_space_info = {
                    "Free space": [
                        free_space_region.getSize(),  # Size in MB
                        free_space_region.start,  # Start sector
                        free_space_region.end,  # End sector
                        None,  # Filesystem type
                    ]
                }

                partitions_info.append(free_space_info)

            # Sort the partitions_info list by the start sector
            partitions_info.sort(key=lambda x: list(x.values())[0][1])
            partitions_dict[disk] = partitions_info

        except Exception as e:
            lp(f"Error while processing disk {disk}: {str(e)}", mode="error")
            # if str(e) contains "unrecognised disk label" then the disk is not partitioned and we have to return free_space for the whole disk
            if "unrecognised disk label" in str(e):
                partitions_dict[disk] = [
                    {
                        "Free space": [
                            int(
                                device.length * device.sectorSize / 1024 / 1024
                            ),  # Size in MB
                            0,  # Start sector
                            device.length,  # End sector
                            None,  # Filesystem type
                        ]
                    }
                ]

    return partitions_dict  # {disk: [{part1: [size, start, end, fs]}, {part2: [size, start, end, fs]}, {"free_space": [size, start, end, None]}]}


@catch_exceptions
def gen_new_partitions(old_partitions: dict, action: str, part_to_replace=None) -> dict:
    # get the drives physical sector size, sector size, length
    disk = list(old_partitions.keys())[0]
    device = parted.getDevice(disk)
    sector_size = device.sectorSize
    physical_sector_size = device.physicalSectorSize
    length = device.length
    drive_size = length * sector_size / 1024 / 1024  # in MB
    if action == "erase_all":
        # efi 256M, root rest
        new_partitions = {}
        for disk, partitions in old_partitions.items():
            new_partitions[disk] = [
                {"EFI": [float(256), 2048, 256 * 1024 * 1024 // sector_size, "fat32"]},
                {
                    "BredOS": [
                        int(drive_size) - 257,
                        257 * 1024 * 1024 // sector_size,
                        length - sector_size,
                        "btrfs",
                    ]
                },
            ]
        return new_partitions
    elif action == "replace":
        # check there is a fat32 that can be used for efi if not create one before the partition to be replaced
        # check for fat32 partition
        for disk, partitions in old_partitions.items():
            for partition in partitions:
                if partition[list(partition.keys())[0]][3] == "fat32":
                    fat32 = partition
                    break
                else:
                    fat32 = None
        new_partitions = {}
        for disk, partitions in old_partitions.items():
            # Get the partition to be replaced using the  number
            part = partitions[part_to_replace]

            # Initialize the new partitions list for the disk
            new_partitions[disk] = []

            # Add all the partitions except the one to be replaced
            for partition in partitions:
                if partition != part:
                    new_partitions[disk].append(partition)

            # Get the start and end of the partition to be replaced
            start = part[list(part.keys())[0]][1]
            end = part[list(part.keys())[0]][2]
            size = part[list(part.keys())[0]][0]
            sector_size = 512  # Assume a default sector size

            if fat32:
                new_partitions[disk].append(
                    {
                        "fat32": [
                            256,
                            start,
                            start + (256 * 1024 * 1024 // sector_size),
                            "fat32",
                        ]
                    }
                )

                # Add the root partition
                new_partitions[disk].append(
                    {
                        "BredOS": [
                            size - 257,
                            start + (257 * 1024 * 1024 // sector_size),
                            end,
                            "btrfs",
                        ]
                    }
                )
            else:
                new_partitions[disk].append({"BredOS": [size, start, end, "btrfs"]})
        # sort the partitions by the start sector
        for disk, partitions in new_partitions.items():
            partitions.sort(key=lambda x: list(x.values())[0][1])
        return new_partitions


@catch_exceptions
def format_partition(
    partition: str, fs: str, subvols: bool = False, home_subvol: bool = False
) -> None:
    if fs == "fat32":
        lp("Formatting partition: " + partition + " as fat32")
        lrun(["mkfs.fat", "-F32", partition])
    elif fs == "ext4":
        lp("Formatting partition: " + partition + " as ext4")
        lrun(["mkfs.ext4", partition])
    elif fs == "btrfs":
        lp("Formatting partition: " + partition + " as btrfs")
        lrun(["mkfs.btrfs", "-f", partition])
        if subvols:
            temp_dir = tempfile.mkdtemp()
            lp("Mounting partition: " + partition + " to " + temp_dir)
            lp("Creating subvolumes")
            try:
                lrun(["mount", partition, temp_dir])
                subvolumes = ["@", "@cache", "@log", "@pkg", "@.snapshots"]
                if home_subvol:
                    subvolumes.append("@home")
                for subvol in subvolumes:
                    lp("Creating subvolume: " + subvol)
                    lrun(
                        [
                            "btrfs",
                            "subvolume",
                            "create",
                            os.path.join(temp_dir, subvol),
                        ]
                    )
            finally:
                lp("Done creating subvolumes")
                lp("Unmounting partition: " + partition)
                lrun(["umount", temp_dir])
                os.rmdir(temp_dir)


@catch_exceptions
def get_fs(partition: str) -> str:
    cmd = ["lsblk", "-no", "FSTYPE", partition]
    return subprocess.check_output(cmd).decode("utf-8").strip()


@catch_exceptions
def get_uuid(partition: str) -> str:
    cmd = ["blkid", "-s", "UUID", "-o", "value", partition]
    return subprocess.check_output(cmd).decode("utf-8").strip()


@catch_exceptions
def get_disk_size(disk: str) -> int:
    device = parted.getDevice(disk)
    return int(device.length * device.sectorSize / 1024 / 1024)


@catch_exceptions
def mount_partition(
    partition: str,
    mount_point: str,
    opts: str = None,
    btrfs: bool = False,
    home_subvol: bool = False,
) -> None:
    if not btrfs:
        lp("Mounting partition: " + partition + " to " + mount_point)
        if opts:
            lrun(["mount", "-o", opts, partition, mount_point])
        else:
            lrun(["mount", partition, mount_point])
    else:
        lp("Mounting btrfs partition: " + partition + " to " + mount_point)
        if opts:
            lrun(["mount", "-o", "subvol=@", opts, partition, mount_point])
        else:
            lrun(["mount", "-o", "subvol=@", partition, mount_point])
        lp("Mounting btrfs subvolumes")
        subvolumes = {
            "log": "/var/log",
            "cache": "/var/cache",
            "pkg": "/var/cache/pacman/pkg",
        }
        if home_subvol:
            subvolumes["home"] = "/home"
        for subvol, path in subvolumes.items():
            os.makedirs(mount_point + path, exist_ok=True)
            lp("Mounting subvolume: " + subvol + " to " + path)
            lrun(
                [
                    "mount",
                    "-o",
                    "subvol=@" + subvol,
                    partition,
                    mount_point + path,
                ]
            )


@catch_exceptions
def mount_all_partitions(partitions: dict, mnt_dir: str) -> None:
    if partitions["type"] == "guided":
        if partitions["mode"] == "erase_all":
            disk = partitions["disk"]
            if "nvme" in disk or "mmcblk" in disk:
                part_prefix = "p"
            else:
                part_prefix = ""
            mount_partition(
                disk + part_prefix + "2", mnt_dir, "", btrfs=True, home_subvol=True
            )
            if partitions["efi"]:
                os.makedirs(os.path.join(mnt_dir, "boot", "efi"), exist_ok=True)
                mount_partition(
                    disk + part_prefix + "1",
                    os.path.join(mnt_dir, "boot/efi"),
                    "",
                    btrfs=False,
                )
            else:
                os.makedirs(os.path.join(mnt_dir, "boot"), exist_ok=True)
                mount_partition(
                    disk + part_prefix + "1",
                    os.path.join(mnt_dir, "boot"),
                    "",
                    btrfs=False,
                )
            lp("Mounted partitions")
    elif partitions["type"] == "manual":
        # Check if user wants seperate home partition
        home_subvol = True
        for part, options in partitions["partitions"].items():
            if options["mp"] == "Use as home":
                home_subvol = False
                break
        # First find and mount the "Use as root" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as root":
                mount_partition(part, mnt_dir, "", btrfs=True, home_subvol=home_subvol)
                break
        # Then find and mount the "Use as boot" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as boot":
                os.makedirs(os.path.join(mnt_dir, "boot", "efi"), exist_ok=True)
                mount_partition(
                    part, os.path.join(mnt_dir, "boot", "efi"), "", btrfs=False
                )
                break
        # Then find and mount the "Use as home" partition
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mount_point = options["mp"]
            if mount_point == "Use as home":
                os.makedirs(os.path.join(mnt_dir, "home"), exist_ok=True)
                mount_partition(part, os.path.join(mnt_dir, "home"))


@catch_exceptions
def rescan_partitions() -> None:
    lp("Rescanning partitions")
    lrun(["partprobe"])


@catch_exceptions
def partition_disk(partitions: dict) -> None:
    # {'type': 'guided', 'efi': True, 'disk': '/dev/nvme1n1', 'mode': 'erase_all', 'partitions': {'/dev/nvme1n1': [{'EFI': [256.0, 2048, 524288, 'fat32']}, {'swap': [2048.0, 526336, 4196352, 'swap']}, {'BredOS': [241891, 4198400, 500117680, 'btrfs']}]}}
    # OR
    # {'type': 'manual', 'efi': True, 'disk': '/dev/nvme1n1', 'partitions': {'/dev/nvme1n1p1': {'fs': 'fat32', 'mp': 'Use as boot'}, '/dev/nvme1n1p2': {'fs': 'btrfs', 'mp': 'Use as root'}, '/dev/nvme1n1p3': {'fs': None, 'mp': 'Use as home'}}}
    disk = partitions["disk"]
    # make sure the disk doesn't have any mounted partitions
    parts = psutil.disk_partitions()

    # Find partitions on the specified disk
    for partition in parts:
        if partition.device.startswith(disk):
            lp("Unmounting partition: " + partition.device)
            lrun(["umount", partition.device])
    if partitions["type"] == "guided":
        if partitions["mode"] == "erase_all":
            if "nvme" in disk or "mmcblk" in disk:
                part_prefix = "p"
            else:
                part_prefix = ""
            # size = get_disk_size(disk)
            parted_cmd = [
                "parted",
                "--script",
                disk,
                "--align",
                "optimal",
            ]
            parted_cmd.extend(["mklabel", "gpt"])
            parted_cmd.extend(["mkpart", "primary", "fat32", "2048s", "256M"])
            parted_cmd.extend(["set", "1", "esp", "on"])
            # parted_cmd.extend(["set", "1", "boot", "on"])
            parted_cmd.extend(["mkpart", "primary", "btrfs", "256M", "100%"])
            lp("Partitioning disk: " + disk)
            lp("Creating new GPT partition table")
            lp("Creating EFI partition")
            lp("Creating BredOS root partition")
            lp("Running parted command: " + " ".join(parted_cmd))
            lrun(parted_cmd)
            sleep(1)
            format_partition(disk + part_prefix + "1", "fat32")
            format_partition(
                disk + part_prefix + "2", "btrfs", subvols=True, home_subvol=True
            )
    elif partitions["type"] == "manual":
        # Check if user wants seperate home partition
        home_subvol = True
        for part, options in partitions["partitions"].items():
            if options["mp"] == "Use as home":
                home_subvol = False
                break
        # Iterate through the partitions in the manual scheme
        for part, options in partitions["partitions"].items():
            fs_type = options["fs"]
            mp = options["mp"]
            # Format partitions based on filesystem type
            if mp == "Use as boot":
                format_partition(part, fs_type)
            elif mp == "Use as root":
                if fs_type == "btrfs":
                    format_partition(
                        part, fs_type, subvols=True, home_subvol=home_subvol
                    )
                else:
                    format_partition(part, fs_type, home_subvol=home_subvol)
            elif mp == "Use as home":
                fs = get_fs(part)
                # if fs_type is None or "Don't format" is selected and the actual fs is either btrfs or ext4 dont do anything
                if (fs_type == None or fs_type == "Don't format") and (
                    fs != "btrfs" or fs != "ext4"
                ):
                    format_partition(part, fs)


# ISO functions


def run_chroot_cmd(work_dir: str, cmd: list, *args, **kwargs) -> None:
    lrun(["arch-chroot", work_dir] + cmd, *args, **kwargs)


@catch_exceptions
def grub_install(mnt_dir: str, arch: str = "arm64-efi") -> None:
    lp("Installing GRUB for the " + arch + " platform")
    run_chroot_cmd(
        mnt_dir,
        [
            "grub-install",
            f"--target={arch}",
            "--efi-directory=/boot/efi",
            "--removable",
            "--bootloader-id=BredOS",
        ],
    )
    lp("GRUB installation complete")
    lp("Generating GRUB configuration")
    run_chroot_cmd(mnt_dir, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
    lp("GRUB configuration generated")


def file_update(file_path: str, comment_keys: list = [], updates: dict = {}):
    """
    Validates a file exists and updates specific lines' values, while retaining the order and optionally commenting/uncommenting lines.

    Args:
        file_path (str): The path to the file to validate and update.
        updates (dict, optional): A dictionary where keys are line keys and values are the new values to set.
        comment_keys (list, optional): A list of keys to comment out.

    Returns:
        bool: If the operation was successful or not.
    """
    # Check if the file exists
    if not os.path.isfile(file_path):
        return False

    # Read the file
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
    except Exception as e:
        lp(f"Error reading {file_path}: {e}")
        return False

    # Pattern to match lines (supports whitespace variations)
    pattern = re.compile(r"^\s*#?\s*(\w+)\s*=\s*(.*)$")
    updated_lines = []
    modified = False

    for line in lines:
        match = pattern.match(line)
        if match:
            key = match.group(1)
            value = match.group(2)

            # Handle updates
            if key in updates:
                updated_value = updates[key]
                updated_lines.append(f"{key} = {updated_value}\n")
                modified = True
            # Handle commenting out lines
            elif key in comment_keys:
                updated_lines.append(f"# {key} = {value}\n")
                modified = True
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Write back the updated file if changes were made
    if modified:
        try:
            with open(file_path, "w") as file:
                file.writelines(updated_lines)
        except Exception as e:
            lp(f"Error writing to the file: {e}")
            return False
    return True


@catch_exceptions
def grub_cfg(
    cmdline: str = None,
    dtb: str = None,
    distribution: str = "BredOS",
    timeout: int = 5,
    update: bool = True,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
    grubpath = (mnt_dir if chroot else "") + "/etc/default/grub"
    lp("Configuring GRUB..")
    updates = {}
    comment_keys = []

    if cmdline is not None:
        lp(f'Setting cmdline to "{cmdline}"')
        updates["GRUB_CMDLINE_LINUX_DEFAULT"] = f'"{cmdline}"'

    if dtb is not None:
        if dtb:
            lp('Setting Device Tree to "{dtb}"')
            updates["GRUB_DTB"] = f'"{dtb}"'
        else:
            lp("Disabling Device Tree")
            comment_keys.append("GRUB_DTB")

    if distribution:
        lp("Configuring distribution name..")
        updates["GRUB_DISTRIBUTOR"] = f'"{distribution}"'

    if timeout > 0:
        lp("Setting timeout..")
        updates["GRUB_TIMEOUT"] = str(timeout)
    else:
        lp("Disabling timeout..")
        comment_keys.append("GRUB_TIMEOUT")

    if file_update(grubpath, comment_keys, updates):
        lp("Reconfiguration complete.")
    else:
        lp("Failed to update GRUB configuration!")
        raise RuntimeError("Failed to update GRUB configuration!")

    if not update:
        lp("Skipping GRUB regeneration..")
        return

    cmd = ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"]
    if chroot and mnt_dir is not None:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)
    lp("GRUB update complete")


@catch_exceptions
def unpack_sqfs(sqfs_file: str, mnt_dir: str) -> None:
    squashfs_mnt = tempfile.mkdtemp()
    lp("Mounting squashfs file: " + sqfs_file + " to " + squashfs_mnt)
    mount_partition(sqfs_file, squashfs_mnt, "loop")
    lp("Copying files from squashfs to " + mnt_dir)
    lrun(["cp", "-apr", squashfs_mnt + "/*", mnt_dir], shell=True)
    lp("Done copying files! Unmounting squashfs")
    lrun(["umount", squashfs_mnt])
    os.rmdir(squashfs_mnt)


@catch_exceptions
def unmount_all(mnt_dir: str) -> None:
    lp("Unmounting all partitions")
    lrun(["umount", "-R", mnt_dir])


@catch_exceptions
def copy_kern_from_iso(mnt_dir: str) -> None:
    lp("Copying kernel and initramfs from ISO to " + mnt_dir)
    arch = platform.machine()
    lrun(
        [
            "cp",
            "-avr",
            "/run/archiso/bootmnt/arch/boot/" + arch + "/*",
            mnt_dir + "/boot",
        ],
        shell=True,
    )
    if arch == "x86_64":
        lrun(
            [
                "cp",
                "-avr",
                "/run/archiso/bootmnt/arch/boot/intel-ucode.img",
                mnt_dir + "/boot",
            ]
        )
        lrun(
            [
                "cp",
                "-avr",
                "/run/archiso/bootmnt/arch/boot/amd-ucode.img",
                mnt_dir + "/boot",
            ]
        )
    lp("Done copying kernel and initramfs")


@catch_exceptions
def regenerate_initramfs(mnt_dir: str) -> None:
    # mnt_dir/etc/mkinitcpio.conf.bak -> mnt_dir/etc/mkinitcpio.conf
    lrun(
        [
            "mv",
            mnt_dir + "/etc/mkinitcpio.conf.bak",
            mnt_dir + "/etc/mkinitcpio.conf",
        ]
    )
    lp("Regenerating initramfs")
    run_chroot_cmd(mnt_dir, ["mkinitcpio", "-P"], postrunfn=expected_to_fail)
    lp("Initramfs regeneration complete")


@catch_exceptions
def generate_fstab(mnt_dir: str) -> None:
    lp("Generating fstab")
    fstab_path = os.path.join(mnt_dir, "etc", "fstab")

    # Generate the fstab file
    lrun(["genfstab", "-U", mnt_dir, ">", fstab_path], shell=True)

    # Process the generated fstab
    with open(fstab_path, "r") as f:
        lines = f.readlines()

    updated_lines = []
    skip_next = False

    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if line.startswith("# /dev/zram0"):
            updated_lines.append(line)
            skip_next = True
        else:
            updated_lines.append(line)

    with open(fstab_path, "w") as f:
        f.writelines(updated_lines)

    lp("Fstab generated")


@catch_exceptions
def pacstrap(mnt_dir: str, packages: list) -> None:
    lp("Pacstrapping packages: " + " ".join(packages))
    lrun(["pacstrap", mnt_dir] + packages)
    lp("Pacstrap complete")


@catch_exceptions
def install_packages(packages: list, chroot: bool = False, mnt_dir: str = None) -> None:
    cmd = ["pacman", "-Sy", "--noconfirm"] + packages
    lp("Installing packages: " + " ".join(packages))
    if chroot and mnt_dir is not None:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)
    lp("Package installation complete")


@catch_exceptions
def remove_packages(packages: list, chroot: bool = False, mnt_dir: str = None) -> None:
    # Remove each package in the list separately
    for package in packages:
        cmd = ["pacman", "-R", "--noconfirm", package]
        lp("Removing package: " + package)
        if chroot and mnt_dir is not None:
            run_chroot_cmd(mnt_dir, cmd, postrunfn=expected_to_fail)
        else:
            lrun(cmd, postrunfn=expected_to_fail)


def final_setup(settings, mnt_dir: str = None) -> None:
    if settings["install_type"]["source"] == "on_device":
        lrun(["systemctl", "disable", "resizefs.service"], silent=True)
        enable_services(
            ["bluetooth.service", "fstrim.timer", "oemcleanup.service", "cups.socket"],
        )
        if (
            settings["session_configuration"]["dm"] == "gdm"
            and settings["user"]["autologin"] == True
        ):
            # rm /etc/gdm/custom.conf
            lrun(["rm", "/etc/gdm/custom.conf"], silent=True)
        lrun(
            [
                "rm",
                "-f",
                "/etc/sudoers.d/g_wheel",
                "/etc/polkit-1/rules.d/49-nopasswd_global.rules",
            ]
        )
    elif settings["install_type"]["source"] == "from_iso":
        cfg = load_config()
        if is_sbc(settings["install_type"]["device"]):
            tweaks = cfg["devices"][settings["install_type"]["device"]].get("dt")
            if tweaks:
                grub_cfg(
                    cmdline=tweaks.get("cmdline", None),
                    dtb=tweaks.get("dtb", None),
                    timeout=tweaks.get("timeout", 5),
                    update=True,
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
            pythontweaks = tweaks.get("tweaks", None)
            if pythontweaks:
                exec(pythontweaks["python"])
        else:
            arch = platform.machine()
            tweaks = cfg.get(f"arch_{arch}")
            if tweaks:
                grub_cfg(
                    cmdline=tweaks.get("cmdline", None),
                    dtb=tweaks.get("dtb", None),
                    timeout=tweaks.get("timeout", 5),
                    update=True,
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                pythontweaks = tweaks.get("tweaks", None)
                if pythontweaks:
                    exec(pythontweaks["python"])

        if settings["install_type"]["type"] == "offline":
            enable_services(
                [
                    "bluetooth.service",
                    "fstrim.timer",
                    "oemcleanup.service",
                    "cups.socket",
                ],
                chroot=True,
                mnt_dir=mnt_dir,
            )
            if (
                settings["session_configuration"]["dm"] == "gdm"
                and settings["user"]["autologin"] == True
            ):
                # rm /etc/gdm/custom.conf
                lrun(["rm", mnt_dir + "/etc/gdm/custom.conf"], silent=True)
            lrun(
                [
                    "rm",
                    "-f",
                    mnt_dir + "/etc/sudoers.d/g_wheel",
                    mnt_dir + "/etc/polkit-1/rules.d/49-nopasswd_global.rules",
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


def adduser(
    username: str,
    password: str,
    uid,
    gid,
    shell: str,
    groups: list,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
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
    if chroot:
        run_chroot_cmd(mnt_dir, ["groupadd", username, "-g", gid])
    else:
        lrun(["groupadd", username, "-g", gid])  # May silently fail, which is fine.
    lp("Adding user " + username + " on " + uid + ":" + gid + " with shell " + shell)
    if chroot:
        run_chroot_cmd(
            mnt_dir,
            [
                "useradd",
                "-N",
                username,
                "-u",
                uid,
                "-g",
                gid,
                "-m",
                "-s",
                shell,
            ],
        )
    else:
        lrun(["useradd", "-N", username, "-u", uid, "-g", gid, "-m", "-s", shell])
    for i in groups:
        groupadd(username, i, chroot, mnt_dir)
    passwd(username, password, chroot, mnt_dir)


def groupadd(
    username: str, group: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    lp("Adding " + username + " to group " + group)
    cmd = ["usermod", "-aG", group, username]
    if chroot:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)


def passwd(
    username: str, password: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    lp("Setting user " + username + " password")
    cmd = ["passwd", username]
    if dryrun:
        lp("Would have run: " + str(cmd) + ", with the password via stdin.")
    elif dryrun and chroot:
        lp("Would have run: " + str(cmd) + ", with the password via stdin in chroot")
    elif chroot:
        subprocess.run(
            ["arch-chroot", mnt_dir] + cmd, input=f"{password}\n{password}", text=True
        )
    else:
        subprocess.run(cmd, input=f"{password}\n{password}", text=True)


def sudo_nopasswd(no_passwd: bool, chroot: bool = False, mnt_dir: str = None) -> None:
    if dryrun:
        lp("Would have set sudoers to " + str(not no_passwd))
    else:
        if chroot:
            path = mnt_dir + "/etc/sudoers"
        else:
            path = "/etc/sudoers"
        if no_passwd:
            content = "%wheel ALL=(ALL:ALL) NOPASSWD: ALL"
        else:
            content = "%wheel ALL=(ALL:ALL) ALL"
        lp(f"Setting {path} to {content}")
        with open(path, "a") as f:
            f.write(content)


def enable_autologin(
    username: str,
    session_configuration: dict,
    install_type: dict,
    chroot: bool = False,
    mnt_dir: str = None,
) -> None:
    dm = session_configuration["dm"]
    de = session_configuration["de"]
    is_wayland = session_configuration["is_wayland"]
    if dm == "lightdm":
        lp("Enabling autologin for " + username + " in " + dm)
        if (install_type["source"] == "on_device") or (
            install_type["source"] == "from_iso" and install_type["type"] == "offline"
        ):
            cmd = [
                "cp",
                "/etc/lightdm/lightdm.conf.bak",
                "/etc/lightdm/lightdm.conf",
            ]
            if chroot and mnt_dir:
                run_chroot_cmd(mnt_dir, cmd)
            else:
                lrun(cmd)
        if dm == "cinnamon" and is_wayland:
            dm = "cinnamon-wayland"
        cmd = [
            "sh",
            "-c",
            f"sed -i '/^\[Seat:\*\]$/a autologin-user={username}\\nuser-session={de}\\n"
            + "greeter-session=lightdm-slick-greeter\\nautologin-user-timeout=0\\nautologin-guest=false'"
            + " /etc/lightdm/lightdm.conf",
        ]
        if chroot and mnt_dir:
            run_chroot_cmd(mnt_dir, cmd)
        else:
            lrun(cmd)
    elif dm == "gdm":
        lp("Enabling autologin for " + username + " in " + dm)

        config = f"""# GDM configuration storage

[daemon]
# Uncomment the line below to force the login screen to use Xorg
#WaylandEnable=false
AutomaticLogin={username}
AutomaticLoginEnable=True
# TimedLoginEnable=true
# TimedLogin={username}
# TimedLoginDelay=5
DefaultSession={de}

[security]

[xdmcp]

[chooser]

[debug]
# Uncomment the line below to turn on debugging
#Enable=true
"""
        cmd = f'echo "{config}" > /etc/gdm/custom.conf'
        if chroot and mnt_dir:
            run_chroot_cmd(mnt_dir, ["sh", "-c", cmd])
        else:
            lrun(["sh", "-c", cmd])
    groupadd(username, "autologin", chroot, mnt_dir)


def enable_autologin_tty(
    username: str, chroot: bool = False, mnt_dir: str = None
) -> None:
    cmd_mkdir = ["mkdir", "-p", "/etc/systemd/system/getty@tty1.service.d/"]
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, cmd_mkdir)
    else:
        lrun(cmd_mkdir)

    overrideconf = f"""[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin {username} --noclear %I $TERM
"""
    cmd_override = f'echo "{overrideconf}" |  tee /etc/systemd/system/getty@tty1.service.d/override.conf'
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, ["sh", "-c", cmd_override])
    else:
        lrun(["sh", "-c", cmd_override])


def set_hostname(hostname: str, chroot: bool = False, mnt_dir: str = None) -> None:
    cmd = ["bash", "-c", f"echo {hostname} > /etc/hostname"]
    if chroot and mnt_dir:
        run_chroot_cmd(mnt_dir, cmd)
    else:
        lrun(cmd)


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


def time_fn(func):
    def wrapped(*args, **kwargs):
        start_time = time.time()  # Record the start time
        result = func(*args, **kwargs)  # Call the original function
        end_time = time.time()  # Record the end time
        duration = end_time - start_time  # Calculate the duration
        print(f"Function '{func.__name__}' took {duration:.4f} seconds to execute.")
        return result  # Return the result of the original function

    return wrapped


def reboot(time: int = 5) -> None:
    if time < 0:
        raise ValueError("Time cannot be lower than 0")
    if not dryrun:
        subprocess.run(["sh", "-c", f"sleep {time} && shutdown -r now &"])
    else:
        print("Skipping reboot during dryrun.")


# Main functions


def install(settings=None) -> int:
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
                "session_configuration": {
                    "dm": "lightdm",
                    "de": "XFCE",
                    "is_wayland": False,
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
                "packages": {},
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
            "session_configuration",
            "layout",
            "locale",
            "timezone",
            "hostname",
            "user",
            "root_password",
            "packages",
        ]:
            if i not in settings.keys():
                lp("Invalid manifest, does not contain " + i, mode="error")
                return 2
        for i in ["type", "source", "device"]:
            if i not in settings["install_type"].keys():
                lp("Invalid install_type manifest, does not contain " + i, mode="error")
                return 2
        for i in ["dm", "de", "is_wayland"]:
            if i not in settings["session_configuration"].keys():
                lp(
                    "Invalid session_configuration manifest, does not contain " + i,
                    mode="error",
                )
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
        populate_messages(
            type=settings["install_type"]["source"]
            + "_"
            + settings["install_type"]["type"]
        )
        lp("Took {:.5f}".format(get_timer()))
        st(1)  # Locales
        reset_timer()

        if settings["install_type"]["source"] == "on_device":
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
            passwd("root", settings["user"]["password"])
            # ideally, we should have a way to check which DM/DE is installed
            if settings["user"]["autologin"]:
                enable_autologin(
                    settings["user"]["username"],
                    settings["session_configuration"],
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

            final_setup(settings)

            lp("Took {:.5f}".format(get_timer()))
            st(7)  # Cleanup
            reset_timer()

            # Done
            lp(
                "Installation finished. Total time: {:.5f}".format(
                    monotonic() - start_time
                )
            )
            copy_logs(settings["user"]["username"])
            return 0
        elif settings["install_type"]["source"] == "from_iso":
            try:
                lp("Took {:.5f}".format(get_timer()))
                st(1)  # Partitioning
                reset_timer()
                # Partition disk
                partition_disk(settings["partitions"])

                arch = platform.machine()
                if arch == "aarch64":
                    grub_arch = "arm64-efi"
                    sqfs_file = "/run/archiso/bootmnt/arch/aarch64/airootfs.sfs"
                else:
                    grub_arch = "x86_64-efi"
                    sqfs_file = "/run/archiso/bootmnt/arch/x86_64/airootfs.sfs"

                lp("Took {:.5f}".format(get_timer()))
                st(2)  # Mounting
                reset_timer()

                mnt_dir = tempfile.mkdtemp()
                # Mount partitions
                mount_all_partitions(settings["partitions"], mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(3)  # Unsquash
                reset_timer()
                # unpack squashfs
                unpack_sqfs(sqfs_file, mnt_dir)

                # Copy kernel and initramfs
                copy_kern_from_iso(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(4)  # initramfs
                reset_timer()
                # Regenerate initramfs
                regenerate_initramfs(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(5)  # fstab
                reset_timer()
                # Generate fstab
                generate_fstab(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(6)  # Grub
                reset_timer()
                # Install grub
                grub_install(mnt_dir, arch=grub_arch)

                lp("Took {:.5f}".format(get_timer()))
                st(7)  # Removing packages
                reset_timer()
                # Remove packages
                remove_packages(
                    settings["packages"]["to_remove"], chroot=True, mnt_dir=mnt_dir
                )

                lp("Took {:.5f}".format(get_timer()))
                st(8)  # Locale
                reset_timer()
                enable_locales([settings["locale"]], chroot=True, mnt_dir=mnt_dir)
                set_locale(settings["locale"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(9)  # keyboard
                reset_timer()

                kb_set(
                    settings["layout"]["model"],
                    settings["layout"]["layout"],
                    settings["layout"]["variant"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )

                lp("Took {:.5f}".format(get_timer()))
                st(10)  # TZ
                reset_timer()

                tz_set(
                    settings["timezone"]["region"],
                    settings["timezone"]["zone"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                tz_ntp(settings["timezone"]["ntp"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(11)  # Configure users
                reset_timer()

                adduser(
                    settings["user"]["username"],
                    settings["user"]["password"],
                    settings["user"]["uid"],
                    settings["user"]["gid"],
                    settings["user"]["shell"],
                    settings["user"]["groups"],
                    chroot=True,
                    mnt_dir=mnt_dir,
                )
                lp("sudo_nopasswd")
                sudo_nopasswd(
                    settings["user"]["sudo_nopasswd"], chroot=True, mnt_dir=mnt_dir
                )
                passwd(
                    "root", settings["user"]["password"], chroot=True, mnt_dir=mnt_dir
                )
                # ideally, we should have a way to check which DM/DE is installed
                if settings["user"]["autologin"]:
                    enable_autologin(
                        settings["user"]["username"],
                        settings["session_configuration"],
                        settings["install_type"],
                        chroot=True,
                        mnt_dir=mnt_dir,
                    )

                    enable_autologin_tty(
                        settings["user"]["username"], chroot=True, mnt_dir=mnt_dir
                    )

                lp("Took {:.5f}".format(get_timer()))
                st(12)  # Configure hostname
                reset_timer()

                set_hostname(settings["hostname"], chroot=True, mnt_dir=mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(13)  # finishing up
                reset_timer()

                final_setup(settings, mnt_dir)

                unmount_all(mnt_dir)

                lp("Took {:.5f}".format(get_timer()))
                st(14)  # Cleanup
                reset_timer()

                # Done
                lp(
                    "Installation finished. Total time: {:.5f}".format(
                        monotonic() - start_time
                    )
                )
                copy_logs(settings["user"]["username"], chroot=True, mnt_dir=mnt_dir)
                return 0
            except:
                return 1
    elif settings["install_type"]["type"] == "custom":
        lp("Custom mode not yet implemented!", mode="error")
        return 3
