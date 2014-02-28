Hacking on treeoflife
=====================


The treeoflife system is divided up into two and a half main components:

- The python backend; generally speaking, this is responsible for managing the data
- (Potentially optional) the os embed; the only existing one is an OSX embed
- The frontend webpage; this is in charge of displaying data and sending user input commands to the backend


Backend
-------

.. testsetup:: backend_assertions
    import treeoflife.main
    assert treeoflife.main.JSONProtocol
    assert treeoflife.main.RemoteInterface
    assert treeoflife.main.main

The backend is made of several parts, more or less each nested inside each other.

1. The tree itself. Multiple trees may be loaded during the runtime
   of the backend; when a new one is loaded, the old one is discarded. The tree is
   represented as an instance of TreeRootNode, and its children.
2. The tracker object. This is responsible for holding on to the current tree root node,
   and provides methods for loading and unloading it from files and strings.
3. The CommandInterface class. This is a subclass of Tracker that provides methods
   for command line interfaces: tracker.command(), primarily.
4. The SavingInterface class. This is a subclass of CommandInterface that provides
   methods for saving, an autosave-check, and loading, from a centralized directory.
5. The RemoteInterface class. This is a subclass of SavingInterface that provides
   methods for use in treeoflife/main.py.
6. The JSONProtocol class. This is a twisted protocol class that implements the
   protocol that the UI code understands, and has a reference to the tracker object.
   There can be multiple instances of JSONProtocol, one for each connected client,
   but they will all share the same tracker object.

   JSONProtocol also keeps track of command history (probably
   the wrong thing to do that), of sending updates to the UI, and of handling
   messages coming in from the UI.

7. Misc twisted stuff, initiated from main(), restarter, etc. This code can be found at the bottom
   of treeoflife/main.py. 

Embed
-----

The embed is a small cocoa application based off of https://github.com/shpakovski/Popup.
its primary job is embedding webkit, but it also provides an object to the page's javascript
environment that can be used to control the displayed menu text and provides a socket for
communicating with the backend. It's available in the angular code as a service, or if you
must, it's available as a global object called tracker_api.

There's also an implementation of the tracker_api object's interface that uses websockets,
and stubs out the menu text controls. This is automatically switched to if you load the webpage
in a browser.


Webpage
-------



note: I used under_score_names in the js code, but I'm not hugely attached to them anymore. input welcome on js styling.
