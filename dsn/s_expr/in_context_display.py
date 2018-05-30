"""
This module is part of the tooling to "show notes in some structural context". Which is to say: show to the user the
structural effects of playing one or more notes at t=0, t=1, t=2, ... t=n-1, given the structure at t=n-1.

Another intuition is: given some point in time ("present"), look at some preceding notes and show how those notes have
affected this "present".

We have 2 separate approaches for this, with varying amounts of information about what happened:

* render_t0 shows all notes that have affected the structure at t=n-1 as compared to t=0. That is: any note that could
be removed without changing the situation at t=n-1 is hidden. An example being: insertion inside a list that is later
deleted.

* render_most_completely shows all notes in some way; insertions without effects on the end-result are shown as both
inserted and deleted.

Note the following contrast:

* A NerdSExpr (from nerd.py) contains information (inserted, deleted) about what happened to that node in particular
* A InContextDisplay contains information on how to render a particular node's (inserted, deleted) status, including
    information that is implied by that node's context.

By the way: the name InContextDisplay is provisional (it's not very descriptive).
"""


from utils import pmts

from dsn.s_expr.nerd import NerdAtom


def plusminus(is_inserted, is_deleted):
    if is_inserted and is_deleted:
        return "±"
    if is_inserted:
        return "+"
    if is_deleted:
        return "-"
    return ""


class ICHAddress(object):
    """
    An ICHAddress uniquely identifies a rendered "non-terminal" in the ic_history's rendering of history.

    Note that "In Context History", by design, shows a part of history (note) by showing the effects the application of
    the note has on a certain structure, and by using the rendering mechanism of that structure.

    This mixing of 'construction' and 'structure' is reflected in the address of the rendered elements; each rendered
    element is denoted first by the note which it represents, and second by an address (t_address, for stability over
    time) in the tree. (further steps in the rendering chain add further details, i.e. icd_specific and render_specific)
    """

    def __init__(self, note_address=(), t_address=(), icd_specific="", render_specific=""):
        self.note_address = note_address
        self.t_address = t_address
        self.icd_specific = icd_specific
        self.render_specific = render_specific

    def plus_t(self, t_index):
        return ICHAddress(self.note_address, self.t_address + (t_index,))

    def as_icd(self, icd_specific):
        """Adds the information specific to the render_* functions, i.e. the information that is specific in the
        transformation from NerdSExpr => InContextDisplay."""
        return ICHAddress(self.note_address, self.t_address, icd_specific)

    def with_render(self, render_specific):
        """Adds the information specific to the rendering to Box[Non]Terminal, e.g. the fact that a single ICList is
        rendered as 2 parens."""
        return ICHAddress(self.note_address, self.t_address, self.icd_specific, render_specific)

    def __repr__(self):
        return repr((self.note_address, self.t_address, self.icd_specific, self.render_specific))

    def __eq__(self, other):
        return (isinstance(other, ICHAddress) and
                self.note_address == other.note_address and
                self.t_address == other.t_address and
                self.icd_specific == other.icd_specific and
                self.render_specific == other.render_specific)

    def __hash__(self):
        return hash((self.note_address, self.t_address, self.icd_specific, self.render_specific))


class InContextDisplay(object):

    def __init__(self, *args):
        raise Exception("Abstract class; use ICAtom or ICSExpr instead")


class ICAtom(InContextDisplay):

    def __init__(self, atom, is_inserted, is_deleted, address=None):
        pmts(atom, str)
        self.atom = atom
        self.is_inserted = is_inserted
        self.is_deleted = is_deleted
        self.address = address

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + self.atom


class ICList(InContextDisplay):

    def __init__(self, children, is_inserted, is_deleted, address=None):
        pmts(children, list)
        self.children = children
        self.is_inserted = is_inserted
        self.is_deleted = is_deleted
        self.address = address

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + "(" + " ".join(repr(c) for c in self.children) + ")"


def render_t0(nerd_s_expr, context_is_deleted=False, address=ICHAddress()):
    """ :: NerdSExpr => [InContextDisplay] """
    context_is_deleted = context_is_deleted or nerd_s_expr.is_deleted

    if isinstance(nerd_s_expr, NerdAtom):
        if len(nerd_s_expr.versions) == 0:  # A.K.A. "not is_inserted"
            return [ICAtom(nerd_s_expr.atom, False, context_is_deleted, address)]

        # Implied else: is_inserted == True
        if context_is_deleted:
            # In `render_t0` we completely hide insertions inside deletions; we show only the situation at t=0, which is
            # the first version (if any)
            if nerd_s_expr.versions[0] is None:
                return []

            return [ICAtom(nerd_s_expr.versions[0], False, True, address)]  # i.e. show the t=0 state as deleted.

        # Implied else: is_inserted == True, is_deleted == False:
        # show the t=0 state (if any) as deleted, t=n-1 as inserted
        if nerd_s_expr.versions[0] is None:
            return [ICAtom(nerd_s_expr.atom, True, False, address)]

        return (
            [ICAtom(nerd_s_expr.versions[0], False, True, address.as_icd('original'))] +
            [ICAtom(nerd_s_expr.atom, True, False, address.as_icd('final-version'))]
            )

    # implied else: NerdList
    if context_is_deleted and nerd_s_expr.is_inserted:
        # In `render_t0` we completely hide insertions inside deletions.
        return []

    children = []
    for index, child in enumerate(nerd_s_expr.children):
        children.extend(render_t0(child, context_is_deleted, address.plus_t(nerd_s_expr.n2t[index])))

    return [ICList(children, nerd_s_expr.is_inserted, context_is_deleted, address)]


def render_most_completely(nerd_s_expr, context_is_deleted=False, address=ICHAddress()):
    """ :: NerdSExpr => [InContextDisplay] """
    context_is_deleted = context_is_deleted or nerd_s_expr.is_deleted

    if isinstance(nerd_s_expr, NerdAtom):
        if len(nerd_s_expr.versions) == 0:  # A.K.A. "not is_inserted"
            return [ICAtom(nerd_s_expr.atom, False, context_is_deleted, address)]

        # Implied else: is_inserted == True

        # In `render_most_completely` we show all insertions, both in and out of is_deleted contexts. For atoms, this
        # means we show all previous versions (except the none-ness of new beginnings) as both deleted and inserted.
        # We also show the "present state"
        return [ICAtom(version, i > 0, True, address.plus_t(i)) for i, version in enumerate(nerd_s_expr.versions)
                if version is not None] + [ICAtom(nerd_s_expr.atom, True, context_is_deleted, address.as_icd('last'))]

    # implied else: NerdList

    # In `render_most_completely` we show all insertions, both in and out of is_deleted contexts. For lists, this
    # simply means we don't filter insertions out when in context_is_deleted.
    children = []
    for index, child in enumerate(nerd_s_expr.children):
        children.extend(render_most_completely(child, context_is_deleted, address.plus_t(nerd_s_expr.n2t[index])))

    return [ICList(children, nerd_s_expr.is_inserted, context_is_deleted, address)]
