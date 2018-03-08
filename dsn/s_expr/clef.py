# coding=utf-8

from vlq import to_vlq, from_vlq
from utils import pmts, rfs

BECOME_ATOM = 0
SET_ATOM = 1

BECOME_LIST = 2
INSERT = 3
DELETE = 4
EXTEND = 5
CHORD = 6


class Note(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            BECOME_ATOM: BecomeAtom,
            SET_ATOM: SetAtom,
            BECOME_LIST: BecomeList,
            INSERT: Insert,
            DELETE: Delete,
            EXTEND: Extend,
            CHORD: Chord,
        }[byte0].from_stream(byte_stream)


class BecomeAtom(Note):
    def __init__(self, atom):
        pmts(atom, str)
        self.atom = atom

    def __repr__(self):
        return "(become-atom " + self.atom + ")"

    def as_bytes(self):
        utf8 = self.atom.encode('utf-8')
        return bytes([BECOME_ATOM]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return BecomeAtom(str(utf8, 'utf-8'))


class SetAtom(Note):
    def __init__(self, atom):
        pmts(atom, str)
        self.atom = atom

    def __repr__(self):
        return "(set-atom " + self.atom + ")"

    def as_bytes(self):
        utf8 = self.atom.encode('utf-8')
        return bytes([SET_ATOM]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return SetAtom(str(utf8, 'utf-8'))


class BecomeList(Note):
    def __repr__(self):
        return "(become-list)"

    def as_bytes(self):
        return bytes([BECOME_LIST])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeList()


class Insert(Note):
    def __init__(self, index, child_note):
        pmts(index, int)
        pmts(child_note, Note)

        self.index = index
        self.child_note = child_note

    def __repr__(self):
        return "(insert " + repr(self.index) + " " + repr(self.child_note) + ")"

    def as_bytes(self):
        return bytes([INSERT]) + to_vlq(self.index) + self.child_note.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        # N.B.: The TypeConstructor byte is not repeated here; it happens before we reach this point
        return Insert(from_vlq(byte_stream), Note.from_stream(byte_stream))


class Delete(Note):
    def __init__(self, index):
        """index :: index to be deleted"""
        pmts(index, int)
        self.index = index

    def __repr__(self):
        return "(delete " + repr(self.index) + ")"

    def as_bytes(self):
        return bytes([DELETE]) + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return Delete(from_vlq(byte_stream))


class Extend(Note):
    def __init__(self, index, child_note):
        pmts(index, int)
        pmts(child_note, Note)

        self.index = index
        self.child_note = child_note

    def __repr__(self):
        return "(extend " + repr(self.index) + " " + repr(self.child_note) + ")"

    def as_bytes(self):
        return bytes([EXTEND]) + to_vlq(self.index) + self.child_note.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Extend(from_vlq(byte_stream), Note.from_stream(byte_stream))


class Chord(Note):
    def __init__(self, score):
        self.score = score

    def __repr__(self):
        return "(chord " + repr(self.score) + ")"

    def as_bytes(self):
        return bytes([CHORD]) + self.score.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Chord(Score.from_stream(byte_stream))


class Score(object):

    def __init__(self, notes):
        self.notes = notes

    def __repr__(self):
        return "(" + " ".join(repr(note) for note in self.notes) + ")"

    def as_bytes(self):
        return to_vlq(len(self.notes)) + b"".join(note.as_bytes() for note in self.notes)

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        notes = []
        for i in range(length):
            notes.append(Note.from_stream(byte_stream))
        return Score(notes)
