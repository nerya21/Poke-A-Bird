import hashlib
import json
from shutil import copyfile
from tkinter import *
from tkinter.filedialog import askopenfilename, asksaveasfilename
import math
import vlc
import pathlib
import os
import platform
import time
import csv
from threading import Thread, Event

class ControlBlock:
    events = []
    current_media_hash= ''
    cached = {}
    default_cache = {'total_number_of_events': 0}

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

            self.scrollbar = Scrollbar(self)
            self.listbox = Listbox(self, yscrollcommand=self.scrollbar.set,
                                   highlightthickness=0, exportselection=False, activestyle=NONE)
            self.listbox.bind('<Double-1>', self.parent.on_click)
            self.scrollbar.config(command=self.listbox.yview)

            self.scrollbar.pack(side=RIGHT, fill=Y)
            self.listbox.pack(side=LEFT, fill = BOTH, expand=TRUE)

            self.refresh_events()

        def refresh_events(self):
            self.clear_events()
            for item in control_block.events:
                self.listbox.insert(END, item)

        def clear_events(self):
            self.listbox.delete(0, 'end')

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
        self.minsize(300,300)

        event_manager_config = configuration.config['event_manager']
        self.geometry("%dx%d%+d%+d" % (event_manager_config['size_x'], event_manager_config['size_y'],
                                       event_manager_config['pos_x'], event_manager_config['pos_y']))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.parent.side_bar.upper_bar.eventManagerButton.config(relief=SUNKEN)

        self.control_bar = self.Control(self, borderwidth=2)
        self.list = self.List(self, borderwidth=2)
        self.status_bar = self.StatusBar(self)

        self.control_bar.pack(fill=BOTH)
        self.list.pack(fill=BOTH, expand=TRUE)
        self.status_bar.pack(fill=BOTH)

        self.bind_all('<Enter>', self.status_bar.display, add=True)

    def delete_item(self):
        current_selection = self.list.listbox.curselection()
        if current_selection != ():
            control_block.events.pop(current_selection[0])
            control_block.cached['total_number_of_events'] -= 1
            self.list.listbox.delete(current_selection)

    def on_click(self,event=None):
        current_selection = self.list.listbox.curselection()
        if current_selection != ():
            self.parent.playback_panel.player.set_pause(1)
            self.parent.playback_panel.player.set_time(int(self.list.listbox.get(current_selection[0])[0]) * 1000)  # expects milliseconds

    def on_closing(self):
        configuration.config['event_manager']['size_x'] = self.winfo_width()
        configuration.config['event_manager']['size_y'] = self.winfo_height()
        configuration.config['event_manager']['pos_x'] = self.winfo_x()
        configuration.config['event_manager']['pos_y'] = self.winfo_y()
        self.parent.side_bar.upper_bar.eventManagerButton.config(relief=RAISED)
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
                                   highlightthickness=0, exportselection=False, activestyle=NONE)
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
        window.destroy()

    def add_item(self):
        window = Toplevel(self.parent.parent.parent)
        entryStr = StringVar()
        Label(window, text="Add "+self.title).pack(side=LEFT)
        Entry(window, textvariable=entryStr, bd=5).pack()
        clicked = [False]
        Button(window, text="OK", width=5, command=lambda: self.close_popup(window, clicked)).pack()
        window.wait_window()
        if (clicked[0] and entryStr.get() != ""):
            configuration.config[self.attribute].append(entryStr.get())
            self.list.listbox.insert(END, entryStr.get())

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
        self.timer = ttkTimer(self.parent.playback_panel.videopanel.OnTimer, 1.0)

        #buttons and other widgets
        self.pause_icon = PhotoImage(file='./media/pause.png')
        self.pause = Button(self,image=self.pause_icon, command=self.parent.playback_panel.videopanel.OnPause)

        self.play_icon = PhotoImage(file='./media/play.png')
        self.play = Button(self, image=self.play_icon, command=self.parent.playback_panel.videopanel.OnPlay)

        self.stop_icon = PhotoImage(file='./media/stop.png')
        self.stop = Button(self, image=self.stop_icon, command=self.parent.playback_panel.videopanel.OnStop)

        self.previous_frame_icon = PhotoImage(file='./media/previous_frame.png')
        self.previous_frame = Button(self, image=self.previous_frame_icon, state=DISABLED)

        self.next_frame_icon = PhotoImage(file='./media/next_frame.png')
        self.next_frame = Button(self, image=self.next_frame_icon, state=DISABLED)

        self.speedup_icon = PhotoImage(file='./media/speed_up.png')
        self.speedup = Button(self, image=self.speedup_icon, command=self.parent.playback_panel.videopanel.OnSpeedUp)

        self.speeddown_icon = PhotoImage(file='./media/speed_down.png')
        self.speeddown = Button(self, image=self.speeddown_icon, command=self.parent.playback_panel.videopanel.OnSpeedDown)

        self.zoom_in_icon = PhotoImage(file='./media/zoom_in.png')
        self.zoomin = Button(self, image=self.zoom_in_icon, command=self.parent.playback_panel.videopanel.OnZoomIn)

        self.zoom_out_icon = PhotoImage(file='./media/zoom_out.png')
        self.zoomout = Button(self, image=self.zoom_out_icon, command=self.parent.playback_panel.videopanel.OnZoomOut)

        self.int_forward_icon = PhotoImage(file='./media/int_forward.png')
        self.iforward = Button(self, image=self.int_forward_icon, state=DISABLED)

        self.int_backward_icon = PhotoImage(file='./media/int_backward.png')
        self.ibackword = Button(self, image=self.int_backward_icon, state=DISABLED)

        self.fullscreen_icon = PhotoImage(file='./media/fullscreen.png')
        self.fullsc = Button(self, image=self.fullscreen_icon, command=self.parent.playback_panel.videopanel.OnFullScreen)

        self.show_grid_icon = PhotoImage(file='./media/show_grid.png')
        self.set_grid = Button(self,image=self.show_grid_icon, command=self.parent.playback_panel.videopanel.OnSetGrid)

        self.volslider = Scale(self, variable=self.volume_var, command=self.parent.playback_panel.videopanel.volume_sel,
                                  from_=0, to=100, orient=HORIZONTAL, length=100, showvalue=0)
        self.timeScaleFrame = Frame(self) #contains: time slider, time label (currentTime)
        self.timeslider = Scale(self.timeScaleFrame, variable=self.scale_var, command=self.parent.playback_panel.videopanel.scale_sel,
                                   from_=0, to=1000, orient=HORIZONTAL, length=100, resolution=0.001, showvalue=0)
        self.currentTimeLabel = Label(self.timeScaleFrame, text="00:00:00", width=6)
        self.currentTimeLabel.pack(side=RIGHT)
        self.timeslider.pack(side=RIGHT, fill=X, expand=1)

        #packing
        self.timeScaleFrame.pack(side=TOP, fill=X, expand=1)
        self.play.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.pause.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.stop.pack(side=LEFT, fill=Y, padx=1, pady=3)
        Frame(self).pack(side=LEFT, fill=Y, padx=5)
        self.speedup.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.speeddown.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.previous_frame.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.next_frame.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.zoomin.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.zoomout.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.ibackword.pack(side=LEFT, fill=Y, padx=1, pady=3)
        self.iforward.pack(side=LEFT, fill=Y, padx=1, pady=3)
        Frame(self).pack(side=LEFT, fill=Y, padx=5)

        self.set_grid.pack(side=LEFT, fill=Y, padx=1, pady=3)
        Frame(self).pack(side=LEFT, fill=Y, padx=5)

        self.fullsc.pack(side=LEFT, fill=Y, padx=1, pady=3)

        self.volslider.pack(side=LEFT, expand=TRUE, anchor=E, padx=1, pady=3)

        #bind to status bar function

        #timer thread
        self.timer.start()
        self.parent.parent.update()

    def CalcTime(self, cur_val):
        mval = "%.0f" % (cur_val * 1000)
        nval = (int(mval)) // 1000 #in seconds
        HH = nval // 3600
        MM = nval // 60
        SS = nval % 60
        self.currentTimeLabel.config(text="{:>02d}:{:>02d}:{:>02d}".format(HH,MM,SS))

class VideoPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.canvas = Canvas(self, bg="black")
        self.canvas.bind('<Button-1>', self.on_click)

    def on_click(self, event):
        if self.parent.parent.side_bar.upper_bar.recordButton.cget("relief") == RAISED:
            return
        identities_selection = self.parent.parent.side_bar.identity.list.listbox.curselection()
        events_selection = self.parent.parent.side_bar.events.list.listbox.curselection()
        if len(identities_selection) == 0 or len(events_selection) == 0:
            return
        identities_text = configuration.config['identity_list'][identities_selection[0]]
        events_text = configuration.config['event_list'][events_selection[0]]

        record = [self.parent.player.get_time() * 0.001, identities_text,events_text , event.x, event.y]
        if len(control_block.events) >= configuration.config['event_manager']['number_of_events']:
            old_record = control_block.events.pop(0)
            if self.parent.parent.event_manager:
                self.parent.parent.event_manager.list.listbox.delete(0)

            with open(str(control_block.current_media_hash + '.csv'), "a") as events_file:
                csv.writer(events_file, delimiter=',').writerow(old_record)

        control_block.events.append(record)
        control_block.cached['total_number_of_events'] += 1

        if self.parent.parent.event_manager:
            self.parent.parent.event_manager.refresh_events()

        self.parent.TextOnScreen(identities_text + ' -> ' + events_text)

    def OnPause(self):
        self.parent.player.pause()

    def OnStop(self):
        self.parent.player.stop()
        self.parent.player.set_media(None)
        self.parent.parent.control_bar.timeslider.set(0)


        self.parent.parent.dump_events_to_file()

        control_block.dump_cache()

        if self.parent.parent.event_manager:
            self.parent.parent.event_manager.on_media_stop()




    def OnPlay(self):
        if not self.parent.player.get_media():
            self.OnOpen()
        else:
            if self.parent.player.play() == -1:
                self.parent.errorDialog("Unable to play.")

    def OnOpen(self):
        self.OnStop()
        p = pathlib.Path(os.path.expanduser(configuration.config['last_path']))
        fullname = askopenfilename(initialdir = p, title = "choose your file",filetypes = (("all files","*.*"),("mp4 files","*.mp4")))
        if os.path.isfile(fullname):
            dirname = os.path.dirname(fullname)
            filename = os.path.basename(fullname)
            configuration.config['last_path'] = dirname
            media = self.parent.vlc_instance.media_new(str(os.path.join(dirname, filename)))
            self.parent.player.set_media(media)
            if platform.system() == 'Windows':
                self.parent.player.set_hwnd(self.winfo_id())

            control_block.current_media_hash = md5(fullname)
            control_block.load_cache()
            if self.parent.parent.event_manager:
                self.parent.parent.event_manager.on_media_open()

            self.parent.player.play()
            # self.parent.parent.control_bar.volslider.set(50)



    def OnSetGrid(self):
        self.parent.gridpanel.setGrid()

    def OnTimer(self):
        if self.parent.player == None:
            return
        length = self.parent.player.get_length()
        dbl = length * 0.001
        self.parent.parent.control_bar.timeslider.config(to=dbl)
        curtime = self.parent.player.get_time()
        if curtime == -1:
            curtime = 0
        dbl = curtime * 0.001
        self.parent.parent.control_bar.timeslider_last_val = dbl
        self.parent.parent.control_bar.timeslider.set(dbl)


    #increase speed by 0.1 until a limit of 2.0
    def OnSpeedUp(self):
        if (self.parent.player.get_rate() == 0.25):
            self.parent.player.set_rate(0.3)
        elif (self.parent.player.get_rate() + 0.1 > 2.0):
            self.parent.player.set_rate(2.0)
        else:
            self.parent.player.set_rate(self.parent.player.get_rate() + 0.1)
        self.parent.TextOnScreen("Speed: {:0>.2f}".format(self.parent.player.get_rate()))


    #decrease speed by 0.1 until a limit of 0.25
    def OnSpeedDown(self):
        if (self.parent.player.get_rate() - 0.1 < 0.25):
            self.parent.player.set_rate(0.25)
        else:
            self.parent.player.set_rate(self.parent.player.get_rate() - 0.1)
        self.parent.TextOnScreen("Speed: {:0>.2f}".format(self.parent.player.get_rate()))

    #zoom in until a limit of 2x
    def OnZoomIn(self):
        if (self.parent.player.video_get_scale() == 0.0): #0 means fit automatically to the window
            self.parent.player.video_set_scale(1)
        elif (self.parent.player.video_get_scale() + 0.1 > 2):
            self.parent.player.video_set_scale(2)
        else:
            self.parent.player.video_set_scale(self.parent.player.video_get_scale() + 0.1)

    #zoom out until a limit of 1x
    def OnZoomOut(self):
        if (self.parent.player.video_get_scale() - 0.1 < 1):
            self.parent.player.video_set_scale(0)
        else:
            self.parent.player.video_set_scale(self.parent.player.video_get_scale() - 0.1)

    #enters and exits fullscreen mode
    def OnFullScreen(self):
        if not(self.parent.parent.parent.attributes("-fullscreen")):
            self.parent.parent.parent.attributes('-fullscreen', True)
        else:
            self.parent.parent.parent.attributes('-fullscreen', False)

    def scale_sel(self, evt):
        cur_val = self.parent.parent.control_bar.scale_var.get()
        self.parent.parent.control_bar.CalcTime(cur_val)
        if (math.fabs(cur_val - self.parent.parent.control_bar.timeslider_last_val) > 1.5):
            self.parent.parent.control_bar.timeslider_last_val = cur_val
            mval = "%.0f" % (cur_val * 1000)
            self.parent.player.set_time(int(mval)) # expects milliseconds

    def volume_sel(self, evt):
        if self.parent.player == None:
            return
        volume = self.parent.parent.control_bar.volume_var.get()
        if volume > 100:
            volume = 100
        if self.parent.player.audio_set_volume(volume) == -1:
            self.errorDialog("Failed to set volume")
        self.parent.parent.status_bar.status_label.config(text="Volume: " + str(self.parent.parent.control_bar.volslider.get()) + '%')

    def errorDialog(self, errormessage):
        print(errormessage)

class GridPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.eatingPoints = []
        self.canvasFirstUse = False
        self.canvasWH = (0,0)

    def setGrid(self):
        numOfPoints = 0
        for i in range(5):
            for j in range(5):
                numOfPoints += 1
                obj = self.parent.videopanel.canvas.create_text(140+ 60*i,20 + 60*j, text='Point {}'.format(numOfPoints), fill="yellow")
                if (j==0):
                    self.eatingPoints.append([])
                self.eatingPoints[i].append(obj)
        self.parent.videopanel.canvas.bind('<Button-1>', self.onCanvasClick) #'<Double-1>' for double-click
        #self.parent.videopanel.canvas.bind('<Button-3>', self.OnCanvasClickRight) #only for testing
        self.parent.videopanel.canvas.bind('<Configure>', self.OnCanvasSizeChange) #when frame grows
        #TODO: create rect from user clicks 4 points - pack objects on the rect instead of the canvas itself (2nd phase)
        #TODO: button "show grid" to show and hide the grid which is the rect (2nd phase)
        self.parent.videopanel.canvas.pack(fill=BOTH, expand=1)

    def onCanvasClick(self, event):
        #TODO: send the details of this click to EventManager
        currtime = self.parent.player.get_time() * 0.001
        currbird = self.parent.parent.side_bar.identity.list_frame.listbox.curselection()
        currevent = self.parent.parent.side_bar.events.list_frame.listbox.curselection()
        if (currbird != () and currevent!= () and self.parent.parent.side_bar.isRecording):
            print("Click: ({},{}), Closest Element: {}".format(event.x, event.y, (event.widget.find_closest(event.x, event.y))[0]))
            print("Time: {}, Bird: {}, Event: {}".format(round(currtime,3), currbird[0], currevent[0]))
            print("")

    #only for testing - not useful
    def OnCanvasClickRight(self, event):
        clickxy = self.parent.player.video_get_cursor() #doesn't work - check this (trying to prints cursor's coordinates in the video frame)
        vwei, vhei = self.parent.player.video_get_size()
        fhei = self.parent.winfo_height()
        fwei = self.parent.winfo_width()
        #print("PRINTXY: ({},{})".format(clickxy[0],clickxy[1]))
        print("Video Wei, Hei: ({},{})".format(vwei, vhei)) #video size=1280x720
        print("Frame Wei, Hei: ({},{})".format(fwei, fhei)) #current frame size (say): 1000x200
        #need to calculate (x,y) click on frame to percent of (width, height) of video

    #scaling the "eating points" when the frame size changes
    def OnCanvasSizeChange(self, event):
        if (not self.canvasFirstUse):
            self.canvasFirstUse = True
            self.canvasWH = (self.parent.videopanel.canvas.winfo_width(), self.parent.videopanel.canvas.winfo_height())
            return
        newWH = (event.width, event.height)
        distWH = (newWH[0] - self.canvasWH[0] , newWH[1] - self.canvasWH[1])

        #TODO: find a real scaling-to-frame algorithm!!! below is bullshit
        if (distWH[0] == 0): #changes only in y axis
            for i in range(5):
                for j in range(5):
                    self.parent.videopanel.canvas.move(self.eatingPoints[i][j], 0, distWH[1] // 2)
        elif (distWH[1] == 0): #changes only in x axis
            for i in range(5):
                for j in range(5):
                    self.parent.videopanel.canvas.move(self.eatingPoints[i][j], distWH[0] // 2, 0)
        elif (distWH[0] > 0): #frame grows
            self.parent.videopanel.canvas.scale("all",0,0,1.02,1.02)
        else: #frame shrinks
            self.parent.videopanel.canvas.scale("all", 0, 0, 0.98, 0.98)
        self.canvasWH = newWH


class PlaybackPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.videopanel = VideoPanel(self, bg="black")
        self.gridpanel = GridPanel(self)
        self.videopanel.pack(fill=BOTH, expand=1)


    #config of marquee strings (a.k.a messages on the video)
    def TextOnScreen(self, text):
        self.player.video_set_marquee_int(0, 1)  # enable marquee
        self.player.video_set_marquee_int(6, 48)  # font size
        self.player.video_set_marquee_int(7, 2000)  # timeout
        self.player.video_set_marquee_string(1, text) #set text
        self.player.video_get_marquee_string(1) #show text

    def ShowLogoOnScreen(self, logopath):
        self.parent.playback_panel.player.video_set_logo_int(vlc.VideoLogoOption.enable, 1)
        self.parent.playback_panel.player.video_set_logo_string(vlc.VideoLogoOption.file, logopath)
        # self.parent.playback_panel.player.video_set_logo_int(vlc.VideoLogoOption.opacity, 150)
        # self.parent.playback_panel.player.video_set_logo_string(vlc.VideoLogoOption.logo_x, "10")
        # self.parent.playback_panel.player.video_set_logo_string(vlc.VideoLogoOption.logo_y, "10")
        # self.parent.playback_panel.player.video_set_logo_int(vlc.VideoLogoOption.position, 3)
        # self.parent.playback_panel.player.video_set_logo_int(vlc.VideoLogoOption.repeat, 1)
        self.parent.playback_panel.player.video_get_logo_int(1)

    def RemoveLogoFromScreen(self):
        self.parent.playback_panel.player.video_set_marquee_int(0, 0)
        self.parent.playback_panel.player.video_set_logo_int(vlc.VideoLogoOption.enable, 0)

class SideBar(Frame):
    class UpperBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.record_icon = PhotoImage(file='./media/record.png')
            self.recordButton = Button(self, image=self.record_icon, command=self.parent.OnRecord)
            self.recordButton.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

            self.event_manager_icon = PhotoImage(file='./media/event_manager.png')
            self.eventManagerButton = Button(self, image=self.event_manager_icon, command=self.parent.parent.on_event_manager_button_click)
            self.eventManagerButton.pack(side=LEFT, expand=TRUE, fill=BOTH, padx=2)

    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.upper_bar = SideBar.UpperBar(self)
        self.identity = ListBox(self, 'identity_list','Birds')
        self.events = ListBox(self, 'event_list', 'Events')

        self.upper_bar.pack(fill=X)
        self.identity.pack(pady=2)
        self.events.pack(pady=2)

    def OnRecord(self):
        if not self.parent.playback_panel.player.get_media():
            return

        if self.upper_bar.recordButton.cget("relief") == RAISED:
            self.parent.playback_panel.videopanel.canvas.pack(fill=BOTH, expand=1)
            self.upper_bar.recordButton.config(relief=SUNKEN)
            # self.parent.playback_panel.ShowLogoOnScreen("record-button2.png")
        else:
            self.upper_bar.recordButton.config(relief=RAISED)
            # self.parent.playback_panel.RemoveLogoFromScreen()

class MenuBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.menu = Menu(self)

        filemenu = Menu(self.menu, tearoff=0)
        filemenu.add_command(label="Open", command=self.parent.playback_panel.videopanel.OnOpen)
        filemenu.add_command(label="Exit", command=self.parent.parent.quit)
        self.menu.add_cascade(label="File", menu=filemenu)

        calimenu = Menu(self.menu, tearoff=0)
        calimenu.add_command(label="Calibrate")
        calimenu.add_command(label="Load existing calibration")
        self.menu.add_cascade(label="Calibration", menu=calimenu)

        eventmenu = Menu(self.menu, tearoff=0)
        eventmenu.add_command(label="Open event manager", command=parent.on_open_event_manager_menu_click)
        eventmenu.add_command(label="Export events", command=parent.on_export_events)
        self.menu.add_cascade(label="Events", menu=eventmenu)

        settingsmenu = Menu(self.menu, tearoff=0)
        settingsmenu.add_command(label="Shortcuts")
        self.menu.add_cascade(label="Settings", menu=settingsmenu)

        helpmenu = Menu(self.menu, tearoff=0)
        helpmenu.add_command(label="Check for updates")
        helpmenu.add_command(label="Website")
        helpmenu.add_command(label="About", command=self.help_about)
        self.menu.add_cascade(label="Help", menu=helpmenu)

    def help_about(self):
        window = Toplevel(self.parent.parent)
        labelframe = LabelFrame(window, text="About Poke-A-Bird")
        labelframe.pack(fill="both", expand="yes")
        Label(labelframe, text="Nerya Meshulam\nElad Yacovi", width=20, height=10).pack()
        Button(window, text="OK", width=5, command=window.destroy).pack()
        window.wait_window()



class MainApplication(Frame):
    class StatusBar(Frame):
        def __init__(self, parent, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.status_label = Label(self, text="Poke-A-Bird", bd=2, relief=SUNKEN, anchor=W)
            self.status_label.pack(side=BOTTOM, fill=X)

        def DisplayOnLabel(self, event):
            if event.widget == self.parent.control_bar.play:
                self.status_label.config(text="Play")
            elif event.widget == self.parent.control_bar.pause:
                self.status_label.config(text="Pause")
            elif event.widget == self.parent.control_bar.stop:
                self.status_label.config(text="Stop")
            elif event.widget == self.parent.control_bar.speedup:
                self.status_label.config(text="Speed Up")
            elif event.widget == self.parent.control_bar.speeddown:
                self.status_label.config(text="Speed Down")
            elif event.widget == self.parent.control_bar.previous_frame:
                self.status_label.config(text="Previous Frame")
            elif event.widget == self.parent.control_bar.next_frame:
                self.status_label.config(text="Next Frame")
            elif event.widget == self.parent.control_bar.zoomin:
                self.status_label.config(text="Zoom In")
            elif event.widget == self.parent.control_bar.zoomout:
                self.status_label.config(text="Zoom Out")
            elif event.widget == self.parent.control_bar.iforward:
                self.status_label.config(text="Intellegent Fast Forward")
            elif event.widget == self.parent.control_bar.ibackword:
                self.status_label.config(text="Intellegent Fast Backward")
            elif event.widget == self.parent.control_bar.fullsc:
                self.status_label.config(text="Full Screen")
            elif event.widget == self.parent.control_bar.set_grid:
                self.status_label.config(text="Set Grid")
            elif event.widget == self.parent.control_bar.volslider:
                self.status_label.config(text="Volume: " + str(self.parent.control_bar.volslider.get()) + '%')
            elif event.widget == self.parent.side_bar.upper_bar.eventManagerButton:
                self.status_label.config(text="Open Event Manager")
            elif event.widget == self.parent.side_bar.upper_bar.recordButton:
                self.status_label.config(text="Set Events Recording")
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

    #API for jumping to a certain point in time - d_time(in seconds)
    def JumpToTime(self, d_time):
        self.control_bar.timeslider.set(d_time)

    def on_event_manager_button_click(self):
        if not self.event_manager:
            self.event_manager = EventManager(self, takefocus=True)
        else:
            self.event_manager.on_closing()

    def on_open_event_manager_menu_click(self):
        if not self.event_manager:
            self.event_manager = EventManager(self, takefocus=True)

    def on_export_events(self):
        p = pathlib.Path(os.path.expanduser(configuration.config['last_export_path']))
        fullname = asksaveasfilename(initialdir = p, title = "Export As",filetypes = (("CSV file (*.csv)","*.csv"),("All files (*)","*.*")))
        if fullname == '':
            return
        export_path = pathlib.Path(fullname)
        if pathlib.Path(control_block.current_media_hash + '.csv').is_file():
            copyfile(str(control_block.current_media_hash + '.csv'), fullname)
        with open(export_path, "a") as events_file:
            csv.writer(events_file, delimiter=',').writerows(control_block.events)

        configuration.config['last_export_path'] = os.path.dirname(fullname)

    def on_exit(self):
        self.playback_panel.videopanel.OnStop()
        with open(configuration.config_file, 'w') as fp:
            json.dump(configuration.config, fp)
        self.parent.destroy()

    def dump_events_to_file(self):
        for item in control_block.events:
            with open(str(control_block.current_media_hash + '.csv'), "a") as events_file:
                csv.writer(events_file, delimiter=',').writerow(item)

        control_block.events.clear()

if __name__ == "__main__":
    root = Tk()
    root.minsize(width=840, height=460)
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

