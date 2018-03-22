from dsn.s_expr.legato import NoteCapo, NoteSlur, NoteNoutHash

PMM = "I understand that this is protected"


class Score(object):
    """
    An immutable list (singly linked, backwards in time) of notes.
    NB we have 2 (different) Scores; the present one, and simply a list (not necessarily to the beginning of time) of
    some notes, which is defined in dsn/s_expr/clef.py. To be resolved at some point.

    This class was created while "scavenging" nerf0 for parts; it is the quickest way I could think of to get from nerf0
    to "something on screen". The alternative being: less reliance on hashes & nouts, just backlinking directly.

    The idea is: let's do a bit more encapsulation of all this Hashing/Nouts business, to recover some sanity. In nerf0
    all that stuff was the (programmer) interface. This was the most obvious in the fact that Insert & Replace are
    expressed in terms of such hashes directly.

    In nerf1 we don't express the notes directly in terms of hashes and Nouts. Which enables us to push them out of
    view. Still, there are at least some reasons to keep them around in the background.

    First, the prevalence of reliance on hasshes in nerf0 makes it so that keeping them aroun at least somewhere allows
    for a "quickest path to a visual".

    Second, Hashes make for an easy implementation of deduplication/uniqueness guarantee, and for cheap lookups (i.e.
    when using the score as a key in a memoization table).

    TODO: The uniqueness guarantee is currently implemented using "cache everything forever"; if the present solution
    ever makes it to some kind of "production editor" we should rethink this, i.e. use the appropriate dict from
    `weakref` (and think through and test whether this actually means unused lists will be collected)
    """

    glob = {}

    def __init__(self, nout, hash_, len_, poor_mans_protected):
        if poor_mans_protected != PMM:
            raise Exception("Instantiate NoteList using empty() or slur(note) rather than directly.")

        self.__nout = nout
        self.__hash = hash_
        self.__len = len_

    def __hash__(self):
        return hash(self.__hash)

    def __eq__(self, other):
        return self.__hash == other.__hash

    def __repr__(self):
        return "(" + " ".join(repr(n) for n in self.notes()) + ")"

    def __len__(self):
        return self.__len

    @classmethod
    def unique(cls, nout, len_):
        hash_ = NoteNoutHash.for_object(nout)

        if hash_ not in cls.glob:
            insert_this = cls(nout, hash_, len_, PMM)
            cls.glob[hash_] = insert_this

        return cls.glob[hash_]

    @classmethod
    def empty(cls):
        return cls.unique(NoteCapo(), 0)

    def slur(self, note):
        return self.unique(NoteSlur(note, self.__hash), self.__len + 1)

    def reversed_notes(self):
        return (score.__nout.note for score in self.scores())

    def notes(self):
        return reversed(list(self.reversed_notes()))

    def last_note(self):
        return self.__nout.note

    def scores(self):
        score = self
        while True:
            nout = score.__nout
            nout_hash = score.__hash
            if score.__nout == NoteCapo():
                return

            yield score
            nout_hash = nout.previous_hash
            score = self.glob[nout_hash]
