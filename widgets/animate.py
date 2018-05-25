from widgets.utils import Offset, OffsetBox
from functools import partial


# I found that floating items from/to the left of the screen is visually pleasing; YMMV.
FLOAT_LEFT = -400


def animate_scalar(fraction, a, b):
    return a + ((b - a) * fraction)


def animate(fraction, present, target):
    """
    Takes 2 dictionaries:
    * keyed by some identifier. Which expresses: if the identifier is the same in the 2 dicts, it's the same thing.
    * values: OffsetBox

    Returns: a dict which interpolates x, y and alpha of the 2 inputs. Shifting a `fraction` from `present` to `target`

    An assumption here is: if it's the same thing (same identifier), it's also rendered the same way. In our actual
    usage, this assumption is sometimes violated; for example, when the cursor moves, the associated items are not
    rendered identically pre- and post-move. The proper solution to this is: model "the cursor" as a separately
    identifyable thing, which can float from one place to the other. For now, we simply accept the jerky animation.
    """

    if fraction >= 1:
        return target

    result = {}
    rr = partial(animate_scalar, fraction)

    for key in set(list(present.keys()) + list(target.keys())):
        if key not in present:
            item = target[key].item
            t = target[key].offset
            p = Offset(t.x + FLOAT_LEFT, t.y, 0)

        elif key not in target:
            item = present[key].item
            p = present[key].offset
            t = Offset(p.x + FLOAT_LEFT, p.y, 0)

        else:
            # In the below either present or target is fine... but if the assumption "rendered identically" is violated,
            # it's visually more pleasing to have the jerky animation at the beginning of the animation rather than at
            # its conclusion; hence: target.
            item = target[key].item

            p = present[key].offset
            t = target[key].offset

        offset = Offset(rr(p.x, t.x), rr(p.y, t.y), rr(p.alpha, t.alpha))

        result[key] = OffsetBox(offset, item)

    return result
