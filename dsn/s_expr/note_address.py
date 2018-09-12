# ## Classes for note-addresses

from utils import pmts


class NoteAddress(object):
    """(Global) address of a Note, the path of that note in a with respect to some global root score."""

    def __init__(self, address=()):
        pmts(address, tuple)
        for part in address:
            pmts(part, NoteAddressPart)

        self.address = address

    def __eq__(self, other):
        return isinstance(other, NoteAddress) and \
            self.address == other.address

    def __hash__(self):
        return hash(self.address)

    def _repr_parts(self):
        return self.address

    def __repr__(self):
        return "(" + ", ".join(repr(p) for p in self._repr_parts()) + ")"

    def plus(self, part):
        return NoteAddress(self.address + (part,))

    def is_prefix_of(self, other):
        return self.address == other.address[:len(self.address)]


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


class SExprELS18NoteAddress(object):
    """Notes may be represented as S-Expressions, as we do in the paper that was presented at ELS18. How an individual
    so formed s-expression relates to the global address of the represented note, and which part (i.e. field) of the
    represented note it represents, can be expressed using an `SExprELS18NoteAddress`"""

    def __init__(self, note_address, note_field=None):
        self.note_address = note_address

        # the note_field may be None, when a given s-expression represents the whole Note.
        self.note_field = note_field

    def __eq__(self, other):
        return isinstance(other, SExprELS18NoteAddress) and \
            self.note_address == other.note_address and \
            self.note_field == other.note_field

    def __hash__(self):
        return hash((self.note_address, self.note_field))

    def _repr_parts(self):
        return self.note_address._repr_parts() + (() if not self.note_field else (self.note_field,))

    def __repr__(self):
        return "(" + ", ".join(repr(p) for p in self._repr_parts()) + ")"

    def with_render(self, part=None):
        return ELS18RenderingAddress(self, part)

    def is_prefix_of(self, other):
        if self.note_field is None:
            return self.note_address.is_prefix_of(other.note_address)

        if self.note_field == 'list':
            # This branch is here to deal with descending into chords' list field. The hackyness of it arises
            # from the fact that the fact that the 'list' note_field only shows up in the list-expr that is used to
            # represent that score, but not in its children. In short: (@3, 'list') is a prefix of (@3, @2)
            #
            # We also check if the other_note has a longer note_address to ensure there actually is a next part of the
            # global address to consider (i.e. guard against index out of bounds)
            #
            return (len(self.note_address.address) < len(other.note_address.address) and
                    isinstance(other.note_address.address[len(self.note_address.address) - 1 + 1], InScore))

            return self.note_address.is_prefix_of(other.note_address)

        return self.note_address == other.note_address and self.note_field == other.note_field


els18_root_address = SExprELS18NoteAddress(NoteAddress(()), None)


class ELS18RenderingAddress(object):
    """For list-expressions: open-paren or close-paren; for atoms: no further information"""

    def __init__(self, node_address, part):
        self.node_address = node_address
        self.part = part

    def __eq__(self, other):
        return isinstance(other, ELS18RenderingAddress) and \
            self.node_address == other.node_address and \
            self.part == other.part

    def __hash__(self):
        return hash((self.node_address, self.part))

    def _repr_parts(self):
        return self.node_address._repr_parts() + ([] if not self.part else [self.part])

    def __repr__(self):
        return "(" + ", ".join(self._repr_parts()) + ")"
