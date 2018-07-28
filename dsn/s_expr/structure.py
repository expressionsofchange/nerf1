from utils import pmts, pmts_or_none
from dsn.s_expr.note_address import SExprELS18NoteAddress


class SExpr(object):
    def __init__(self, *args, **kwargs):
        raise TypeError("SExpr is Abstract; use List or Atom instead")


class Atom(SExpr):

    def __init__(self, atom, score=None, address=None):
        pmts(atom, str)
        self.atom = atom
        self.score = score

        # NOTE: `address` is used exclusively when the SExpr is the result of clef_address.py's "GlobNote" to_s_expr()
        pmts_or_none(address, SExprELS18NoteAddress)
        self.address = address

    def __repr__(self):
        return pp_flat(self)

    def restructure(self, score):
        return Atom(self.atom, score)


class List(SExpr):

    def __init__(self, children, t2s=None, s2t=None, score=None, address=None):
        for i, child in enumerate(children):
            pmts(child, SExpr, "child: %s" % i)

        self.children = children
        self.t2s = t2s
        self.s2t = s2t
        self.score = score

        # NOTE: `address` is used exclusively when the SExpr is the result of clef_address.py's "GlobNote" to_s_expr()
        pmts_or_none(address, SExprELS18NoteAddress)
        self.address = address

    def __repr__(self):
        return pp_flat(self)

    def restructure(self, score):
        return List(self.children, self.t2s, self.s2t, score)


def pp_flat(node):
    if isinstance(node, Atom):
        return node.atom
    return "(" + " ".join(pp_flat(c) for c in node.children) + ")"
