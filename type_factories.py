from binascii import hexlify
from hashlib import sha256

from utils import pmts, rfs

bytes_iterator = type(iter(bytes()))

NOUT_CAPO = 0
NOUT_SLUR = 1


def hash_factory(clazz, name_prefix):

    class HashPrototype(object):
        def __init__(self, hash_bytes):
            pmts(hash_bytes, bytes)

            # i.e. if you want to construct a hash _for_ a bunch of bytes, use 'for_bytes'
            assert len(hash_bytes) == 32, "Direct construction of Hash objects takes a 32-byte hash"

            self.hash_bytes = hash_bytes

        def __repr__(self):
            return str(hexlify(self.hash_bytes)[:12], 'utf-8')

        def as_bytes(self):
            return self.hash_bytes

        @staticmethod
        def for_object(serializable):
            pmts(serializable, clazz)
            bytes_ = serializable.as_bytes()
            return Hash._for_bytes(bytes_)

        @staticmethod
        def _for_bytes(bytes_):
            pmts(bytes_, bytes)
            hash_ = sha256(bytes_).digest()
            return Hash(hash_)

        @staticmethod
        def from_stream(byte_stream):
            """_reads_ (i.e. picks exactly 32 chars) from the stream"""
            pmts(byte_stream, bytes_iterator)
            return Hash(rfs(byte_stream, 32))

        def __hash__(self):
            # Based on the following understanding:
            # * AFAIK, Python's hash function works w/ 64-bit ints; hence I take 8 bytes
            # * byteorder was picked arbitrarily
            return int.from_bytes(self.hash_bytes[:8], byteorder='big')

        def __eq__(self, other):
            if not isinstance(other, Hash):
                return False
            return self.hash_bytes == other.hash_bytes

    Hash = type(name_prefix + "Hash", (object,), dict(HashPrototype.__dict__))
    return Hash


def nout_factory(NoteClass, name_prefix):
    """nout_factory is some implementation of "Generic Types" (albeit as dynamic types), i.e. allows us to create the 3
    Nout classes for a given type of "payload" (note).

    The 3 classes are: `Nout` (abstract base class), `Capo` & `Slur`. They form a small class hierarchy with each
    other, but are unrelated to other types of Nout. This is intentional.
    """

    class NoutPrototype(object):
        def __init__(self, *args, **kwargs):
            raise TypeError("%s is Abstract; use %s or %s instead" % (Nout.__name__, Capo.__name__, Slur.__name__))

        @staticmethod
        def from_stream(byte_stream):
            byte0 = next(byte_stream)
            return {
                NOUT_CAPO: Capo,
                NOUT_SLUR: Slur,
            }[byte0].from_stream(byte_stream)

    class CapoPrototype(object):
        def __init__(self):
            pass

        def __repr__(self):
            return "(CAPO)"

        def as_bytes(self):
            return bytes([NOUT_CAPO])

        @staticmethod
        def from_stream(byte_stream):
            return Capo()

        def __eq__(self, other):
            return isinstance(other, Capo)

    class SlurPrototype(object):
        def __init__(self, note, previous_hash):
            pmts(note, NoteClass)
            pmts(previous_hash, Hash)

            self.note = note
            self.previous_hash = previous_hash

        def __repr__(self):
            return "(SLUR " + repr(self.note) + " -> " + repr(self.previous_hash) + ")"

        def as_bytes(self):
            return bytes([NOUT_SLUR]) + self.note.as_bytes() + self.previous_hash.as_bytes()

        @staticmethod
        def from_stream(byte_stream):
            return Slur(NoteClass.from_stream(byte_stream), Hash.from_stream(byte_stream))

    # Construct a small hierarchy with "readable names" (names that don't betray that the classes are created inside a
    # method). N.B.: The unqualified names `Nout`, `Capo` and `Slur` are local to this method, after returning the fully
    # qualified name (including the prefix) is used.
    Nout = type(name_prefix + "Nout", (object,), dict(NoutPrototype.__dict__))
    Capo = type(name_prefix + "Capo", (Nout,), dict(CapoPrototype.__dict__))
    Slur = type(name_prefix + "Slur", (Nout,), dict(SlurPrototype.__dict__))

    Hash = hash_factory(Nout, name_prefix + "Nout")

    return Nout, Capo, Slur, Hash
