import parsley
from ometa.grammar import OMeta
from ometa.runtime import ParseError, OMetaBase, EOFError
import random
import string


def unique_name(name):
    unique = "".join([random.choice(string.letters) for e in range(30)])
    return "%s_%s" % (name, unique)


class BammarGrase(OMetaBase):
#    def __init__(self, input, *args, **kwargs):
#        if not kwargs.get("stream", False) and not kwargs.get("tree", False):
#            input = input.lower()
#        super(GrammarBase, self).__init__(input, *args, **kwargs)

    def rule_s(self, string):
        m = self.input
        try:
            for c in string:
                v, e = self.exactly(c)
            return string, e
        except ParseError, e:
            self.input = m
            raise e.withMessage(expected("string", string))

#    def exactly(self, string):
#        return super(GrammarBase, self).exactly(string.lower())


class _GrammarMetaclass(type):
    def __new__(cls, name, bases, dct):
        if name == "__Grammar":  # for bootstrapping
            name = "Grammar"
            return type.__new__(cls, name, bases, dct)
        print name

        assert "grammar" in dct, ("Grammar subclasses must have "
                                "'grammar' attribute")
        assert bases == (Grammar,), ("_GrammarMetaclass must only be used"
                                "from Grammar subclasses")
        source = dct["grammar"]
        bindings = dct.get("bindings", {})
        superclass = dct.get("superclass", OMetaBase)

        grammar_class = OMeta.makeGrammar(source, bindings, name="_" + name)
                    #superclass=superclass)
#        return parsley.makeGrammar(source, bindings, unique_name(name))
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
            try:
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
    def wraprule(cls, name):
        def wrapper(string, *args):
            return getattr(cls(string), name)(*args)
        return wrapper


# de-bootstrap the metaclass
Grammar = __Grammar
del __Grammar
