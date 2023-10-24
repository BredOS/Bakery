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
import faulthandler

faulthandler.enable()
import sys
import gi
import os
import gettext
import babel
import requests
import json
import threading
import bakery
from bakery import (
    kb_langs,
    langs,
    tz_list,
    geoip,
    validate_username,
    validate_fullname,
    validate_hostname,
    lp,
)
from time import sleep
from datetime import date, datetime, time
from babel import dates, numbers
from pyrunning import (
    LoggingHandler,
    LogMessage,
    Command,
    LoggingLevel,
    BatchJob,
    Function,
)
from pytz import timezone
import config

# from bakery import kb_langs

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

# py file path
script_dir = os.path.dirname(os.path.realpath(__file__))


def setup_translations(lang: object = None) -> gettext.GNUTranslations:
    """
    Setup translations

        Does the following:
        - Loads the translations from the locale folder
        - Sets the translations for the gettext module

        Returns:  A gettext translation object
        :rtype: object
    """
    lang_path = os.path.join(os.path.dirname(__file__), "locale")
    # Load translations
    if lang is not None:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        translation = gettext.translation("bakery", lang_path, languages=[lang])
        translation.install()
        return translation.gettext  # type: ignore
    else:
        gettext.bindtextdomain("bakery", lang_path)
        gettext.textdomain("bakery")
        return gettext.gettext  # type: ignore


class BakeryApp(Adw.Application):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app) -> None:
        self.create_action("about", self.on_about_action)

    def do_activate(self) -> None:
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        global _
        _ = setup_translations()
        global win
        win = self.props.active_window
        if not win:
            win = BakeryWindow(application=self)
            self.win = win
        win.present()

    def on_preferences_action(self, widget, _) -> None:
        """Callback for the app.preferences action."""
        # Implement your preferences logic here
        pass

    def on_about_action(self, widget, py) -> None:
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="BredOS Installer",
            application_icon="org.bredos.bakery",
            developer_name="BredOS",
            debug_info=self.win.collect_data(),
            version="0.1.0",
            developers=["Panda", "bill88t"],
            designers=["Panda", "DustyDaimler"],
            copyright="© 2023 BredOS",
            comments=_("Bakery is a simple installer for BredOS"),
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
    main_page = Gtk.Template.Child()
    install_page = Gtk.Template.Child()
    offline_install = Gtk.Template.Child()
    # online_install = Gtk.Template.Child()
    custom_install = Gtk.Template.Child()
    install_cancel = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # go to the first page of main stack
        self.main_stk.set_visible_child(self.main_page.get_child())
        self.cancel_dialog = self.install_cancel
        self.install_type = None
        # self.online_install.connect("clicked", self.main_button_clicked)
        self.offline_install.connect("clicked", self.main_button_clicked)
        self.custom_install.connect("clicked", self.main_button_clicked)
        self.cancel_dialog.connect("response", self.delete_pages)

        self.next_btn.connect("clicked", self.on_next_clicked)
        self.back_btn.connect("clicked", self.on_back_clicked)
        self.cancel_btn.connect("clicked", self.on_cancel_clicked)

    def main_button_clicked(self, button) -> None:
        if button == self.offline_install:
            print("offline install")
            self.init_screens("offline")
        # elif button == self.online_install:
        #     print("online install")
        #     self.init_screens("online")
        elif button == self.custom_install:
            print("custom install")
            self.init_screens("custom")

    def on_finish_clicked(self, button) -> None:
        builder = Gtk.Builder.new_from_file(script_dir + "/data/summary_screen.ui")
        install_confirm = builder.get_object("install_confirm")

    def on_next_clicked(self, button) -> None:
        num_pages = len(self.pages)
        if self.current_page < num_pages - 1:
            self.current_page += 1
            page_name = self.pages[self.current_page]
            page_id = self.get_page_id(page_name)
            self.stack1.set_visible_child_name(page_id)
            self.update_buttons()

    def on_back_clicked(self, button) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            page_name = self.pages[self.current_page]
            page_id = self.get_page_id(page_name)
            self.stack1.set_visible_child_name(page_id)
            self.update_buttons()

    def update_buttons(self) -> None:
        num_pages = len(self.pages)
        # if page is user page make it so user cant go forward
        global user_event
        user_event = threading.Event()
        self.check_thread = CheckThread(all_pages["User"])
        if self.current_page == self.pages.index("User"):
            self.next_btn.set_sensitive(False)
            # start the thread to check when all fields are filled
            self.check_thread.start()
        elif self.current_page == self.pages.index("Summary"):
            user_event.set()
            all_pages["Summary"].page_shown()
            self.next_btn.set_sensitive(self.current_page < num_pages - 1)
            self.back_btn.set_sensitive(self.current_page > 0)
        else:
            user_event.set()
            self.next_btn.set_sensitive(self.current_page < num_pages - 1)
            self.back_btn.set_sensitive(self.current_page > 0)

    def on_cancel_clicked(self, button) -> None:
        # connect the yes button to the delete_pages function
        self.cancel_dialog.present()

    def delete_pages(self, dialog, resp) -> None:
        if resp == "yes":
            self.main_stk.set_visible_child(self.main_page.get_child())
            # remove all pages from stack1

            pages = [self.get_page_id(x) for x in self.pages]
            for page_id in pages:
                w = self.stack1.get_child_by_name(page_id)
                self.stack1.remove(w)
        self.cancel_dialog.hide()

    def get_page_id(self, page_name) -> str:
        return config.pages[page_name]

    def collect_data(self, *_) -> dict:
        data = {}
        if not self.install_type == None:
            data["installer_version"] = config.installer_version
            data["install_type"] = self.install_type
            data["shown_pages"] = self.pages
            data["root_password"] = None
            data["ntp"] = True
            data["layout"] = all_pages["Keyboard"].layout
            data["locale"] = all_pages["Locale"].locale
            data["timezone"] = all_pages["Timezone"].timezone
            data["hostname"] = all_pages["User"].get_hostname()
            data["user"] = all_pages["User"].collect_data()
            data["packages"] = []
            data["de_packages"] = []
            return data
        else:
            return {"install_type": "None"}

    def set_list_text(list, string) -> None:
        n = list.get_n_items()
        if n > 0:
            list.splice(0, n, [string])
        else:
            list.append(string)

    def add_pages(self, stack, pages) -> None:
        global all_pages
        all_pages = {}
        for page in pages:
            page_ = globals()[config.pages[page]](window=self)
            all_pages[page] = page_
            stack.add_titled(page_, config.pages[page], page)

    def init_screens(self, install_type) -> None:
        if install_type == "online":
            self.pages = config.online_pages
            self.add_pages(self.stack1, self.pages)
        elif install_type == "offline":
            self.pages = config.offline_pages
            self.add_pages(self.stack1, self.pages)

        self.current_page = 0
        self.update_buttons()
        self.install_type = install_type
        self.main_stk.set_visible_child(self.install_page.get_child())


