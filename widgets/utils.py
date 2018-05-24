from utils import pmts

from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate
from contextlib import contextmanager
from collections import namedtuple

from annotated_tree import annotated_node_factory


X = 0
Y = 1

OffsetBox = namedtuple('OffsetBox', ('offset', 'item'))


def no_offset(item):
    return OffsetBox(Offset(0, 0), item)


class Offset(object):
    def __init__(self, x, y, alpha=1):
        self.x = x
        self.y = y
        self.alpha = alpha

    def __getitem__(self, item):
        # HACK for translation from tuple
        if item == 0:
            return self.x
        if item == 1:
            return self.y
        raise KeyError("or something %s" % item)

    def __iter__(self):
        # HACK for translation from tuple
        return iter([self.x, self.y])

    def __repr__(self):
        return repr((self.x, self.y, self.alpha))


class BoxTerminal(object):
    def __init__(self, instructions, outer_dimensions, address=None):
        self.instructions = instructions
        self.outer_dimensions = outer_dimensions
        self.address = address


class BoxNonTerminal(object):
    def __init__(self, offset_nonterminals, offset_terminals):
        """The idea here is: draw tree-like structures using 'boxes', rectangular shapes that may contain other such
        shapes. Some details:

        * The direction of drawing is from top left to bottom right. Children may have (X, Y) offsets of respectively
            postive (including 0), and negative (including 0) values.

        * The current box may have some child-boxes

        * There outer_dimensions of represent the smallest box that can be drawn around this entire node. This is useful
            to quickly decide whether the current box needs to be considered at all in e.g. collision checks.
        """
        pmts(offset_nonterminals, list)  # not checked: list of what?
        pmts(offset_terminals, list)  # not checked: list of what?

        self.offset_nonterminals = offset_nonterminals
        self.offset_terminals = offset_terminals

        self.outer_dimensions = self.calc_outer_dimensions()

    def calc_outer_dimensions(self):
        max_x = max([0] + [(obs.offset[X] + obs.item.outer_dimensions[X])
                    for obs in self.offset_terminals + self.offset_nonterminals])

        # min_y, because we're moving _down_ which is negative in Kivy's coordinate system
        min_y = min([0] + [(obs.offset[Y] + obs.item.outer_dimensions[Y])
                    for obs in self.offset_terminals + self.offset_nonterminals])

        return (max_x, min_y)

    def get_all_terminals(self):
        def k(ob):
            return ob.offset[Y] * -1, ob.offset[X]

        result = self.offset_terminals[:]
        for ((offset_x, offset_y), nt) in self.offset_nonterminals:
            for ((recursive_offset_x, recursive_offset_y), t) in nt.get_all_terminals():
                result.append(OffsetBox((offset_x + recursive_offset_x, offset_y + recursive_offset_y), t))

        # sorting here is a bit of a hack. We need it to be able to access the "last added item" while throwing
        # terminals and non-terminals on a single big pile during construction time. Better solution: simply remember in
        # which order items were constructed in the first place.
        return sorted(result, key=k)


def bring_into_offset(offset, point):
    """The _inverse_ of applying to offset on the point"""
    return point[X] - offset[X], point[Y] - offset[Y]


@contextmanager
def apply_offset(canvas, offset):
    canvas.add(PushMatrix())
    canvas.add(Translate(int(offset[X]), int(offset[Y])))
    yield
    canvas.add(PopMatrix())


SAddress = list  # the most basic expression of an SAddress' type; we can do something more powerful if needed

SAddressAnnotatedBoxNonTerminal = annotated_node_factory('SAddressAnnotatedBoxNonTerminal', BoxNonTerminal, SAddress)


def annotate_boxes_with_s_addresses(nt, path):
    children = [
        annotate_boxes_with_s_addresses(offset_box.item, path + [i])
        for (i, offset_box) in enumerate(nt.offset_nonterminals)]

    return SAddressAnnotatedBoxNonTerminal(
        underlying_node=nt,
        annotation=path,
        children=children
    )


def from_point(nt_with_s_address, point):
    """X & Y in the reference frame of `nt_with_s_address`"""

    nt = nt_with_s_address.underlying_node

    # If any of our terminals matches, we match
    for o, t in nt.offset_terminals:
        if (point[X] >= o[X] and point[X] <= o[X] + t.outer_dimensions[X] and
                point[Y] <= o[Y] and point[Y] >= o[Y] + t.outer_dimensions[Y]):

            return nt_with_s_address

    # Otherwise, recursively check our children
    for child_with_s_address, (o, nt) in zip(nt_with_s_address.children, nt.offset_nonterminals):
        if (point[X] >= o[X] and point[X] <= o[X] + nt.outer_dimensions[X] and
                point[Y] <= o[Y] and point[Y] >= o[Y] + nt.outer_dimensions[Y]):

            # it's within the outer bounds, and _might_ be a hit. recurse to check:
            result = from_point(child_with_s_address, bring_into_offset(o, point))
            if result is not None:
                return result

    return None


def cursor_dimensions(annotated_box_structure, s_address, y_offset=0):
    """given a box_structure and a s_address to lookup return the looked up items' y_offset & height.
    This function is used in the context of "following the cursor".

    This is a bit of a kludge as it stands; I don't want to clean it up now though, because we're likely to rewrite the
    drawing of cursors at some point in the future (i.e.: have the cursors be a separate layer), at which point we can
    use that new functionality

    (One observation about the kludgy nature of the present solution: we already know where the cursor is at the moment
    of drawing; but we re-lookup that information at the present point).

    Furhter ad hoc solutions are documented below.
    """

    if s_address == []:
        # The cursor's height is (as of yet) just returned as a constant. Another attempt at a solution is commented
        # out. It's wrong, because it returns the height of the whole subtree under consideration, rather than the
        # height of the higlighted element.
        # How this plays out in e.g. a lispy layout, I'm not sure yet (we may have to tie in the solution with the idea
        # that in such a layout we visit the nodes twice (once for the opening bracket, once for the closing bracket)).
        return y_offset, -40
        # return y_offset, annotated_box_structure.underlying_node.outer_dimensions

    o, nt = annotated_box_structure.underlying_node.offset_nonterminals[s_address[0]]
    child = annotated_box_structure.children[s_address[0]]

    return cursor_dimensions(child, s_address[1:], y_offset + o[Y])


def flatten_nt_to_dict(nt, offset):
    """Takes a BoxNonTerminal tree-structure with address-annotated BoxTerminals, flattens this to a dict of
    BoxTerminals keyed by those addresses, and with the offsets corrected for the flattening."""

    def add_offsets(o1, o2):
        return Offset(o1[X] + o2[X], o1[Y] + o2[Y])

    pmts(nt, BoxNonTerminal)
    result = {}

    for o, t in nt.offset_terminals:
        result[t.address] = OffsetBox(add_offsets(o, offset), t)

    for o, nt in nt.offset_nonterminals:
        subresult = flatten_nt_to_dict(nt, add_offsets(o, offset))
        result.update(subresult)

    return result
