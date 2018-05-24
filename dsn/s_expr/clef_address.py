"""
This module contains machinery to annotate Notes with a "global address", the path of that note in a with respect to
some global root note or root score.

Note: the annotated Notes are defined here with considerable amount of duplication with clef.py, most notably in the
fact that we define a separate subclass for each note class. Also: in the fact that `to_s_expression` is fully
duplicated (but extended with the relevant address information)

For now, this isn't pretty but it works. I'm open to a more elegant/general solution.
"""

from dsn.s_expr.clef import BecomeAtom, SetAtom, BecomeList, Insert, Delete, Extend, Chord, Score as ChordScore
from dsn.s_expr.simple_score import SimpleScore
from dsn.s_expr.construct import play_note
from dsn.s_expr.structure import Atom, List

from utils import pmts

from dsn.s_expr.score import Score


# ## Classes for note-addresses

class NoteAddressPart(object):
    """The global paths are defined as tuples of NoteAddressPart."""
    pass


class TheChild(NoteAddressPart):
    """For notes which take a single child: this part of the path denotes descending into that child."""

    def __repr__(self):
        return '>'

    def __eq__(self, other):
        return isinstance(other, TheChild)

    def __hash__(self):
        return hash(repr(self))


class InScore(NoteAddressPart):
    """For Scores, the path is denoted by indicating which child in the score we're talking abuot. (by index)"""

    def __init__(self, index):
        self.index = index

    def __repr__(self):
        return '@%s' % self.index

    def __eq__(self, other):
        return isinstance(other, InScore) and self.index == other.index

    def __hash__(self):
        return hash(self.index)


# ## Classes for GlobNote (which isn't actually a class itself; we simply subclass each note in clef.py separately)

class GlobBecomeAtom(BecomeAtom):
    def __init__(self, address, *args):
        super(GlobBecomeAtom, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("become-atom", address=self.address + ("name",)),
            Atom(self.atom, address=self.address + ("atom",)),
            ], address=self.address)


class GlobSetAtom(SetAtom):
    def __init__(self, address, *args):
        super(GlobSetAtom, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("set-atom", address=self.address + ("name",)),
            Atom(self.atom, address=self.address + ("atom",)),
            ], address=self.address)


class GlobBecomeList(BecomeList):
    def __init__(self, address, *args):
        super(GlobBecomeList, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("become-list", address=self.address + ("name",)),
            ], address=self.address)


class GlobInsert(Insert):
    def __init__(self, address, *args):
        super(GlobInsert, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("insert", address=self.address + ("name",)),
            Atom(str(self.index), address=self.address + ("index",)),
            self.child_note.to_s_expression()
            ], address=self.address)


class GlobDelete(Delete):
    def __init__(self, address, *args):
        super(GlobDelete, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("delete", address=self.address + ("name",)),
            Atom(str(self.index), address=self.address + ("index",))
        ], address=self.address)


class GlobExtend(Extend):
    def __init__(self, address, *args):
        super(GlobExtend, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("extend", address=self.address + ("name",)),
            Atom(str(self.index), address=self.address + ("index",)),
            self.child_note.to_s_expression()
            ], address=self.address)


class GlobChord(Chord):
    def __init__(self, address, *args):
        super(GlobChord, self).__init__(*args)
        self.address = address

    def to_s_expression(self):
        return List([
            Atom("chord", address=self.address + ("name",)),
            List([c.to_s_expression() for c in self.score.notes], address=self.address + ("list",)),
            ], address=self.address)


normal_to_glob = {
    BecomeAtom: GlobBecomeAtom,
    SetAtom: GlobSetAtom,
    BecomeList: GlobBecomeList,
    Insert: GlobInsert,
    Delete: GlobDelete,
    Extend: GlobExtend,
    Chord: GlobChord,
}


def note_with_global_address(note, at_address):
    """Recursively annotate a note and (all its descendants) with an address (and the relevant sub-addresses). """

    if isinstance(note, Chord):
        children = [
            note_with_global_address(child, at_address + (InScore(i),)) for
            i, child in enumerate(note.score.notes)
        ]

        return GlobChord(at_address, ChordScore(children))

    elif isinstance(note, Insert) or isinstance(note, Extend):
        child = note_with_global_address(note.child_note, at_address + (TheChild(),))
        return normal_to_glob[type(note)](at_address, note.index, child)

    # further instance-offing below is to account for unequal param-counts and param-names; hackish, I know
    elif isinstance(note, SetAtom) or isinstance(note, BecomeAtom):  # one param, named 'atom'
        return normal_to_glob[type(note)](at_address, note.atom)

    elif isinstance(note, Delete):  # one param, named 'index'
        return normal_to_glob[type(note)](at_address, note.index)

    return normal_to_glob[type(note)](at_address)


def score_with_global_address(score):
    """
    Score => SimpleScore
    i.e. turn a score into a score of notes w/ address annotations.
    """

    pmts(score, Score)

    return SimpleScore([
        note_with_global_address(note, (i,))
        for i, note in enumerate(score.notes())])


def play_simple_score(score):
    """
    This is a copy/pasted version of `play_score`, with the following differences:

    * It does not rely on or use the memoization framework (we can't, because GlobNotes are not memoizable (yet?))
    * The scores that are created in the tree are themselves SimpleScore objects.
    """

    pmts(score, SimpleScore)

    tree = None  # In the beginning, there is nothing, which we model as `None`
    for note in score.notes():
        tree = play_note(note, tree, ScoreClass=SimpleScore)

    return tree
