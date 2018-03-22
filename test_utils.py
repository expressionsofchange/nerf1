"""
Utils for testing.
"""


class Generator:
    """When (doc)testing decomposed generators, we want to be able to independently inspect the returned and yielded
    values. Writing this as try/except blocks is cumbersome; hence we created the below.
    """

    def __init__(self, gen):
        self.gen = gen
        initial_result = self.send(None)
        print(repr(initial_result))

    def send(self, value):
        try:
            yielded = self.gen.send(value)
            return ("Y", yielded)
        except StopIteration as si:
            return_value = si.value
            return ("R", return_value)
