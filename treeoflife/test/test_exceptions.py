from __future__ import unicode_literals, print_function

from treeoflife.exceptions import LoadError, ErrorContext


def test_loaderror():
    assert str(LoadError("derp")) == "derp"

    error_context = ErrorContext()
    error = LoadError("herk")
    error.error_context = error_context

    assert str(error) == error.message
    assert str(error) == "At unknown line: herk"

    error_context.line = 0
    assert str(error) == "At line 1: herk"

    error_context.line = "error_cause"
    assert str(error) == "herk"
