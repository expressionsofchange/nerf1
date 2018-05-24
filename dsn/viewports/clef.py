CURSOR_TO_BOTTOM = 0
CURSOR_TO_CENTER = 1
CURSOR_TO_TOP = 2

VIEWPORT_LINE_UP = 3
VIEWPORT_LINE_DOWN = 4

HERE = 0
ELSEWHERE = 1


class ViewportNote(object):
    pass


class ViewportContextChange(ViewportNote):
    def __init__(self, context, change_source):
        """`change_source` is either HERE or ELSEWHERE; the difference matters in what we try to keep stationary when
        multiple elements on the screen change: the cursor, the viewport, or something else?

        HERE: If the user is navigating through or editing in the editor we want the viewport to remain stationary,
        and the user's cursor to move within it.

        ELSEWHERE: If changes are coming from another source (potentially: same person editing in another window) we
        want the last explicit viewport-change at the present window to be determining what remains in view. If the last
        explicit viewport-change was MoveViewportRelativeToCursor, we want to keep the cursor stationary; moving the
        viewport around it if required; if the last explicit viewport-change was ScrollToFraction we want to stay at
        that fraction.

        Both of these cases only indicate a preference; e.g. bounding-by-window takes precedence to that preference.
        """

        self.context = context
        self.change_source = change_source


class MoveViewportRelativeToCursor(ViewportNote):
    def __init__(self, relative_move):
        self.relative_move = relative_move


class ScrollToFraction(ViewportNote):
    def __init__(self, fraction):
        self.fraction = fraction
