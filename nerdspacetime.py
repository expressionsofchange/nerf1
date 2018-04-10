"""
Come into being; add a first item
>>> t2s, s2t = st_become()
>>> t2s, s2t
([], [])
>>> t2s, s2t = st_insert(t2s, s2t, 0)
>>> t2s, s2t
([0], [0])

Insert at the beginning, after which s_address 0 maps to t_address 1
>>> t2s, s2t = st_insert(t2s, s2t, 0)
>>> t2s, s2t
([1, 0], [1, 0])

Delete the first item (s_address 0, t_address 1)
>>> t2s, s2t = st_delete(t2s, s2t, 0)
>>> t2s, s2t
([0, None], [0])

Insert a new (t_address: 2) item at the end (s_address: 1)
>>> t2s, s2t = st_insert(t2s, s2t, 1)
>>> t2s, s2t
([0, None, 1], [0, 2])

Delete the first item (s_address 0, t_address 0)
>>> t2s, s2t = st_delete(t2s, s2t, 0)
>>> t2s, s2t
([None, None, 0], [2])
"""


class NST(object):
    def __init__(self, s2n, t2n, asdf):
        # ordering of the arguments?
        pass

    def __repr__(self):
        return "(%s, %s, %s)" % (self.asdf, self.asdf, self.asdf)


def nst_become_out_of():
    pass


def nst_become():
    # trivial; introduced here for reasons of symmetry
    return NST([], [], asdf)


def nst_insert(prev, index):
    n_index = somehow_determined

    t2n = [(i if i is None or i < index else i + 1) for i in prev_t2s] + [index]

    s2t = prev_s2t[:]
    s2t.insert(index, len(t2s) - 1)

    return NST(something)


def nst_delete(prev, index):
    t2s = [(i if (i is None or i < index) else i - 1) for i in prev_t2s]
    t2s[prev_s2t[index]] = None

    s2t = prev_s2t[:]
    del s2t[index]

    return NST(something_else)


def nst_replace(prev, index):
    # trivial, introduced here for reasons of symmetry
    return NST(asdf)


# def sanity ...
