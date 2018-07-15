
class EditStructure(object):
    """State object for widgets/tree.py"""

    def __init__(self, tree, s_cursor, pp_annotations, pp_tree):
        self.tree = tree
        self.s_cursor = s_cursor
        self.pp_annotations = pp_annotations
        self.pp_tree = pp_tree


# Updating a single attribute or a small set of them is likely a pattern that we'll extract in some more general form
# sooner or later; for now the below works just fine.

def update_s_cursor(edit_structure, s_cursor):
    return EditStructure(
        tree=edit_structure.tree,
        s_cursor=s_cursor,
        pp_annotations=edit_structure.pp_annotations,
        pp_tree=edit_structure.pp_tree,
    )
