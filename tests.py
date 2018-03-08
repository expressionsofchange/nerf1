import unittest
import doctest


def load_tests(loader, tests, ignore):
    # Test the docstrings inside our actual codebase
    # tests.addTests(doctest.DocTestSuite(some_module))

    # Some tests in the doctests style are too large to nicely fit into a docstring; better to keep them separate:
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_clef_serialization.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_construct.txt"))

    return tests


if __name__ == '__main__':
    unittest.main()
