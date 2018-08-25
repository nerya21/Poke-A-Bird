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

class ControlBlock:
    events = []
    current_media_hash= ''
    cached = {}
    default_cache = {'total_number_of_events': 0,
                     'session_timestamp': {'is_set': 0, 'value': 0},
                     'export_location': {'is_set': 0, 'value': ''}}

    def dump_cache(self):
        if control_block.current_media_hash != '':
            cached_json = {}
            if configuration.cache_file.is_file():
                with open(configuration.cache_file, 'r') as fp:
                    cached_json = json.load(fp)

            cached_json[control_block.current_media_hash] = control_block.cached

            with open(configuration.cache_file, 'w') as fp:
                json.dump(cached_json, fp)

            control_block.current_media_hash = ''

        control_block.cached = control_block.default_cache

    def load_cache(self):
        if configuration.cache_file.is_file():
            with open(configuration.cache_file, 'r') as fp:
                cached_json = json.load(fp)
                if control_block.current_media_hash in cached_json:
                    control_block.cached = cached_json[control_block.current_media_hash]

class Configuration:
    config_file = pathlib.Path('config.json')
    cache_file = pathlib.Path('cache.json')
    config = {'last_export_path':'%USERPROFILE%',
              'last_path':'%USERPROFILE%',
              'identity_list': [],
              'event_list': [],
              'event_manager': {'size_x': 300,
                                'size_y': 300,
                                'pos_x': 300,
                                'pos_y': 300,
                                'number_of_events': 10},
              'main_application': {'size_x': 300,
                                   'size_y': 300,
                                   'pos_x': 300,
                                   'pos_y': 300}}

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        buffer = f.read(65536)
        hash_md5.update(buffer)
    return hash_md5.hexdigest()

