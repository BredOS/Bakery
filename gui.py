#! /usr/bin/env python

"""Installer for BredOS written in py"""

from sys import argv

from pyrunning import LogMessage, LoggingHandler

import bakery
import config
import gi
import locale
import os
import subprocess

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio


class MenuButton(Gtk.MenuButton):
    def __init__(self, xml, name, icon_name="open-menu-symbolic"):
        super(MenuButton, self).__init__()
        builder = Gtk.Builder()
        builder.add_from_string(xml)
        menu = builder.get_object(name)
        self.set_menu_model(menu)
        self.set_icon_name(icon_name)


# class Window(Gtk.ApplicationWindow):
#     def __init__(self, title, width, height, **kwargs):
#         super(Window, self).__init__(**kwargs)
#         self.set_default_size(width, height)
#         self.headerbar = Gtk.HeaderBar()
#         self.set_titlebar(self.headerbar)
#         label = Gtk.Label()
#         label.set_text(title)
#         self.headerbar.set_title_widget(label)
#         self.css_provider = None
#         # self.set_resizable(False)

#     def load_css(self, css_fn) -> None:
#         if css_fn and os.path.exists(css_fn):
#             css_provider = Gtk.CssProvider()
#             try:
#                 css_provider.load_from_path(css_fn)
#             except GLib.Error as e:
#                 print(_("CSS loading failed:", str(e)))
#                 return None
#             print("Loaded styling:", str(css_fn))
#             self.css_provider = css_provider

#     def _add_widget_styling(self, widget) -> None:
#         if self.css_provider:
#             context = widget.get_style_context()
#             context.add_provider(self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

#     def add_custom_styling(self, widget) -> None:
#         self._add_widget_styling(widget)
#         for child in widget:
#             self.add_custom_styling(child)

#     def create_action(self, name, callback) -> None:
#         action = Gio.SimpleAction.new(name, None)
#         action.connect("activate", callback)
#         self.add_action(action)


APP_MENU = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
<menu id='app-menu'>
  <section>
    <item>
      <attribute name='label' translatable='yes'>_About</attribute>
      <attribute name='action'>win.about</attribute>
    </item>
    <item>
        <attribute name='label' translatable='yes'>_Settings</attribute>
        <attribute name='action'>win.settings</attribute>
    </item> 
  </section>
