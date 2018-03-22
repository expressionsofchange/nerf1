"""
A number of options in modelling were considered, and the below may very well still change.

Examples are: The cursor movement can be modelled in a DFS model (with or without "return to parent), using
tree-navigation etc. Other example: Sibbling insertion: will we make distinct Notes for the directionality, or will we
instead have this be a parameter?

For now I'm going to just pick some options that together describe the functionality of the editor as it currently
exists.
"""


class EditNote(object):
    pass


class InsertNodeSibbling(EditNote):
    def __init__(self, direction):
        self.direction = direction


class InsertNodeChild(EditNote):
    pass


class TextReplace(EditNote):
    def __init__(self, s_address, text):
        self.s_address = s_address
        self.text = text


class TextInsert(EditNote):
    def __init__(self, parent_s_address, index, text):
        self.parent_s_address = parent_s_address
        self.index = index
        self.text = text


class SwapSibbling(EditNote):
    def __init__(self, direction):
        self.direction = direction


class LeaveChildrenBehind(EditNote):
    pass


class EncloseWithParent(EditNote):
    pass


class EDelete(EditNote):
    pass


class MoveSelectionSibbling(EditNote):
    # NOTE: both types of Move need access to the location of the selection, which is why we have those accessible as an
    # attribute of those notes. It might also point at "maybe keeping selections outside of the main structure was a
    # mistake"... if that turns out to be the case we can always refactor.

    def __init__(self, selection_edge_0, selection_edge_1, direction):
        self.selection_edge_0 = selection_edge_0
        self.selection_edge_1 = selection_edge_1
        self.direction = direction


class MoveSelectionChild(EditNote):
    def __init__(self, selection_edge_0, selection_edge_1):
        self.selection_edge_0 = selection_edge_0
        self.selection_edge_1 = selection_edge_1


class CursorSet(EditNote):
    def __init__(self, s_address):
        self.s_address = s_address


class CursorDFS(EditNote):
    def __init__(self, direction):
        self.direction = direction


class CursorParent(EditNote):
    pass


class CursorChild(EditNote):
    pass
