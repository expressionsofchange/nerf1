"""
Intended usage: tools to "display notes in some structural context"; for this we need some mechanism to keep track of
deletions and insertions from some point onwards.

The pop-culture reference here is  N*E*R*D (No-one ever really dies); in this case meaning Nothing ever really
disappears.

This is a secondary structure-construct pair for the s-expr clef; I've grouped this different structure and construct in
a single module.

In the present version we deal with 2 problems at once:
* Nerd, i.e. the ability to contain deleted information
* Tracking of is_inserted & is_deleted; which is required for in-context rendering.
"""

from nerdspace import sn_become, sn_insert, sn_delete, sn_replace
from utils import pmts
from list_operations import l_become, l_insert, l_replace
from spacetime import st_insert

from dsn.s_expr.structure import SExpr, Atom
from dsn.s_expr.clef import Note, BecomeAtom, SetAtom, BecomeList, Insert, Delete, Extend, Chord
from dsn.s_expr.score import Score
from spacetime import _best_lookup
from s_address import node_for_s_address


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
        if s_expr is None:
            # TODO really the best place for this?
            return None

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

    def __init__(self, children, n2s, s2n, n2t, t2n, is_inserted, is_deleted, score=None):
        """
        children are of type NerdSExpr, which also implies: need not actually be alive.

        We have the following 3 address spaces, and mappings between them:

        * s[pace]: the position of the child in the list of children when deleted children are ignored. That is: the
            position if the parent would not have been not a NerdSExpr.
        * n[erd]: the position of the child in self.children, i.e. assigning such numbers to deleted children.
        * t[ime]: a sequencenumber expressing the order-of-creation
        """
        self.children = children

        self.n2s = n2s
        self.s2n = s2n
        self.n2t = n2t
        self.t2n = t2n

        assert len(n2t) == len(n2s)

        self.is_inserted = is_inserted
        self.is_deleted = is_deleted

        self.score = score

    @classmethod
    def from_s_expr(cls, s_expr):
        # At creation from a normal s-expression, N and S are the same because no deleted children exist in non-deleted
        # form: the mapping between them is 1 to 1
        # Because N = S, we can assign s2t to n2t and t2s to t2n

        return NerdList(
            children        = [NerdSExpr.from_s_expr(child) for child in s_expr.children],
            n2s             = [i for i in range(len(s_expr.children))],
            s2n             = [i for i in range(len(s_expr.children))],
            n2t             = s_expr.s2t,
            t2n             = s_expr.t2s,
            is_inserted     = False,
            is_deleted      = False,
            score           = s_expr.score)

    def deleted_version(self):
        return NerdList(
            children        = self.children,
            n2s             = self.n2s,
            s2n             = self.s2n,
            n2t             = self.n2t,
            t2n             = self.t2n,
            is_inserted     = self.is_inserted,
            is_deleted      = True,

            # The deleted version has the same score as the non-deleted one: its deletion is external to it, i.e. it
            # happens at the parent level.
            score           = self.score,
            )

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + "(" + " ".join(repr(c) for c in self.children) + ")"

    def restructure(self, score):
        return NerdList(
            children        = self.children,
            n2s             = self.n2s,
            s2n             = self.s2n,
            n2t             = self.n2t,
            t2n             = self.t2n,
            is_inserted     = self.is_inserted,
            is_deleted      = self.is_deleted,
            score           = score,
            )


# ## Construction
def play_note(note, structure, ScoreClass=Score):
    """
    Plays a single note.
    :: note, s_expr => s_expr
    """

    pmts(note, Note)

    if structure is None:
        score = ScoreClass.empty().slur(note)
    else:
        pmts(structure, NerdSExpr)
        score = structure.score.slur(note)

    if isinstance(note, Chord):
        for score_note in note.score.notes:
            structure = play_note(score_note, structure, ScoreClass)
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
            children        = l_become(),
            n2s             = n2s,
            s2n             = s2n,
            n2t             = [],
            t2n             = [],
            is_inserted     = True,
            is_deleted      = False,
            score           = score
            )

    if not isinstance(structure, NerdList):
        raise Exception("You can only %s on an existing NerdList" % type(note).__name__)

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.s2n)):  # insert _at_ len(..) is ok (a.k.a. append)
            raise Exception("Out of bounds: %s" % note.index)

        child = play_note(note.child_note, None, ScoreClass)

        n2s, s2n, index = sn_insert(structure.n2s, structure.s2n, note.index)
        t2n, n2t = st_insert(structure.t2n, structure.n2t, index)

        children = l_insert(structure.children, index, child)

        return NerdList(
            children        = children,
            n2s             = n2s,
            s2n             = s2n,
            n2t             = n2t,
            t2n             = t2n,
            is_inserted     = structure.is_inserted,
            is_deleted      = structure.is_deleted,
            score           = score,
            )

    if not (0 <= note.index <= len(structure.s2n) - 1):  # For Delete/Extend the check is "inside bounds"
        raise Exception("Out of bounds: %s" % note.index)

    if isinstance(note, Delete):
        n2s, s2n, index = sn_delete(structure.n2s, structure.s2n, note.index)

        children = structure.children[:]
        children[index] = children[index].deleted_version()

        return NerdList(
            children        = children,
            n2s             = n2s,
            s2n             = s2n,
            n2t             = structure.n2t,
            t2n             = structure.t2n,
            is_inserted     = structure.is_inserted,
            is_deleted      = structure.is_deleted,
            score           = score
            )

    if isinstance(note, Extend):
        n2s, s2n, index = sn_replace(structure.n2s, structure.s2n, note.index)

        child = play_note(note.child_note, structure.children[index], ScoreClass)
        children = l_replace(structure.children, index, child)

        return NerdList(
            children        = children,
            n2s             = n2s,
            s2n             = s2n,
            n2t             = structure.n2t,
            t2n             = structure.t2n,
            is_inserted     = structure.is_inserted,
            is_deleted      = structure.is_deleted,
            score           = score
            )

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


# (NERD)SPACETIME STUFF.
# Copy/pasted from the analogous (non-n) locations elsewhere; factoring out commonalities might come later.


def get_n_address_for_t_address(node, t_address):
    # Copied from spacetime.py's get_s_address_for_t_address; substituting n for s.

    n_address = best_n_address_for_t_address(node, t_address)
    if len(n_address) != len(t_address):
        return None

    return n_address


def lookup_n_by_t(node, t_index):
    if not (0 <= t_index <= len(node.t2n) - 1):
        return None, None  # Index out of bounds

    n_index = node.t2n[t_index]
    return n_index, n_index  # n is used both for descending into children and as the thing of interest


def best_n_address_for_t_address(node, t_address):
    # Copied from spacetime.py's get_s_address_for_t_address; substituting n for s.
    return _best_lookup(node, lookup_n_by_t, t_address)


def node_for_n_address(node, n_address):
    # we "reuse" (abuse) the fact that node_for_s_address for normal nodes corresponds precisely with
    # node_for_n_address for Nerd nodes. This is because of ducktyping, and the fact that s- and n-addresses
    # both correspond to "index into children" for the respective kinds of nodes (SExpr and NerdSExpr)
    return node_for_s_address(node, n_address)
