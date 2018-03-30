from tkinter import *
from tkinter.filedialog import askopenfilename
import math
import vlc
import pathlib
import os
import platform
import time
from threading import Thread, Event

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
            self.new_button = Button(self, text='add', command=self.parent.add_item)
            self.remove_button = Button(self, text='rem', command=self.parent.delete_item)

            self.title.pack(fill=BOTH, side=LEFT, expand=TRUE)
            self.new_button.pack(side=LEFT)
            self.remove_button.pack(side=LEFT)

    class List(Frame):
        def __init__(self, parent, list, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.scrollbar = Scrollbar(self)
            self.listbox = Listbox(self, height=5, yscrollcommand=self.scrollbar.set, borderwidth=0,
                                   highlightthickness=0, exportselection=False, activestyle=NONE)
            self.scrollbar.config(command=self.listbox.yview)

            self.scrollbar.pack(side=RIGHT, fill=Y)
            self.listbox.pack(side=LEFT)
            for item in list:
                self.listbox.insert(END, item)

    def delete_item(self):
        current_selection = self.list_frame.listbox.curselection()
        if current_selection != ():
            self.list.remove(self.list_frame.listbox.get(current_selection))
            self.list_frame.listbox.delete(current_selection)

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
            self.list.append(entryStr.get())
            self.list_frame.listbox.insert(END, entryStr.get())

    def __init__(self, parent, title, list, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.title = title
        self.list = list
        self.title_frame = self.Title(self, title)
        self.list_frame = self.List(self, list)

        self.title_frame.pack(fill=BOTH, expand=TRUE)
        self.list_frame.pack(side=BOTTOM)


class ControlBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.volume_var = IntVar()
        self.scale_var = DoubleVar() #time of the video scale var
        self.timeslider_last_val = 0.0
        self.timer = ttkTimer(self.parent.playback_panel.videopanel.OnTimer, 1.0)

        self.pause = Button(self, text="||", command=self.parent.playback_panel.videopanel.OnPause, width=4)
        self.play = Button(self, text=">", command=self.parent.playback_panel.videopanel.OnPlay, width=4)
        self.stop = Button(self, text="#", command=self.parent.playback_panel.videopanel.OnStop, width=4)
        self.speedup = Button(self, text=">>", command=self.parent.playback_panel.videopanel.OnFwd5sec, width=4) #TODO: speedup
        self.speeddown = Button(self, text="<<", command=self.parent.playback_panel.videopanel.OnBwd5sec, width=4) #TODO: speeddown
        self.zoomin = Button(self, text=">$", width=4)  # TODO: zoomin
        self.zoomout = Button(self, text="<$", width=4)  # TODO: zoomout
        self.iforward = Button(self, text=">@", width=4)  # TODO: intellegent forward
        self.ibackword = Button(self, text="<@", width=4)  # TODO: intellegent backward
        self.fullsc = Button(self, text="^", width=4)  # TODO: full screen
        #print_time = Button(self, text="Print Time", command=self.parent.playback_panel.videopanel.OnPrintTime)
        self.set_grid = Button(self, text="Set Grid", command=self.parent.playback_panel.videopanel.OnSetGrid)
        self.volslider = Scale(self, variable=self.volume_var, command=self.parent.playback_panel.videopanel.volume_sel,
                                  from_=0, to=100, orient=HORIZONTAL, length=100, showvalue=0)
        self.timeScaleFrame = Frame(self) #contains: time slider, time label (currentTime)
        self.timeslider = Scale(self.timeScaleFrame, variable=self.scale_var, command=self.parent.playback_panel.videopanel.scale_sel,
                                   from_=0, to=1000, orient=HORIZONTAL, length=100, resolution=0.001, showvalue=0)
        self.currentTimeLabel = Label(self.timeScaleFrame, text="00:00:00", bg="green", fg="white", width=10)
        self.currentTimeLabel.pack(side=RIGHT)
        self.timeslider.pack(side=RIGHT, fill=X, expand=1)


        self.timeScaleFrame.pack(side=TOP, fill=X, expand=1)
        self.play.pack(side=LEFT, fill=Y)
        self.pause.pack(side=LEFT, fill=Y)
        self.stop.pack(side=LEFT, fill=Y)
        self.volslider.pack(side=LEFT, expand=1)
        self.set_grid.pack(side=LEFT, fill=Y)
        self.speedup.pack(side=LEFT, fill=Y)
        self.speeddown.pack(side=LEFT, fill=Y)
        #print_time.pack(side=LEFT, fill=Y)
        self.zoomin.pack(side=LEFT, fill=Y)
        self.zoomout.pack(side=LEFT, fill=Y)
        self.iforward.pack(side=LEFT, fill=Y)
        self.ibackword.pack(side=LEFT, fill=Y)
        self.fullsc.pack(side=LEFT, fill=Y)


        self.bind_all('<Enter>', self.parent.status_bar.DisplayOnLabel)

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

        self.canvas = Canvas(self)

    def OnPause(self):
        self.parent.player.pause()

    def OnStop(self):
        self.parent.player.stop()
        self.parent.parent.control_bar.timeslider.set(0)

    def OnPlay(self):
        if not self.parent.player.get_media():
            self.OnOpen()
        else:
            if self.parent.player.play() == -1:
                self.parent.errorDialog("Unable to play.")

    def OnOpen(self):
        self.OnStop()
        p = pathlib.Path(os.path.expanduser("~"))
        fullname = askopenfilename(initialdir = p, title = "choose your file",filetypes = (("all files","*.*"),("mp4 files","*.mp4")))
        if os.path.isfile(fullname):
            dirname = os.path.dirname(fullname)
            filename = os.path.basename(fullname)
            media = self.parent.vlc_instance.media_new(str(os.path.join(dirname, filename)))
            self.parent.player.set_media(media)
            if platform.system() == 'Windows':
                self.parent.player.set_hwnd(self.winfo_id())
            self.OnPlay()
            self.parent.parent.control_bar.volslider.set(50)

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

    def OnPrintTime(self):
        cur_video_time = self.parent.player.get_time() * 0.001
        print("%.3f" % cur_video_time)

    def OnFwd5sec(self):
        nval = self.parent.parent.control_bar.scale_var.get()
        mval = "%.0f" % (nval * 1000 + 1000)
        self.parent.player.set_time(int(mval))

    def OnBwd5sec(self):
        nval = self.parent.parent.control_bar.scale_var.get()
        mval = "%.0f" % (nval * 1000 - 1000)
        self.parent.player.set_time(int(mval))

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

    def errorDialog(self, errormessage):
        print(errormessage)

class GridPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

    def setGrid(self):
        obj1 = self.parent.videopanel.canvas.create_text(50, 30, text='Click me one')
        obj2 = self.parent.videopanel.canvas.create_text(50, 70, text='Click me two')
        self.parent.videopanel.canvas.bind('<Button-1>', self.onCanvasClick) #'<Double-1>' for double-click
        self.parent.videopanel.canvas.tag_bind(obj1, '<Button-1>', self.onObjectClick)
        self.parent.videopanel.canvas.tag_bind(obj2, '<Button-1>', self.onObjectClick)
        #TODO: create rect from user clicks 4 points - pack objects on the rect instead of the canvas itself (2nd phase)
        #TODO: button "show grid" to show and hide the grid which is the rect (2nd phase)
        #rec = self.parent.videopanel.canvas.create_rectangle(200, 200, 300, 300, fill="green")
        #self.parent.videopanel.canvas.delete(rec)

        self.parent.videopanel.canvas.pack(fill=BOTH, expand=1)

    def onCanvasClick(self, event):
        #print('Got canvas click', event.x, event.y, event.widget)
        #print(event.widget.find_closest(event.x, event.y))
        #TODO: send the details of this click to EventManager
        currtime = self.parent.player.get_time() * 0.001
        currbird = self.parent.parent.side_bar.identity.list_frame.listbox.curselection()
        currevent = self.parent.parent.side_bar.events.list_frame.listbox.curselection()
        if (currbird != () and currevent!= () and self.parent.parent.side_bar.isRecording):
            print("Click: ({},{}), Closest Element: {}".format(event.x, event.y, (event.widget.find_closest(event.x, event.y))[0]))
            print("Time: {}, Bird: {}, Event: {}".format(round(currtime,3), currbird[0], currevent[0]))
            print("")

    def onObjectClick(self, event):
        #print('Got object click', event.x, event.y, event.widget)
        pass

class PlaybackPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.videopanel = VideoPanel(self, bg="black")
        self.gridpanel = GridPanel(self)

        self.videopanel.pack(fill=BOTH, expand=1)


class SideBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.recordButton = Button(self, text="Record:\nOff", command=self.OnRecord)
        self.recordButton.grid(row=0, column=0, sticky=N+S+E+W)
        self.isRecording = False

        self.eventManagerButton = Button(self, text="Event\nManager", command=self.OnEventManager)
        self.eventManagerButton.grid(row=0, column=1, sticky=N+S+E+W)

        self.identity = ListBox(self, 'Bird', ['bird_0', 'bird_1', 'bird_2'])
        self.identity.grid(row=1, columnspan=2)

        self.events = ListBox(self, 'Events', ['event_0', 'event_1', 'event_2'])
        self.events.grid(row=2, columnspan=2)

    def OnEventManager(self):
        window = Toplevel(self.parent.parent)
        labelframe = LabelFrame(window, text="Event Manager")
        labelframe.pack(fill="both", expand="yes")
        Label(labelframe, text="This is event manager").pack()
        Button(window, text="OK", width=5, command=window.destroy).pack()
        window.wait_window()

    def OnRecord(self):
        if (self.recordButton.cget("relief") == RAISED):
            self.recordButton.config(relief=SUNKEN)
            self.isRecording = True
            self.recordButton.config(text="Record:\nOn")
        else:
            self.recordButton.config(relief=RAISED)
            self.isRecording = False
            self.recordButton.config(text="Record:\nOff")

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
        eventmenu.add_command(label="Open event manager")
        eventmenu.add_command(label="Export events")
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
            self.status_label.config(text="Volume")
        else:
            self.status_label.config(text="Poke-A-Bird")

class MainApplication(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.status_bar = StatusBar(self)
        self.side_bar = SideBar(self)
        self.playback_panel = PlaybackPanel(self, bg="black")
        self.menu_bar = MenuBar(self)
        self.control_bar = ControlBar(self, height=50)


        self.parent.config(menu=self.menu_bar.menu)
        self.side_bar.grid(row=0, column=1, rowspan=2, sticky=NS)
        self.control_bar.grid(row=1, column=0, sticky=EW)
        self.playback_panel.grid(row=0, column=0, sticky=NSEW)
        self.status_bar.grid(row=2, columnspan=2, sticky=EW)


if __name__ == "__main__":
    root = Tk()
    root.minsize(width=640, height=360)
    root.title("Poke-A-Bird")
    #root.attributes('-fullscreen', True) #force fullscreen
    #root.state('zoomed') #force zoom

    mainapp = MainApplication(root)
    mainapp.pack(side="top", fill="both", expand=True)
    root.mainloop()
    mainapp.control_bar.timer.stop()

