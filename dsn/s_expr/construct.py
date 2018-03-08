from utils import pmts
from list_operations import l_become, l_insert, l_delete, l_replace  # WHY?

from dsn.s_expr.clef import Note, BecomeAtom, SetAtom, BecomeList, Insert, Delete, Extend, Chord
from dsn.s_expr.structure import SExpr, Atom, List


def play_note(note, structure):
    """
    Plays a single note.
    :: note, node => node
    """

    pmts(note, Note)

    if structure is not None:
        pmts(structure, SExpr)

    if isinstance(note, Chord):
        for score_note in note.score.notes:
            structure = play_note(score_note, structure)
        return structure

    if isinstance(note, BecomeAtom):
        if structure is not None:
            raise Exception("You can only BecomeAtom out of nothingness")

        return Atom(note.atom)

    if isinstance(note, SetAtom):
        if not isinstance(structure, Atom):
            raise Exception("You can only SetAtom on an existing Atom")

        return Atom(note.atom)

    if isinstance(note, BecomeList):
        if structure is not None:
            raise Exception("You can only BecomeList out of nothingness")

        return List(l_become())

    if not isinstance(structure, List):
        raise Exception("You can only %s on an existing List" % type(note).__name__)

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # insert _at_ len(..) is ok (a.k.a. append)
            raise Exception("Out of bounds: %s" % note.index)

        child = play_note(note.child_note, None)
        children = l_insert(structure.children, note.index, child)

        return List(children)

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Extend the check is "inside bounds"
        raise Exception("Out of bounds: %s" % note.index)

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        return List(children)

    if isinstance(note, Extend):
        child = play_note(note.child_note, structure.children[note.index])
        children = l_replace(structure.children, note.index, child)

        return List(children)

    raise Exception("Unknown Note")
