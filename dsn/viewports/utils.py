"""
All sizes and positions are scalars. We assume that the tools below will be orthogonally applicable (literally) in the
2D plane.

Viewport positions are always rounded to ints, to ensure we draw at full pixel boundaries.

## Fractions

Viewport positions may be expressed fractionally in the document. Fractions are floats in the domain [0, 1], or None
(meaning: scrolling is impossible, because the viewport is larger than the document).

## Relative to cursor/anchor.

Viewport positions may also be expressed relative to the position of the top (position 0) of a cursor (an anchor). These
anchors have a size themselves (this is relavant when positioning them at the bottom).

Relativeness is expressed as a shift of the viewport w.r.t. the anchor; i.e. the value at hand must be added to the
anchor to get a viewport_pos.  (This is a matter of definition; the inverse approach is to have the value be an
expression of the position of the anchor within the viewport; this is equally powerful and simply has the inverse sign)
"""


def bounded_viewport(document_size, viewport_size, viewport_pos):
    """
    Returns a viewport pos inside the document, given a viewport that's potentially outside it.

    In-bounds, no effect is achieved by bounding:
    >>> bounded_viewport(500, 200, 250)
    250

    Any kind of scrolling is impossible if the viewport is larger than the document; we just show it at the top:
    >>> bounded_viewport(15, 1000, 45)
    0

    Above the top of the document (below y=0) there is nothing to be seen:
    >>> bounded_viewport(500, 200, -100)
    0

    Below the bottom of the document (below document_size) there is nothing to be seen:
    >>> bounded_viewport(500, 200, 400)
    300

    Open question: is it useful to return a smaller viewport if the document is actually smaller? For now, I have no
    use for it yet, so we just return the viewport_pos.
    """

    if document_size < viewport_size:
        return 0

    if viewport_pos < 0:
        return 0

    return min(document_size - viewport_size, viewport_pos)


def document_fraction_for_viewport_position(document_size, viewport_size, viewport_position):
    """
    We take any point of the viewpoint, and calculate its relative position with respect to the posible positions it
    can be in (in practice: we use the top of the viewport, and realize that it cannot be lower than a viewport_size
    from the bottom).

    +--------------------+
    |Document            |
    |                    |
    +----------+   <------------lowest possible position of the top of the viewport, a.k.a. 100%
    |Viewport  |         |
    |          |         |
    |          |         |
    |          |         |
    |          |         |
    +----------+---------+
    """

    if document_size <= viewport_size:
        return None

    return viewport_position / (document_size - viewport_size)


def viewport_position_for_document_fraction(document_size, viewport_size, document_fraction):
    if document_fraction is None:
        # If scrolling is impossible, we put the viewport at the top.
        return 0

    return int((document_size - viewport_size) * document_fraction)


def vrtc_for_viewport_position_and_cursor_position(viewport_position, cursor_position):
    return viewport_position - cursor_position


def viewport_position_for_vrtc_and_cursor_position(viewport_relative_to_cursor, cursor_position):
    return viewport_relative_to_cursor + cursor_position


def vrtc_top():
    """Puts the cursor at the top of the viewport"""
    return 0


def vrtc_center(viewport_size, cursor_size):
    """Puts the cursor at the center of the viewport"""
    return int((viewport_size - cursor_size) / -2)


def vrtc_bottom(viewport_size, cursor_size):
    """Puts the cursor at the bottom"""
    return -1 * (viewport_size - cursor_size)


def viewport_line_up(vrtc, cursor_size):
    return vrtc - cursor_size


def viewport_line_down(vrtc, cursor_size):
    return vrtc + cursor_size


def follow_cursor(viewport_size, cursor_size, vrtc):
    """Ensures that a vrtc is such that the cursor is inside the viewport."""
    top = vrtc_top()
    bottom = vrtc_bottom(viewport_size, cursor_size)

    if vrtc > top:
        return top
    if vrtc < bottom:
        return bottom
    return vrtc
