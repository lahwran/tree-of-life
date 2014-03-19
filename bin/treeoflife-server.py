#!/usr/bin/env python
# windows version
try:
    import os, sys

    try:
        import _preamble
    except ImportError:
        sys.exc_clear()

    import treeoflife.tracker # primary module entry point
    from treeoflife import main
    main._main()

except:
    import traceback
    traceback.print_exc()
print("")
print("")
raw_input("        Press enter to close\n\n ->")
