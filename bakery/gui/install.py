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

from bakery import lp, lrun, _, st_msgs
from pyrunning import LoggingLevel
from bakery.install import install
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # type: ignore


@Gtk.Template(resource_path="/org/bredos/bakery/ui/install_screen.ui")
class install_screen(Adw.Bin):
    __gtype_name__ = "install_screen"

    progress_bar = Gtk.Template.Child()
    curr_action = Gtk.Template.Child()
    console_text_view = Gtk.Template.Child()
    console = Gtk.Template.Child()  # GtkScrolledWindow

    def __init__(self, window, **kwargs) -> None:
        super().__init__(**kwargs)
        self.window = window
        self.console_buffer = self.console_text_view.get_buffer()
        self.console_buffer.connect("changed", self.on_text_buffer_changed)

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

    def on_text_buffer_changed(self, buffer):
        # Scroll to the end of the text buffer
        adj = self.console.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

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

        pos = message.find("%ST")
        if pos != -1:
            prs = message.rfind("%")
            stm = st_msgs[int(message[pos + 3 : prs])]
            self.progress_bar.set_fraction(stm[1] / 100)
            self.curr_action.set_label(stm[0])
        else:
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


class InstallThread(threading.Thread):
    def __init__(self, window, install_window):
        threading.Thread.__init__(self)
        self.window = window
        self.install_window = install_window

    def run(self):
        install_data = self.window.collect_data(show_pass=True)
        lp(
            "Starting install with data: "
            + str(self.window.collect_data(show_pass=False))
        )
        res = install(install_data)
        if res == 0:
            # Change to finish page
            self.window.current_page = self.window.pages.index("Finish")
            page_name = self.window.pages[self.window.current_page]
            page_id = self.window.get_page_id(page_name)
            self.window.stack1.set_visible_child_name(page_id)
            self.window.button_box.set_visible(True)
            self.window.back_btn.set_visible(False)
            self.window.next_btn.disconnect_by_func(self.window.on_install_btn_clicked)
            self.window.next_btn.connect("clicked", self.window.on_done_clicked)
            self.window.next_btn.set_label(
                _("Reboot")
            )  # pyright: ignore[reportCallIssue]
        else:
            GLib.timeout_add(500, self.window.err_dialog.present)
