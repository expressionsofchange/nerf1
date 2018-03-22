# from kivy.utils import rgba
from kivy.utils import get_color_from_hex
from kivy.compat import string_types


def rgba(s, *args):
    '''Return a Kivy color (4 value from 0-1 range) from either a hex string or
    a list of 0-255 values.

    .. versionadded:: 1.9.2
    '''
    if isinstance(s, string_types):
        return get_color_from_hex(s)
    elif isinstance(s, (list, tuple)):
        s = list(map(lambda x: x / 255., s))
        return s
    elif isinstance(s, (int, float)):
        s = list(map(lambda x: x / 255., [s] + list(args)))
        return s
    raise Exception('Invalid value (not a string / list / tuple)')


WHITE = rgba(255, 255, 255, 255)
GUARDSMAN_RED = rgba(211, 1, 2, 255)
CERISE = rgba(211, 54, 130, 255)
CUTTY_SARK = rgba(88, 110, 117, 255)
CURIOUS_BLUE = rgba(38, 141, 210, 255)
LAUREL_GREEN = rgba(10, 130, 0, 255)
AQUA_GREEN = rgba(42, 161, 152, 255)
OLD_LACE = rgba(253, 246, 229, 255)
BLACK = rgba(0, 0, 0, 255)
