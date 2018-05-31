from utils import pmts


class EICHStructure(object):
    """EICH means: Edit In-Context History"""

    def __init__(self, score, items, cursor, tree_t_address, expanded_chords):
        pmts(items, list)
        self.score = score
        self.items = items
        self.cursor = cursor
        self.tree_t_address = tree_t_address
        self.expanded_chords = expanded_chords
