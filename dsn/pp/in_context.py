from annotated_tree import annotated_node_factory

from dsn.s_expr.structure import SExpr

from dsn.pp.structure import PPSingleLine, PPNone, PPMultiLineAligned, PPMultiLineIndented


# Multiline modes:
MULTI_LINE_ALIGNED = 0
MULTI_LINE_INDENTED = 1
SINGLE_LINE = 2


class InheritedRenderingInformation(object):
    """When rendering trees, ancestors may affect how their descendants are rendered.

    Such information is formalized as InheritedRenderingInformation."""

    def __init__(self, multiline_mode):
        self.multiline_mode = multiline_mode


IriAnnotatedNode = annotated_node_factory("IriAnnotatedNode", SExpr, InheritedRenderingInformation)


def construct_iri_top_down(pp_annotated_node, inherited_information):
    """Constructs the InheritedRenderingInformation in a top-down fashion. Note the difference between the PP
    instructions and the InheritedRenderingInformation: the PP instructions must be viewed in the light of their
    ancestors, the InheritedRenderingInformation can be used without such lookups in the tree, and is therefore more
    easily used. Of course, we must construct it first, which is what we do in the present function.
    """

    # I attempted to write this more generally, as a generic map-over-trees function and a function that operates on a
    # single node; however: the fact that the index of a child is such an important piece of information (it determines
    # SINGLE_LINE mode) made this very unnatural, so I just wrote a single non-generic recursive function instead.

    children = getattr(pp_annotated_node, 'children', [])
    annotated_children = []

    my_information = inherited_information

    if type(pp_annotated_node.annotation) in [PPSingleLine]:
        my_information = InheritedRenderingInformation(SINGLE_LINE)

    elif type(pp_annotated_node.annotation) in [PPMultiLineAligned, PPNone]:  # i.e. this is the default
        my_information = InheritedRenderingInformation(MULTI_LINE_ALIGNED)

    elif type(pp_annotated_node.annotation) in [PPMultiLineIndented]:
        my_information = InheritedRenderingInformation(MULTI_LINE_INDENTED)

    for i, child in enumerate(children):
        if i == 0 or my_information.multiline_mode == SINGLE_LINE:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.

            # If we were ever to make it a user-decision how to render that child (i.e. allow for a non-single-line
            # override), the below must also be updated (offset_down for child[n > 0] should be non-zero)
            child_information = InheritedRenderingInformation(SINGLE_LINE)
        elif my_information.multiline_mode == MULTI_LINE_ALIGNED:
            child_information = InheritedRenderingInformation(MULTI_LINE_ALIGNED)

        else:  # implied: MULTI_LINE_INDENTED
            child_information = InheritedRenderingInformation(MULTI_LINE_INDENTED)

        annotated_children.append(construct_iri_top_down(child, child_information))

    return IriAnnotatedNode(
        underlying_node=pp_annotated_node.underlying_node,
        annotation=my_information,
        children=annotated_children,
    )
