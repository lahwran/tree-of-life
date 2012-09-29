
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
        try:
            result = ""
            if getattr(self, "error_context", False):
                line = getattr(self.error_context, "line", None)
                if line is not None:
                    line = int(line) + 1 # zero indexed to human indexed
                    result = "At line %d: " % line
                else:
                    result = "At unknown line: "
            result += self._message
            return result
        except Exception as e:
            print e
            return self._message


class CantStartNodeError(LoadError):
    pass


class InvalidInputError(Exception):
    pass
