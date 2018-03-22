from s_address import node_for_s_address, s_dfs

from dsn.history.clef import (
    EHCursorChild,
    EHCursorDFS,
    EHCursorParent,
    EHCursorSet,
)


def eh_note_play(structure, edit_note):
    # :: EHStructure, EHNote => (new) s_cursor, error
    def an_error():
        return structure.s_cursor, True

    # It seems a good idea to push for factoring out the commonalities between cursor movement in the HistoryWidget and
    # the TreeWidget.

    # In practice that's somewhat complicated by the fact that they don't both use trees with .children (in that case we
    # could just ducktype)

    # Besides that, there are some questions on how to model the shared Notes, and the shared playing of notes. For now,
    # the answer doesn't really matter... options are:
    # * Include certain Notes in both Clefs.
    # * Have a wrapper-note (ECursor / EHCursor) which refers to a Cursor note.

    # Given the above, I have just pushed forward by copy/pasting and editing; cleanup to follow later.

    def move_cursor(new_cursor):
        return new_cursor, False

    if isinstance(edit_note, EHCursorDFS):
        dfs = s_dfs(structure.node, [])
        dfs_index = dfs.index(structure.s_cursor) + edit_note.direction
        if not (0 <= dfs_index <= len(dfs) - 1):
            return an_error()
        return move_cursor(dfs[dfs_index])

    if isinstance(edit_note, EHCursorSet):
        return move_cursor(edit_note.s_address)

    if isinstance(edit_note, EHCursorParent):
        # N.B.: different from the TreeWidget case: our root is a single list, rather than an actual root.
        if len(structure.s_cursor) == 1:
            return an_error()
        return move_cursor(structure.s_cursor[:-1])

    if isinstance(edit_note, EHCursorChild):
        cursor_node = node_for_s_address(structure.node, structure.s_cursor)
        if not hasattr(cursor_node, 'children') or len(cursor_node.children) == 0:
            return an_error()
        return move_cursor(structure.s_cursor + [0])

    raise Exception("Unknown Note")
