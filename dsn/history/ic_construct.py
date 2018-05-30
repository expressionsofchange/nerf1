from dsn.history.ic_clef import (
    EICHCursorMove,
    EICHCursorSet,
)


def eich_note_play(structure, edit_note):
    # :: EHStructure, EHNote => (new) cursor, error

    def an_error():
        return structure.cursor, True

    def move_cursor(new_cursor):
        return new_cursor, False

    if isinstance(edit_note, EICHCursorSet):
        return move_cursor(edit_note.address)

    if isinstance(edit_note, EICHCursorMove):
        new_cursor = structure.cursor + edit_note.direction
        if new_cursor < 0 or new_cursor > len(structure.items) - 1:
            return an_error()

        return move_cursor(new_cursor)

    raise Exception("Unknown Note")
