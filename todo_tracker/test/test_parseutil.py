from todo_tracker import parseutil
import parsley


def test_grammar():
    class MyOtherGrammar(parseutil.Grammar):
        grammar = """
            target :arg = s('herp') -> arg + 100
        """

    class MyGrammar(parseutil.Grammar):
        grammar = """
            source :arg = othergrammar.target(arg):t ' derp' -> t + 10
        """
        bindings = {
            "othergrammar": MyOtherGrammar
        }

    assert MyGrammar("herp derp").source(1000) == 1110
    assert MyGrammar("herk derk").source(1000, optional=True) is None
    assert MyGrammar("herp derp").source(1000, optional=True) == 1110

    MyGrammar.printSource()
