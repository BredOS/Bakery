"""Settings for the installer"""

supported_languages = {"English": "en_US.UTF-8"}
timezone = {"region": "Europe", "zone": "London"}
installer_version = "0.1.0"
api_version = 1

pages = {
    "Keyboard": "kb_screen",
    "Locale": "locale_screen",
    "Timezone": "timezone_screen",
    "User": "user_screen",
    "Desktops": "de_screen",
    "Summary": "summary_screen",
}

offline_pages = ["Keyboard", "Timezone", "User", "Locale"]
online_pages = ["Keyboard", "Timezone", "Locale", "User"]
