def pmts(v, type_, extra_information=""):
    """Poor man's type system"""
    assert isinstance(v, type_), "Expected value of type '%s' but is type '%s'%s" % (
        type_.__name__,
        type(v).__name__,
        "" if not extra_information else "; %s" % extra_information
        )


def rfs(byte_stream, n):
    # read n bytes from stream
    return bytes((next(byte_stream) for i in range(n)))
