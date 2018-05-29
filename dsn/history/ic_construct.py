from dsn.history.ic_clef import (
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

    raise Exception("Unknown Note")
