from dsn.viewports.clef import (
    MoveViewportRelativeToCursor,
    ViewportContextChange,
    ScrollToFraction,
    CURSOR_TO_BOTTOM,
    CURSOR_TO_CENTER,
    CURSOR_TO_TOP,
    VIEWPORT_LINE_UP,
    VIEWPORT_LINE_DOWN,
)

from dsn.viewports.structure import DocumentFraction, VRTC, ViewportStructure
from dsn.viewports.utils import (
    bounded_viewport,
    follow_cursor,
    viewport_line_down,
    viewport_line_up,
    viewport_position_for_vrtc_and_cursor_position,
    vrtc_bottom,
    vrtc_center,
    vrtc_for_viewport_position_and_cursor_position,
    vrtc_top,
)


def play_viewport_note(note, structure):
    previous_viewport_position = structure.get_position()

    if isinstance(structure.internal_mode, DocumentFraction):
        # We deduce the previous vrtc (even though we were not previously in VRTC mode):
        previous_vrtc = vrtc_for_viewport_position_and_cursor_position(
            previous_viewport_position, structure.context.cursor_position)

    else:  # i.e. isinstance(structure.internal_mode, VRTC)
        # We were already in vrtc mode, so the previous vrtc can be trivially gotten
        previous_vrtc = structure.internal_mode.viewport_offset

    if isinstance(note, ViewportContextChange):
        if note.user_moved_cursor:
            # If the user moved the cursor, we switch to "cursor-related" mode, and make sure to keep the cursor in the
            # viewport:

            # First, we shift the vrtc (the cursor has moved, but the viewport does not move)
            shifted_vrtc = vrtc_for_viewport_position_and_cursor_position(  # the new vrtc is deduced by taking...
                previous_viewport_position,  # ... the unmoved viewport and ...
                note.context.cursor_position)  # ... the new cursor position

            # We then make sure that the cursor does not go out of bounds... if it does, we move the viewport after all.
            followed_vrtc = follow_cursor(note.context.viewport_size, note.context.cursor_size, shifted_vrtc)

            return ViewportStructure(
                context=note.context,
                internal_mode=VRTC(followed_vrtc))

        # If the user did not move the cursor, the viewport's internal mode remains unchanged, to express the idea
        # "viewport relative to cursor remains constant" (viewport revolves around cursor); the viewport may actually
        # shift in the document, but that calculation is not here (it's a getter of the ViewportStructure class)
        return ViewportStructure(
            context=note.context,
            internal_mode=structure.internal_mode)  # i.e. unchanged

    elif isinstance(note, MoveViewportRelativeToCursor):
        if note.relative_move == CURSOR_TO_BOTTOM:
            vrtc = vrtc_bottom(structure.context.viewport_size, structure.context.cursor_size)

        elif note.relative_move == CURSOR_TO_TOP:
            vrtc = vrtc_top()

        elif note.relative_move == CURSOR_TO_CENTER:
            vrtc = vrtc_center(structure.context.viewport_size, structure.context.cursor_size)

        elif note.relative_move == VIEWPORT_LINE_UP:
            vrtc = viewport_line_up(previous_vrtc, structure.context.cursor_size)

        elif note.relative_move == VIEWPORT_LINE_DOWN:
            vrtc = viewport_line_down(previous_vrtc, structure.context.cursor_size)

        else:
            raise Exception("Unknown type of relative move (programming error): %s" % note.relative_move)

        # We bound the vrtc before storing it, to ensure there is no over- or underscrolling
        unbounded_viewport_position = viewport_position_for_vrtc_and_cursor_position(
            vrtc, structure.context.cursor_position)

        bounded_viewport_position = bounded_viewport(
            structure.context.document_size,
            structure.context.viewport_size,
            unbounded_viewport_position)

        bounded_vrtc = vrtc_for_viewport_position_and_cursor_position(
            bounded_viewport_position, structure.context.cursor_position)

        return ViewportStructure(
            context=structure.context,  # i.e. unchanged
            internal_mode=VRTC(bounded_vrtc))

    elif isinstance(note, ScrollToFraction):
        return ViewportStructure(
            context=structure.context,  # i.e. unchanged
            internal_mode=DocumentFraction(note.fraction))

    else:
        raise Exception("Illegal note (programming error): %s" % note)
