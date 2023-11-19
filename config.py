"Settings for the installer"

supported_languages = {"English": "en_US.UTF-8"}
timezone = {"region": "Europe", "zone": "London"}
installer_version = "1.0.0"
api_version = 1


def pages(_):
    return {
        "Keyboard": ["kb_screen", _("Keyboard")],
        "Locale": ["locale_screen", _("Locale")],
        "Timezone": ["timezone_screen", _("Timezone")],
        "User": ["user_screen", _("User")],
        "Desktops": ["de_screen", _("Desktops")],
        "Partitioning": ["partitioning_screen", _("Partitioning")],
        "Summary": ["summary_screen", _("Summary")],
        "Install": ["install_screen", _("Install")],
        "Finish": ["finish_screen", _("Finish")],
    }


offline_pages_on_dev = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Summary",
    "Install",
    "Finish",
]
online_pages_on_dev = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Desktops",
    "Summary",
    "Install",
    "Finish",
]
online_pages_from_iso = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Desktop" "Partitioning",
    "Summary",
    "Install",
    "Finish",
]
offline_pages_from_iso = [
    "Locale",
    "Keyboard",
    "Timezone",
    "User",
    "Partitioning",
    "Summary",
    "Install",
    "Finish",
]
