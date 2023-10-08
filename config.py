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
}

online_pages = ["Keyboard", "Timezone", "Locale", "User"]
offline_pages = ["Keyboard", "Timezone", "Locale", "User"]
