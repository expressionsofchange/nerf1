def ignore():
    """Useful placeholder for e.g. close_receiver"""
    pass


def fail():
    """Useful token for e.g. close_receiver (if that's unexpected)"""
    pass


class Channel(object):
    """
    >>> from channel import Channel
    >>> c = Channel()
    >>> def r0(data):
    ...     print("R0 RECEIVED", data)
    ...
    >>> def r1(data):
    ...     print("R1 RECEIVED", data)
    ...
    >>> s0 = c.connect(r0)
    >>> s1 = c.connect(r1)
    >>> s0("hallo")
    R1 RECEIVED hallo
    >>> s1("hallo")
    R0 RECEIVED hallo
    >>> def r2(data):
    ...     print("R2 RECEIVED", data)
    ...
    >>> s2 = c.connect(r2)
    >>> s2("hallo")
    R0 RECEIVED hallo
    R1 RECEIVED hallo
    >>> s0("hallo")
    R1 RECEIVED hallo
    R2 RECEIVED hallo
    """

    def __init__(self):
        self.receivers = []

    def connect(self, receiver):
        # receiver :: function that takes data
        sender_index = len(self.receivers)
        self.receivers.append(receiver)

        def send(data):
            for index, r in enumerate(self.receivers):
                if index != sender_index:
                    r(data)

        return send

    def broadcast(self, data):
        for r in self.receivers:
            r(data)


class ClosableChannel(object):
    """
    Channel w/ an explicit close() call; alternatively this could be modelled by sending either Open(data) or Close()
    over a regular Channel, or by opening a second channel that will be used for communicating open/closed info.

    >>> from channel import ClosableChannel
    >>> c = ClosableChannel()
    >>>
    >>> def r0(data):
    ...     print("R0 RECEIVED", data)
    ...
    >>> def c0():
    ...     print("C0 RECEIVED")
    ...
    >>> def r1(data):
    ...     print("R1 RECEIVED", data)
    ...
    >>> def c1():
    ...     print("C1 RECEIVED")
    ...
    >>> s0, close0 = c.connect(r0, c0)
    >>> s1, close1 = c.connect(r1, c1)
    >>>
    >>> close0()
    C1 RECEIVED
    """

    def __init__(self):
        self.receivers = []
        self.close_receivers = []
        self.closed = False

    def connect(self, receiver, close_receiver=fail):
        # receiver :: function that takes data;
        # close_receiver :: argless function

        sender_index = len(self.receivers)
        self.receivers.append(receiver)
        self.close_receivers.append(close_receiver)

        def send(data):
            if self.closed:
                raise Exception("Channel closed")

            for index, r in enumerate(self.receivers):
                if index != sender_index:
                    r(data)

        def close():
            self.closed = True
            for index, c in enumerate(self.close_receivers):
                if index != sender_index:
                    c()

        return send, close

    def broadcast(self, data):
        for r in self.receivers:
            r(data)
