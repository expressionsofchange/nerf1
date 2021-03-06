from utils import pmts
from spacetime import get_s_address_for_t_address
from s_address import node_for_s_address

from dsn.s_expr.nerd import NerdSExpr, get_n_address_for_t_address, node_for_n_address

from dsn.s_expr.structure import Atom
from dsn.s_expr.nerd import NerdAtom

from dsn.pp.structure import PPNone, PPSingleLine, PPMultiLineAligned, PPMultiLineIndented
from dsn.pp.structure import PPAnnotatedSExpr, PPAnnotatedNerdSExpr
from dsn.pp.clef import PPUnset, PPSetSingleLine, PPSetMultiLineAligned, PPSetMultiLineIndented


def build_annotated_tree(node, default_annotation):
    if isinstance(node, Atom):
        annotated_children = []
    else:
        annotated_children = [build_annotated_tree(child, default_annotation) for child in node.children]

    return PPAnnotatedSExpr(
        node,
        default_annotation,
        annotated_children,
    )


def construct_pp_tree(tree, pp_annotations):
    """Because pp notes take a t_address, they can be applied on future trees (i.e. the current tree).

    The better (more general, more elegant and more performant) solution is to build the pp_tree in sync with the
    general tree, and have construct_pp_tree be a function over notes from those clefs rather than on trees.
    """
    annotated_tree = build_annotated_tree(tree, PPNone())

    for annotation in pp_annotations:
        pp_note = annotation.annotation

        s_address = get_s_address_for_t_address(tree, pp_note.t_address)
        if s_address is None:
            # the node either:
            # * no longer exists
            # * doesn't exist yet (when future pp_annotations are applied on a tree from the past)
            continue

        if isinstance(pp_note, PPUnset):
            new_value = PPNone()
        elif isinstance(pp_note, PPSetSingleLine):
            new_value = PPSingleLine()
        elif isinstance(pp_note, PPSetMultiLineAligned):
            new_value = PPMultiLineAligned()
        elif isinstance(pp_note, PPSetMultiLineIndented):
            new_value = PPMultiLineIndented()
        else:
            raise Exception("Unknown PP Note")

        annotated_node = node_for_s_address(annotated_tree, s_address)
        # let's just do this mutably first... this is the lazy approach (but that fits with the caveats mentioned at the
        # top of this method)
        annotated_node.annotation = new_value

    return annotated_tree


def build_annotated_nerd_tree(node, default_annotation):
    # NOTE: copy-pasted from construct_pp_tree, with small modifactions.

    if isinstance(node, NerdAtom):
        annotated_children = []
    else:
        annotated_children = [build_annotated_nerd_tree(child, default_annotation) for child in node.children]

    return PPAnnotatedNerdSExpr(
        node,
        default_annotation,
        annotated_children,
    )


def construct_pp_nerd_tree(tree, pp_annotations):
    # NOTE: copy-pasted from construct_pp_tree, with small modifactions.

    pmts(tree, NerdSExpr)
    annotated_tree = build_annotated_nerd_tree(tree, PPNone())

    for annotation in pp_annotations:
        pp_note = annotation.annotation

        n_address = get_n_address_for_t_address(tree, pp_note.t_address)
        if n_address is None:
            # the node either:
            # * no longer exists
            # * doesn't exist yet (when future pp_annotations are applied on a tree from the past)
            continue

        if isinstance(pp_note, PPUnset):
            new_value = PPNone()
        elif isinstance(pp_note, PPSetSingleLine):
            new_value = PPSingleLine()
        elif isinstance(pp_note, PPSetMultiLineAligned):
            new_value = PPMultiLineAligned()
        elif isinstance(pp_note, PPSetMultiLineIndented):
            new_value = PPMultiLineIndented()
        else:
            raise Exception("Unknown PP Note")

        annotated_node = node_for_n_address(annotated_tree, n_address)

        # let's just do this mutably first... this is the lazy approach (but that fits with the caveats mentioned at the
        # top of this method)
        annotated_node.annotation = new_value

    return annotated_tree