@Gtk.Template.from_file(script_dir + "/data/kb_screen.ui")
class kb_screen(Adw.Bin):
    __gtype_name__ = "kb_screen"

    event_controller = Gtk.EventControllerKey.new()
    langs_list = Gtk.Template.Child()  # GtkListBox

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.kb_data = {
            k: v for k, v in sorted(kb_langs().items())
        }  # {country: layouts in a list]}
        self.lang_to_country = {lang: code for code, lang in bakery._kblangmap.items()}

        self.layout = {"lang": None, "variant": None}

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

            # preselect the American English layout
            if lang == "American English":
                self.langs_list.select_row(row)
                self.last_selected_row = row
                self.layout["lang"] = lang
                self.layout["variant"] = "normal"
                self.change_kb_layout(lang, "normal")

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
            self.layout["lang"] = lang
            if layouts[0] is None:
                print("no layouts")
                self.layout["variant"] = "normal"
                self.change_kb_layout(self.layout["lang"], self.layout["variant"])
            else:
                # clear the listbox
                self.variant_list.remove_all()
                # add normal layout
                newrow = Gtk.ListBoxRow()
                # Language - Layout
                layout_label = Gtk.Label(label=f"{lang} - normal")
                newrow.set_child(layout_label)

                self.variant_list.append(newrow)
                self.variant_list.connect("row-activated", self.selected_layout)
                self.last_selected_layout = None
                for layout_ in layouts[0]:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    layout_label = Gtk.Label(label=f"{lang} - {layout_}")
                    newrow.set_child(layout_label)

                    self.variant_list.append(newrow)
                    self.variant_list.connect("row-activated", self.selected_layout)

                self.show_dialog()

    def selected_layout(self, widget, row) -> None:
        if row != self.last_selected_layout:
            self.last_selected_layout = row
            self.layout["variant"] = row.get_child().get_label().split(" - ")[1]
            self.change_kb_layout(self.layout["lang"], self.layout["variant"])

    def change_kb_layout(self, lang, layout) -> None:
        if layout == "normal":
            layout = ""
        Command(["setxkbmap", self.lang_to_country[lang], layout]).run_log_and_wait(
            logging_handler=bakery.logging_handler
        )


