from dsn.viewports.utils import (
    viewport_position_for_document_fraction,
    viewport_position_for_vrtc_and_cursor_position,
)


class ViewportContext(object):
    def __init__(self, document_size, viewport_size, cursor_size, cursor_position):
        self.document_size = document_size
        self.viewport_size = viewport_size
        self.cursor_size = cursor_size
        self.cursor_position = cursor_position

    def __repr__(self):
        return "Context(%s, %s, %s, %s)" % (
            self.document_size, self.viewport_size, self.cursor_size, self.cursor_position)


class ViewportInternalMode(object):
    pass


class DocumentFraction(ViewportInternalMode):

    def __init__(self, fraction):
        self.fraction = fraction

    def __repr__(self):
        return "DocumentFraction(%s)" % self.fraction


class VRTC(ViewportInternalMode):
    """Viewport relative to cursor"""

    def __init__(self, viewport_offset):
        self.viewport_offset = viewport_offset

    def __repr__(self):
        return "VRTC(%s)" % self.viewport_offset


class ViewportStructure(object):
    def __init__(self, context, internal_mode):
        """In the ViewportStructure we distinguish between the external context on the one hand and the mode which is
        internal to the viewport on the other.

        The idea is: the external context is that information that's simply announced to the viewport about changes to
        the shape of the viewed document; the "mode" is built up over time through cursor moves, scrollbar-drags and
        such.
        """
        self.context = context
        self.internal_mode = internal_mode

    def __repr__(self):
        return "Viewport(%s, %s)" % (self.context, self.internal_mode)

    def get_position(self):
        if isinstance(self.internal_mode, DocumentFraction):
            return viewport_position_for_document_fraction(
                self.context.document_size,
                self.context.viewport_size,
                self.internal_mode.fraction)

        # else implied: VRTC

        return viewport_position_for_vrtc_and_cursor_position(
            self.internal_mode.viewport_offset,
            self.context.cursor_position)
