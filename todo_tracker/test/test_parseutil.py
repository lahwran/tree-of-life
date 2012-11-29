from todo_tracker import parseutil
import parsley


def test_grammar():
    class MyGrammar(parseutil.Grammar):
        grammar = """
            herp = '12'
        """

    assert MyGrammar("12").herp() == "12"
