from utils import pmts


def annotated_node_factory(name, node_class, annotation_class):

    class AnnotatedNodePrototype(object):
        def __init__(self, underlying_node, annotation, children):
            pmts(underlying_node, node_class)
            pmts(annotation, annotation_class)

            for child in children:
                pmts(child, AnnotatedNode)  # or: just start programming in Haskell :-P

            self.underlying_node = underlying_node
            self.annotation = annotation
            self.children = children

    AnnotatedNode = type(name, (object,), dict(AnnotatedNodePrototype.__dict__))
    return AnnotatedNode
