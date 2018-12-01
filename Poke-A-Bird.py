"""
Copyright (c) 2018 Elad Yacovi, Nerya Meshulam

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import hashlib
import json
from shutil import copyfile
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename
import math
import vlc
import pathlib
import os
import platform
import time
import csv
from threading import Thread, Event
import tkinter.ttk as ttk
import datetime
import time
import PIL
from PIL import Image
from pandas import to_datetime
from Pmw import Balloon

__version__ = '0.3'

class ControlBlock:
    def __init__(self):
        self.cache_file = pathlib.Path('cache.json')
        self.events = []
        self.current_media_hash = ''
        self.cached = {}
        self.cached = self.default_cache = {'total_number_of_events': 0,
                                            'session_timestamp': {'is_set': 0, 'value': 0},
                                            'export_location': {'is_set': 0, 'value': ''},
                                            'grid': {'is_set': 0, 'value': {"rows": 0, "cols": 0, "borders": [], "inner_lines": [], "inner_points": [], "attributes": ''}},
                                            'media_name': '',
                                            'timestamp_type': 'global'}

    def dump_cache(self):
        if self.current_media_hash != '':
            cached_json = {}
            if self.cache_file.is_file():
                with open(self.cache_file, 'r') as fp:
                    cached_json = json.load(fp)

            cached_json[self.current_media_hash] = self.cached

            with open(self.cache_file, 'w') as fp:
                json.dump(cached_json, fp)

            self.current_media_hash = ''

        self.cached = self.default_cache

    def load_cache(self):
        if self.cache_file.is_file():
            with open(self.cache_file, 'r') as fp:
                cached_json = json.load(fp)
                if self.current_media_hash in cached_json:
                    self.cached = cached_json[self.current_media_hash]


class Configuration:

    def __init__(self):
        self.config_file = pathlib.Path('config.json')

        if self.config_file.is_file():
            with open(self.config_file, 'r') as fp:
                self.config = json.load(fp)
        else:
            self.config = {'last_export_path': '%USERPROFILE%',
                           'last_path': '%USERPROFILE%',
                           'identity_list': [],
                           'event_list': [],
                           'speed': 1,
                           'grid_point_size': 10,
                           'grid_line_size': 5,
                           'event_manager': {'size_x': 300, 'size_y': 300, 'pos_x': 300, 'pos_y': 300, 'number_of_events': 10},
                           'main_application': {'size_x': 300, 'size_y': 300, 'pos_x': 300, 'pos_y': 300}}


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        buffer = f.read(65536)
        hash_md5.update(buffer)
    return hash_md5.hexdigest()


class EventManager(Toplevel):

    class List(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent
            self.listbox = ttk.Treeview(self, height=1)
            self.y_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
            self.listbox.bind('<Double-1>', self.parent.on_click)
            self.listbox.bind('<Delete>', self.parent.delete_selected_item)
            self.listbox["columns"] = ('video_timestamp', 'session_timestamp', 'identities', 'events', 'description', 'pos_x', 'pos_y', 'attribute')
            self.listbox['show'] = 'headings'
            self.listbox.column("video_timestamp", minwidth=110, width=110, anchor='w')
            self.listbox.column("session_timestamp", minwidth=110, width=110, anchor='w')
            self.listbox.column("identities", minwidth=100, width=100, anchor='w')
            self.listbox.column("events", minwidth=100, width=100, anchor='w')
            self.listbox.column("description", minwidth=100, width=100, anchor='w')
            self.listbox.column("pos_x", minwidth=70, width=70, anchor='w')
            self.listbox.column("pos_y", minwidth=50, width=50, anchor='w')
            self.listbox.column("attribute", minwidth=100, width=100, anchor='w')
            self.listbox.heading("video_timestamp", text='Video Time', anchor='w')
            self.listbox.heading("session_timestamp", text='Session Time', anchor='w')
            self.listbox.heading("identities", text='Birds', anchor='w')
            self.listbox.heading("events", text='Events', anchor='w')
            self.listbox.heading("description", text='Description', anchor='w')
            self.listbox.heading("pos_x", text='Column', anchor='w')
            self.listbox.heading("pos_y", text='Row', anchor='w')
            self.listbox.heading("attribute", text='Attribute', anchor='w')
            self.y_scrollbar.pack(side=RIGHT, fill=Y)
            self.listbox.pack(side=LEFT, fill=BOTH, expand=TRUE)
            self.refresh_events()

        def refresh_events(self):
            self.clear_events()
            for event in control_block.events:
                self.listbox.insert('', END, values=self.parent.parent.translate_to_friendly_record(event))

        def clear_events(self):
            self.listbox.delete(*self.listbox.get_children())

    class StatusBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.status_label = Label(self, text='Total number of events: ' + str(control_block.cached['total_number_of_events']), bd=2, relief=SUNKEN, anchor=W)
            self.status_label.pack(side=BOTTOM, fill=X)

        def display(self, event):
            self.status_label.config(text='Total number of events: ' + str(control_block.cached['total_number_of_events']))

        def refresh_default_status(self):
            self.status_label.config(
                text='Total number of events: ' + str(control_block.cached['total_number_of_events']))

    def __init__(self, parent, *args, **kwargs):
        Toplevel.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.title('Event Manager')
        self.minsize(790, 250)

        event_manager_config = configuration.config['event_manager']
        self.geometry("%dx%d%+d%+d" % (event_manager_config['size_x'], event_manager_config['size_y'],
                                       event_manager_config['pos_x'], event_manager_config['pos_y']))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.list = self.List(self, borderwidth=2)
        self.status_bar = self.StatusBar(self)
        self.list.pack(fill=BOTH, expand=TRUE)
        self.status_bar.pack(fill=BOTH)

        self.bind_all('<Enter>', self.status_bar.display, add=True)

    def get_selected_event_index(self):
        iid = self.list.listbox.focus()
        if iid == '':
            return -1
        else:
            return self.list.listbox.index(iid)

    def delete_item(self, item):
        control_block.events.pop(item)
        control_block.cached['total_number_of_events'] -= 1
        self.list.refresh_events()

    def delete_selected_item(self, event=None):
        current_selection = self.get_selected_event_index()
        if current_selection == -1:
            return
        self.delete_item(current_selection)

    def on_click(self, event=None):
        current_selection = self.get_selected_event_index()
        if current_selection == -1:
            return
        self.parent.playback_panel.goto_timestamp(int(control_block.events[current_selection][0]))

    def on_closing(self):
        configuration.config['event_manager']['size_x'] = self.winfo_width()
        configuration.config['event_manager']['size_y'] = self.winfo_height()
        configuration.config['event_manager']['pos_x'] = self.winfo_x()
        configuration.config['event_manager']['pos_y'] = self.winfo_y()
        self.bind_all('<Enter>', self.parent.status_bar.DisplayOnLabel)
        self.destroy()
        self.parent.event_manager = None

    def on_media_stop(self):
        self.list.clear_events()
        self.status_bar.refresh_default_status()

    def refresh_events(self):
        self.list.refresh_events()
        self.status_bar.refresh_default_status()

    def on_media_open(self):
        self.list.refresh_events()
        self.status_bar.refresh_default_status()


class ttkTimer(Thread):
    def __init__(self, callback, tick):
        Thread.__init__(self)
        self.callback = callback
        self.stopFlag = Event()
        self.tick = tick
        self.iters = 0

    def run(self):
        while not self.stopFlag.wait(self.tick):
            self.iters += 1
            self.callback()

    def stop(self):
        self.stopFlag.set()

    def get(self):
        return self.iters


class ListBox(Frame):
    class Title(Frame):
        def __init__(self, parent, title, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.title = Label(self, text=title, anchor=W)

            self.new_icon = PhotoImage(file='./media/icons8-add-row-25.png')
            self.new_button = Button(self, image=self.new_icon, command=self.parent.add_item, relief=FLAT)

            self.remove_icon = PhotoImage(file='./media/icons8-delete-row-25.png')
            self.remove_button = Button(self, image=self.remove_icon, command=self.parent.delete_item, relief=FLAT)

            self.title.pack(fill=BOTH, side=LEFT, expand=TRUE)
            self.new_button.pack(side=LEFT, padx=1, pady=1)
            self.remove_button.pack(side=LEFT, padx=1, pady=1)

    class List(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.scrollbar = Scrollbar(self)
            self.listbox = Listbox(self, height=5, yscrollcommand=self.scrollbar.set, borderwidth=0,
                                   highlightthickness=0, exportselection=False, activestyle=NONE, selectmode=EXTENDED)
            self.scrollbar.config(command=self.listbox.yview)

            self.scrollbar.pack(side=RIGHT, fill=Y)
            self.listbox.pack(side=LEFT)
            for item in configuration.config[self.parent.attribute]:
                self.listbox.insert(END, item)

    def delete_item(self):
        current_selection = self.list.listbox.curselection()
        if current_selection != ():
            configuration.config[self.attribute].remove(self.list.listbox.get(current_selection))
            self.list.listbox.delete(current_selection)

    def ok_clicked(self, event=None):
        if self.entryStr.get() != '':
            self.list.listbox.insert(END, self.entryStr.get())
            configuration.config[self.attribute].append(self.entryStr.get())
            self.mark_item(END)
        self.window.destroy()

    def close(self, event=None):
        self.window.destroy()

    def add_item(self):
        self.window = window = Toplevel(self.parent.parent.parent, borderwidth=5)
        window.grab_set()
        window.title('Add ' + self.title)
        window.resizable(0, 0)
        self.entryStr = entryStr = StringVar()
        Label(window, text='Name: ').grid(row=0, column=0)
        self.entry = Entry(window, textvariable=entryStr, width=20)
        self.entry.grid(row=0, column=1)
        self.entry.focus_set()
        Button(window, text="Add", width=5, command=self.ok_clicked).grid(row=1, column=0, columnspan=2, pady=2)
        window.bind('<Return>', self.ok_clicked)
        window.bind('<Escape>', self.close)
        window.wait_window()

    def get_selected_items(self):
        items = []
        for item in self.list.listbox.curselection():
            items.append(self.list.listbox.get(item))
        return items

    def clear_all(self):
        self.list.listbox.selection_clear(0, END)

    def mark_item(self, index):
        self.clear_all()
        self.list.listbox.select_set(index)

    def on_mark_event(self, event):
        if event.keycode in range(ord('1'), ord('9') + 1):
            index = event.keycode - ord('1')
            if index >= 0 and index < self.list.listbox.size():
                self.mark_item(index)

    def __init__(self, parent, attribute, title, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.title = title
        self.attribute = attribute

        self.title_frame = self.Title(self, title)
        self.list = self.List(self)

        self.title_frame.pack(fill=BOTH, expand=TRUE)
        self.list.pack(side=BOTTOM)


class ControlBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.volume_var = IntVar()
        self.scale_var = DoubleVar()
        self.timer = ttkTimer(self.parent.playback_panel.OnTimer, 0.001)
        self.pause_icon = PhotoImage(file='./media/icons8-pause-32.png')
        self.play_icon = PhotoImage(file='./media/icons8-play-32.png')
        self.play = Button(self, image=self.play_icon, command=self.parent.playback_panel.on_play)
        self.stop_icon = PhotoImage(file='./media/icons8-stop-32.png')
        self.stop = Button(self, image=self.stop_icon, command=self.parent.playback_panel.on_stop)
        self.next_frame_icon = PhotoImage(file='./media/icons8-resume-button-32.png')
        self.next_frame = Button(self, image=self.next_frame_icon, command=self.parent.playback_panel.on_next_frame)
        self.speedup_icon = PhotoImage(file='./media/icons8-fast-forward-32.png')
        self.speedup = Button(self, image=self.speedup_icon, command=self.parent.playback_panel.on_speed_up)
        self.speeddown_icon = PhotoImage(file='./media/icons8-rewind-32.png')
        self.speeddown = Button(self, image=self.speeddown_icon, command=self.parent.playback_panel.on_speed_down)
        # self.zoom_in_icon = PhotoImage(file='./media/icons8-zoom-in-32.png')
        # self.zoomin = Button(self, image=self.zoom_in_icon, command=self.parent.playback_panel.on_zoom_in)
        # self.zoom_out_icon = PhotoImage(file='./media/icons8-zoom-out-32.png')
        # self.zoomout = Button(self, image=self.zoom_out_icon, command=self.parent.playback_panel.on_zoom_out)
        self.jump_forward_icon = PhotoImage(file='./media/icons8-end-32.png')
        self.jump_forward = Button(self, image=self.jump_forward_icon, command=self.on_jump_backward)
        self.jump_backward_icon = PhotoImage(file='./media/icons8-skip-to-start-32.png')
        self.jump_backword = Button(self, image=self.jump_backward_icon, command=self.on_jump_forward)
        self.fullscreen_icon = PhotoImage(file='./media/icons8-fit-to-width-32.png')
        self.fullsc = Button(self, image=self.fullscreen_icon, command=self.parent.playback_panel.on_full_screen)
        # self.show_grid_icon = PhotoImage(file='./media/show_grid.png')
        self.volslider = Scale(self, variable=self.volume_var, command=self.parent.playback_panel.on_volume_change, from_=0, to=100, orient=HORIZONTAL, length=100, showvalue=0)
        self.time_frame = Frame(self)
        self.time_label_balloon = Balloon(self)
        self.time_slider = Scale(self.time_frame, variable=self.scale_var, command=self.parent.playback_panel.scale_sel_without_media_update, from_=0, orient=HORIZONTAL, resolution=-1, showvalue=0)
        self.time_label = Label(self.time_frame, text="00:00:00.000", width=9)
        self.time_label.pack(side=RIGHT)
        self.time_label.bind('<Button-1>', self.on_time_label_click)
        self.time_label_balloon.bind(self.time_label, '{}'.format(control_block.cached['timestamp_type']))
        self.time_slider.pack(side=RIGHT, fill=X, expand=1)
        self.time_frame.pack(side=TOP, fill=X, expand=1)
        self.play.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.stop.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.speeddown.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.speedup.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.next_frame.pack(side=LEFT, fill=Y, padx=1, pady=3)
        # self.zoomin.pack(side=LEFT, fill=Y, padx=1, pady=3)
        # self.zoomout.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.jump_backword.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.jump_forward.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.fullsc.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.volslider.pack(side=LEFT, expand=TRUE, anchor=E, padx=1, pady=3)
        self.timer.start()
        self.parent.parent.update()

    def on_jump_backward(self, event=None):
        if not self.parent.playback_panel.is_media_loaded():
            return

        new_timestamp = self.parent.playback_panel.player.get_time() + 400
        if new_timestamp > self.parent.playback_panel.get_media_length():
            new_timestamp = self.parent.playback_panel.get_media_length()

        self.parent.playback_panel.player.set_time(new_timestamp)

    def on_jump_forward(self, event=None):
        if not self.parent.playback_panel.is_media_loaded():
            return

        new_timestamp = self.parent.playback_panel.player.get_time() - 400
        if new_timestamp < 0:
            new_timestamp = 0

        self.parent.playback_panel.player.set_time(new_timestamp)

    def on_mouse_wheel(self, event):
        if not self.parent.playback_panel.is_media_loaded():
            return

        if self.parent.playback_panel.player.get_state == 'Playing':
            was_playing = True
            self.parent.playback_panel.player.pause()
        else:
            was_playing = False

        if event.delta > 0:
            self.on_jump_forward()
        else:
            self.on_jump_backward()

        if was_playing:
            self.parent.playback_panel.player.play()

    def on_time_label_click(self, event=None):
        if not self.parent.playback_panel.is_media_loaded():
            return
        if control_block.cached['timestamp_type'] == 'global':
            control_block.cached['timestamp_type'] = 'session'
        elif control_block.cached['timestamp_type'] == 'session':
            control_block.cached['timestamp_type'] = 'total'
        elif control_block.cached['timestamp_type'] == 'total':
            control_block.cached['timestamp_type'] = 'global'

        self.update_time_label(self.parent.playback_panel.get_current_timestamp()/1000)
        self.time_label_balloon.bind(self.time_label, '{} timestamp'.format(control_block.cached['timestamp_type']))

    def on_play(self):
        self.play.configure(image=self.pause_icon, command=self.parent.playback_panel.on_pause)

    def on_pause(self):
        self.play.configure(image=self.play_icon, command=self.parent.playback_panel.on_play)

    def on_media_reached_end(self):
        self.on_pause()

    def on_stop(self):
        self.on_pause()

    def update_time_label(self, seconds):
        if control_block.cached['timestamp_type'] == 'global':
            time_label_text = self.parent.translate_timestamp_to_clock(seconds)
        elif control_block.cached['timestamp_type'] == 'session':
            time_label_text = self.parent.translate_timestamp_to_clock(seconds - control_block.cached['session_timestamp']['value']/1000)
        elif control_block.cached['timestamp_type'] == 'total':
            time_label_text = self.parent.translate_timestamp_to_clock(self.parent.playback_panel.get_media_length()/1000)
        self.time_label.config(text=time_label_text)


class Description(Frame):

    class Title(Frame):
        def __init__(self, parent, title, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.title = Label(self, text=title, anchor=W)

            self.remove_icon = PhotoImage(file='./media/icons8-delete-row-25.png')
            self.remove_button = Button(self, image=self.remove_icon, command=self.parent.clear, relief=FLAT)

            self.title.pack(fill=BOTH, side=LEFT, expand=TRUE)
            self.remove_button.pack(side=LEFT, padx=1, pady=1)

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.entry_str = StringVar()
        self.title = Description.Title(self, 'Description')
        self.entry = Entry(self, textvariable=self.entry_str)

        self.title.pack(side=TOP, fill=X)
        self.entry.pack(fill=X)

    def clear(self):
        self.entry_str.set('')

    def get_and_clear(self):
        description = self.entry_str.get()
        self.clear()
        return description


class PrespectiveGrid(Toplevel):

    class GenImageProjective:
        def __init__(self, source_area, dest_area):
            self.sourceArea = source_area
            self.destArea = dest_area
            self.coefficientsComputed = False
            self.vc = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        def Terminate(self, retValue):
            self.coefficientsComputed = True if retValue == 0 else False
            return retValue

        def computeCoeefficients(self):
            retValue = 0
            a = [[0 for x in range(8)] for y in range(8)]  # 8x8 matrix A
            b = self.vc  # rhs vector of primed coords X'; coeffs returned in vc[]

            b[0] = self.destArea[0][0]  # take the x value
            b[1] = self.destArea[0][1]  # take the y value
            b[2] = self.destArea[1][0]
            b[3] = self.destArea[1][1]
            b[4] = self.destArea[2][0]
            b[5] = self.destArea[2][1]
            b[6] = self.destArea[3][0]
            b[7] = self.destArea[3][1]

            a[0][0] = self.sourceArea[0][0]
            a[0][1] = self.sourceArea[0][1]
            a[0][2] = 1
            a[0][6] = -self.sourceArea[0][0] * b[0]
            a[0][7] = -self.sourceArea[0][1] * b[0]
            a[1][3] = self.sourceArea[0][0]
            a[1][4] = self.sourceArea[0][1]
            a[1][5] = 1
            a[1][6] = -self.sourceArea[0][0] * b[1]
            a[1][7] = -self.sourceArea[0][1] * b[1]
            a[2][0] = self.sourceArea[1][0]
            a[2][1] = self.sourceArea[1][1]
            a[2][2] = 1
            a[2][6] = -self.sourceArea[1][0] * b[2]
            a[2][7] = -self.sourceArea[1][1] * b[2]
            a[3][3] = self.sourceArea[1][0]
            a[3][4] = self.sourceArea[1][1]
            a[3][5] = 1
            a[3][6] = -self.sourceArea[1][0] * b[3]
            a[3][7] = -self.sourceArea[1][1] * b[3]
            a[4][0] = self.sourceArea[2][0]
            a[4][1] = self.sourceArea[2][1]
            a[4][2] = 1
            a[4][6] = -self.sourceArea[2][0] * b[4]
            a[4][7] = -self.sourceArea[2][1] * b[4]
            a[5][3] = self.sourceArea[2][0]
            a[5][4] = self.sourceArea[2][1]
            a[5][5] = 1
            a[5][6] = -self.sourceArea[2][0] * b[5]
            a[5][7] = -self.sourceArea[2][1] * b[5]
            a[6][0] = self.sourceArea[3][0]
            a[6][1] = self.sourceArea[3][1]
            a[6][2] = 1
            a[6][6] = -self.sourceArea[3][0] * b[6]
            a[6][7] = -self.sourceArea[3][1] * b[6]
            a[7][3] = self.sourceArea[3][0]
            a[7][4] = self.sourceArea[3][1]
            a[7][5] = 1
            a[7][6] = -self.sourceArea[3][0] * b[7]
            a[7][7] = -self.sourceArea[3][1] * b[7]

            retValue = self.gaussjordan(a, b, 8)
            return self.Terminate(retValue)

        def mapSourceToDestPoint(self, sourcePoint):  # return dest point
            if self.coefficientsComputed:
                factor = (1.0 / (self.vc[6] * sourcePoint[0] + self.vc[7] * sourcePoint[1] + 1.0))
                destPoint_x = (factor * (self.vc[0] * sourcePoint[0] + self.vc[1] * sourcePoint[1] + self.vc[2]))
                destPoint_y = (factor * (self.vc[3] * sourcePoint[0] + self.vc[4] * sourcePoint[1] + self.vc[5]))
                return destPoint_x, destPoint_y
            else:
                return sourcePoint[0], sourcePoint[1]

        def gaussjordan(self, a, b, n):
            retValue = 0
            icol, irow = 0, 0
            indexc, indexr, ipiv = [0]*n, [0]*n, [0]*n
            big, dum, pivinv, temp = 0.0, 0.0, 0.0, 0.0

            if (a == None):
                retValue = -1
                self.Terminate(retValue)

            if (b == None):
                retValue = -2
                self.Terminate(retValue)

            for i in range(n):
                big = 0.0
                for j in range(n):
                    if ipiv[j] != 1:
                        for k in range(n):
                            if ipiv[k] == 0:
                                if math.fabs(a[j][k]) >= big:
                                    big = math.fabs(a[j][k])
                                    irow = j
                                    icol = k
                            elif ipiv[k] > 1:
                                retValue = -6
                                self.Terminate(retValue)
                ipiv[icol] += 1

                if irow != icol:
                    for l in range(n):
                        temp = a[irow][l]
                        a[irow][l] = a[icol][l]
                        a[icol][l] = temp
                    temp = b[irow]
                    b[irow] = b[icol]
                    b[icol] = temp
                indexr[i] = irow
                indexc[i] = icol
                if a[icol][icol] == 0.0:
                    retValue = -7
                    self.Terminate(retValue)
                pivinv = 1.0 / a[icol][icol]
                a[icol][icol] = 1.0
                for l in range(n):
                    a[icol][l] *= pivinv
                b[icol] *= pivinv

                for ll in range(n):
                    if ll != icol:
                        dum = a[ll][icol]
                        a[ll][icol] = 0.0
                        for l in range(n):
                            a[ll][l] -= a[icol][l] * dum
                        b[ll] -= b[icol] * dum

            for l in range(n-1, -1, -1):
                if indexr[l] != indexc[l]:
                    for k in range(n):
                        temp = a[k][indexr[l]]
                        a[k][indexr[l]] = a[k][indexc[l]]
                        a[k][indexc[l]] = temp

            return self.Terminate(retValue)

    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        self.grid_window = None
        self.canvas_grid = None
        self.grid_borders = list()
        self.grid_points = [None, None, None, None]
        self.grid_lines = [None, None, None, None]
        self.grid_inner_lines = list()
        self.grid_inner_points = list()
        self.grabbed_obj = None
        self.grabbed_xy = None
        self.grid_num_rows = 1
        self.grid_num_cols = 1
        self.grid_label = None
        self.outer_borders_has_been_set = False
        self.grid_attributes = list()
        self.attributes_label = None
        self.attr_file_path = None

    def set_grid(self):
        if not self.parent.playback_panel.is_media_loaded():
            return

        self.parent.playback_panel.player.video_take_snapshot(0, 'snapshot.tmp.png', 0, 0)
        self.grid_window = Toplevel(self.parent.parent)
        self.grid_window.title("PrespectiveGrid Calibration: Top Left")
        baseheight = self.parent.playback_panel.winfo_height() + 10
        snapshot = Image.open('snapshot.tmp.png')
        hpercent = (baseheight / float(snapshot.size[1]))
        wsize = int((float(snapshot.size[0]) * float(hpercent)))
        snapshot = snapshot.resize((wsize, baseheight), PIL.Image.ANTIALIAS)
        snapshot.save('snapshot_r.tmp.png')
        snapshot = PhotoImage(file='snapshot_r.tmp.png')
        self.canvas_grid = Canvas(self.grid_window, height=snapshot.height(), width=snapshot.width())
        self.canvas_grid.grid(row=0, column=0, rowspan=12, columnspan=4)
        self.canvas_grid.create_image(0, 0, anchor=NW, image=snapshot)
        entryInt1 = IntVar()  # cols
        entryInt2 = IntVar()  # rows
        Label(self.grid_window, text="Rows").grid(row=0, column=5)
        Label(self.grid_window, text="Cols").grid(row=1, column=5)
        Entry(self.grid_window, textvariable=entryInt2, width=20).grid(row=0, column=6)
        Entry(self.grid_window, textvariable=entryInt1, width=20).grid(row=1, column=6)
        Button(self.grid_window, text="OK", height=4, width=10, command=lambda: self.grid_get_cols_rows(entryInt1.get(), entryInt2.get())).grid(row=2, column=5, columnspan=2)
        if control_block.cached['grid']['is_set'] == 1:
            self.grid_load_from_cache()
        self.grid_window.wait_window()

    def grid_get_cols_rows(self, cols, rows):  # 1st phase of grid calibration - rows & cols
        self.grid_num_cols = cols
        self.grid_num_rows = rows
        for widget in self.grid_window.grid_slaves():  # remove widgets from window (rows & cols entry boxes etc.)
            if int(widget.grid_info()["column"]) > 4:
                widget.grid_forget()
        # start calibration
        self.grid_label = Label(self.grid_window, text="Top Left", height=4, width=20)
        self.grid_label.grid(row=0, column=5, columnspan=2)
        self.canvas_grid.bind('<Button-1>', self.grid_create_outer)

    def grid_create_outer(self, event, eventExist=True):  # 2nd phase of grid calibration - outer lines and points
        if eventExist:
            self.grid_borders.append((event.x, event.y))
        if len(self.grid_borders) == 1:
            self.grid_window.title("PrespectiveGrid Calibration: Top Right")
            self.grid_label.config(text="Top Right")
        elif len(self.grid_borders) == 2:
            self.grid_window.title("PrespectiveGrid Calibration: Bottom Right")
            self.grid_label.config(text="Bottom Right")
        elif len(self.grid_borders) == 3:
            self.grid_window.title("PrespectiveGrid Calibration: Bottom Left")
            self.grid_label.config(text="Bottom Left")
        elif len(self.grid_borders) == 4 or not eventExist:  # if we have 4 points for the grid, or got here from cache load
            self.grid_label.config(text="Outer Borders")
            self.grid_window.title("PrespectiveGrid Calibration")
            Button(self.grid_window, text="OK", height=4, width=10,
                   command=lambda: self.grid_create_inner(first_use=True)).grid(row=1, column=5, columnspan=2)
            for i in range(4):  # draw lines
                self.grid_lines[i] = self.canvas_grid.create_line(self.grid_borders[i][0], self.grid_borders[i][1], self.grid_borders[(i+1) % 4][0], self.grid_borders[(i+1) % 4][1], fill="blue", width=configuration.config['grid_line_size'], tags="line")
                self.canvas_grid.tag_bind(self.grid_lines[i], "<ButtonPress-1>", self.on_start_grab)
                self.canvas_grid.tag_bind(self.grid_lines[i], "<ButtonRelease-1>", self.on_drop_grab)
            for i in range(4):  # draw points
                self.grid_points[i] = self.canvas_grid.create_oval(self.grid_borders[i][0], self.grid_borders[i][1], self.grid_borders[i][0], self.grid_borders[i][1], width=configuration.config['grid_point_size'], fill='white', outline='white', tags="point")
                self.canvas_grid.tag_bind(self.grid_points[i], "<ButtonPress-1>", self.on_start_grab)
                self.canvas_grid.tag_bind(self.grid_points[i], "<ButtonRelease-1>", self.on_drop_grab)
        else:  # canvas clicks after this calibration
            return

    def load_attributes_from_clipboard(self):
        clipboard = self.parent.parent.clipboard_get()
        self.grid_attributes = [line.split('\t') for line in clipboard.split('\n')][:-1]

    def grid_create_inner(self, modify=False, first_use=False, from_cache=False, json_lines=None, json_points=None):  # 3rd phase of calibration - create the inner lines and points
        if modify:  # remove current inner grid (and later create one from scratch)
            for line in self.grid_inner_lines:
                self.canvas_grid.delete(line)
            self.grid_inner_lines = list()
            for point in self.grid_inner_points:
                self.canvas_grid.delete(point)
            self.grid_inner_points = list()
        if first_use:  # if its the first time creating the inner grid, create the other buttons on the windows
            for widget in self.grid_window.grid_slaves():  # remove widgets from window (rows & cols entry boxes etc.)
                if int(widget.grid_info()["column"]) == 5 and int(widget.grid_info()["row"]) == 1:  # catch the OK button
                    widget.grid_forget()
                    break
            self.grid_label.config(text="Inner Borders")
            self.outer_borders_has_been_set = True
            Button(self.grid_window, text="Finish", height=4, width=12,
                   command=lambda: self.grid_finish()).grid(row=1, column=5, columnspan=2)
            Button(self.grid_window, text="Reset", height=4, width=12,
                   command=lambda: self.grid_reset()).grid(row=2, column=5, columnspan=2)
            self.attributes_label = Label(self.grid_window, text="")
            self.attributes_label.grid(row=5, column=5)
            Button(self.grid_window, text="Load Attributes", height=4, width=12,
                   command=lambda: self.grid_load_attributes()).grid(row=3, column=5, columnspan=2)
            Button(self.grid_window, text="Load Attributes from clipboard", height=4, width=12,
                   command=self.load_attributes_from_clipboard).grid(row=4, column=5, columnspan=2)
        if from_cache:
            for json_line in json_lines:
                self.grid_inner_lines.append(
                    self.canvas_grid.create_line(json_line[0], json_line[1], json_line[2], json_line[3],
                                                 fill="red", width=configuration.config['grid_line_size'], tags="inner_line"))
            for json_point in json_points:
                self.grid_inner_points.append(
                    self.canvas_grid.create_oval(json_point[0], json_point[1], json_point[0], json_point[1],
                                                 width=configuration.config['grid_point_size'], fill='white', tags="inner_point"))
        else:  # not from cache - calculate prespective using genImageProjective class
            # first create a rectangle as it was straight
            top_left = (0, 0)
            top_right = (self.grid_num_cols, 0)
            buttom_right = (self.grid_num_cols, self.grid_num_rows)
            buttom_left = (0, self.grid_num_rows)
            width = top_right[0] - top_left[0]
            height = buttom_left[1] - top_left[1]
            source_area = [top_left, top_right, buttom_right, buttom_left]
            dest_area = self.grid_borders
            imageProjective = PrespectiveGrid.GenImageProjective(source_area, dest_area)

            # now calculate coeefficients for the right prespective
            if imageProjective.computeCoeefficients() != 0:  # 3 points on the same line, can't calculate
                return
            # vertical lines
            for i in range(1, self.grid_num_cols):
                pos = i * (1 / self.grid_num_rows)
                tempPnt = (top_left[0] + pos * height, top_left[1])
                upper_point = imageProjective.mapSourceToDestPoint(tempPnt)
                tempPnt = (top_left[0] + pos * height, buttom_left[1])
                lower_point = imageProjective.mapSourceToDestPoint(tempPnt)
                self.grid_inner_lines.append(
                    self.canvas_grid.create_line(upper_point[0], upper_point[1], lower_point[0], lower_point[1],
                                                 fill="red", width=configuration.config['grid_line_size'], tags="inner_line"))
                self.grid_inner_points.append(
                    self.canvas_grid.create_oval(upper_point[0], upper_point[1], upper_point[0], upper_point[1],
                                                 width=configuration.config['grid_point_size'], fill='white', tags="inner_point"))
                self.grid_inner_points.append(
                    self.canvas_grid.create_oval(lower_point[0], lower_point[1], lower_point[0], lower_point[1],
                                                 width=configuration.config['grid_point_size'], fill='white', tags="inner_point"))
            # horizontal lines
            for i in range(1, self.grid_num_rows):
                pos = i * (1 / self.grid_num_cols)
                tempPnt = (top_left[0], top_left[1] + pos * width)
                left_point = imageProjective.mapSourceToDestPoint(tempPnt)
                tempPnt = (top_right[0], top_left[1] + pos * width)
                right_point = imageProjective.mapSourceToDestPoint(tempPnt)
                self.grid_inner_lines.append(
                    self.canvas_grid.create_line(left_point[0], left_point[1], right_point[0], right_point[1],
                                                 fill="red", width=configuration.config['grid_line_size'], tags="inner_line"))
                self.grid_inner_points.append(
                    self.canvas_grid.create_oval(left_point[0], left_point[1], left_point[0], left_point[1],
                                                 width=configuration.config['grid_point_size'], fill='white', tags="inner_point"))
                self.grid_inner_points.append(
                    self.canvas_grid.create_oval(right_point[0], right_point[1], right_point[0], right_point[1],
                                                 width=configuration.config['grid_point_size'], fill='white', tags="inner_point"))

        # bind the inner widgets to the grab function
        for point in self.grid_inner_points:
            self.canvas_grid.tag_bind(point, "<ButtonPress-1>", self.on_start_grab)
            self.canvas_grid.tag_bind(point, "<ButtonRelease-1>", self.on_drop_grab)
        for line in self.grid_inner_lines:
            self.canvas_grid.tag_bind(line, "<ButtonPress-1>", self.on_start_grab)
            self.canvas_grid.tag_bind(line, "<ButtonRelease-1>", self.on_drop_grab)

    def grid_finish(self):  # 4th phase of calibration - save to cache and hide the grid window
        self.grid_window.withdraw()  # hides the grid window, but we can still work on it in the background
        control_block.cached['grid']['is_set'] = 1
        # self.is_grid_set = True

        self.parent.side_bar.upper_bar.calibrate_button.config(relief=SUNKEN)
        self.grid_dump_to_cache()

    def grid_reset(self, generalReset=False):
        if self.grid_window:
            self.grid_window.destroy()
        self.grid_window = None
        self.canvas_grid = None
        self.grid_borders = []
        self.grid_points = [None, None, None, None]  # outer
        self.grid_lines = [None, None, None, None]  # outer
        self.grid_inner_lines = []
        self.grid_inner_points = []
        self.grabbed_obj = None
        self.grabbed_xy = None
        self.grid_num_rows = 1
        self.grid_num_cols = 1
        self.grid_label = None
        self.outer_borders_has_been_set = False
        self.grid_attributes = []
        self.attributes_label = None
        self.attr_file_path = None
        self.is_grid_set = False
        self.parent.side_bar.upper_bar.calibrate_button.config(relief=RAISED)
        control_block.cached['grid']['is_set'] = 0
        self.grid_dump_to_cache()

    def grid_load_attributes(self, filename=None):
        if (filename == None):  # user clicks the button and select by himself
            p = pathlib.Path(os.path.expanduser(configuration.config['last_path']))
            self.attr_file_path = askopenfilename(initialdir=p, title="choose your file", filetypes=(("all files", "*.*"), ("CSV file (*.csv)", "*.csv")))
            filename = self.attr_file_path
        else:  # load from cache - given filename from json
            self.attr_file_path = filename
        if filename == "":  # no file selected
            return
        with open(filename, newline='') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
            self.grid_attributes = list()
            for row in spamreader:
                vals_in_row = ', '.join(row)
                vals_in_row = vals_in_row.split(",")
                self.grid_attributes.append(vals_in_row)
        self.attributes_label.config(text="Attributes Loaded:\n %s" % os.path.basename(self.attr_file_path))
        self.grid_window.focus_force()

    def grid_dump_to_cache(self):
        control_block.cached['grid']['value']['inner_points'] = []
        for point in self.grid_inner_points:
            control_block.cached['grid']['value']['inner_points'].append(self.canvas_grid.coords(point))
        control_block.cached['grid']['value']['inner_lines'] = []
        for line in self.grid_inner_lines:
            control_block.cached['grid']['value']['inner_lines'].append(self.canvas_grid.coords(line))
        control_block.cached['grid']['value']['rows'] = self.grid_num_rows
        control_block.cached['grid']['value']['cols'] = self.grid_num_cols
        control_block.cached['grid']['value']['borders'] = self.grid_borders
        control_block.cached['grid']['value']['attributes'] = self.grid_attributes

    def grid_load_from_cache(self):
        if control_block.cached['grid']['is_set'] == 0:
            return

        self.grid_borders = control_block.cached['grid']['value']['borders']
        self.grid_points = [None, None, None, None]
        self.grid_lines = [None, None, None, None]
        self.grid_get_cols_rows(control_block.cached['grid']['value']['cols'], control_block.cached['grid']['value']['rows'])
        self.grid_create_outer(None, eventExist=False)
        self.grid_create_inner(first_use=True, modify=True, from_cache=True, json_lines=control_block.cached['grid']['value']['inner_lines'], json_points=control_block.cached['grid']['value']['inner_points'])
        self.grid_attributes = control_block.cached['grid']['value']['attributes']

    def find_closest_outerline(self, x, y):
        outerline = None
        dist_from_outer = 100000
        cur_dist = -1
        for i in range(4):  # find the outerline - so the inner point can move only across the outer line
            outer_coords = self.canvas_grid.coords(self.grid_lines[i])
            cur_dist = self.find_dist_point_from_line(x, y, outer_coords)
            if cur_dist < dist_from_outer:
                dist_from_outer = cur_dist
                outerline = outer_coords
        return outerline

    def find_closest_point(self, x, y, outer=False):  # given (x,y) coords, get the point (a.k.a "oval" instance) it represents (inner or outer point)
        dist = 100000
        closest_point = None
        if outer:
            for i in range(len(self.grid_points)):
                p_coords = self.canvas_grid.coords(self.grid_points[i])
                cur_dist = math.sqrt((p_coords[0] - x) ** 2 + (p_coords[1] - y) ** 2)
                if cur_dist < dist:
                    dist = cur_dist
                    closest_point = self.grid_points[i]
        else:
            for i in range(len(self.grid_inner_points)):
                p_coords = self.canvas_grid.coords(self.grid_inner_points[i])
                cur_dist = math.sqrt((p_coords[0] - x)**2 + (p_coords[1] - y)**2)
                if cur_dist < dist:
                    dist = cur_dist
                    closest_point = self.grid_inner_points[i]
        return closest_point

    def find_closest_point_on_line(self, x, y, line):  # get the point (a,b) on the line "line" which is the closest to the point (x,y)
        side_a_to_point = (x - line[0], y - line[1])
        side_b_to_side_a = (line[2] - line[0], line[3] - line[1])
        atb2 = side_b_to_side_a[0] ** 2 + side_b_to_side_a[1] ** 2
        atp_dot_atb = side_a_to_point[0] * side_b_to_side_a[0] + side_a_to_point[1] * side_b_to_side_a[1]
        t = atp_dot_atb / atb2
        return line[0] + side_b_to_side_a[0]*t, line[1] + side_b_to_side_a[1]*t

    def find_dist_point_from_line(self, x, y, line):  # distance between (x,y) and the line
        x_diff = line[2] - line[0]
        y_diff = line[3] - line[1]
        num = abs(y_diff * x - x_diff * y + line[2] * line[1] - line[3] * line[0])
        den = math.sqrt(y_diff**2 + x_diff**2)
        return num / den

    def find_grid_cell(self, relative_click):  # from relative click on screen, find the right (x,y) cell on grid
        min_dist_right = 100000
        min_dist_bottom = 100000
        right = 0
        bottom = 0
        x, y = relative_click[0] * self.canvas_grid.winfo_width(), relative_click[1] * self.canvas_grid.winfo_height()
        if not self.is_in_grid_borders(x, y):
            return -1, -1
        # find from right - vertical lines
        for i in range(self.grid_num_cols):
            cur_line = self.grid_inner_lines[i] if i < self.grid_num_cols - 1 else self.grid_lines[1]
            cur_dist = self.find_dist_point_from_line(x, y, self.canvas_grid.coords(cur_line))
            if cur_dist <= min_dist_right:
                point_on_line = self.find_closest_point_on_line(x, y, self.canvas_grid.coords(cur_line))
                if x < point_on_line[0]:
                    min_dist_right = cur_dist
                    right = i
        # find from bottom - horizonal lines
        for i in range(self.grid_num_cols - 1, self.grid_num_cols + self.grid_num_rows - 1):
            cur_line = self.grid_inner_lines[i] if i < self.grid_num_cols + self.grid_num_rows - 2 else self.grid_lines[2]
            cur_dist = self.find_dist_point_from_line(x, y, self.canvas_grid.coords(cur_line))
            if cur_dist <= min_dist_bottom:
                point_on_line = self.find_closest_point_on_line(x, y, self.canvas_grid.coords(cur_line))
                if y < point_on_line[1]:
                    min_dist_bottom = cur_dist
                    bottom = i - self.grid_num_cols + 1
        return right, bottom

    def adjust_neighbor_lines(self, p1_coords, p2_coords, new_coords):  # when an outerline moved to new_coords, adjust the other outerline to their new location
        # new coords is the line that has moved, p1_coords and p2_coords are the line edges before it moved
        for i in range(4):
            line_old_coords = self.canvas_grid.coords(self.grid_lines[i])
            if self.grid_lines[i] == self.grabbed_obj:
                continue
            elif math.fabs(line_old_coords[0] - p1_coords[0]) < configuration.config['grid_point_size'] and math.fabs(line_old_coords[1] - p1_coords[1]) < configuration.config['grid_point_size']:
                self.canvas_grid.coords(self.grid_lines[i], new_coords[0], new_coords[1], line_old_coords[2], line_old_coords[3])
            elif math.fabs(line_old_coords[2] - p1_coords[0]) < configuration.config['grid_point_size'] and math.fabs(line_old_coords[3] - p1_coords[1]) < configuration.config['grid_point_size']:
                self.canvas_grid.coords(self.grid_lines[i], line_old_coords[0], line_old_coords[1], new_coords[0],
                                        new_coords[1])
            elif math.fabs(line_old_coords[0] - p2_coords[0]) < configuration.config['grid_point_size'] and math.fabs(line_old_coords[1] - p2_coords[1]) < configuration.config['grid_point_size']:
                self.canvas_grid.coords(self.grid_lines[i], new_coords[2], new_coords[3], line_old_coords[2],
                                        line_old_coords[3])
            elif math.fabs(line_old_coords[2] - p2_coords[0]) < configuration.config['grid_point_size'] and math.fabs(line_old_coords[3] - p2_coords[1]) < configuration.config['grid_point_size']:
                self.canvas_grid.coords(self.grid_lines[i], line_old_coords[0], line_old_coords[1], new_coords[2],
                                        new_coords[3])
        for i in range(4):  # update borders
            if math.fabs(self.grid_borders[i][0] - p1_coords[0]) < configuration.config['grid_point_size'] and math.fabs(
                    self.grid_borders[i][1] - p1_coords[1]) < configuration.config['grid_point_size']:
                self.grid_borders[i] = (new_coords[0], new_coords[1])
            elif math.fabs(self.grid_borders[i][0] - p2_coords[0]) < configuration.config['grid_point_size'] and math.fabs(
                    self.grid_borders[i][1] - p2_coords[1]) < configuration.config['grid_point_size']:
                self.grid_borders[i] = (new_coords[2], new_coords[3])

    def is_in_grid_borders(self, x, y):  # determine whether the point (x,y) is inside grid borders
        counter = 0
        p1 = self.grid_borders[0]
        for i in range(1, 5):
            p2 = self.grid_borders[i % 4]
            if y > min(p1[1], p2[1]):
                if y <= max(p1[1], p2[1]):
                    if x <= max(p1[0], p2[0]):
                        if p1[1] != p2[1]:
                            xinters = (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]) + p1[0]
                            if p1[0] == p2[0] or x <= xinters:
                                counter += 1
            p1 = p2
        if counter % 2 == 0:
            return False
        else:
            return True

    def on_start_grab(self, event):  # one can grab: line, point, innerline, innerpoint. identify the widget and location
        self.grabbed_obj = event.widget.find_closest(event.x, event.y)[0]
        self.grabbed_xy = event.x, event.y  # coords of the beginning of the drag

    def on_drop_grab(self, event):  # when the dragged item is released
        if self.grabbed_obj == 1:  # if accidently grabbed the canvas itself
            return
        lines_moved = False
        if self.canvas_grid.gettags(self.grabbed_obj)[0] == "line":
            old_coords = self.canvas_grid.coords(self.grabbed_obj)
            point1 = self.find_closest_point(old_coords[0], old_coords[1], outer=True)
            point2 = self.find_closest_point(old_coords[2], old_coords[3], outer=True)
            point1_coords = self.canvas_grid.coords(point1)
            point2_coords = self.canvas_grid.coords(point2)
            self.canvas_grid.move(self.grabbed_obj, event.x - self.grabbed_xy[0], event.y - self.grabbed_xy[1])
            new_coords = self.canvas_grid.coords(self.grabbed_obj)
            self.canvas_grid.move(point1, new_coords[0] - point1_coords[0], new_coords[1] - point1_coords[1])
            self.canvas_grid.move(point2, new_coords[2] - point2_coords[0], new_coords[3] - point2_coords[1])
            self.adjust_neighbor_lines(point1_coords, point2_coords, new_coords)
            if (self.outer_borders_has_been_set):
                self.grid_create_inner(modify=True)

        elif self.canvas_grid.gettags(self.grabbed_obj)[0] == "point":
            line_coords = list()  # old coords and new coords for 2 lines
            for i in range(4):
                old_coords = self.canvas_grid.coords(self.grid_lines[i])
                if math.fabs(old_coords[0] - self.grabbed_xy[0]) < configuration.config['grid_point_size'] and math.fabs(old_coords[1] - self.grabbed_xy[1]) < configuration.config['grid_point_size']:
                    self.canvas_grid.coords(self.grid_lines[i], event.x, event.y, old_coords[2], old_coords[3])
                    lines_moved = True
                    line_coords.append(old_coords)
                    line_coords.append(self.canvas_grid.coords(self.grid_lines[i]))
                elif math.fabs(old_coords[2] - self.grabbed_xy[0]) < configuration.config['grid_point_size'] and math.fabs(old_coords[3] - self.grabbed_xy[1]) < configuration.config['grid_point_size']:
                    self.canvas_grid.coords(self.grid_lines[i], old_coords[0], old_coords[1], event.x, event.y)
                    lines_moved = True
                    line_coords.append(old_coords)
                    line_coords.append(self.canvas_grid.coords(self.grid_lines[i]))
            if lines_moved:  # move the point
                self.canvas_grid.move(self.grabbed_obj, event.x - self.grabbed_xy[0], event.y - self.grabbed_xy[1])
                for i in range(4):  # find the points in border list
                    if math.fabs(self.grid_borders[i][0] - self.grabbed_xy[0]) < configuration.config['grid_point_size'] and math.fabs(self.grid_borders[i][1] - self.grabbed_xy[1]) < configuration.config['grid_point_size']:
                        self.grid_borders[i] = (event.x, event.y)
                if self.outer_borders_has_been_set:
                    self.grid_create_inner(modify=True)

        elif self.canvas_grid.gettags(self.grabbed_obj)[0] == "inner_line":
            old_coords = self.canvas_grid.coords(self.grabbed_obj)
            point1 = self.find_closest_point(old_coords[0], old_coords[1])
            point2 = self.find_closest_point(old_coords[2], old_coords[3])
            point1_coords = self.canvas_grid.coords(point1)
            point2_coords = self.canvas_grid.coords(point2)
            self.canvas_grid.move(self.grabbed_obj, event.x - self.grabbed_xy[0], event.y - self.grabbed_xy[1])
            old_coords = self.canvas_grid.coords(self.grabbed_obj)
            outerline1 = self.find_closest_outerline(old_coords[0], old_coords[1])
            outerline2 = self.find_closest_outerline(old_coords[2], old_coords[3])
            x1, y1 = self.find_closest_point_on_line(old_coords[0], old_coords[1], outerline1)
            x2, y2 = self.find_closest_point_on_line(old_coords[2], old_coords[3], outerline2)
            self.canvas_grid.coords(self.grabbed_obj, x1, y1, x2, y2)  # in order not to exit the borders
            self.canvas_grid.move(point1, x1 - point1_coords[0], y1 - point1_coords[1])
            self.canvas_grid.move(point2, x2 - point2_coords[0], y2 - point2_coords[1])

        elif self.canvas_grid.gettags(self.grabbed_obj)[0] == "inner_point":
            outerline = self.find_closest_outerline(event.x, event.y)
            new_x, new_y = self.find_closest_point_on_line(event.x, event.y, outerline)
            for i in range(len(self.grid_inner_lines)):
                old_coords = self.canvas_grid.coords(self.grid_inner_lines[i])
                if math.fabs(old_coords[0] - self.grabbed_xy[0]) < configuration.config['grid_point_size'] and math.fabs(old_coords[1] - self.grabbed_xy[1]) < configuration.config['grid_point_size']:
                    self.canvas_grid.coords(self.grid_inner_lines[i], new_x, new_y, old_coords[2], old_coords[3])
                    lines_moved = True
                elif math.fabs(old_coords[2] - self.grabbed_xy[0]) < configuration.config['grid_point_size'] and math.fabs(old_coords[3] - self.grabbed_xy[1]) < configuration.config['grid_point_size']:
                    self.canvas_grid.coords(self.grid_inner_lines[i], old_coords[0], old_coords[1], new_x, new_y)
                    lines_moved = True
            if lines_moved:
                self.canvas_grid.move(self.grabbed_obj, new_x - self.grabbed_xy[0], new_y - self.grabbed_xy[1])
        self.grabbed_obj = None


class PlaybackPanel(Frame):

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.vlc_instance = vlc.Instance()  # self.vlc_instance = vlc.Instance('--no-ts-trust-pcr','--ts-seek-percent')
        self.player = self.vlc_instance.media_player_new()
        self.filename = None
        self.player.set_hwnd(self.winfo_id())
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)
        self.bind('<Button-1>', self.on_click)
        self.bind('<ButtonRelease-1>', self.on_click_released)
        self.parent.side_bar.upper_bar.calibrate_button.config(command=self.parent.on_grid_set_button_click)
        self.events = self.player.event_manager()
        self.events.event_attach(vlc.EventType.MediaPlayerEndReached, self.EventManager)

    def EventManager(self, event):
        if event.type == vlc.EventType.MediaPlayerEndReached:
            self.parent.control_bar.on_media_reached_end()

    def get_relative_location(self, click_x, click_y, window_x, window_y, video_res_x, video_res_y):
        video_size_x, video_size_y = window_x, window_y

        if window_x / video_res_x > window_y / video_res_y:
            video_size_x = window_y * video_res_x / video_res_y
        else:
            video_size_y = window_x * video_res_y / video_res_x

        rel_click_x = (click_x - (abs(window_x - video_size_x) / 2)) / video_size_x
        rel_click_y = (click_y - (abs(window_y - video_size_y) / 2)) / video_size_y

        if rel_click_x < 0 or rel_click_x > 1:
            rel_click_x = -1
        if rel_click_y < 0 or rel_click_y > 1:
            rel_click_y = -1

        return rel_click_x, rel_click_y

    def on_click_released(self, event):
        self.config(cursor='')

    def on_click(self, event=None):
        if not self.parent.side_bar.is_clock_set():
            return
        if not self.parent.side_bar.is_location_set():
            return
        if not self.parent.side_bar.is_grid_set():
            return
        if self.player.get_time() < 0:
            return

        identities = ", ".join(self.parent.side_bar.identity.get_selected_items())
        events = ", ".join(self.parent.side_bar.events.get_selected_items())
        if len(events) == 0:
            return

        if event and event.type == EventType.ButtonPress:
            relative_click = self.get_relative_location(event.x, event.y, self.winfo_width(), self.winfo_height(), self.winfo_screenwidth(), self.winfo_screenheight())
            if relative_click[0] == -1 or relative_click[1] == -1:
                return
            cell = self.parent.grid.find_grid_cell(relative_click)
            if cell == (-1, -1):
                return
            attribute_on_cell = "None" if (len(self.parent.grid.grid_attributes) == 0 or self.parent.grid.grid_attributes[cell[0]] == None or self.parent.grid.grid_attributes[cell[0]][cell[1]] == None) else self.parent.grid.grid_attributes[cell[1]][cell[0]]
            self.config(cursor='gobbler')
        else:
            cell = (-1, -1)
            attribute_on_cell = 'None'

        session_timestamp = self.player.get_time()-control_block.cached['session_timestamp']['value']
        self.parent.add_item(self.player.get_time(), session_timestamp, identities, events, self.parent.side_bar.description.get_and_clear(), cell[0]+1, cell[1]+1, attribute_on_cell)

    def on_media_reached_end(self):
        self.player.set_time(0)

    def on_pause(self):
        self.player.pause()
        self.parent.control_bar.on_pause()

    def on_stop(self):
        self.player.stop()
        self.player.set_media(None)
        self.parent.control_bar.time_slider.set(0)
        self.parent.dump_events_to_file()
        control_block.dump_cache()
        if self.parent.event_manager:
            self.parent.event_manager.on_media_stop()
        self.parent.control_bar.on_stop()
        self.parent.side_bar.on_stop()

    def on_play_pause(self, event=None):
        if self.player.get_state() == vlc.State.Paused:
            self.on_play()
        elif self.player.get_state() == vlc.State.Playing:
            self.on_pause()

    def on_play(self):
        if not self.player.get_media():
            self.on_open()
        else:
            if self.player.get_state() == vlc.State.Ended:
                self.player.set_media(self.media)
            self.parent.control_bar.on_play()
            self.parent.side_bar.on_play()

    def on_open(self):
        self.on_stop()
        p = pathlib.Path(os.path.expanduser(configuration.config['last_path']))
        fullname = askopenfilename(initialdir=p, title="Select media", filetypes=(("All Files", "*.*"), ("MP4 Video", "*.mp4"), ("AVCHD Video", "*.mts")))
        if os.path.isfile(fullname):
            dirname = os.path.dirname(fullname)
            filename = os.path.basename(fullname)
            self.filename = filename
            configuration.config['last_path'] = dirname
            self.media = self.vlc_instance.media_new(str(os.path.join(dirname, filename)))
            self.player.set_media(self.media)
            control_block.current_media_hash = md5(fullname)
            control_block.load_cache()
            control_block.cached['media_name'] = filename
            if self.parent.event_manager:
                self.parent.event_manager.on_media_open()

            self.player.play()
            self.parent.control_bar.on_play()
            self.parent.side_bar.on_play()
            self.player.set_rate(configuration.config['speed'])

    def OnTimer(self):
        if self.player == None or self.player.get_time() == -1:
            return

        self.parent.control_bar.time_slider.config(command=self.scale_sel_without_media_update, to=self.player.get_length())
        self.parent.control_bar.time_slider.set(self.player.get_time())
        self.parent.control_bar.time_slider.config(command=self.scale_sel)

    def on_next_frame(self, event=None):
        self.player.next_frame()

    def set_speed(self, speed):
        self.player.set_rate(speed)

    def on_speed_up(self):
        if self.player.get_rate() == 0.25:
            self.player.set_rate(0.3)
        elif self.player.get_rate() + 0.1 > 2.0:
            self.player.set_rate(2.0)
        else:
            self.player.set_rate(self.player.get_rate() + 0.1)
        self.set_text_on_screen("Speed: {:0>.2f}".format(self.player.get_rate()))
        configuration.config['speed'] = self.player.get_rate()

    def on_speed_down(self):
        if self.player.get_rate() - 0.1 < 0.25:
            self.player.set_rate(0.25)
        else:
            self.player.set_rate(self.player.get_rate() - 0.1)
        self.set_text_on_screen("Speed: {:0>.2f}".format(self.player.get_rate()))
        configuration.config['speed'] = self.player.get_rate()

    def on_speed_change(self, event):
        if event.delta < 0:
            self.on_speed_down()
        else:
            self.on_speed_up()

    def on_zoom_in(self):
        if (self.player.video_get_scale() == 0.0):
            self.player.video_set_scale(1)
        elif (self.player.video_get_scale() + 0.1 > 2):
            self.player.video_set_scale(2)
        else:
            self.player.video_set_scale(self.player.video_get_scale() + 0.1)

    def on_zoom_out(self):
        if self.player.video_get_scale() - 0.1 < 1:
            self.player.video_set_scale(0)
        else:
            self.player.video_set_scale(self.player.video_get_scale() - 0.1)

    def on_full_screen(self):
        if not self.parent.parent.attributes("-fullscreen"):
            self.parent.parent.attributes('-fullscreen', True)
        else:
            self.parent.parent.attributes('-fullscreen', False)

    def scale_sel_without_media_update(self, evt):
        milliseconds = self.parent.control_bar.scale_var.get()
        if not (milliseconds <= self.player.get_length() and milliseconds >= 0):
            return 0
        self.parent.control_bar.update_time_label(milliseconds/1000)
        return milliseconds

    def scale_sel(self, event):
        milliseconds = self.scale_sel_without_media_update(event)
        self.player.set_time(int(milliseconds))

    def on_volume_change(self, evt):
        if self.player == None:
            return
        volume = self.parent.control_bar.volume_var.get()
        if volume > 100:
            volume = 100
        self.player.audio_set_volume(volume)
        self.parent.status_bar.status_label.config(text="Volume: " + str(self.parent.control_bar.volslider.get()) + '%')

    def set_text_on_screen(self, text):
        self.player.video_set_marquee_int(0, 1)
        self.player.video_set_marquee_int(6, 48)
        self.player.video_set_marquee_int(7, 200)
        self.player.video_set_marquee_string(1, text)
        self.player.video_get_marquee_string(1)

    def is_media_loaded(self):
        return self.player.get_media()

    def get_media_length(self):
        return self.player.get_length()

    def get_current_timestamp(self):
        return self.player.get_time()

    def goto_timestamp(self, timestamp):
        self.parent.playback_panel.player.set_time(timestamp)

    def get_video_name(self):
        return self.player.get_title()


class SideBar(Frame):
    class UpperBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.set_clock_icon = PhotoImage(file='./media/icons8-clock-32.png')
            self.set_clock_button = Button(self, image=self.set_clock_icon, command=self.parent.on_set_clock_click)
            self.set_clock_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

            self.set_location_icon = PhotoImage(file='./media/icons8-csv-32.png')
            self.set_location_button = Button(self, image=self.set_location_icon, command=self.parent.on_set_location)
            self.set_location_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

            self.calibrate_icon = PhotoImage(file='./media/icons8-grid-32.png')
            self.calibrate_button = Button(self, image=self.calibrate_icon)
            self.calibrate_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.upper_bar = SideBar.UpperBar(self)
        self.upper_bar_spacer = ttk.Separator(self, orient=HORIZONTAL)
        self.identity = ListBox(self, 'identity_list', 'Bird')
        self.events = ListBox(self, 'event_list', 'Event')
        self.description = Description(self)
        self.description_spacer = ttk.Separator(self, orient=HORIZONTAL)

        self.upper_bar.pack(fill=X)
        self.upper_bar_spacer.pack(fill=X, pady=5)
        self.identity.pack(pady=2)
        self.events.pack(pady=2)
        self.description.pack(fill=X)
        self.description_spacer.pack(fill=X, pady=5)

    def on_set_clock_click(self):
        if control_block.cached['session_timestamp']['is_set'] == 1:
            return
        if not self.parent.playback_panel.is_media_loaded():
            return

        control_block.cached['session_timestamp']['value'] = self.parent.playback_panel.get_current_timestamp()
        control_block.cached['session_timestamp']['is_set'] = 1

        self.upper_bar.set_clock_button.config(relief=SUNKEN)

    def on_stop(self):
        self.upper_bar.set_clock_button.config(relief=RAISED)
        self.upper_bar.set_location_button.config(relief=RAISED)
        self.upper_bar.calibrate_button.config(relief=RAISED)

    def on_play(self):
        if control_block.cached['session_timestamp']['is_set']:
            self.upper_bar.set_clock_button.config(relief=SUNKEN)
        if control_block.cached['export_location']['is_set']:
            self.upper_bar.set_location_button.config(relief=SUNKEN)

    def on_reset(self):
        control_block.cached['session_timestamp']['value'] = 0
        control_block.cached['session_timestamp']['is_set'] = 0
        self.upper_bar.set_clock_button.config(relief=RAISED)

        control_block.cached['export_location']['is_set'] = 0
        control_block.cached['export_location']['value'] = ''
        self.upper_bar.set_location_button.config(relief=RAISED)

        self.parent.playback_panel.grid_reset(generalReset=True)

    def is_clock_set(self):
        return control_block.cached['session_timestamp']['is_set'] == 1

    def on_set_location(self):
        if control_block.cached['export_location']['is_set'] == 1:
            return
        if not self.parent.playback_panel.is_media_loaded():
            return
        last_export_path = pathlib.Path(os.path.expanduser(configuration.config['last_export_path']))
        full_path = asksaveasfilename(initialdir=last_export_path, title="Set Export Location", filetypes=[("CSV File (*.csv)", "*.csv")])
        if not full_path.endswith('.csv'):
            full_path += '.csv'

        control_block.cached['export_location']['is_set'] = 1
        control_block.cached['export_location']['value'] = full_path
        configuration.config['last_export_path'] = os.path.dirname(full_path)
        self.upper_bar.set_location_button.config(relief=SUNKEN)
        with open(control_block.cached['export_location']['value'], "a", encoding='utf-8', newline='') as events_file:
            csv.writer(events_file, delimiter=',').writerow(['Video Time', 'Session Time', 'Birds', 'Events', 'Description', 'Column', 'Row', 'Attribute', 'File Name', 'Media Name'])

    def is_location_set(self):
        return control_block.cached['export_location']['is_set'] == 1

    def is_grid_set(self):
        return control_block.cached['grid']['is_set'] == 1


class MenuBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.about_window = None
        self.menu = Menu(self)

        file_menu = Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Open", command=self.parent.playback_panel.on_open)
        file_menu.add_command(label="Exit", command=self.parent.parent.quit)
        self.menu.add_cascade(label="File", menu=file_menu)

        session_menu = Menu(self.menu, tearoff=0)
        session_menu.add_command(label="Reset grid", command=self.parent.grid.grid_reset)
        session_menu.add_command(label="Reset clock")
        session_menu.add_command(label="Reset CSV")
        session_menu.insert_separator(3)
        session_menu.add_command(label="Reset session settings", accelerator='Ctrl+R', command=self.parent.on_reset)
        self.menu.add_cascade(label="Session", menu=session_menu)

        events_menu = Menu(self.menu, tearoff=0)
        events_menu.add_command(label="Open event manager", accelerator='Ctrl+M', command=parent.on_open_event_manager_menu_click)
        events_menu.insert_separator(1)
        events_menu.add_command(label="Add general event", accelerator='Ctrl+E', command=self.parent.playback_panel.on_click)
        events_menu.add_command(label="Undo last event", accelerator='Ctrl+Z', command=self.parent.on_delete_last_event)
        self.menu.add_cascade(label="Events", menu=events_menu)

        help_menu = Menu(self.menu, tearoff=0)
        help_menu.add_command(label="About", command=self.help_about)
        self.menu.add_cascade(label="Help", menu=help_menu)

    def help_about(self):
        if self.about_window:
            return
        self.about_window = Toplevel(self.parent.parent)
        self.about_window.resizable(0, 0)
        self.about_window.geometry("260x350")
        tau_logo = PhotoImage(file='./media/tau.png')
        Label(self.about_window, image=tau_logo).pack()
        ttk.Separator(self.about_window, orient=HORIZONTAL).pack(fill=X, pady=5)

        Label(self.about_window, justify=LEFT, anchor=W, text="Poke-A-Bird v" + __version__ + "\n\nFinal Project 2018, Faculty of Engineering,\nTel Aviv University\n\nDeveloped by:\nElad Yacovi\nNerya Meshulam").pack(fill=X, padx=5)
        self.about_window.wait_window()
        self.about_window = None


class MainApplication(Frame):
    class StatusBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.status_label = Label(self, text="Poke-A-Bird", bd=2, relief=SUNKEN, anchor=W)
            self.status_label.pack(side=BOTTOM, fill=X)

        def DisplayOnLabel(self, event):
            if event.widget == self.parent.control_bar.play:
                self.status_label.config(text="Play/Pause")
            elif event.widget == self.parent.control_bar.stop:
                self.status_label.config(text="Stop")
            elif event.widget == self.parent.control_bar.speedup:
                self.status_label.config(text="Speed Up")
            elif event.widget == self.parent.control_bar.speeddown:
                self.status_label.config(text="Speed Down")
            elif event.widget == self.parent.control_bar.next_frame:
                self.status_label.config(text="Next Frame")
            # elif event.widget == self.parent.control_bar.zoomin:
            #     self.status_label.config(text="Zoom In")
            # elif event.widget == self.parent.control_bar.zoomout:
            #     self.status_label.config(text="Zoom Out")
            elif event.widget == self.parent.control_bar.jump_forward:
                self.status_label.config(text="Jump Forward")
            elif event.widget == self.parent.control_bar.jump_backword:
                self.status_label.config(text="Jump Backward")
            elif event.widget == self.parent.control_bar.fullsc:
                self.status_label.config(text="Full Screen")
            elif event.widget == self.parent.control_bar.volslider:
                self.status_label.config(text="Volume: " + str(self.parent.control_bar.volslider.get()) + '%')
            elif event.widget == self.parent.side_bar.upper_bar.set_location_button:
                self.status_label.config(text="Set Exporting Location")
            elif event.widget == self.parent.side_bar.upper_bar.set_clock_button:
                self.status_label.config(text="Set Clock")
            elif event.widget == self.parent.side_bar.upper_bar.calibrate_button:
                self.status_label.config(text="Calibrate")
            else:
                self.status_label.config(text="Poke-A-Bird")

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.event_manager = None
        self.grid = PrespectiveGrid(self)
        self.parent.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.temp = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_application_config = configuration.config['main_application']
        self.parent.geometry("%dx%d%+d%+d" % (main_application_config['size_x'], main_application_config['size_y'],
                                              main_application_config['pos_x'], main_application_config['pos_y']))

        self.status_bar = self.StatusBar(self)
        self.side_bar = SideBar(self)
        self.playback_panel = PlaybackPanel(self, bg="black")
        self.menu_bar = MenuBar(self)
        self.control_bar = ControlBar(self, height=50)

        self.parent.config(menu=self.menu_bar.menu)
        self.side_bar.grid(row=0, column=1, rowspan=2, sticky=NS)
        self.control_bar.grid(row=1, column=0, sticky=EW)
        self.playback_panel.grid(row=0, column=0, sticky=NSEW)
        self.status_bar.grid(row=2, columnspan=2, sticky=EW)

        self.register_hotkeys()
        self.bind_all('<Enter>', self.status_bar.DisplayOnLabel)

    def JumpToTime(self, d_time):
        self.control_bar.time_slider.set(d_time)

    def translate_timestamp_to_clock(self, seconds):
        if seconds < 0:
            sign = '-'
            seconds *= -1
        else:
            sign = ' '
        HH = seconds // 3600
        MM = seconds // 60
        SS = seconds % 60
        return "{}{:02.0f}:{:02.0f}:{:06.3f}".format(sign, HH, MM, SS)

    def translate_to_friendly_record(self, record):
        friendly_record = list.copy(record)
        friendly_record[0] = self.translate_timestamp_to_clock(friendly_record[0]/1000)
        friendly_record[1] = self.translate_timestamp_to_clock(friendly_record[1]/1000)
        return friendly_record

    def write_record_to_csv(self, record):
        line = self.translate_to_friendly_record(record)
        line += [os.path.basename(control_block.cached['export_location']['value'])]
        line += [control_block.cached['media_name']]
        with open(control_block.cached['export_location']['value'], "a", encoding='utf-8', newline='') as events_file:
            csv.writer(events_file, delimiter=',').writerow(line)

    def add_item(self, video_timestamp, session_timestamp, identities, events, description, pos_x, pos_y, attribute):
        record = [video_timestamp, session_timestamp, identities, events, description, pos_x, pos_y, attribute]
        if len(control_block.events) >= configuration.config['event_manager']['number_of_events']:
            old_record = control_block.events.pop(0)
            self.write_record_to_csv(old_record)
            if self.event_manager:
                self.event_manager.refresh_events()

        control_block.events.append(record)
        control_block.cached['total_number_of_events'] += 1

        if self.event_manager:
            self.event_manager.refresh_events()

        self.playback_panel.set_text_on_screen(identities + ' -> ' + events)

    def on_event_manager_button_click(self):
        if not self.event_manager:
            self.event_manager = EventManager(self, takefocus=True)
        else:
            self.event_manager.on_closing()

    def on_grid_set_button_click(self):
        self.grid.set_grid()

    def on_open_event_manager_menu_click(self, event=None):
        if not self.event_manager:
            self.event_manager = EventManager(self, takefocus=True)

    def on_delete_last_event(self, event=None):
        if not control_block.events:
            return

        control_block.events.pop(-1)
        control_block.cached['total_number_of_events'] -= 1
        self.playback_panel.set_text_on_screen('Undo last event')
        if self.event_manager:
            self.event_manager.refresh_events()

    def on_exit(self):
        configuration.config['main_application']['size_x'] = self.winfo_width()
        configuration.config['main_application']['size_y'] = self.winfo_height()
        configuration.config['main_application']['pos_x'] = self.winfo_x()
        configuration.config['main_application']['pos_y'] = self.winfo_y()
        self.playback_panel.on_stop()
        with open(configuration.config_file, 'w') as fp:
            json.dump(configuration.config, fp)
        self.parent.destroy()

    def on_reset(self, event=None):
        if not self.playback_panel.is_media_loaded():
            return
        if messagebox.askokcancel("Reset Session", 'Are you sure you wish to reset\nall session settings?'):
            self.dump_events_to_file()
            control_block.cached['total_number_of_events'] = 0
            if self.event_manager:
                self.event_manager.on_media_stop()
            self.side_bar.on_reset()

    def dump_events_to_file(self):
        if not self.side_bar.is_location_set():
            if len(control_block.events) > 0:
                raise Exception()
            return
        for item in control_block.events:
            self.write_record_to_csv(item)

        control_block.events.clear()

    def register_hotkeys(self):
        self.bind_all("<Control-Key-z>", self.on_delete_last_event)
        self.bind_all("<Control-Key>", self.side_bar.events.on_mark_event)
        self.bind_all("<Shift-Key>", self.side_bar.identity.on_mark_event)
        self.playback_panel.bind("<MouseWheel>", self.playback_panel.on_speed_change)
        self.control_bar.time_slider.bind("<MouseWheel>", self.control_bar.on_mouse_wheel)
        self.bind_all("<space>", self.playback_panel.on_play_pause)
        self.bind_all("<Control-Key-e>", self.playback_panel.on_click)
        self.bind_all("<Control-Key-m>", self.on_open_event_manager_menu_click)
        self.bind_all("<Control-Key-r>", self.on_reset)
        self.bind_all("<Right>", self.playback_panel.on_next_frame)


if __name__ == "__main__":
    root = Tk()
    root.minsize(width=988, height=551)
    root.title("Poke-A-Bird")
    root.iconbitmap('./media/bird.ico')
    configuration = Configuration()
    control_block = ControlBlock()
    mainapp = MainApplication(root)
    mainapp.pack(side="top", fill="both", expand=True)
    root.mainloop()
    mainapp.control_bar.timer.stop()
