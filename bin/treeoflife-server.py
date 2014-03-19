#!/usr/bin/env python
# windows version
import os, sys

try:
    import _preamble
except ImportError:
    sys.exc_clear()

import treeoflife.tracker # primary module entry point
from treeoflife import main
main._main()
