class PPNote(object):
    def __init__(self, t_address):
        self.t_address = t_address


class PPUnset(PPNote):
    pass


class PPSetSingleLine(PPNote):
    pass


class PPSetLispy(PPNote):
    pass
