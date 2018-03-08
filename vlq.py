r"""
From wikipedia:
https://en.wikipedia.org/wiki/Variable-length_quantity

The encoding assumes an octet (an eight-bit byte) where the most significant bit (MSB), also commonly known as the sign
bit, is reserved to indicate whether another VLQ octet follows.

If the MSB is 0, then this is the last VLQ octet of the integer. If A is 1, then another VLQ octet follows.  B is a
7-bit number [0x00, 0x7F] and n is the position of the VLQ octet where B0 is the least significant. The VLQ octets are
arranged most significant first in a stream.


>>> interesting = [0, 1, 42, 0x7f, 0x80, 0x2000, 0x3fff, 0x4000, 1234567890]
>>> for i in interesting:
...     print("%12d: %s" % (i, to_vlq(i)))
...     assert from_vlq(iter(to_vlq(i))) == i
...
           0: b'\x00'
           1: b'\x01'
          42: b'*'
         127: b'\x7f'
         128: b'\x81\x00'
        8192: b'\xc0\x00'
       16383: b'\xff\x7f'
       16384: b'\x81\x80\x00'
  1234567890: b'\x84\xcc\xd8\x85R'

"""

from utils import pmts


def to_vlq(i):
    pmts(i, int)
    needed_bytes = 1
    result = b''

    while pow(128, needed_bytes) <= i:
        needed_bytes += 1

    mod = None
    for j in reversed(range(needed_bytes)):
        div = pow(128, j)
        result += bytes([(i % mod if mod else i) // div + (128 if j > 0 else 0)])
        mod = div

    return result


def from_vlq(bytes_stream):
    # bytes_stream is a bytes_stream of bytes, on which next(...) can be called which yields a byte
    result = 0

    while True:
        b = next(bytes_stream)

        result += (b % 128)

        if b < 128:
            return result

        result *= 128
