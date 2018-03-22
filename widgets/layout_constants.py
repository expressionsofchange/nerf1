MARGIN = 5
PADDING = 3


GREY = (0.95, 0.95, 0.95, 1)  # Ad Hoc Grey
LIGHT_YELLOW = (1, 1, 0.97, 1)  # Ad Hoc Light Yellow
RED = (1, 0.5, 0.5, 1)  # ad hoc; fine-tune please
PINK = (1, 0.95, 0.95, 1)  # ad hoc; fine-tune please
DARK_GREY = (0.5, 0.5, 0.5, 1)  # ad hoc; fine-tune please


font_size = 14


def get_font_size():
    return font_size


def set_font_size(fs):
    global font_size
    font_size = fs