@Gtk.Template.from_file(script_dir + "/data/locale_screen.ui")
class locale_screen(Adw.Bin):
    __gtype_name__ = "locale_screen"

    langs_list = Gtk.Template.Child()
    date_preview = Gtk.Template.Child()
    currency_preview = Gtk.Template.Child()

    locale_dialog = Gtk.Template.Child()
    locales_list = Gtk.Template.Child()
    select_locale_btn = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.lang_data = {k: v for k, v in sorted(langs().items())}

        self.populate_locales_list()
        self.select_locale_btn.connect("clicked", self.hide_dialog)

    def populate_locales_list(self) -> None:
        for lang in self.lang_data:
            row = Gtk.ListBoxRow()
            lang_label = Gtk.Label(label=lang)
            row.set_child(lang_label)

            self.langs_list.append(row)
            self.langs_list.connect("row-activated", self.selected_lang)
            self.last_selected_row = None

            if lang == "English":
                self.langs_list.select_row(row)
                self.last_selected_row = row
                self.update_previews("en_US")

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            print(lang)
            if len(self.lang_data[lang]) == 1:
                self.update_previews(self.lang_data[lang][0])
            else:
                # clear the listbox
                self.locales_list.remove_all()
                for locale in langs()[lang]:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    locale_label = Gtk.Label(label=locale)
                    newrow.set_child(locale_label)

                    self.locales_list.append(newrow)
                    self.locales_list.connect("row-activated", self.selected_locale)
                    self.show_dialog()
                    self.last_selected_locale = None

    def selected_locale(self, widget, row) -> None:
        if row != self.last_selected_locale:
            self.last_selected_locale = row
            self.update_previews(row.get_child().get_label())

    def update_previews(self, selected_locale) -> None:
        try:
            the_locale, encoding = selected_locale.split(" ")
            if not encoding == "UTF-8":
                the_locale += "." + encoding
        except ValueError:
            the_locale = selected_locale
        self.locale = the_locale
        locale_ = babel.Locale.parse(the_locale)
        date = dates.format_date(date=datetime.utcnow(), format="full", locale=locale_)
        time = dates.format_time(time=datetime.utcnow(), format="long", locale=locale_)
        currency = numbers.get_territory_currencies(locale_.territory)[0]
        currency_format = numbers.format_currency(1234.56, currency, locale=locale_)
        number_format = numbers.format_decimal(1234567.89, locale=locale_)
        self.date_preview.set_label(time + "  -  " + date)
        self.currency_preview.set_label(number_format + "  -  " + currency_format)

    def hide_dialog(self, *_) -> None:
        self.locale_dialog.hide()

    def show_dialog(self, *_) -> None:
        self.locale_dialog.present()


class CheckThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

    def run(self):
        while True:
            if user_event.is_set():
                break
            if (
                (self.window.get_username() is not None)
                and (self.window.get_hostname() is not None)
                and (self.window.get_password() is not None)
            ):
                print("All good")
                win.next_btn.set_sensitive(True)
            else:
                win.next_btn.set_sensitive(False)
            sleep(0.5)


