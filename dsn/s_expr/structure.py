from utils import pmts


class SExpr(object):
    def __init__(self, *args, **kwargs):
        raise TypeError("SExpr is Abstract; use List or Atom instead")


class Atom(SExpr):

    def __init__(self, atom, score=None):
        pmts(atom, str)
        self.atom = atom
        self.score = score

    def __repr__(self):
        return pp_flat(self)

    def restructure(self, score):
        return Atom(self.atom, score)


class List(SExpr):

    def __init__(self, children, t2s=None, s2t=None, score=None):
        for i, child in enumerate(children):
            pmts(child, SExpr, "child: %s" % i)

        self.children = children
        self.t2s = t2s
        self.s2t = s2t
        self.score = score

    def __repr__(self):
        return pp_flat(self)

    def restructure(self, score):
        return List(self.children, self.t2s, self.s2t, score)


def pp_flat(node):
    if isinstance(node, Atom):
        return node.atom
    return "(" + " ".join(pp_flat(c) for c in node.children) + ")"


def play_note(note, structure):
    """
    Plays a single note.
    :: note, node => node
    """

    pmts(note, Note)

    if structure is None:
        score = Score.empty().slur(note)
    else:
        pmts(structure, SExpr)
        score = structure.score.slur(note)

    if isinstance(note, Chord):
        for score_note in note.score.notes:
            structure = play_note(score_note, structure)
        return structure.restructure(score)

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

        child = play_note(note.child_note, None)
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
        child = play_note(note.child_note, structure.children[note.index])
        children = l_replace(structure.children, note.index, child)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)
        return List(children, t2s, s2t, score)

    raise Exception("Unknown Note")


def play_score(m, score):
    """Constructs a TreeNode by playing the full score."""
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
