from utils import pmts


class SExpr(object):
    def __init__(self, *args, **kwargs):
        raise TypeError("SExpr is Abstract; use List or Atom instead")


class Atom(SExpr):

    def __init__(self, atom):
        pmts(atom, str)
        self.atom = atom

    def __repr__(self):
        return pp_flat(self)


class List(SExpr):

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return pp_flat(self)


def pp_flat(node):
    if isinstance(node, Atom):
        return node.atom
    return "(" + " ".join(pp_flat(c) for c in node.children) + ")"