</menu>
</interface>
"""


# noinspection PyAttributeOutsideInit
class MainWindow():
    def __init__(self):
        LogMessage.Info("Initializing main window").write(logging_handler=logger_handler)
        

        main_builder = Gtk.Builder()
        main_builder.add_from_file("ui/bakery.ui")

        self.add(main_builder.get_object("window"))
        if self.window:
            self.window.connect("destroy", Gtk.main_quit)



    def create_welcome_page(self) -> Gtk.Box:
        welcome_label = Gtk.Label(label=_("Welcome to BredOS!"))
        welcome_label.set_halign(Gtk.Align.CENTER)  # Align the label to the center
        # add image
        image = Gtk.Image.new_from_file(config.logo_path)
        image.set_halign(Gtk.Align.CENTER)  # Align the image to the center
        image.set_margin_top(10)  # Add top margin to the image
        image.set_margin_bottom(10)  # Add bottom margin to the image
        # size 256x256
        image.set_pixel_size(256)
        butbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        butbox.set_halign(Gtk.Align.CENTER)

        buttons = {"offline": [_("Offline Installation"), config.logo_path],
                   "online": [_("Online Installation"), config.logo_path],
                   "custom": [_("Custom Installation"), config.logo_path]}
        for i in buttons:
            # Create the button
            btn = self.create_button(i, buttons[i][0], buttons[i][1])
            butbox.append(btn)

        language_selector = Gtk.ComboBoxText()
        languages = ["English", "Danish", "French", "Hungarian", "Bulgarian"]
        for lang in languages:
            language_selector.append_text(lang)

        language_selector.set_active(0)

        # Connect a signal to the language selector
        language_selector.connect("changed", self.on_language_changed)

        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        welcome_box.append(welcome_label)
        welcome_box.append(image)
        welcome_box.append(language_selector)
        welcome_box.append(butbox)
        welcome_box.set_valign(Gtk.Align.CENTER)

        return welcome_box

    def post_selection(self, selection) -> Gtk.Box:
        stage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        stage_box.set_vexpand(True)

        stages_config = conf.get("stages", {})

        if selection not in stages_config:
            raise ValueError(f"Invalid selection: {selection}")
        print(stages_config[selection])
        stages = stages_config[selection]

        selection_notebook = Gtk.Notebook()

        for stage in stages:
            stage_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            stage_page.set_vexpand(True)
            stage_label = Gtk.Label(label=stage)
            stage_page.append(stage_label)

            selection_notebook.append_page(stage_page, Gtk.Label(label=stage))

        stage_box.append(selection_notebook)

        # Create back and forward buttons
        back_button = Gtk.Button(label="Back")
        forward_button = Gtk.Button(label="Forward")

        # Connect button click events to their respective handlers
        back_button.connect("clicked", self.on_back_button_clicked)
        forward_button.connect("clicked", self.on_forward_button_clicked)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_valign(Gtk.Align.END)
        button_box.set_margin_end(10)
        button_box.set_margin_bottom(10)
        button_box.append(back_button)
        button_box.append(forward_button)
        button_box.set_hexpand(True)

        button_grid = Gtk.Grid()
        # button_grid.attach(stage_box, 0, 0, 1, 1)
        button_grid.attach(button_box, 0, 1, 1, 1)
        button_grid.set_hexpand(True)
        # button_grid.set_vexpand(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(stage_box)
        # vbox.append(button_grid)
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_hexpand(True)

        return vbox

    @staticmethod
    def create_location_page(self) -> Gtk.Box:
        # Create and return widgets for the language selection page
        language_label = Gtk.Label(label=_("Select Language:"))
        language_combo = Gtk.ComboBoxText()
        language_combo.append_text("English")
        language_combo.append_text("Spanish")
        # Add more languages

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.append(language_label)
        vbox.append(language_combo)
        vbox.set_valign(Gtk.Align.CENTER)

        return vbox

    @staticmethod
    def create_keyboard_page() -> Gtk.Box:
        # Create and return widgets for the keyboard layout selection page
        keyboard_label = Gtk.Label(label="Select Keyboard Layout:")
        keyboard_combo = Gtk.ComboBoxText()
        keyboard_combo.append_text("US")
        keyboard_combo.append_text("UK")
        # Add more keyboard layouts

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.append(keyboard_label)
        vbox.append(keyboard_combo)
        vbox.set_valign(Gtk.Align.CENTER)

        return vbox

    def create_button(self, button_id, label_text, image_path) -> Gtk.Button:
        btn = Gtk.Button()
        grid = Gtk.Grid(column_homogeneous=True, row_spacing=6)
        image = Gtk.Image.new_from_file(image_path)
        image.set_pixel_size(128)
        label = Gtk.Label()
        label.set_label(label_text)
        grid.attach(image, 0, 0, 1, 1)
        grid.attach(label, 0, 1, 1, 1)
        btn.set_child(grid)
        btn.connect("clicked", self.on_button_clicked, button_id)
        return btn


    def on_language_changed(self, combo) -> None:
        active_language = combo.get_active_text()
        if active_language:
            new_locale = config.supported_languages.get(active_language)
            if new_locale:
                locale.setlocale(locale.LC_ALL, new_locale)
                _ = bakery.Bakery().setup_translations(new_locale)
                print(_("Language changed to"), active_language)

    def menu_handler(self, action, data) -> None:
        name = action.get_name()
        if name == "about":
            self.about = Gtk.AboutDialog()
            self.about.set_transient_for(self)
            self.about.set_modal(self)
            self.about.set_program_name(_("BredOS Installer"))
            self.about.set_authors(["Bill Sideris", "Panda"])
            self.about.set_copyright("Copyright 2023 BredOS")
            self.about.set_license_type(Gtk.License.GPL_3_0)
            self.about.set_website("https://bredos.org")
            self.about.set_website_label("BredOS.org")
            self.about.set_version(config.installer_version)
            self.about.set_visible(True)
            logo = Gtk.Image.new_from_file(config.logo_path).get_paintable()
            self.about.set_logo(logo)
        elif name == "settings":
            self.settings = Gtk.Window()
            self.settings_frame = Gtk.Frame()
            self.settings_frame.set_label_align(0.5)
            self.settings_grid = Gtk.Grid()
            self.settings_grid.set_column_homogeneous(True)
            self.settings_grid.set_row_spacing(10)
            self.settings_grid.set_column_spacing(10)
            self.settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.settings_box.append(self.settings_grid)
            self.settings_frame.set_child(self.settings_box)
            self.settings.set_child(self.settings_frame)
            self.check_button = Gtk.CheckButton(label=_("Test"))
            self.settings_grid.attach(self.check_button, 0, 0, 1, 1)
            self.settings.set_title(_("Settings"))
            self.settings.set_default_size(300, 300)
            self.settings.set_resizable(False)
            self.settings.set_modal(self)
            self.settings.set_transient_for(self)
            self.settings.set_visible(True)
            self.settings.connect("close-request", self.close_settings)

    def run(self):
        if self.window:
            self.window.show_all()
        Gtk.main()


if __name__ == "__main__":
    _ = bakery.setup_translations()
    logger = bakery.setup_logging()
    logger_handler = LoggingHandler(logger)
    print(os.path.join(os.path.expanduser("~"), "Bakery") + "/config.toml")
    conf = bakery.load_config(file_path=os.path.join(os.path.expanduser("~"), "Bakery") + "/config.toml")

    if subprocess.check_output(["uname"]).decode().strip() == "Darwin":
        Gtk.Settings.get_default().set_property("gtk-theme-name", "Adwaita-dark")

    app = MainWindow()
    app.run()
