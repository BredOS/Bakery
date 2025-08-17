#!/usr/bin/env python
#
# Copyright 2025 BredOS
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

from datetime import datetime, UTC
from babel import dates, numbers
from babel import Locale as bLocale
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, Pango  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/locale_screen.ui")
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

        self.locale_dialog.set_transient_for(self.window)
        self.locale_dialog.set_modal(self.window)

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
                self.update_previews("en_US.UTF-8 UTF-8")

    def selected_lang(self, widget, row) -> None:
        if row != self.last_selected_row:
            self.last_selected_row = row
            lang = row.get_child().get_label()
            if len(self.lang_data[lang]) == 1:
                self.update_previews(self.lang_data[lang][0])
            else:
                # clear the listbox
                self.locales_list.remove_all()
                sr = langs()[lang]
                sr.sort()
                for locale in sr:
                    newrow = Gtk.ListBoxRow()
                    # Language - Layout
                    locale_label = Gtk.Label(label=locale)
                    newrow.set_child(locale_label)

                    self.locales_list.append(newrow)
                    self.locales_list.connect("row-activated", self.selected_locale)
                    self.show_dialog()
                    self.last_selected_locale = None
                    self.select_locale_btn.set_sensitive(False)

    def selected_locale(self, widget, row) -> None:
        if row != self.last_selected_locale:
            self.last_selected_locale = row
            self.update_previews(row.get_child().get_label())
            self.select_locale_btn.set_sensitive(True)

    def update_previews(self, selected_locale) -> None:
        try:
            the_locale, encoding = selected_locale.split(" ")
            if not encoding == "UTF-8":
                the_locale += "." + encoding
        except ValueError:
            the_locale = selected_locale
        self.locale = selected_locale
        locale_ = bLocale.parse(the_locale)
        date = dates.format_date(date=datetime.now(UTC), format="full", locale=locale_)
        time = dates.format_time(time=datetime.now(UTC), format="long", locale=locale_)
        currency = numbers.get_territory_currencies(locale_.territory)[0]
        currency_format = numbers.format_currency(1234.56, currency, locale=locale_)
        number_format = numbers.format_decimal(1234567.89, locale=locale_)
        self.date_preview.set_label(time + "  -  " + date)
        self.currency_preview.set_label(number_format + "  -  " + currency_format)

    def hide_dialog(self, stuff) -> None:
        try:
            # change the locale and update translations
            try:
                the_locale, encoding = self.locale.split(" ")
                if not encoding == "UTF-8":
                    the_locale += "." + encoding
            except ValueError:
                the_locale = self.locale
            win.queue_draw()
        except Exception as e:
            import traceback

            lp(traceback.format_exc(), mode="error")

        self.locale_dialog.hide()

    def show_dialog(self, *_) -> None:
        self.locales_list.unselect_all()
        self.locale_dialog.present()
