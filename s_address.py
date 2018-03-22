"""
`node_for_s_address`:

>>> from dsn.s_expr.structure import List
>>>

In the examples below, we re-abuse the 'score' attribute for our tests
>>> node = List(children=[
...     List(children=[
...         List(children=[], score=[0, 0]),
...         List(children=[], score=[0, 1]),
...     ], score=[0]),
... ], score=[])
>>>
>>> node_for_s_address(node, []).score
[]
>>> node_for_s_address(node, [0]).score
[0]
>>> node_for_s_address(node, [0, 1]).score
[0, 1]
>>> node_for_s_address(node, [0, 1, 4]).score
Traceback (most recent call last):
IndexError: s_address out of bounds: [0, 1, 4]
>>> get_node_for_s_address(node, [0, 1, 4], 'sentinel value')
'sentinel value'

`s_dfs`:
>>> s_dfs(node, [])
[[], [0], [0, 0], [0, 1]]
"""


def node_for_s_address(node, s_address):
    result = get_node_for_s_address(node, s_address)
    if result is None:
        raise IndexError("s_address out of bounds: %s" % s_address)

    return result


def get_node_for_s_address(node, s_address, default=None):
    # `get` in analogy with {}.get(k, d), returns a default value for non-existing addresses

    if s_address == []:
        return node

    if not hasattr(node, 'children'):
        return default

    if not (0 <= s_address[0] <= len(node.children) - 1):
        return default  # Index out of bounds

    return get_node_for_s_address(node.children[s_address[0]], s_address[1:], default)


def s_dfs(node, s_address):
    """returns the depth first search of all s_addresses"""
    result = [s_address]
    if hasattr(node, 'children'):
        for i, child in enumerate(node.children):
            result.extend(s_dfs(child, s_address + [i]))

    return result


def longest_common_prefix(s_address_0, s_address_1):
    result = []
    for i0, i1 in zip(s_address_0, s_address_1):
        if i0 != i1:
            break
        result.append(i0)
    return result