class InstallThread(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

    def run(self):
        install_data = self.window.collect_data()
        lp("Starting install with data: " + str(install_data))
        bakery.install(install_data)


@Gtk.Template.from_file(script_dir + "/data/user_screen.ui")
class user_screen(Adw.Bin):
    __gtype_name__ = "user_screen"

    fullname_entry = Gtk.Template.Child()
    user_entry = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    pass_entry = Gtk.Template.Child()
    confirm_pass_entry = Gtk.Template.Child()
    user_info = Gtk.Template.Child()

    uid_row = Gtk.Template.Child()
    nopasswd = Gtk.Template.Child()
    autologin = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window

        self.confirm_pass_entry.connect("changed", self.on_confirm_pass_changed)
        self.user_entry.connect("changed", self.on_username_changed)
        self.hostname_entry.connect("changed", self.on_hostname_changed)
        self.fullname_entry.connect("changed", self.on_fullname_changed)
        self.user_info_is_visible = False

    def on_fullname_changed(self, entry):
        fullname = entry.get_text()
        a = validate_fullname(fullname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.fullname_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.fullname_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_hostname_changed(self, entry):
        hostname = entry.get_text()
        a = validate_hostname(hostname)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.hostname_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.hostname_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_username_changed(self, entry):
        username = entry.get_text()
        a = validate_username(username)
        if a == "":
            self.user_info.set_visible(False)
            self.user_info_is_visible = False
            self.user_entry.get_style_context().remove_class("error")
        else:
            self.user_info.set_label(a)
            self.user_entry.get_style_context().add_class("error")
            if not self.user_info_is_visible:
                self.user_info.set_visible(True)
                self.user_info_is_visible = True

    def on_confirm_pass_changed(self, entry):
        pass_text = self.pass_entry.get_text()
        confirm_pass_text = entry.get_text()

        if not pass_text == confirm_pass_text:
            self.confirm_pass_entry.get_style_context().add_class("error")
        elif pass_text == confirm_pass_text:
            self.confirm_pass_entry.get_style_context().remove_class("error")

    def get_fullname(self) -> str:
        if self.fullname_entry.get_text() == "":
            return None
        else:
            if validate_fullname(self.fullname_entry.get_text()) == "":
                return self.fullname_entry.get_text()
            else:
                return None

    def get_username(self) -> str:
        if self.user_entry.get_text() == "":
            return None
        else:
            if validate_username(self.user_entry.get_text()) == "":
                return self.user_entry.get_text()
            else:
                return None

    def get_hostname(self) -> str:
        if self.hostname_entry.get_text() == "":
            return None
        else:
            if validate_hostname(self.hostname_entry.get_text()) == "":
                return self.hostname_entry.get_text()
            else:
                return None

    def get_password(self) -> str:
        if self.pass_entry.get_text() == "":
            return None
        else:
            pass_text = self.pass_entry.get_text()
            confirm_pass_text = self.confirm_pass_entry.get_text()
            if pass_text == confirm_pass_text:
                return pass_text
            else:
                return None

    def collect_data(self) -> dict:
        data = {}
        data["fullname"] = self.get_fullname()
        data["username"] = self.get_username()
        data["password"] = self.get_password()
        data["uid"] = int(self.uid_row.get_value())
        data["gid"] = int(self.uid_row.get_value())
        data["sudo_nopasswd"] = self.nopasswd.get_active()
        data["autologin"] = self.autologin.get_active()
        data["shell"] = "/bin/zsh"
        data["groups"] = ["wheel", "network", "video", "audio", "storage"]
        return data


@Gtk.Template.from_file(script_dir + "/data/timezone_screen.ui")
class timezone_screen(Adw.Bin):
    __gtype_name__ = "timezone_screen"

    regions_list = Gtk.Template.Child()
    zones_list = Gtk.Template.Child()
    curr_time = Gtk.Template.Child()
    preview_row = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.tz_list = tz_list()
        current_timezone = geoip()
        self.timezone = {}
        self.timezone["region"] = current_timezone["region"]
        self.timezone["zone"] = current_timezone["zone"]
        print(type(self.curr_time))

        self.zones_list.connect("notify::selected-item", self.on_zone_changed)
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)

        self.regions_list.connect("notify::selected-item", self.on_region_changed)
        self.region_model = Gtk.StringList()
        self.regions_list.set_model(self.region_model)
        for item in list(self.tz_list.keys()):
            self.region_model.append(item)

        self.change_regions_list(current_timezone["region"])
        self.regions_list.set_selected(
            list(self.tz_list.keys()).index(current_timezone["region"])
        )
        self.select_zone(current_timezone["region"], current_timezone["zone"])

    def on_region_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["region"] = selected.props.string
            self.change_regions_list(selected.props.string)

    def on_zone_changed(self, dropdown, *_):
        selected = dropdown.props.selected_item
        if selected is not None:
            self.timezone["zone"] = selected.props.string
            self.preview_timezone(self.timezone["region"], selected.props.string)

    def change_regions_list(self, region) -> None:
        self.zone_model = Gtk.StringList()
        self.zones_list.set_model(self.zone_model)
        for zone in self.tz_list[region]:
            self.zone_model.append(zone)

    def select_zone(self, region, zone) -> None:
        # get the index of the zone in the list
        index = self.tz_list[region].index(zone)
        self.zones_list.set_selected(index)

    def preview_timezone(self, region, zone) -> None:
        # timezone expects region/zone
        try:
            tz = timezone(str(region + "/" + zone))
        except:
            tz = None
        if tz is not None:
            time = datetime.now(tz)
            self.curr_time.set_label(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.preview_row.set_subtitle("Previewing time in " + str(tz))


@Gtk.Template.from_file(script_dir + "/data/de_screen.ui")
class de_screen(Adw.Bin):
    __gtype_name__ = "de_screen"

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window


@Gtk.Template.from_file(script_dir + "/data/summary_screen.ui")
class summary_screen(Adw.Bin):
    __gtype_name__ = "summary_screen"

    locale_preview = Gtk.Template.Child()
    kb_lang = Gtk.Template.Child()
    kb_variant = Gtk.Template.Child()
    tz_preview = Gtk.Template.Child()

    name_preview = Gtk.Template.Child()
    username_preview = Gtk.Template.Child()
    hostname_preview = Gtk.Template.Child()

    autologin = Gtk.Template.Child()  # switch
    nopasswd = Gtk.Template.Child()  # switch

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        # print(type(self.locale_preview))

    def page_shown(self) -> None:
        self.data = self.window.collect_data()
        self.locale_preview.set_label(self.data["locale"])
        self.kb_lang.set_label(self.data["layout"]["lang"])
        self.kb_variant.set_label(self.data["layout"]["variant"])
        self.tz_preview.set_label(
            self.data["timezone"]["region"] + "/" + self.data["timezone"]["zone"]
        )
        self.name_preview.set_label(self.data["user"]["fullname"])
        self.username_preview.set_label(self.data["user"]["username"])
        self.hostname_preview.set_label(self.data["hostname"])
        self.autologin.set_active(self.data["user"]["autologin"])
        self.nopasswd.set_active(self.data["user"]["sudo_nopasswd"])


@Gtk.Template.from_file(script_dir + "/data/install_screen.ui")
class install_screen(Adw.Bin):
    __gtype_name__ = "install_screen"

    progress_bar = Gtk.Template.Child()
    curr_action = Gtk.Template.Child()
    console_text_view = Gtk.Template.Child()

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.console_buffer = self.console_text_view.get_buffer()

        self.colors = {
            "CRITICAL": "#a40000",
            "ERROR": "#ff0000",
            "EXCEPTION": "#ff0000",
            "WARNING": "#ffa500",
            "INFO": "#3584e4",
            "DEBUG": "#808080",
            "NOTSET": "#808080",
            "": "#808080",
            None: "#808080",
        }

    def console_logging(
        self,
        logging_level: int,
        message: str,
        *args,
        loginfo_filename="",
        loginfo_line_number=-1,
        loginfo_function_name="",
        loginfo_stack_info=None,
        **kwargs,
    ):
        logging_level_name = LoggingLevel(logging_level).name
        GLib.idle_add(
            lambda: (
                self.console_buffer.insert_markup(
                    self.console_buffer.get_end_iter(),
                    "".join(
                        (
                            "- ",
                            '<span color="{:s}">',
                            logging_level_name.rjust(8, " "),
                            ": ",
                            "</span>",
                        )
                    ).format(self.colors[logging_level_name]),
                    -1,
                )
            )
        )

        if LoggingLevel(logging_level) != LoggingLevel.DEBUG:
            GLib.idle_add(
                lambda: (
                    self.console_buffer.insert(
                        self.console_buffer.get_end_iter(), "".join((message, "\n"))
                    )
                )
            )
        else:
            GLib.idle_add(
                lambda: (
                    self.console_buffer.insert_markup(
                        self.console_buffer.get_end_iter(),
                        "".join(
                            (
                                '<span color="{:s}">',
                                GLib.markup_escape_text(message),
                                "</span>" "\n",
                            )
                        ).format(self.colors[logging_level_name]),
                        -1,
                    )
                )
            )


@Gtk.Template.from_file(script_dir + "/data/finish_screen.ui")
class finish_screen(Adw.Bin):
    __gtype_name__ = "finish_screen"

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window


app = BakeryApp(application_id="org.bredos.bakery")
app.run(sys.argv)
