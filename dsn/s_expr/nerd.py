"""
The pop-culture reference here is  N*E*R*D (No-one ever really dies); in this case meaning Nothing ever really
disappears.

This is a secondary structure-construct pair for the s-expr clef; I've grouped this different structure and construct in
a single module.

Intended usage: tools to "display notes in some structural context"; for this we need some mechanism to keep track of
deletions and insertions from some point onwards.

In the present version we deal with 2 problems at once:
* Nerd, i.e. the ability to contain deleted information
* Tracking of is_inserted & is_deleted; which is required for in-context rendering.
"""

from nerdspace import sn_become, sn_insert, sn_delete, sn_replace
from utils import pmts
from list_operations import l_become, l_insert, l_replace

from dsn.s_expr.structure import SExpr, Atom
from dsn.s_expr.clef import Note, BecomeAtom, SetAtom, BecomeList, Insert, Delete, Extend, Chord
from dsn.s_expr.score import Score


# ## Utils
def plusminus(is_inserted, is_deleted):
    if is_inserted and is_deleted:
        return "±"
    if is_inserted:
        return "+"
    if is_deleted:
        return "-"
    return ""


# ## Structure
class NerdSExpr(object):
    def __init__(self, *args, **kwargs):
        raise TypeError("NerdSExpr is Abstract; use NerdList or NerdAtom instead")

    @classmethod
    def from_s_expr(cls, s_expr):
        pmts(s_expr, SExpr)

        if isinstance(s_expr, Atom):
            return NerdAtom.from_s_expr(s_expr)

        return NerdList.from_s_expr(s_expr)


class NerdAtom(NerdSExpr):

    def __init__(self, atom, versions, is_deleted, score=None):
        pmts(atom, str)
        pmts(versions, list)
        pmts(is_deleted, bool)

        self.atom = atom

        # The historic information of NERD atoms is captured in a list of "versions"
        # * for atoms that have not been changed this list is empty
        # * for atoms that have been changed, all previous values are in this list
        # * the special value None may be a first item in the list; this represents "no previous version", i.e. newness
        #
        # In practice, pretty-printing will probably rely on:
        # * len ?= 0
        # * the value of the first item

        self.versions = versions
        self.is_deleted = is_deleted
        self.score = score

    @classmethod
    def from_s_expr(cls, s_expr):
        return NerdAtom(
            s_expr.atom,
            [],
            False,
            s_expr.score)

    def __repr__(self):
        return "«" + " ".join(str(v) for v in self.versions) + "»" + plusminus(False, self.is_deleted) + self.atom

    def deleted_version(self):
        return NerdAtom(self.atom, self.versions, True, self.score)

    def restructure(self, score):
        return NerdAtom(self.atom, self.versions, self.is_deleted, score)


class NerdList(NerdSExpr):

    def __init__(self, children, n2s, s2n, is_inserted, is_deleted, score=None):
        # children are nerd-children, that is they have a type from the present module **and they need not actually be
        # alive**

        self.children = children

        self.n2s = n2s
        self.s2n = s2n

        self.is_inserted = is_inserted
        self.is_deleted = is_deleted

        self.score = score

    @classmethod
    def from_s_expr(cls, s_expr):
        return NerdList(
            [NerdSExpr.from_s_expr(child) for child in s_expr.children],
            [i for i in range(len(s_expr.children))],  # 1-to-1 mapping
            [i for i in range(len(s_expr.children))],  # 1-to-1 mapping
            False,
            False,
            s_expr.score)

    def deleted_version(self):
        return NerdList(
            self.children,
            self.n2s,
            self.s2n,
            self.is_inserted,
            True,
            # The deleted version has the same score as the non-deleted one: its deletion is external to it, i.e. it
            # happens at the parent level.
            self.score,
            )

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + "(" + " ".join(repr(c) for c in self.children) + ")"

    def restructure(self, score):
        return NerdList(
            self.children,
            self.n2s,
            self.s2n,
            self.is_inserted,
            self.is_deleted,
            score,
            )


# ## Construction
def play_note(note, structure):
    """
    Plays a single note.
    :: note, s_expr => s_expr
    """

    pmts(note, Note)

    if structure is None:
        score = Score.empty().slur(note)
    else:
        pmts(structure, NerdSExpr)
        score = structure.score.slur(note)

    if isinstance(note, Chord):
        for score_note in note.score.notes:
            structure = play_note(score_note, structure)
        return structure.restructure(score)

    if isinstance(note, BecomeAtom):
        if structure is not None:
            raise Exception("You can only BecomeAtom out of nothingness")

        return NerdAtom(note.atom, [None], False, score)

    if isinstance(note, SetAtom):
        if not isinstance(structure, NerdAtom):
            raise Exception("You can only SetAtom on an existing NerdAtom")

        return NerdAtom(note.atom, structure.versions + [structure.atom], False, score)

    if isinstance(note, BecomeList):
        if structure is not None:
            raise Exception("You can only BecomeList out of nothingness")

        n2s, s2n = sn_become()
        return NerdList(
            l_become(),
            n2s,
            s2n,
            True,
            False,
            score)

    if not isinstance(structure, NerdList):
        raise Exception("You can only %s on an existing NerdList" % type(note).__name__)

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.s2n)):  # insert _at_ len(..) is ok (a.k.a. append)
            raise Exception("Out of bounds: %s" % note.index)

        child = play_note(note.child_note, None)

        n2s, s2n, index = sn_insert(structure.n2s, structure.s2n, note.index)

        children = l_insert(structure.children, index, child)

        return NerdList(
            children,
            n2s,
            s2n,
            structure.is_inserted,
            structure.is_deleted,
            score,
            )

    if not (0 <= note.index <= len(structure.s2n) - 1):  # For Delete/Extend the check is "inside bounds"
        raise Exception("Out of bounds: %s" % note.index)

    if isinstance(note, Delete):
        n2s, s2n, index = sn_delete(structure.n2s, structure.s2n, note.index)

        children = structure.children[:]
        children[index] = children[index].deleted_version()

        return NerdList(
            children,
            n2s,
            s2n,
            structure.is_inserted,
            structure.is_deleted,
            score)

    if isinstance(note, Extend):
        n2s, s2n, index = sn_replace(structure.n2s, structure.s2n, note.index)

        child = play_note(note.child_note, structure.children[index])
        children = l_replace(structure.children, index, child)

        return NerdList(
            children,
            n2s,
            s2n,
            structure.is_inserted,
            structure.is_deleted,
            score)

    raise Exception("Unknown Note")


def play_score(m, score):
    """Constructs a NerdSExpr by playing the full score."""
    pmts(score, Score)

    tree = None  # In the beginning, there is nothing, which we model as `None`

    todo = []
    for score in score.scores():
        if score in m.construct_nerd:
            tree = m.construct_nerd[score]
            break
        todo.append(score)

    for score in reversed(todo):
        tree = play_note(score.last_note(), tree)
        m.construct_nerd[score] = tree

    return tree
