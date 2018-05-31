from dsn.s_expr.clef_address import InScore

from dsn.history.ic_clef import (
    EICHChordCollapse,
    EICHChordExpand,
    EICHCursorMove,
    EICHCursorSet,
)


def eich_note_play(structure, edit_note):
    # :: EHStructure, EHNote => (new) cursor, expanded_chords, error

    def an_error():
        return structure.cursor, structure.expanded_chords, True

    def move_cursor(new_cursor):
        return new_cursor, structure.expanded_chords, False

    if isinstance(edit_note, EICHCursorSet):
        return move_cursor(edit_note.address)

    if isinstance(edit_note, EICHCursorMove):
        new_cursor = structure.cursor + edit_note.direction
        if new_cursor < 0 or new_cursor > len(structure.items) - 1:
            return an_error()

        return move_cursor(new_cursor)

    if isinstance(edit_note, EICHChordExpand):
        rendered_ic_item = structure.items[structure.cursor]
        address = rendered_ic_item.address.note_address
        return structure.cursor, structure.expanded_chords.union({address}), False

    if isinstance(edit_note, EICHChordCollapse):
        note_address = structure.items[structure.cursor].address.note_address

        for i, part in reversed(list(enumerate(note_address))):
            if isinstance(part, InScore):
                to_pop = note_address[:i]
                new_cursor = structure.cursor - part.index  # TODO explain
                return new_cursor, structure.expanded_chords.difference({to_pop}), False

        return an_error()

    raise Exception("Unknown Note")
