class PPNote(object):
    def __init__(self, t_address):
        self.t_address = t_address

    def __repr__(self):
        return self.__class__.__name__


class PPUnset(PPNote):
    pass


class PPSetSingleLine(PPNote):
    pass


class PPSetMultiLineAligned(PPNote):
    pass


class PPSetMultiLineIndented(PPNote):
    pass
