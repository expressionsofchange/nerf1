CURSOR_TO_BOTTOM = 0
CURSOR_TO_CENTER = 1
CURSOR_TO_TOP = 2

VIEWPORT_LINE_UP = 3
VIEWPORT_LINE_DOWN = 4


class ViewportNote(object):
    pass


class ViewportContextChange(ViewportNote):
    def __init__(self, context, user_moved_cursor):
        """`user_moved_cursor` is a boolean, that expresses whether the user initiated any edit / cursor move, or
        whether the change "came from the outside". (whether such an edit actually changes the cursor position is not
        expressed by `user_moved_cursor`, which is admittedly a bit confusing)

        This idea is important for the following reason: if the user is controlling the editor, we want the viewport to
        remain stationary, and the user's cursor to move within it; if changes are coming from another source
        (potentially: same person editing in another window) we want the viewport to revolve around the cursor.
        """

        self.context = context
        self.user_moved_cursor = user_moved_cursor


class MoveViewportRelativeToCursor(ViewportNote):
    def __init__(self, relative_move):
        self.relative_move = relative_move


class ScrollToFraction(ViewportNote):
    def __init__(self, fraction):
        self.fraction = fraction
