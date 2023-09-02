#! /usr/bin/env python

"""Installer for BredOS written in py"""

from sys import argv, exit
import locale, os, config, gi, subprocess
import bakery
from pyrunning import logging, LogMessage, LoggingHandler, Command
from datetime import datetime

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk,  Gio

class MenuButton(Gtk.MenuButton):
    def __init__(self, xml, name, icon_name="open-menu-symbolic"):
        super(MenuButton, self).__init__()
        builder = Gtk.Builder()
        builder.add_from_string(xml)
        menu = builder.get_object(name)
        self.set_menu_model(menu)
        self.set_icon_name(icon_name)

class Window(Gtk.ApplicationWindow):
    def __init__(self, title, width, height, **kwargs):
        super(Window, self).__init__(**kwargs)
        self.set_default_size(width, height)
        self.headerbar = Gtk.HeaderBar()
        self.set_titlebar(self.headerbar)
        label = Gtk.Label()
        label.set_text(title)
        self.headerbar.set_title_widget(label)
        self.css_provider = None
        # self.set_resizable(False)

    def load_css(self, css_fn) -> None:
        if css_fn and os.path.exists(css_fn):
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(css_fn)
            except GLib.Error as e:
                print(_("CSS loading failed:", str(e)))
                return None
            print("Loaded styling:", str(css_fn))
            self.css_provider = css_provider

    def _add_widget_styling(self, widget) -> None:
        if self.css_provider:
            context = widget.get_style_context()
            context.add_provider(self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def add_custom_styling(self, widget) -> None:
        self._add_widget_styling(widget)
        for child in widget:
            self.add_custom_styling(child)

    def create_action(self, name, callback) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

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

class MainWindow(Window):
    def __init__(self, title, width, height, **kwargs):
        LogMessage.Info("Initializing main window").write(logging_handler=logger_handler)
        super(MainWindow, self).__init__(title, height, width, **kwargs)
        # self.load_css("main.css")
        self.load_css("extra.css")
        self.revealer = Gtk.Revealer()
        menu = MenuButton(APP_MENU, "app-menu")
        self.headerbar.pack_end(menu)
        self.create_action("about", self.menu_handler)
        self.create_action("settings", self.menu_handler)
        welcome_page = self.create_welcome_page()
        self.set_child(welcome_page)  

    def create_welcome_page(self) -> Gtk.Box:
        welcome_label = Gtk.Label(label=_("Welcome to BredOS!"))
        welcome_label.set_halign(Gtk.Align.CENTER)  # Align the label to the center
        # add image
        image = Gtk.Image.new_from_file(config.logo_path)
        image.set_halign(Gtk.Align.CENTER)  # Align the image to the center
        image.set_margin_top(10)  # Add top margin to the image
        image.set_margin_bottom(10)  # Add bottom margin to the image
        #size 256x256
        image.set_pixel_size(256)
        butbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        butbox.set_halign(Gtk.Align.CENTER)

        buttons ={"offline": [_("Offline Installation"), config.logo_path], "online": [_("Online Installation"), config.logo_path], "custom": [_("Custom Installation"), config.logo_path]}
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

    def post_sellection(self, selection) -> Gtk.Box:

        stage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        stage_box.set_vexpand(True)  # Expand vertically
        stage_list = Gtk.ListBox()
        stage_list.set_selection_mode(Gtk.SelectionMode.NONE)
        stage_list.set_vexpand(True)  # Expand vertically
        stage_box.append(stage_list)
        if selection == "offline":
            self.stages = [_("Location"), _("Keyboard"), _("User"), _("Summary"), _("Install")]  # Add more stages
        elif selection == "online":
            self.stages= [_("Location"), _("Keyboard"), _("Desktop Environment"), _("Packages"), _("User"), _("Summary"), _("Install")]  # Add more stages
        self.stage_labels = []  # List to store references to stage labels

        for stage in self.stages:
            row = Gtk.ListBoxRow()
            stage_label = Gtk.Label(label=_(stage))
            stage_label.set_halign(Gtk.Align.START)  # Align stage labels to the left
            stage_label.set_margin_start(10)  # Add left margin to the label
            stage_label.set_margin_end(10)  # Add right margin to the label
            stage_label.set_margin_top(5)  # Add top margin to the label
            stage_label.set_margin_bottom(5)  # Add bottom margin to the label
            row.set_child(stage_label)
            stage_list.append(row)
            self.stage_labels.append(stage_label) # Keep a reference to the labels

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)  # Expand vertically
        # add extra padding to the right 
        self.stack.set_margin_end(10)  # Add right margin to the stack

        self.location_page = self.create_location_page()
        self.keyboard_page = self.create_keyboard_page()
        # Add more pages as needed

        self.stack.add_named(self.location_page, _("Location"))
        self.stack.add_named(self.keyboard_page, _("Keyboard"))
        

        self.next_button = Gtk.Button(label=_("Next"))
        self.back_button = Gtk.Button(label=_("Back"))

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)  # Align buttons to the right
        button_box.set_valign(Gtk.Align.END)  # Align buttons to the bottom
        button_box.set_margin_end(10)  # Add right margin to the buttons
        button_box.set_margin_bottom(10)  # Add bottom margin to the buttons
        button_box.append(self.back_button)
        button_box.append(self.next_button)
        button_box.set_hexpand(True)  # Expand horizontally

        button_grid = Gtk.Grid()  # Create a grid for buttons and stack
        button_grid.attach(self.stack, 0, 0, 1, 1)
        button_grid.attach(button_box, 0, 1, 1, 1)
        button_grid.set_hexpand(True)  # Expand horizontally
        
        self.current_page_index = 0
        self.stack.set_visible_child_name(_("Location"))
        self.update_button_states()  # Update button states initially

        self.next_button.connect("clicked", self.on_next_clicked)
        self.back_button.connect("clicked", self.on_back_clicked)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.append(stage_box)
        vbox.append(button_grid)
        vbox.set_valign(Gtk.Align.CENTER)  # Align the box to the center
        return vbox

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

    def create_keyboard_page(self) -> Gtk.Box:
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

    def on_button_clicked(self, button, button_id) -> None:
            main_box = self.post_sellection(button_id)
            self.set_child(main_box)
            # trigger next button

    def on_next_clicked(self, button) -> None:
        self.current_page_index += 1
        if self.current_page_index >= len(self.stages):
            self.current_page_index = 0
        self.stack.set_visible_child_name(self.stages[self.current_page_index])
        self.update_button_states()
        self.update_stages_list_selection()

    def on_back_clicked(self, button) -> None:
        self.current_page_index -= 1
        if self.current_page_index < 0:
            self.current_page_index = len(self.stages) - 1
        self.stack.set_visible_child_name(self.stages[self.current_page_index])
        self.update_button_states()
        self.update_stages_list_selection()

    def update_button_states(self) -> None:
        self.next_button.set_sensitive(self.current_page_index < len(self.stages) - 1)
        self.back_button.set_sensitive(self.current_page_index > 0)
    
    def update_stages_list_selection(self) -> None:
        for index, stage_label in enumerate(self.stage_labels):
            if index == self.current_page_index:
                stage_label.set_state_flags(Gtk.StateFlags.SELECTED, True)
            else:
                stage_label.set_state_flags(Gtk.StateFlags.SELECTED, False)

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
            self.about.set_website("http://bredos.org")
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

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="org.bredos.bakery", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow("BredOS Installer", 700, 1100, application=self)
        win.present()

if __name__ == "__main__":
    _ = bakery.setup_translations()
    logger = bakery.setup_logging()
    logger_handler = LoggingHandler(logger)
    if subprocess.check_output(["uname"]).decode().strip() == "Darwin":
        Gtk.Settings.get_default().set_property("gtk-theme-name", "Adwaita-dark")
    app = Application()
    app.run(argv)
