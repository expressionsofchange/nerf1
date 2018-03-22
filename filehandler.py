from utils import pmts
from dsn.s_expr.clef import Note, BecomeList


def all_notes_from_stream(byte_stream):
    while True:
        yield Note.from_stream(byte_stream)  # Transparently yields the StopIteration at the lower level


class FileWriter(object):
    """For lack of a better name: Handles the writing of Notes objects to files."""

    def __init__(self, channel, filename):
        # LATER: proper file-closing too! In the status quo there's 2 (related) open ends:
        # 1] we don't do any file closing ourselves at any point
        # 2] we don't have an implementation for closing channels yet
        self.file_ = open(filename, 'ab')

        # receive-only connection: FileWriters are ChannelReaders
        channel.connect(self.receive)

    def receive(self, data):
        # Receives: Note writes it to the connected file
        pmts(data, Note)
        self.file_.write(data.as_bytes())
        self.file_.flush()


def read_from_file(filename, channel):
    byte_stream = iter(open(filename, 'rb').read())
    for note in all_notes_from_stream(byte_stream):
        channel.broadcast(note)


def initialize_history(channel):
    channel.broadcast(BecomeList())
