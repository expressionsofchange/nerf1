from utils import pmts
from sys import argv
from os.path import isfile
from colorscheme import CURIOUS_BLUE
from kivy.graphics import Color, Rectangle

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.config import Config
from kivy.clock import Clock

from channel import ClosableChannel

from filehandler import (
    FileWriter,
    initialize_history,
    read_from_file
)

from widgets.tree import TreeWidget
from widgets.ic_history import HistoryWidget
from record import Player

from memoization import Memoization

from dsn.s_expr.clef import Note
from dsn.s_expr.score import Score

from kivy.core.image import Image
cursor_normal_image = Image("cursor-normal.png")
cursor_click_image = Image("cursor-click.png")

Config.set('kivy', 'exit_on_escape', '0')

MOVIE_FRAME_RATE = 1 / 30


class NoteCollector(object):
    def __init__(self, channel):
        self.score = Score.empty()

        # receive-only connection: NoteCollector's outwards communication goes via others reading
        # self.note
        channel.connect(self.receive)

    def receive(self, data):
        pmts(data, Note)
        self.score = self.score.slur(data)


class EditorGUI(App):

    def __init__(self, filename):
        super(EditorGUI, self).__init__()

        self.m = Memoization()
        # self.recorder = Recorder() AS_MOVIE: don't record while playing
        self.player = Player()

        self.filename = filename

        self.setup_channels()

        self.do_initial_file_read()

    def setup_channels(self):
        # This is the main channel of Notes for our application.
        self.history_channel = ClosableChannel()  # No relation with the T.V. channel of the same name

        self.lnh = NoteCollector(self.history_channel)

    def do_initial_file_read(self):
        if isfile(self.filename):
            # ReadFromFile before connecting to the Writer to ensure that reading from the file does not write to it
            read_from_file(self.filename, self.history_channel)
            FileWriter(self.history_channel, self.filename)
        else:
            # FileWriter first to ensure that the initialization becomes part of the file.
            FileWriter(self.history_channel, self.filename)
            initialize_history(self.history_channel)

    def add_tree_and_stuff(self, history_channel):
        horizontal_layout = BoxLayout(spacing=10, orientation='horizontal')

        tree = TreeWidget(
            m=self.m,
            size_hint=(.5, 1),
            history_channel=history_channel,
            record=lambda *args: None,  # AS_MOVIE: don't record
            )

        history_widget = HistoryWidget(
            m=self.m,
            size_hint=(.5, 1),
            )
        # Clock.schedule_interval(history_widget.tick, 1 / 60) AS_MOVIE: we'll send these ourselves

        horizontal_layout.add_widget(history_widget)
        horizontal_layout.add_widget(tree)

        self.vertical_layout.add_widget(horizontal_layout)

        tree_data_channel, _, _ = tree._child_channel_for_t_address([])
        tree_data_channel.connect(history_widget.receive_from_parent)

        tree.cursor_channel.connect(history_widget.parent_cursor_update)

        tree.focus = True

        self.tree, self.history_widget = tree, history_widget  # AS_MOVIE: we need access to the widgets
        return tree

    def build(self):
        self.vertical_layout = GridLayout(spacing=10, cols=1)

        tree = self.add_tree_and_stuff(self.history_channel)
        tree.report_new_tree_to_app = self.add_tree_and_stuff

        # we kick off with the state so far
        tree.receive_from_channel(self.lnh.score)

        self.frame_nr = 0

        # 1 / 10: just to make sure we're not faster than any of the normal program's events, scheduled for the next
        # frame:
        Clock.schedule_interval(self.play_tick, 1 / 10)

        return self.vertical_layout

    def get_simulated_time(self):
        return MOVIE_FRAME_RATE * self.frame_nr

    def play_tick(self, dt):
        self.history_widget.tick(MOVIE_FRAME_RATE)
        self.player.simulate_tree_input(self.tree, self.get_simulated_time())

        self.frame_nr += 1
        self.draw_cursor()

        # sadly, the below leaks memory like crazy on my system, leading to the process being killed after some 600
        # frames.  Whatever the reason, an if-statement on frame_nr allows us to generate the frames in batches until
        # enough frames have been generated for any particular movie.
        if self.frame_nr > 583:
            self.vertical_layout.export_to_png('frames/%06d.png' % self.frame_nr)

        if self.frame_nr == 650:
            exit()

    def draw_cursor(self):
        if self.player.get_click_recentness(self.get_simulated_time()) < 0.20:
            cursor_texture = cursor_click_image.texture
        else:
            cursor_texture = cursor_normal_image.texture

        content_height = cursor_texture.height
        content_width = cursor_texture.width

        hotspot = (9, 9)  # this is the pointing part of the cursor

        cursor_pos = self.player.get_cursor_position(self.get_simulated_time())
        bottom_left = (cursor_pos[0] - hotspot[1],
                       cursor_pos[1] - content_height + hotspot[1])

        self.tree.refresh()
        self.tree.canvas.add(Color(*CURIOUS_BLUE))
        self.tree.canvas.add(Rectangle(
            pos=bottom_left,
            size=(content_width, content_height),
            texture=cursor_texture,
        ))


def main():
    if len(argv) != 2:
        print("Usage: ", argv[0], "FILENAME")
        exit()

    EditorGUI(argv[1]).run()


if __name__ == "__main__":
    main()


# Convert to mpeg, after recording full screen on Klaas' laptop
# ffmpeg -i %6d.png -vcodec h264 -vb 20M -pix_fmt yuv420p -s 1920x1200  -r 30  output.mp4

# Convert to mpeg, after recording full screen on Klaas' laptop; cropping the bottom for better YouTube upload
# ffmpeg -i %6d.png -vcodec h264 -vb 20M -pix_fmt yuv420p -filter:v "crop=1920:1080:0:0" -r 30  output.mp4

# (In fact, because the initial resize at program-startup takes a few fractions of a second, I had to copy e.g. frame
# 3 over frames 1 and 2)
