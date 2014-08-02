from __future__ import unicode_literals, print_function

if __name__ == "__main__":
    import sys
    from treeoflife import searching
    if "create" in sys.argv:
        dothing = searching.parse_create
    else:
        dothing = searching.parse

    todofile = "/Users/lahwran/.treeoflife/life"
    from treeoflife.tracker import Tracker
    import time
    tracker = Tracker()
    with open(todofile, "r") as reader:
        tracker.deserialize({"life": reader.read()})

    while True:
        querytext = raw_input("query: ")
        import subprocess
        subprocess.call(["clear"])
        print("query:", querytext)
        a = time.time()
        queryer = dothing(querytext)
        b = time.time()
        print(queryer, b - a)

        inittime = time.time()
        results = queryer(tracker.root)
        finishtime = time.time()

        print()

        if hasattr(results, "list"):
            results = results.list()
            for x in results[:1000]:
                print( " > ".join([
                    str(node) for node in x.iter_parents()][::-1]))
            print()
            print(len(results), finishtime - inittime)
        else:
            print(results)
            print()
            print(1, finishtime - inittime)
