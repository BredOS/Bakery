import toml
import subprocess
from time import sleep

VERSION = "0.0.1-1"


# Config functions
def load_config(file_path: str = "/bakery/config.toml") -> dict:
    # Load a config file as a dict.
    pass


def export_config(config: dict, file_path: str = "/bakery/output.toml") -> dict:
    # Export a config file from a stored config dict.
    pass


def check_override_config() -> bool:
    # check if a /boot/override.toml exists.
    pass


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
