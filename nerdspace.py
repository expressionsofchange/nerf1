"""
Some tools for dealing with "nerdspace", space in which "no-one ever really dies", i.e. there are no deletions.

(Almost) all functions have the signature: prev_n2s, prev_s2n, index -> n2s, s2n, index_in_n

The expected usage is that there is a datastructure, which has the actual data and tombstones for deletions, and which
is to be manipulated using the equivalent manipulations at the returned index_in_n.

Insertion is the most interesting case: Insertions is expressed in terms of an index in _space_, but we want to apply
this on the "nerdspace" (which may have multiple reasonable candidates for an equivalent). A reasonable minimum demand
for what constitutes a correct insertion would be: the order of the live part of nerdspace after insertion must be the
same as the ordering of space.

Which is to say: the insertion in nerdspace should take place between the same 2 live neighbors as in space (where
neighbours may be: beginning and end of list).

How to order with respect to tombstones is then the part of the question to which we may come up with multiple answers.

The 2 answers that are implemented in the below are: insert left of any tombstone, insert right of any tombstone, i.e.
the minimal and maximal allowed indices in nerdspace.

Become
>>> example_usage_data = []
>>> n2s, s2n = sn_become()
>>> n2s, s2n
([], [])

Insert the first item
>>> n2s, s2n, i = sn_insert_left(n2s, s2n, 0)
>>> n2s, s2n, i
([0], [0], 0)
>>> example_usage_data.insert(i, 'a')
>>> example_usage_data
['a']

Delete the first item:
>>> n2s, s2n, i = sn_delete(n2s, s2n, 0)
>>> n2s, s2n, i
([None], [], 0)
>>> example_usage_data[i] = 'NONE'
>>> example_usage_data
['NONE']

Insert a new first item (leftmost possible place); tests branch "left-insert at head"
>>> n2s, s2n, i = sn_insert_left(n2s, s2n, 0)
>>> n2s, s2n, i
([0, None], [0], 0)
>>> example_usage_data.insert(i, 'b')
>>> example_usage_data
['b', 'NONE']

tests branch "right-insert at non-last"
>>> n2s, s2n, i = sn_insert_right(n2s, s2n, 1)
>>> n2s, s2n, i
([0, None, 1], [0, 2], 2)
>>> example_usage_data.insert(i, 'c')
>>> example_usage_data
['b', 'NONE', 'c']

tests branch "left-insert elsewhere"
>>> n2s, s2n, i = sn_insert_left(n2s, s2n, 1)
>>> n2s, s2n, i
([0, 1, None, 2], [0, 1, 3], 1)
>>> example_usage_data.insert(i, 'd')
>>> example_usage_data
['b', 'd', 'NONE', 'c']

tests branch "right-insert as append"
>>> n2s, s2n, i = sn_insert_right(n2s, s2n, 3)
>>> n2s, s2n, i
([0, 1, None, 2, 3], [0, 1, 3, 4], 4)
>>> example_usage_data.insert(i, 'e')
>>> example_usage_data
['b', 'd', 'NONE', 'c', 'e']

>>> sn_sanity(n2s, s2n)

Test deletion on non-trivial data
>>> n2s, s2n, i = sn_delete(n2s, s2n, 0)
>>> n2s, s2n, i
([None, 0, None, 1, 2], [1, 3, 4], 0)
>>> example_usage_data[i] = 'NONE'
>>> example_usage_data
['NONE', 'd', 'NONE', 'c', 'e']

Deletion in the middle
>>> n2s, s2n, i = sn_delete(n2s, s2n, 1)
>>> n2s, s2n, i
([None, 0, None, None, 1], [1, 4], 3)
>>> example_usage_data[i] = 'NONE'
>>> example_usage_data
['NONE', 'd', 'NONE', 'NONE', 'e']

>>> sn_sanity(n2s, s2n)
"""


def sn_sanity(n2s, s2n):
    for (n, s) in enumerate(n2s):
        assert s is None or (0 <= s <= len(s2n) - 1 and s2n[s] == n), "%s <X> %s" % (s2n, n2s)

    for (s, n) in enumerate(s2n):
        assert 0 <= n <= len(n2s) - 1 and n2s[n] == s, "%s <X> %s" % (s2n, n2s)


def sn_become():
    # trivial; introduced here for reasons of symmetry
    return [], []


def sn_insert_left(prev_n2s, prev_s2n, index):
    if index == 0:
        # no left-neighbor lookup required or possible; just insert at the beginning.
        index_in_n = 0

    else:
        # look up the left neighbor in nerdspace, insert just right of it.
        left_neighbor = index - 1
        left_neighbor_in_n = prev_s2n[left_neighbor]
        index_in_n = left_neighbor_in_n + 1

    n2s = _shift_some(prev_n2s, index, 1)
    n2s.insert(index_in_n, index)

    s2n = _shift_some(prev_s2n, index_in_n, 1)
    s2n.insert(index, index_in_n)

    return n2s, s2n, index_in_n


def sn_insert_right(prev_n2s, prev_s2n, index):
    if index == len(prev_s2n):
        # no index-lookup required or possible; just insert at the end (a.k.a. append)
        index_in_n = len(prev_n2s)

    else:
        index_in_n = prev_s2n[index]

    n2s = _shift_some(prev_n2s, index, 1)
    n2s.insert(index_in_n, index)

    s2n = _shift_some(prev_s2n, index_in_n, 1)
    s2n.insert(index, index_in_n)

    return n2s, s2n, index_in_n


sn_insert = sn_insert_left


def sn_delete(prev_n2s, prev_s2n, index):
    index_in_n = prev_s2n[index]  # 0 <= index < len(prev_s2n) => we can do this lookup

    n2s = _shift_some(prev_n2s, index, -1)
    n2s[index_in_n] = None

    s2n = prev_s2n[:]  # n is stable for deletions (which is the point of N*E*R*F) so no update
    del s2n[index]

    return n2s, s2n, index_in_n


def sn_replace(prev_n2s, prev_s2n, index):
    # trivial, introduced here for reasons of symmetry;

    index_in_n = prev_s2n[index]  # 0 <= index < len(prev_s2n) => we can do this lookup
    return prev_n2s[:], prev_s2n[:], index_in_n


def _shift_some(values, threshold, diff):
    return [(i if i is None or i < threshold else i + diff) for i in values]
