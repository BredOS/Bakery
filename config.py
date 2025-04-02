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
        "Partitioning": ["partitioning_screen", _("Partitions")],
        "Summary": ["summary_screen", _("Summary")],
        "Install": ["install_screen", _("Install")],
        "Finish": ["finish_screen", _("Finish")],
    }


#    "Partitioning",

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
    "Desktop",
    "Partitioning",
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

colors = [
    "color1",
    "color2",
    "color3",
    "color4",
    "color5",
    "color6",
    "color7",
    "color8",
    "color9",
    "color10",
    "color11",
    "color12",
    "color13",
    "color14",
    "color15",
]

sbcs = [
    "ArmSoM AIM7 ",
    "ArmSoM Sige7",
    "ArmSoM W3",
    "Banana Pi M7",
    "Embedfire LubanCat-4",
    "Firefly AIO-3588L MIPI101(Linux)",
    "Firefly ITX-3588J HDMI(Linux)",
    "FriendlyElec CM3588",
    "FriendlyElec NanoPC-T6",
    "FriendlyElec NanoPC-T6 LTS",
    "FriendlyElec NanoPi R6C",
    "FriendlyElec NanoPi R6S",
    "Fxblox RK1",
    "Fydetab Duo",
    "HINLINK H88K",
    "Indiedroid Nova",
    "Khadas Edge2",
    "Mekotronics R58 MiniPC (RK3588 MINIPC LP4x V1.0 BlueBerry Board)",
    "Mekotronics R58X (RK3588 EDGE LP4x V1.0 BlueBerry Board)",
    "Mekotronics R58X-4G (RK3588 EDGE LP4x V1.2 BlueBerry Board)",
    "Mixtile Blade 3",
    "Mixtile Blade 3 v1.0.1",
    "Mixtile Core 3588E",
    "Orange Pi 5",
    "Orange Pi 5 Max",
    "Orange Pi 5 Plus",
    "Orange Pi 5 Pro",
    "Orange Pi 5B",
    "Orange Pi CM5",
    "RK3588 CoolPi CM5 EVB Board",
    "RK3588 CoolPi CM5 NoteBook Board",
    "RK3588 EDGE LP4x V1.2 MeiZhuo BlueBerry Board",
    "RK3588 EDGE LP4x V1.4 BlueBerry Board",
    "RK3588 MINIPC-MIZHUO LP4x V1.0 BlueBerry Board",
    "RK3588S CoolPi 4B Board",
    "ROC-RK3588S-PC V12(Linux)",
    "Radxa CM5 IO",
    "Radxa CM5 RPI CM4 IO",
    "Radxa NX5 IO",
    "Radxa NX5 Module",
    "Radxa ROCK 5 ITX",
    "Radxa ROCK 5A",
    "Radxa ROCK 5B",
    "Radxa ROCK 5B Plus",
    "Radxa ROCK 5C",
    "Radxa ROCK 5D",
    "Turing Machines RK1",
]

iso_packages_to_remove = [
    "bakery-device-tweaks",
    "bakery-gui",
    "bakery",
    "mkinitcpio-archiso",
    "mkinitcpio-nfs-utils",
]
