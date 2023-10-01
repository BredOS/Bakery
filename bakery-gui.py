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

import sys
import gi
import os
import gettext
from pyrunning import Command
from bakery import kb_langs

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Gettext
gettext.bindtextdomain("bakery", "./po")
gettext.textdomain("bakery")
gettext.install("bakery", "./po")
# py file path
script_dir = os.path.dirname(os.path.realpath(__file__))


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app) -> None:
        self.create_action("about", self.on_about_action)

    def do_activate(self) -> None:
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = BakeryWindow(application=self)
        win.present()

    def on_preferences_action(self, widget, _) -> None:
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, _) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="BredOS Installer",
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            version="0.1.0",
            developers=["Panda", "bill88t"],
            copyright="© 2023 BredOS",
            comments="BredOS Installer is a simple installer for BredOS.",
            license_type=Gtk.License.GPL_3_0,
            website="https://BredOS.org",
        )
        about.present()

    def create_action(self, name, callback, shortcuts=None) -> None:
        """Add an application action.
        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


@Gtk.Template.from_file(script_dir + "/data/window.ui")
class BakeryWindow(Adw.ApplicationWindow):
    __gtype_name__ = "BakeryWindow"

    stack1 = Gtk.Template.Child()
    stack1_sidebar = Gtk.Template.Child()
    cancel_btn = Gtk.Template.Child()
    back_btn = Gtk.Template.Child()
    next_btn = Gtk.Template.Child()

    main_stk = Gtk.Template.Child()
    offline_install = Gtk.Template.Child()
    online_install = Gtk.Template.Child()
    custom_install = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # go to the first page of main stack
        self.main_stk.set_visible_child_name("main_page")

        self.online_install.connect("clicked", self.main_button_clicked)
        self.offline_install.connect("clicked", self.main_button_clicked)
        self.custom_install.connect("clicked", self.main_button_clicked)

        self.next_btn.connect("clicked", self.on_next_clicked)
        self.back_btn.connect("clicked", self.on_back_clicked)

    def main_button_clicked(self, button) -> None:
        if button == self.online_install:
            print("online install")
            self.init_screens("online")
        elif button == self.offline_install:
            print("offline install")
            self.init_screens("offline")
        elif button == self.custom_install:
            print("custom install")
            self.init_screens("custom")

    def on_next_clicked(self, button) -> None:
        self.current_page += 1
        self.update_buttons()
        self.stack1.set_visible_child_name(f"page{self.current_page}")

    def on_back_clicked(self, button) -> None:
        self.current_page -= 1
        self.update_buttons()
        self.stack1.set_visible_child_name(f"page{self.current_page}")

    def update_buttons(self) -> None:
        num_pages = len(self.stack1.get_children())
        self.next_btn.set_sensitive(self.current_page < num_pages - 1)
        self.back_btn.set_sensitive(self.current_page > 0)

    def on_cancel_clicked(self, button) -> None:
        # go to the first page of main stack
        self.stack1.set_visible_child_name("main_page")

    def set_list_text(list, string) -> None:
        n = list.get_n_items()
        if n > 0:
            list.splice(0, n, [string])
        else:
            list.append(string)

    # def add_page(self, stack, page, title):
    # maybe later

    def init_screens(self, install_type) -> None:
        self.keyboard_page = kb_screen(window=self)
        self.stack1.add_titled(self.keyboard_page, "keyboard_page", "Keyboard")
        self.stack1.set_visible_child_name("keyboard_page")
        self.main_stk.set_visible_child_name("install_page")
        # for testing


@Gtk.Template.from_file(script_dir + "/data/kb_screen.ui")
class kb_screen(Adw.Bin):
    __gtype_name__ = "kb_screen"

    event_controller = Gtk.EventControllerKey.new()
    langs_list = Gtk.Template.Child()  # GtkListBox

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.kb_data = kb_langs()  # {country: layouts in a list]}
        builder = Gtk.Builder.new_from_file(script_dir + "/data/kb_dialog.ui")

        self.variant_dialog = builder.get_object("variant_dialog")

        self.variant_dialog.set_transient_for(self.window)
        self.variant_dialog.set_modal(self.window)

        self.select_variant_btn = builder.get_object("select_variant_btn")
        self.variant_list = builder.get_object("variant_list")  # GtkListBox

        self.select_variant_btn.connect("clicked", self.confirm_selection)
        self.populate_layout_list()

    def populate_layout_list(self) -> None:
        for lang in self.kb_data:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

    def confirm_selection(self, *_) -> None:
        self.variant_dialog.hide()

    def set_layout(self, layout) -> None:
        raise NotImplementedError

    def show_dialog(self, *_) -> None:
        self.variant_dialog.present()

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            layouts = self.kb_data[lang]
            if layouts is None:
                print("no layouts")
            else:
                # clear the listbox
                self.variant_list.remove_all()
                for layout in layouts[0]:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    layout_label = Gtk.Label(label=f"{lang} - {layout}")
                    newrow.set_child(layout_label)

                    self.variant_list.append(newrow)
                    self.variant_list.connect("row-activated", self.selected_layout)
                    self.last_selected_layout = None

                self.show_dialog()

    def selected_layout(self, widget, row) -> None:
        if row != self.last_selected_layout:
            self.last_selected_layout = row
            layout = row.get_child().get_label()
            print(layout)


app = BakeryApp(application_id="org.bredos.bakery")
app.run(sys.argv)
