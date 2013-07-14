import ometa
ometa.FAST = True
import parsley
from parsley import unwrapGrammar
from ometa.grammar import OMeta
from ometa.runtime import (ParseError, OMetaBase, EOFError, expected,
        InputStream)
import random
import string
import sys


class GrammarExtensions(OMetaBase):
    def __init__(self, input, *args, **kwargs):
        if not kwargs.get("stream", False) and not kwargs.get("tree", False):
            input = input.lower()
        super(GrammarExtensions, self).__init__(input, *args, **kwargs)

    def rule_s(self, tok):
        """
        Match and return the given string, consuming any preceding whitespace.
        """
        m = self.input
        try:
            for c in tok:
                v, e = self.exactly(c)
            return tok, e
        except ParseError, e:
            self.input = m
            raise e.withMessage(expected("string", tok))

    def exactly(self, string):
        return super(GrammarExtensions, self).exactly(string.lower())

    def _match_or_none(self, rulename, *args):
        def success():
            apply_result, err = self.apply(rulename, *args)
            self.considerError(err, None)
            return apply_result, self.currentError

        def failure():
            return None, self.input.nullError()

        result, err = self._or([success, failure])
        self.considerError(err, 'donk')

        self.input = InputStream(self.input.data, len(self.input.data))

        return result, self.currentError

utility_source = """
ws = ' '*
wss = ' '+
c_wss = ','? ' '+
number = <digit+>:ds -> int(ds)
number_2dg = <digit{1,2}>:ds -> int(ds)
"""

GrammarUtilities = OMeta.makeGrammar(utility_source, "GrammarBaseUtil")\
        .createParserClass(unwrapGrammar(GrammarExtensions), {})


class _GrammarMetaclass(type):
    def __new__(cls, name, bases, dct):
        if name == "__Grammar":  # for bootstrapping
            name = "Grammar"
            return type.__new__(cls, name, bases, dct)

        assert "grammar" in dct, ("Grammar subclasses must have "
                                "'grammar' attribute")
        assert bases == (Grammar,), ("_GrammarMetaclass must only be used"
                                "from Grammar subclasses")
        source = dct["grammar"]
        bindings = dct.get("bindings", {})
        superclass = dct.get("superclass", GrammarUtilities)

        grammar_class = OMeta.makeGrammar(source, "_" + name)\
                .createParserClass(unwrapGrammar(superclass), bindings)
        dct["_grammarClass"] = grammar_class

        return type.__new__(cls, name, bases, dct)


class __Grammar(object):  # Funny name for bootstrapping
    """
    copy of parsley._GrammarWrapper, with metaclass steroids
    docstring stuff removed because docstrings should describe only
    the nonobvious when they're for the original writer
    """
    __metaclass__ = _GrammarMetaclass

    def __init__(self, input):
        self._grammar = self._grammarClass(input)
        self._input = input

    def __getattr__(self, name):
        def invokeRule(*args, **kwargs):
            """
            Invoke a Parsley rule. Passes any positional args to the rule.
            """
            optional = kwargs.get("optional", False)
            try:
                if optional:
                    ret, err = self._grammar._match_or_none(name, *args)
                else:
                    ret, err = self._grammar.apply(name, *args)
            except ParseError, e:
                err = e
            else:
                try:
                    extra, _ = self._grammar.input.head()
                except EOFError:
                    return ret
            raise err
        return invokeRule

    @classmethod
    def wraprule(cls, name, optional=False):
        def wrapper(string, *args, **kwargs):
            _optional = kwargs.get("optional", optional)
            func = getattr(cls(string), name)
            return func(*args, optional=_optional)
        return wrapper

    @classmethod
    def printSource(cls):
        print sys.modules[cls._grammarClass.__module__].__loader__.source


# de-bootstrap the metaclass
Grammar = __Grammar
del __Grammar
