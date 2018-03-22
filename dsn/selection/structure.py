class Selection(object):

    def __init__(self, context, exists, attached_to, edge_0, edge_1):
        if not exists:
            assert attached_to is None
            assert edge_0 is None
            assert edge_1 is None

        self.context = context
        self.exists = exists
        self.attached_to = attached_to
        self.edge_0 = edge_0
        self.edge_1 = edge_1

    def __repr__(self):
        return "Selection: %s %s %s %s" % (self.exists, self.attached_to, self.edge_0, self.edge_1)
