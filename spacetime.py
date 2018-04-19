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


def st_sanity(t2s, s2t):
    for (t, s) in enumerate(t2s):
        assert s is None or (0 <= s <= len(s2t) - 1 and s2t[s] == t), "%s <X> %s" % (s2t, t2s)

    for (s, t) in enumerate(s2t):
        assert 0 <= t <= len(t2s) - 1 and t2s[t] == s, "%s <X> %s" % (s2t, t2s)


def st_become():
    # trivial; introduced here for reasons of symmetry
    return [], []


def st_insert(prev_t2s, prev_s2t, index):
    t2s = [(i if i is None or i < index else i + 1) for i in prev_t2s] + [index]
    s2t = prev_s2t[:]
    s2t.insert(index, len(t2s) - 1)
    return t2s, s2t


def st_delete(prev_t2s, prev_s2t, index):
    t2s = [(i if (i is None or i < index) else i - 1) for i in prev_t2s]
    t2s[prev_s2t[index]] = None

    s2t = prev_s2t[:]
    del s2t[index]
    return t2s, s2t


def st_replace(prev_t2s, prev_s2t, index):
    # trivial, introduced here for reasons of symmetry
    return prev_t2s[:], prev_s2t[:]


def t_address_for_s_address(node, s_address):
    t_address = _best_lookup(node, lookup_s, lambda s, t: t, s_address)
    if len(t_address) != len(s_address):
        raise IndexError("s_address out of bounds: %s" % s_address)

    return t_address


def get_s_address_for_t_address(node, t_address):
    s_address = best_s_address_for_t_address(node, t_address)
    if len(s_address) != len(t_address):
        return None

    return s_address


def best_s_address_for_t_address(node, t_address):
    return _best_lookup(node, lookup_t, lambda s, t: s, t_address)


def lookup_s(node, s_index):
    if not (0 <= s_index <= len(node.s2t) - 1):
        return None, None  # Index out of bounds

    t_index = node.s2t[s_index]
    return s_index, t_index


def lookup_t(node, t_index):
    if not (0 <= t_index <= len(node.t2s) - 1):
        return None, None  # Index out of bounds

    s_index = node.t2s[t_index]
    return s_index, t_index  # s_index may be None (if it's removed in space)


def _best_lookup(node, do_lookup, collect, lookup_value, _collected=None):
    """Looks up an x_address (the `lookup_value`) using the function `do_lookup` and collecting using `collect`;
    We return the longest matched prefix that we can find."""
    if _collected is None:
        _collected = []

    if (lookup_value == []) or (not hasattr(node, 'children')):  # Done, or no way to proceed.
        return _collected

    s_index, t_index = do_lookup(node, lookup_value[0])
    if s_index is None:
        return _collected

    _collected += [collect(s_index, t_index)]

    child = node.children[s_index]
    return _best_lookup(child, do_lookup, collect, lookup_value[1:], _collected)


def best_stable_s_over_time(tree_0, s_address, tree_1):
    t_address = t_address_for_s_address(tree_0, s_address)
    return best_s_address_for_t_address(tree_1, t_address)


def get_stable_s_over_time(tree_0, s_address, tree_1):
    t_address = t_address_for_s_address(tree_0, s_address)
    return get_s_address_for_t_address(tree_1, t_address)
