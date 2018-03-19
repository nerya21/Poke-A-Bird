from tkinter import *


class ListBox(Frame):
    class Title(Frame):
        def __init__(self, parent, title, *args, **kwargs):
            Frame.__init__(self, parent, *args, **kwargs)
            self.parent = parent

            self.title = Label(self, text=title, anchor=W)
            self.new_button = Button(self, text='add')
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


class PlaybackPanel(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent


class SideBar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.identity = ListBox(self, 'Bird', ['bird_0', 'bird_1', 'bird_2'])
        self.identity.pack()

        self.events = ListBox(self, 'Events', ['event_0', 'event_1', 'event_2'])
        self.events.pack()


class MainApplication(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.side_bar = SideBar(self, bg="red")
        self.control_bar = ControlBar(self, height=50, bg="yellow")
        self.playback_panel = PlaybackPanel(self, bg="black")

        self.side_bar.grid(row=0, column=1, rowspan=2, sticky=NS)
        self.control_bar.grid(row=1, column=0, sticky=EW)
        self.playback_panel.grid(row=0, column=0, sticky=NSEW)


if __name__ == "__main__":
    root = Tk()
    root.minsize(width=640, height=360)

    MainApplication(root).pack(side="top", fill="both", expand=True)
    root.mainloop()
