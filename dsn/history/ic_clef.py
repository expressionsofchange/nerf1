class EICHNote(object):
    pass


# Cursor movement:

class EICHCursorSet(EICHNote):
    def __init__(self, address):
        self.address = address


class EICHCursorMove(EICHNote):
    def __init__(self, direction):
        self.direction = direction
