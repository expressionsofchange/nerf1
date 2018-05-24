"""
Matches the interface of dsn.s_expr.score.py's Score, but:

* Without any reliance on the type of notes stored
* Without any of the optimizations (hash-based tricks) that could follow from such reliance.

This came to be like so:

dsn.s_expr.score's Score is already surrounded by questions of design (it is itself the quickest path to something that
works from nerf0).

When creating the animations I created the globally annotated notes (clef_address.py). These cannot be put in a regular
Score, because they would be deduplicated without regard to their address annotation.

I decided to just make a interface-matched version of Score which doesn't do deduplication, in an attempt to get some
results ASAP.

The alternative would have been: make Score dynamically polymorphic (part of type_factories.py's output) and make sure
that the addressed notes express all their properties (including their address) in their serialization (and thus: their
hash).
"""

from utils import pmts


class SimpleScore(object):

    def __init__(self, data):
        # data :: [Note]   (any kind of note)
        pmts(data, list)
        self._data = data

    def __len__(self):
        return len(self._data)

    @classmethod
    def empty(cls):
        return cls([])

    def slur(self, note):
        return SimpleScore(self._data + [note])

    def reversed_notes(self):
        return list(reversed(self.notes()))

    def notes(self):
        return self._data

    def last_note(self):
        return self._data[-1]

    def scores(self):
        return [SimpleScore(self._data[:i]) for i in (range(len(self._data), 0, -1))]
