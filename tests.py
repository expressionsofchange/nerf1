import unittest
import doctest

import channel
import spacetime
import nerdspace
import vlq
import utils
import s_address
import vim

from dsn.viewports import utils as viewports_utils


def load_tests(loader, tests, ignore):
    # Test the docstrings inside our actual codebase
    tests.addTests(doctest.DocTestSuite(utils))
    tests.addTests(doctest.DocTestSuite(channel))
    tests.addTests(doctest.DocTestSuite(spacetime))
    tests.addTests(doctest.DocTestSuite(nerdspace))
    tests.addTests(doctest.DocTestSuite(vlq))
    tests.addTests(doctest.DocTestSuite(s_address))
    tests.addTests(doctest.DocTestSuite(vim))
    tests.addTests(doctest.DocTestSuite(viewports_utils))

    # Some tests in the doctests style are too large to nicely fit into a docstring; better to keep them separate:
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_clef_serialization.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_clef_to_s_expr.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_construct.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_construct_nerd.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_in_context_display.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/s_expr_in_context_display_annotated.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/note_address.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/spacetime.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/nerd_spacetime.txt"))

    return tests


if __name__ == '__main__':
    unittest.main()
