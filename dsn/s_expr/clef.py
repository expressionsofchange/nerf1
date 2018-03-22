# coding=utf-8
from vlq import to_vlq, from_vlq
from utils import pmts, rfs

from dsn.s_expr.structure import Atom, List

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

    @staticmethod
    def from_s_expression(s_expression):
        """In the paper submitted to ELS'18 I presented a notation for notes in terms of an s-expression.
        from_s_expression parses such expressions into the associated Python object representing the same note.
        Note: the s_expression's history is completely ignored in this process."""

        pmts(s_expression, List)
        pmts(s_expression.children[0], Atom)
        atom = s_expression.children[0].atom
        d = {
            "become-atom": BecomeAtom,
            "set-atom": SetAtom,
            "become-list": BecomeList,
            "insert": Insert,
            "delete": Delete,
            "extend": Extend,
            "chord": Chord,
        }

        if atom not in d:
            raise Exception("Unknown note: %s" % s_expression.children[0].atom)

        return d[atom].from_s_expression(s_expression)

    def to_s_expression(self):
        """In the paper submitted to ELS'18 I presented a notation for notes in terms of an s-expression.
        to_s_expression serializes the Python note into such s_expressions.
        N.B. An s_expression's without any history is created in this process. (Reasoning: we don't have a meaningful
        history available to us, and we don't need one because these s-expressions are exclusively used for
        representation (printing on screen); alternative solution: 'concoct' a history)"""

        raise Exception("to_s_expression() cannot be called on the abstract baseclass")


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

    def to_s_expression(self):
        return List([Atom("become-atom"), Atom(self.atom)])

    @staticmethod
    def from_s_expression(s_expression):
        return BecomeAtom(s_expression.children[1].atom)


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

    def to_s_expression(self):
        return List([Atom("set-atom"), Atom(self.atom)])

    @staticmethod
    def from_s_expression(s_expression):
        return SetAtom(s_expression.children[1].atom)


class BecomeList(Note):
    def __repr__(self):
        return "(become-list)"

    def as_bytes(self):
        return bytes([BECOME_LIST])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeList()

    def to_s_expression(self):
        return List([Atom("become-list")])

    @staticmethod
    def from_s_expression(s_expression):
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

    def to_s_expression(self):
        return List([Atom("insert"), Atom(str(self.index)), self.child_note.to_s_expression()])

    @staticmethod
    def from_s_expression(s_expression):
        return Insert(int(s_expression.children[1].atom), Note.from_s_expression(s_expression.children[2]))


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

    def to_s_expression(self):
        return List([Atom("delete"), Atom(str(self.index))])

    @staticmethod
    def from_s_expression(s_expression):
        return Delete(int(s_expression.children[1].atom))


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

    def to_s_expression(self):
        return List([Atom("extend"), Atom(str(self.index)), self.child_note.to_s_expression()])

    @staticmethod
    def from_s_expression(s_expression):
        return Extend(int(s_expression.children[1].atom), Note.from_s_expression(s_expression.children[2]))


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

    def to_s_expression(self):
        return List([Atom("chord"), List([c.to_s_expression() for c in self.score.notes])])

    @staticmethod
    def from_s_expression(s_expression):
        return Chord(Score([Note.from_s_expression(child) for child in s_expression.children[1].children]))


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
