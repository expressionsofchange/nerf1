from spacetime import get_stable_s_over_time

from dsn.selection.clef import AttachDetach, SwitchToOtherEnd, ClearSelection, SelectionContextChange
from dsn.selection.structure import Selection

from dsn.editor.structure import update_s_cursor


def selection_note_play(note, structure):
    """:: note, structure => structure"""

    if isinstance(note, SelectionContextChange):
        if not structure.exists:
            return Selection(note.context, False, None, None, None)

        edge_0 = get_stable_s_over_time(structure.context.tree, structure.edge_0, note.context.tree)
        edge_1 = get_stable_s_over_time(structure.context.tree, structure.edge_1, note.context.tree)

        if structure.attached_to == 0:
            edge_0 = note.context.s_cursor

        if structure.attached_to == 1:
            edge_1 = note.context.s_cursor

        if edge_0 is None or edge_1 is None:
            # if either of the edges no longer exists in the new context: remove the selection
            return Selection(
                context=note.context,
                exists=False,
                attached_to=None,
                edge_0=None,
                edge_1=None,
                )

        return Selection(
            context=note.context,
            exists=True,
            attached_to=structure.attached_to,
            edge_0=edge_0,
            edge_1=edge_1,
            )

    elif isinstance(note, AttachDetach):
        if not structure.exists:
            # Create selection & attach
            return Selection(
                context=structure.context,
                exists=True,
                attached_to=0,  # arbitrarily pick one end to attach the cursor to (they are the same)
                edge_0=structure.context.s_cursor,
                edge_1=structure.context.s_cursor,
                )

        # Attach to existing selection
        if structure.attached_to is None:
            # Reattaching always jumps to the "end" of the selection. This is an arbitrary decision, but at least it's a
            # predictable one from the perspective of the user (as opposed to always picking "edge_0", which might be
            # any of the edges)
            if structure.edge_0 > structure.edge_1:
                new_cursor_pos = structure.edge_0
                attached_to = 0
            else:
                new_cursor_pos = structure.edge_1
                attached_to = 1

            return Selection(
                context=update_s_cursor(structure.context, new_cursor_pos),
                exists=True,
                attached_to=attached_to,
                edge_0=structure.edge_0,
                edge_1=structure.edge_1,
                )

        # Detach and leave selection in place
        return Selection(
            context=structure.context,
            exists=True,
            attached_to=None,
            edge_0=structure.edge_0,
            edge_1=structure.edge_1,
            )

    elif isinstance(note, SwitchToOtherEnd):
        if not structure.exists or structure.attached_to is None:
            # do nothing; (alternative might be: Attach)
            return structure

        new_cursor_pos = structure.edge_1 if structure.attached_to == 0 else structure.edge_0

        return Selection(
            context=update_s_cursor(structure.context, new_cursor_pos),
            exists=structure.exists,
            attached_to=1 if structure.attached_to == 0 else 0,
            edge_0=structure.edge_0,
            edge_1=structure.edge_1,
            )

    elif isinstance(note, ClearSelection):
        return Selection(
            context=structure.context,
            exists=False,
            attached_to=None,
            edge_0=None,
            edge_1=None,
            )
