from dsn.viewports.clef import (
    MoveViewportRelativeToCursor,
    ViewportContextChange,
    ScrollToFraction,
    CURSOR_TO_BOTTOM,
    CURSOR_TO_CENTER,
    CURSOR_TO_TOP,
    HERE,
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


def get_bounded_vrtc(context, vrtc):
    # use the cursor_position to calculate the viewport_position
    unbounded_viewport_position = viewport_position_for_vrtc_and_cursor_position(
        vrtc, context.cursor_position)

    # use the viewport_position to do the bounding
    bounded_viewport_position = bounded_viewport(
        context.document_size,
        context.viewport_size,
        unbounded_viewport_position)

    # back to a (now bounded) vrtc
    return vrtc_for_viewport_position_and_cursor_position(
        bounded_viewport_position, context.cursor_position)


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
        if note.change_source == HERE:
            # We switch to "cursor-related" mode first, to facilitate any Viewport-repositioning that might be needed.
            # NOTE: strictly speaking, such a switch might not actually be required; I imagine there are cases, namely
            # those, in which no repositioning whatsoever is required, in which we might as well stay in
            # ScrollToFraction mode if we already are. However, the present solution works fine for now so I'm not
            # touching it.

            # First, we shift the vrtc (the cursor has moved, but the viewport should not move)
            shifted_vrtc = vrtc_for_viewport_position_and_cursor_position(  # the new vrtc is deduced by taking...
                previous_viewport_position,  # ... the unmoved viewport and ...
                note.context.cursor_position)  # ... the new cursor position

            # We then make sure that the cursor does not go out of bounds... if it does, we move the viewport after all.
            followed_vrtc = follow_cursor(note.context.viewport_size, note.context.cursor_size, shifted_vrtc)

            # We bound the vrtc before storing it, to ensure there is no over- or underscrolling
            bounded_vrtc = get_bounded_vrtc(note.context, followed_vrtc)

            return ViewportStructure(
                context=note.context,
                internal_mode=VRTC(bounded_vrtc))

        # If the change_source is ELSEWHERE, the viewport's internal mode remains unchanged, to express the idea
        # of respecting the last explicit viewport-change we did at our own window; (but respecting bounds)
        internal_mode = structure.internal_mode
        if isinstance(internal_mode, VRTC):
            internal_mode = VRTC(get_bounded_vrtc(note.context, internal_mode.viewport_offset))

        return ViewportStructure(
            context=note.context,
            internal_mode=internal_mode)

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
        bounded_vrtc = get_bounded_vrtc(structure.context, vrtc)

        return ViewportStructure(
            context=structure.context,  # i.e. unchanged
            internal_mode=VRTC(bounded_vrtc))

    elif isinstance(note, ScrollToFraction):
        return ViewportStructure(
            context=structure.context,  # i.e. unchanged
            internal_mode=DocumentFraction(note.fraction))

    else:
        raise Exception("Illegal note (programming error): %s" % note)
