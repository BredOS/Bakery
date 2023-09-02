import toml
import subprocess
import os
import gettext
from time import sleep
from pathlib import Path
from pyrunning import logging, LogMessage, LoggingHandler, Command
from datetime import datetime

API_VERSION = 1

# Config functions

# Config spec
#
# bakery_conf_ver = int | Used to test if this config is compatible.
# uninstall_upon_completion = bool | Remove bakery on completion.
# headless = bool | Do not ask or wait for any user confirmation.
#
# [gui]
# logo = str | Used to override the BredOS logo
#
# [settings]
# lang = str | Main display language ex. "en_us"
# kb_lanf = list | Languages to be added to the keyboard.
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
#
# [about]
# author = str | Author of this bakery config.



def setup_translations(lang=None) -> gettext.GNUTranslations:
    """
    Setup translations
    
        Does the following:
        - Loads the translations from the locale folder
        - Sets the translations for the gettext module

        Returns:  A gettext translation object
    """
    lang_path = os.path.join(os.path.dirname(__file__), "locale")
    # Load translations
    if lang is not None:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        translation = gettext.translation("bakery", lang_path , languages=[lang])
        translation.install()
        return translation.gettext # type: ignore
    else:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        return gettext.gettext # type: ignore

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
        Path(log_dir).mkdir( parents= True, exist_ok=True )
        if not os.path.isdir(log_dir):
            raise FileNotFoundError("The directory {} does not exist".format(log_dir))
        # get write perms
        elif not os.access(log_dir, os.W_OK):
            raise PermissionError("You do not have permission to write to {}".format(log_dir))
    except Exception as e: 
        import traceback
        traceback.print_exception(type(e), e, e.__traceback__)
        exit(1)
    
    print("Logging to:" + str(log_file))
    rm_old_logs(log_dir, keep=5)

    log_file_handler = logging.FileHandler(log_file)
    log_file_handler.setLevel(logging.DEBUG)
    log_file_formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s (%(pathname)s > %(funcName)s; Line %(lineno)d)', '%Y-%m-%d %H:%M:%S')
    log_file_handler.setFormatter(log_file_formatter)

    # # For console (when installing)
    # log_error_handler = logging.StreamHandler()
    # log_error_handler.setLevel(logging.INFO)
    # log_error_formatter = logging.Formatter('%(levelname)8s: %(message)s')
    # log_error_handler.setFormatter(log_error_formatter)
    # logger.addHandler(log_error_handler)
    return logger

def rm_old_logs( log_dir_path, keep: int) -> None:
    subprocess.Popen(
        "ls -tp * | grep -v '/$' | tail -n +" 
            + str(keep + 1) 
            + " | xargs -I {} rm -- {}",
        shell=True,
        cwd=log_dir_path
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
    if check_override_config() and file_path == "/bakery/config.toml":
        file_path = "/boot/override.toml"
    try:
        return toml.load(file_path)
    except:
        return None


def export_config(config: dict, file_path: str = "/bakery/output.toml") -> bool:
    # Export a config file from a stored config dict.
    try:
        with open(file_path, "w") as f:
            f.write(toml.dumps(config))
    except:
        return False
    return True


def _ping(ip: str) -> bool:
    return (
        subprocess.Popen(["/bin/ping", "-c1", "-w1", ip], stdout=subprocess.PIPE)
        .stdout.read()
        .find(b"1 received")
        != -1
    )


# Networking functions
def networking_up() -> bool:
    # Tests if an internet connection is configured.
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
def set_lang(lang: str) -> bool:
    """
    Set the system display language

    Returns True on success.
    """
    return False


def localegen(locale_list: list) -> bool:
    """
    Generate locales from the given list.

    Returns True on success.
    """
    return False
