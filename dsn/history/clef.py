class EHNote(object):
    pass


# Cursor movement:

class EHCursorSet(EHNote):
    def __init__(self, s_address):
        self.s_address = s_address


class EHCursorDFS(EHNote):
    def __init__(self, direction):
        self.direction = direction


class EHCursorParent(EHNote):
    pass


class EHCursorChild(EHNote):
    pass
