from dsn.s_expr.clef import (
    BecomeAtom,
    SetAtom,
    BecomeList,
    Insert,
    Extend,
)


def bubble_history_up(note, tree, s_address):
    for i in reversed(range(len(s_address))):
        # We slide over the s_address from right to left, like so:
        # [..., ..., ..., ..., ..., ..., ...]  <- s_address
        #                                 ^
        #                                 i
        # For each such i, s_address[i] gives you the index to replace at.
        #
        # Regarding the range (0, len(s_address)) the following:
        # * len(s_address) means the s_address itself is the first thing to be replaced.
        # * 0 means: the last replacement is _inside_ the root node (s_address=[]), at index s_address[0]
        note = Extend(s_address[i], note)

    return note


def insert_text_at(tree, parent_s_address, index, text):
    insertion = Insert(index, BecomeAtom(text))
    return bubble_history_up(insertion, tree, parent_s_address)


def insert_node_at(tree, parent_s_address, index):
    insertion = Insert(index, BecomeList())
    return bubble_history_up(insertion, tree, parent_s_address)


def replace_text_at(tree, s_address, text):
    replacement = Extend(s_address[-1], SetAtom(text))
    return bubble_history_up(replacement, tree, s_address[:-1])
