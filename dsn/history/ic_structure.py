from utils import pmts


class EICHStructure(object):
    # Edit In-Context History Structure

    def __init__(self, score, items, s_cursor, tree_t_address):
        pmts(items, list)
        self.score = score
        self.items = items
        self.s_cursor = s_cursor
        self.tree_t_address = tree_t_address
