import sys
import xtraceback

from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import CommandInterface, command, generate_listing

class CommandLineInterface(CommandInterface):
    max_ps1_len = 47

    def _format_active(self):
        items = []
        result = ""
        for node in self.displaychain():
            items.append(str(node))
            result = " > ".join(items[::-1])
            if len(result) > self.max_ps1_len:
                break
            
        minchar = min(0, len(result) - self.max_ps1_len)
        if minchar > 0:
            result = "..." + result[minchar:]

        return result

    def prompt(self):
        return "[%s] > " % self._format_active()

    def _run_vim(self, source, callback, *filenames):
        import subprocess
        process = subprocess.Popen(["vim", "-o", "--"] + list(filenames))
        process.wait()
        callback()

    def display_lines(self, lines):
        print "\n".join(lines)

class ExitMainloop(BaseException):
    pass

@command
def quit(event):
    raise ExitMainloop

@command
def pdb(event):
    import pdb; pdb.set_trace()

@command("list")
def list_current(event):
    event.ui.display_lines(lines)

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

            commandline.command(None, line)
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
