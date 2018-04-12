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


class InContextDisplay(object):

    def __init__(self, *args):
        raise Exception("Abstract class; use ICAtom or ICSExpr instead")


class ICAtom(InContextDisplay):

    def __init__(self, atom, is_inserted, is_deleted):
        pmts(atom, str)
        self.atom = atom
        self.is_inserted = is_inserted
        self.is_deleted = is_deleted

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + self.atom


class ICList(InContextDisplay):

    def __init__(self, children, is_inserted, is_deleted):
        pmts(children, list)
        self.children = children
        self.is_inserted = is_inserted
        self.is_deleted = is_deleted

    def __repr__(self):
        return plusminus(self.is_inserted, self.is_deleted) + "(" + " ".join(repr(c) for c in self.children) + ")"


def render_t0(nerd_s_expr, context_is_deleted=False):
    """ :: NerdSExpr => [InContextDisplay] """
    context_is_deleted = context_is_deleted or nerd_s_expr.is_deleted

    if isinstance(nerd_s_expr, NerdAtom):
        if len(nerd_s_expr.versions) == 0:  # A.K.A. "not is_inserted"
            return [ICAtom(nerd_s_expr.atom, False, context_is_deleted)]

        # Implied else: is_inserted == True
        if context_is_deleted:
            # In `render_t0` we completely hide insertions inside deletions; we show only the situation at t=0, which is
            # the first version (if any)
            if nerd_s_expr.versions[0] is None:
                return []

            return [ICAtom(nerd_s_expr.versions[0], False, True)]  # i.e. show the t=0 state as deleted.

        # Implied else: is_inserted == True, is_deleted == False:
        # show the t=0 state (if any) as deleted, t=n-1 as inserted
        if nerd_s_expr.versions[0] is None:
            return [ICAtom(nerd_s_expr.atom, True, False)]
        return [ICAtom(nerd_s_expr.versions[0], False, True)] + [ICAtom(nerd_s_expr.atom, True, False)]

    # implied else: NerdList
    if context_is_deleted and nerd_s_expr.is_inserted:
        # In `render_t0` we completely hide insertions inside deletions.
        return []

    children = []
    for child in nerd_s_expr.children:
        children.extend(render_t0(child, context_is_deleted))

    return [ICList(children, nerd_s_expr.is_inserted, context_is_deleted)]


def render_most_completely(nerd_s_expr, context_is_deleted=False):
    """ :: NerdSExpr => [InContextDisplay] """
    context_is_deleted = context_is_deleted or nerd_s_expr.is_deleted

    if isinstance(nerd_s_expr, NerdAtom):
        if len(nerd_s_expr.versions) == 0:  # A.K.A. "not is_inserted"
            return [ICAtom(nerd_s_expr.atom, False, context_is_deleted)]

        # Implied else: is_inserted == True

        # In `render_most_completely` we show all insertions, both in and out of is_deleted contexts. For atoms, this
        # means we show all previous versions (except the none-ness of new beginnings) as both deleted and inserted.
        # We also show the "present state"
        return [ICAtom(version, i > 0, True) for i, version in enumerate(nerd_s_expr.versions)
                if version is not None] + [ICAtom(nerd_s_expr.atom, True, context_is_deleted)]

    # implied else: NerdList

    # In `render_most_completely` we show all insertions, both in and out of is_deleted contexts. For lists, this
    # simply means we don't filter insertions out when in context_is_deleted.
    children = []
    for child in nerd_s_expr.children:
        children.extend(render_most_completely(child, context_is_deleted))

    return [ICList(children, nerd_s_expr.is_inserted, context_is_deleted)]