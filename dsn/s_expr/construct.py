from spacetime import st_become, st_insert, st_replace, st_delete
from utils import pmts
from list_operations import l_become, l_insert, l_delete, l_replace

from dsn.s_expr.clef import Note, BecomeAtom, SetAtom, BecomeList, Insert, Delete, Extend, Chord
from dsn.s_expr.structure import SExpr, Atom, List
from dsn.s_expr.score import Score


def play_note(note, structure, ScoreClass=Score):
    """
    Plays a single note.
    :: note, node => node
    """

    pmts(note, Note)

    if structure is None:
        score = ScoreClass.empty().slur(note)
    else:
        pmts(structure, SExpr)
        score = structure.score.slur(note)

    if isinstance(note, Chord):
        for score_note in note.score.notes:
            structure = play_note(score_note, structure, ScoreClass=ScoreClass)

        # When constructing the result of playing a Chord by consecutively playing the notes in the Chord, we get the
        # correct s_expr back; it has however been annotated by a score that consists of the individual notes rather
        # than the Chord. We return a version with the Chord-based version instead by calling `rescore`.
        return structure.rescore(score)

    if isinstance(note, BecomeAtom):
        if structure is not None:
            raise Exception("You can only BecomeAtom out of nothingness")

        return Atom(note.atom, score)

    if isinstance(note, SetAtom):
        if not isinstance(structure, Atom):
            raise Exception("You can only SetAtom on an existing Atom")

        return Atom(note.atom, score)

    if isinstance(note, BecomeList):
        if structure is not None:
            raise Exception("You can only BecomeList out of nothingness")

        t2s, s2t = st_become()
        return List(l_become(), t2s, s2t, score)

    if not isinstance(structure, List):
        raise Exception("You can only %s on an existing List" % type(note).__name__)

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # insert _at_ len(..) is ok (a.k.a. append)
            raise Exception("Out of bounds: %s" % note.index)

        child = play_note(note.child_note, None, ScoreClass=ScoreClass)
        children = l_insert(structure.children, note.index, child)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        return List(children, t2s, s2t, score)

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Extend the check is "inside bounds"
        raise Exception("Out of bounds: %s" % note.index)

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)
        return List(children, t2s, s2t, score)

    if isinstance(note, Extend):
        child = play_note(note.child_note, structure.children[note.index], ScoreClass=ScoreClass)
        children = l_replace(structure.children, note.index, child)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)
        return List(children, t2s, s2t, score)

    raise Exception("Unknown Note")


def play_score(m, score):
    """Constructs an SExpr by playing the full score."""
    pmts(score, Score)

    tree = None  # In the beginning, there is nothing, which we model as `None`

    todo = []
    for score in score.scores():
        if score in m.construct:
            tree = m.construct[score]
            break
        todo.append(score)

    for score in reversed(todo):
        tree = play_note(score.last_note(), tree)
        m.construct[score] = tree

    return tree