class EventManager(Toplevel):
    class Control(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.export_icon = PhotoImage(file='./media/save_20.png')
            self.export_button = Button(self, image=self.export_icon, command=self.parent.parent.on_export_events)
            self.remove_icon = PhotoImage(file='./media/remove_record_20.png')
            self.remove_button = Button(self, image=self.remove_icon, command=self.parent.delete_item)
            self.goto_icon = PhotoImage(file='./media/goto_20.png')
            self.goto_button = Button(self, image=self.goto_icon, command=self.parent.on_click)

            self.export_button.pack(side=LEFT,padx=1)
            Frame(self).pack(side=LEFT, fill=Y, padx=5)
            self.goto_button.pack(side=LEFT,padx=1)
            self.remove_button.pack(side=LEFT,padx=1)



    class List(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.listbox = ttk.Treeview(self, height=1)
            self.y_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
            # self.x_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.listbox.xview)
            self.listbox.bind('<Double-1>', self.parent.on_click)

            self.listbox["columns"]=('video_timestamp', 'session_timestamp', 'identities','events','description' , 'pos_x', 'pos_y', 'attribute')
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
            # self.x_scrollbar.pack(side=BOTTOM, fill=X)
            self.listbox.pack(side=LEFT, fill = BOTH, expand=TRUE)

            self.refresh_events()

        def refresh_events(self):
            self.clear_events()
            for event in control_block.events:
                self.listbox.insert('',END, values=self.parent.parent.translate_to_friendly_record(event))

        def clear_events(self):
            self.listbox.delete(*self.listbox.get_children())

    class StatusBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.status_label = Label(self, text='Total number of events: ' + str(control_block.cached['total_number_of_events']), bd=2, relief=SUNKEN, anchor=W)
            self.status_label.pack(side=BOTTOM, fill=X)

        def display(self, event):
            if event.widget == self.parent.control_bar.export_button:
                self.status_label.config(text="Export events list")
            elif event.widget == self.parent.control_bar.goto_button:
                self.status_label.config(text="Go to selected event")
            elif event.widget == self.parent.control_bar.remove_button:
                self.status_label.config(text="Remove selected event")
            else:
                self.status_label.config(text='Total number of events: ' + str(control_block.cached['total_number_of_events']))

        def refresh_default_status(self):
            self.status_label.config(
                text='Total number of events: ' + str(control_block.cached['total_number_of_events']))

    def __init__(self, parent, *args, **kwargs):
        Toplevel.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.title('Event Manager')
        self.minsize(790,250)

        event_manager_config = configuration.config['event_manager']
        self.geometry("%dx%d%+d%+d" % (event_manager_config['size_x'], event_manager_config['size_y'],
                                       event_manager_config['pos_x'], event_manager_config['pos_y']))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # self.parent.side_bar.upper_bar.eventManagerButton.config(relief=SUNKEN)

        self.control_bar = self.Control(self, borderwidth=2)
        self.list = self.List(self, borderwidth=2)
        self.status_bar = self.StatusBar(self)

        self.control_bar.pack(fill=BOTH)
        self.list.pack(fill=BOTH, expand=TRUE)
        self.status_bar.pack(fill=BOTH)

        self.bind_all('<Enter>', self.status_bar.display, add=True)

    def get_selected_event_index(self):
        iid = self.list.listbox.focus()
        if iid == '':
            return -1
        else:
            return self.list.listbox.index(iid) 

    def delete_item(self):
        current_selection = self.get_selected_event_index()
        if current_selection != -1:
            control_block.events.pop(current_selection)
            control_block.cached['total_number_of_events'] -= 1
            self.list.refresh_events()

    def on_click(self,event=None):
        current_selection = self.get_selected_event_index()
        if current_selection != -1:
            self.parent.playback_panel.goto_timestamp(int(control_block.events[current_selection][0]))

    def on_closing(self):
        configuration.config['event_manager']['size_x'] = self.winfo_width()
        configuration.config['event_manager']['size_y'] = self.winfo_height()
        configuration.config['event_manager']['pos_x'] = self.winfo_x()
        configuration.config['event_manager']['pos_y'] = self.winfo_y()
        # self.parent.side_bar.upper_bar.eventManagerButton.config(relief=RAISED)
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

            self.new_icon = PhotoImage(file='./media/add_record_25.png')
            self.new_button = Button(self, image=self.new_icon, command=self.parent.add_item, relief=FLAT)

            self.remove_icon = PhotoImage(file='./media/remove_record_25.png')
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
                                   highlightthickness=0, exportselection=False, activestyle=NONE, selectmode = EXTENDED)
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

    def close_popup(self, window, clicked):
        clicked[0] = True
        window.grab_release()
        window.destroy()

    def add_item(self):
        window = Toplevel(self.parent.parent.parent, borderwidth=5)
        window.grab_set()
        window.title('Add '+ self.title)
        window.resizable(0, 0)
        entryStr = StringVar()
        Label(window, text='Name: ').grid(row=0, column=0)
        Entry(window, textvariable=entryStr, width=20).grid(row=0, column=1)
        clicked = [False]
        Button(window, text="Add", width=5, command=lambda: self.close_popup(window, clicked)).grid(row=1, column=0, columnspan=2, pady=2)
        # window.bind('<Enter>', self.close_popup(window, clicked))
        window.wait_window()
        if (clicked[0] and entryStr.get() != ""):
            configuration.config[self.attribute].append(entryStr.get())
            self.list.listbox.insert(END, entryStr.get())

    def get_selected_items(self):
        items = []
        for item in self.list.listbox.curselection():
            items.append(self.list.listbox.get(item))
        return items

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

        #variables
        self.volume_var = IntVar()
        self.scale_var = DoubleVar() #time of the video scale var
        self.timeslider_last_val = 0.0
        self.timer = ttkTimer(self.parent.playback_panel.OnTimer, 1.0)

        #buttons and other widgets
        self.pause_icon = PhotoImage(file='./media/pause.png')
        self.play_icon = PhotoImage(file='./media/play.png')
        self.play = Button(self, image=self.play_icon, command=self.parent.playback_panel.on_play)
        self.stop_icon = PhotoImage(file='./media/stop.png')
        self.stop = Button(self, image=self.stop_icon, command=self.parent.playback_panel.on_stop)
        # self.previous_frame_icon = PhotoImage(file='./media/previous_frame.png')
        # self.previous_frame = Button(self, image=self.previous_frame_icon, state=DISABLED)
        self.next_frame_icon = PhotoImage(file='./media/next_frame.png')
        self.next_frame = Button(self, image=self.next_frame_icon, command=self.parent.playback_panel.on_next_frame)
        self.speedup_icon = PhotoImage(file='./media/speed_up.png')
        self.speedup = Button(self, image=self.speedup_icon, command=self.parent.playback_panel.on_speed_up)
        self.speeddown_icon = PhotoImage(file='./media/speed_down.png')
        self.speeddown = Button(self, image=self.speeddown_icon, command=self.parent.playback_panel.on_speed_down)
        self.zoom_in_icon = PhotoImage(file='./media/zoom_in.png')
        self.zoomin = Button(self, image=self.zoom_in_icon, command=self.parent.playback_panel.on_zoom_in)
        self.zoom_out_icon = PhotoImage(file='./media/zoom_out.png')
        self.zoomout = Button(self, image=self.zoom_out_icon, command=self.parent.playback_panel.on_zoom_out)
        self.int_forward_icon = PhotoImage(file='./media/int_forward.png')
        self.iforward = Button(self, image=self.int_forward_icon, state=DISABLED)
        self.int_backward_icon = PhotoImage(file='./media/int_backward.png')
        self.ibackword = Button(self, image=self.int_backward_icon, state=DISABLED)
        self.fullscreen_icon = PhotoImage(file='./media/fullscreen.png')
        self.fullsc = Button(self, image=self.fullscreen_icon, command=self.parent.playback_panel.on_full_screen)
        self.show_grid_icon = PhotoImage(file='./media/show_grid.png')
        self.volslider = Scale(self, variable=self.volume_var, command=self.parent.playback_panel.on_volume_change, from_=0, to=100, orient=HORIZONTAL, length=100, showvalue=0)
        self.timeScaleFrame = Frame(self)
        self.timeslider = Scale(self.timeScaleFrame, variable=self.scale_var, command=self.parent.playback_panel.scale_sel,
                                   from_=0, to=1000, orient=HORIZONTAL, length=100, resolution=0.001, showvalue=0)
        self.currentTimeLabel = Label(self.timeScaleFrame, text="00:00:00", width=6)
        self.currentTimeLabel.pack(side=RIGHT)
        self.timeslider.pack(side=RIGHT, fill=X, expand=1)

        self.timeScaleFrame.pack(side=TOP, fill=X, expand=1)
        self.play.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.stop.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.speedup.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.speeddown.pack(side=LEFT, fill=Y, padx=1, pady=3)
        # self.previous_frame.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.next_frame.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.zoomin.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.zoomout.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.ibackword.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.iforward.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.fullsc.pack(side=LEFT, fill=Y, padx=1, pady=3)
        ttk.Separator(self, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=5)
        self.volslider.pack(side=LEFT, expand=TRUE, anchor=E, padx=1, pady=3)

        self.timer.start()
        self.parent.parent.update()

    def on_play(self):
        self.play.configure(image=self.pause_icon, command=self.parent.playback_panel.on_pause)

    def on_pause(self):
        self.play.configure(image=self.play_icon, command=self.parent.playback_panel.on_play)

    def on_stop(self):
        self.on_pause()

    def CalcTime(self, cur_val):
        HH = cur_val // 3600
        MM = cur_val // 60
        SS = cur_val % 60
        self.currentTimeLabel.config(text="{:>02d}:{:>02d}:{:>02d}".format(HH,MM,SS))

class Description(Frame):

    class Title(Frame):
        def __init__(self, parent, title, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.title = Label(self, text=title, anchor=W)

            self.remove_icon = PhotoImage(file='./media/remove_record_25.png')
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

class PlaybackPanel(Frame):

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        
        # self.vlc_instance = vlc.Instance('--no-ts-trust-pcr','--ts-seek-percent')
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.player.set_hwnd(self.winfo_id())
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)
        self.bind('<Button-1>', self.on_click)

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

    def on_click(self, event):
        if not self.parent.side_bar.is_clock_set():
            return
        if not self.parent.side_bar.is_location_set():
            return

        relative_click = self.get_relative_location(event.x, event.y, self.winfo_width(), self.winfo_height(), self.player.video_get_width(), self.player.video_get_height())
        if relative_click[0] == -1 or relative_click[1] == -1:
            return
            
        identities = ", ".join(self.parent.side_bar.identity.get_selected_items())
        events = ", ".join(self.parent.side_bar.events.get_selected_items())
        if len(events) == 0:
            return
        self.parent.add_item(self.player.get_time(),self.player.get_time()-control_block.cached['session_timestamp']['value'],identities,events,self.parent.side_bar.description.get_and_clear(), relative_click[0], relative_click[1],'')

    def on_pause(self):
        self.player.pause()
        self.parent.control_bar.on_pause()

    def on_stop(self):
        self.player.stop()
        self.player.set_media(None)
        self.parent.control_bar.timeslider.set(0)
        self.parent.dump_events_to_file()
        control_block.dump_cache()
        if self.parent.event_manager:
            self.parent.event_manager.on_media_stop()
        self.parent.control_bar.on_stop()
        self.parent.side_bar.on_stop()

    def on_play(self):
        if not self.player.get_media():
            self.on_open()
        else:
            if self.player.play() == -1:
                self.error_dialog("Unable to play.")
            self.parent.control_bar.on_play()
            self.parent.side_bar.on_play()

    def on_open(self):
        self.on_stop()
        p = pathlib.Path(os.path.expanduser(configuration.config['last_path']))
        fullname = askopenfilename(initialdir = p, title = "choose your file",filetypes = (("all files","*.*"),("mp4 files","*.mp4")))
        if os.path.isfile(fullname):
            dirname = os.path.dirname(fullname)
            filename = os.path.basename(fullname)
            configuration.config['last_path'] = dirname
            media = self.vlc_instance.media_new(str(os.path.join(dirname, filename)))
            self.player.set_media(media)
            control_block.current_media_hash = md5(fullname)
            control_block.load_cache()
            if self.parent.event_manager:
                self.parent.event_manager.on_media_open()

            self.player.play()
            self.parent.control_bar.on_play()
            self.parent.side_bar.on_play()

    def OnTimer(self):
        if self.player == None:
            return
        length = self.player.get_length()
        dbl = length * 0.001
        self.parent.control_bar.timeslider.config(to=dbl)
        curtime = self.player.get_time()
        if curtime == -1:
            curtime = 0
        dbl = curtime * 0.001
        self.parent.control_bar.timeslider_last_val = dbl
        self.parent.control_bar.timeslider.set(dbl)

    def on_next_frame(self):
        self.player.next_frame()

    def on_speed_up(self):
        if self.player.get_rate() == 0.25:
            self.player.set_rate(0.3)
        elif self.player.get_rate() + 0.1 > 2.0:
            self.player.set_rate(2.0)
        else:
            self.player.set_rate(self.player.get_rate() + 0.1)
        self.set_text_on_screen("Speed: {:0>.2f}".format(self.player.get_rate()))

    def on_speed_down(self):
        if self.player.get_rate() - 0.1 < 0.25:
            self.player.set_rate(0.25)
        else:
            self.player.set_rate(self.player.get_rate() - 0.1)
        self.set_text_on_screen("Speed: {:0>.2f}".format(self.player.get_rate()))

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

    def scale_sel(self, evt):
        cur_val = self.parent.control_bar.scale_var.get()
        self.parent.control_bar.CalcTime(int(cur_val))
        if (math.fabs(cur_val - self.parent.control_bar.timeslider_last_val) > 1.5):
            self.parent.control_bar.timeslider_last_val = cur_val
            # mval = "%.0f" % (cur_val * 1000)
            self.player.set_time(int(cur_val*1000)) # expects milliseconds

    def on_volume_change(self, evt):
        if self.player == None:
            return
        volume = self.parent.control_bar.volume_var.get()
        if volume > 100:
            volume = 100
        if self.player.audio_set_volume(volume) == -1:
            self.error_dialog("Failed to set volume")
        self.parent.status_bar.status_label.config(text="Volume: " + str(self.parent.control_bar.volslider.get()) + '%')

    def error_dialog(self, errormessage):
        print(errormessage)
    
    def set_text_on_screen(self, text):
        self.player.video_set_marquee_int(0, 1)
        self.player.video_set_marquee_int(6, 48)
        self.player.video_set_marquee_int(7, 2000)
        self.player.video_set_marquee_string(1, text)
        self.player.video_get_marquee_string(1)

    def is_media_loaded(self):
        return self.player.get_media()

    def get_current_timestamp(self):
        return self.player.get_time()

    def goto_timestamp(self, timestamp):
        # self.parent.playback_panel.on_pause()
        # self.parent.playback_panel.player.set_time(timestamp)
        self.parent.playback_panel.player.play()
        self.parent.playback_panel.player.set_time(timestamp)
        time.sleep(0.5)

        self.parent.playback_panel.player.pause()

    def get_video_name(self):
        return self.player.get_title()

class SideBar(Frame):
    class UpperBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.set_clock_icon = PhotoImage(file='./media/clock_32.png')
            self.set_clock_button = Button(self, image=self.set_clock_icon, command=self.parent.on_set_clock_click)
            self.set_clock_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

            self.set_location_icon = PhotoImage(file='./media/csv_32.png')
            self.set_location_button = Button(self, image=self.set_location_icon, command=self.parent.on_set_location)
            self.set_location_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

            self.calibrate_icon = PhotoImage(file='./media/grid_32.png')
            self.calibrate_button = Button(self, image=self.calibrate_icon, state=DISABLED)
            self.calibrate_button.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.upper_bar = SideBar.UpperBar(self)
        self.upper_bar_spacer = ttk.Separator(self, orient=HORIZONTAL)
        self.identity = ListBox(self, 'identity_list','Bird')
        self.events = ListBox(self, 'event_list', 'Event')
        self.description = Description(self)
        self.description_spacer = ttk.Separator(self, orient=HORIZONTAL)

        self.upper_bar.pack(fill=X)
        self.upper_bar_spacer.pack(fill=X,pady=5)
        self.identity.pack(pady=2)
        self.events.pack(pady=2)
        self.description.pack(fill=X)
        self.description_spacer.pack(fill=X,pady=5)


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

    def is_clock_set(self):
        return control_block.cached['session_timestamp']['is_set'] == 1

    def on_set_location(self):
        if control_block.cached['export_location']['is_set'] == 1:
            return
        if not self.parent.playback_panel.is_media_loaded():
            return
        p = pathlib.Path(os.path.expanduser(configuration.config['last_export_path']))
        # fullname = asksaveasfilename(initialfile = self.parent.playback_panel.get_video_name() + '.csv',initialdir = p, title = "Export As",filetypes = (("CSV file (*.csv)","*.csv"),("All files (*)","*.*")))
        fullname = asksaveasfilename(initialdir = p, title = "Export As",filetypes = (("CSV file (*.csv)","*.csv"),("All files (*)","*.*")))
        # if fullname == '':
        #     return
        # if pathlib.Path(fullname).is_file():
        #     pass #TODO: handle file exist
        control_block.cached['export_location']['is_set'] = 1
        control_block.cached['export_location']['value'] = fullname + '.csv'
        configuration.config['last_export_path'] = os.path.dirname(fullname + '.csv')
        self.upper_bar.set_location_button.config(relief=SUNKEN)

    def is_location_set(self):
        return control_block.cached['export_location']['is_set'] == 1

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
        session_menu.add_command(label="Set grid")
        session_menu.add_command(label="Set clock", command=self.parent.side_bar.on_set_clock_click)
        session_menu.add_command(label="Set export location", command=self.parent.side_bar.on_set_location)
        session_menu.add_command(label="Reset session settings", command=self.parent.on_reset)
        self.menu.add_cascade(label="Session", menu=session_menu)

        events_menu = Menu(self.menu, tearoff=0)
        events_menu.add_command(label="Open event manager", command=parent.on_open_event_manager_menu_click)
        self.menu.add_cascade(label="Events", menu=events_menu)

        help_menu = Menu(self.menu, tearoff=0)
        help_menu.add_command(label="About", command=self.help_about)
        self.menu.add_cascade(label="Help", menu=help_menu)

    def help_about(self):
        if self.about_window:
            return
        self.about_window = Toplevel(self.parent.parent)
        self.about_window.resizable(0, 0)
        self.about_window.geometry("400x415")
        tau_logo = PhotoImage(file='./media/tau.png')
        Label(self.about_window, image=tau_logo).pack()
        ttk.Separator(self.about_window, orient=HORIZONTAL).pack(fill=X, pady=5)
        
        Label(self.about_window, justify=LEFT, anchor=W, text="Poke-A-Bird v0.1.1\n\nFinal Project 2018, Faculty of Engineering,\nTel Aviv University\n\nDeveloped by:\nElad Yacovi\nNerya Meshulam").pack(fill=X,padx=5)
        Button(self.about_window, text="OK", width=5, command=self.about_window.destroy).pack( pady=10)
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
            # elif event.widget == self.parent.control_bar.previous_frame:
                # self.status_label.config(text="Previous Frame")
            elif event.widget == self.parent.control_bar.next_frame:
                self.status_label.config(text="Next Frame")
            elif event.widget == self.parent.control_bar.zoomin:
                self.status_label.config(text="Zoom In")
            elif event.widget == self.parent.control_bar.zoomout:
                self.status_label.config(text="Zoom Out")
            elif event.widget == self.parent.control_bar.iforward:
                self.status_label.config(text="Intelligent Fast Forward")
            elif event.widget == self.parent.control_bar.ibackword:
                self.status_label.config(text="Intelligent Fast Backward")
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
        self.parent.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.temp =0

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

        self.bind_all('<Enter>', self.status_bar.DisplayOnLabel)

    def JumpToTime(self, d_time):
        self.control_bar.timeslider.set(d_time)

    def translate_timestamp_to_clock(self, cur_val):
        return datetime.timedelta(milliseconds=cur_val)

    def translate_to_friendly_record(self, record):
        friendly_record = list.copy(record)
        friendly_record[0] = self.translate_timestamp_to_clock(friendly_record[0])
        friendly_record[1] = self.translate_timestamp_to_clock(friendly_record[1])
        return friendly_record 

    def add_item(self, video_timestamp, session_timestamp, identities,events ,description, pos_x, pos_y, attribute):
        record = [video_timestamp, session_timestamp, identities,events,description , pos_x, pos_y, attribute ]
        if len(control_block.events) >= configuration.config['event_manager']['number_of_events']:
            old_record = control_block.events.pop(0)
            with open(control_block.cached['export_location']['value'], "a") as events_file:
                csv.writer(events_file, delimiter=',').writerow(self.translate_to_friendly_record(old_record))
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

    def on_open_event_manager_menu_click(self):
        if not self.event_manager:
            self.event_manager = EventManager(self, takefocus=True)



    def on_export_events(self):
        raise Exception()

    def on_exit(self):
        configuration.config['main_application']['size_x'] = self.winfo_width()
        configuration.config['main_application']['size_y'] = self.winfo_height()
        configuration.config['main_application']['pos_x'] = self.winfo_x()
        configuration.config['main_application']['pos_y'] = self.winfo_y()
        self.playback_panel.on_stop()
        with open(configuration.config_file, 'w') as fp:
            json.dump(configuration.config, fp)
        self.parent.destroy()

    def on_reset(self):
        if not self.playback_panel.is_media_loaded:
            return
        if messagebox.askokcancel("Reset Session", 'Are you sure you wish to continue?'):
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
            with open(control_block.cached['export_location']['value'], "a") as events_file:
                csv.writer(events_file, delimiter=',').writerow(item)

        control_block.events.clear()
        
if __name__ == "__main__":
    root = Tk()
    root.minsize(width=988, height=551)
    root.title("Poke-A-Bird")
    root.iconbitmap('./media/bird.ico')
    #root.attributes('-fullscreen', True) #force fullscreen
    #root.state('zoomed') #force zoom

    configuration = Configuration()
    control_block = ControlBlock()

    if configuration.config_file.is_file():
        with open(configuration.config_file, 'r') as fp:
            configuration.config = json.load(fp)
    control_block.cached = control_block.default_cache

    mainapp = MainApplication(root)
    mainapp.pack(side="top", fill="both", expand=True)
    root.mainloop()
    mainapp.control_bar.timer.stop()

