import toml
import subprocess
from time import sleep

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
