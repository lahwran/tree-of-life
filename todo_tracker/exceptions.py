
class ListIntegrityError(Exception):
    pass

class LoadError(Exception):
    def __init__(self, message):
        self._message = message
        self.error_context = None

    @property
    def message(self):
        return str(self)

    def __str__(self):
        result = ""
        if self.error_context:
            result = "At line %d: " % (self.error_context.line + 1) # zero indexed to human indexed
        result += self._message
        return result


class CantStartNodeError(LoadError):
    pass

