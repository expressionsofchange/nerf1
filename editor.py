from utils import pmts
from sys import argv
from os.path import isfile

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.config import Config

from channel import ClosableChannel

from filehandler import (
    FileWriter,
    initialize_history,
    read_from_file
)

from widgets.tree import TreeWidget
from widgets.history import HistoryWidget

from memoization import Memoization

from dsn.s_expr.clef import Note
from dsn.s_expr.score import Score

Config.set('kivy', 'exit_on_escape', '0')


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
            )

        history_widget = HistoryWidget(
            m=self.m,
            size_hint=(.5, 1),
            )
        horizontal_layout.add_widget(history_widget)
        horizontal_layout.add_widget(tree)

        self.vertical_layout.add_widget(horizontal_layout)

        tree.cursor_channel.connect(history_widget.parent_cursor_update)
        tree.focus = True
        return tree

    def build(self):
        self.vertical_layout = GridLayout(spacing=10, cols=1)

        tree = self.add_tree_and_stuff(self.history_channel)
        tree.report_new_tree_to_app = self.add_tree_and_stuff

        # we kick off with the state so far
        tree.receive_from_channel(self.lnh.score)

        return self.vertical_layout


def main():
    if len(argv) != 2:
        print("Usage: ", argv[0], "FILENAME")
        exit()

    EditorGUI(argv[1]).run()


if __name__ == "__main__":
    main()
