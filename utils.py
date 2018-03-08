def pmts(v, type_):
    """Poor man's type system"""
    assert isinstance(v, type_), "Expected value of type '%s' but is type '%s'" % (type_.__name__, type(v).__name__)


def rfs(byte_stream, n):
    # read n bytes from stream
    return bytes((next(byte_stream) for i in range(n)))
