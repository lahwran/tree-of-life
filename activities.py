import sys
import xtraceback

from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import CommandLineInterface, command

class ExitMainloop(BaseException):
    pass

@command
def quit(event):
    raise ExitMainloop

@command
def pdb(event):
    import pdb; pdb.set_trace()

def main(filename):
    tracker = Tracker()
    try:
        reader = open(filename, "r")
    except IOError:
        pass
    else:
        tracker.load(reader)

    commandline = CommandLineInterface(tracker)

    while True:
        try:
            line = raw_input(commandline.prompt()).strip()

            commandline.command(line)
        except (KeyboardInterrupt, EOFError, ExitMainloop) as e:
            print
            break
        except Exception:
            print xtraceback.XTraceback(*sys.exc_info(), color=False)

    tracker.save(open(filename, "w"))


if __name__ == "__main__":
    name = "activities"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    main(name)
