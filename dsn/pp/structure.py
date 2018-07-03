from annotated_tree import annotated_node_factory
from dsn.s_expr.structure import SExpr


class PPAnnotation(object):
    pass


class PPNone(PPAnnotation):
    # No manual overrides
    pass


class PPSingleLine(PPAnnotation):
    pass


class PPMultiLineAligned(PPAnnotation):
    pass


PPAnnotatedSExpr = annotated_node_factory('PPAnnotatedSExpr', SExpr, PPAnnotation)
