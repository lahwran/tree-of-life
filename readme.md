Tree of Life
============

A tool for managing your life, working backwards from goals and tasks;
starting all the way back from The Task: life.


Setting Up
----------

note: as a matter of habit, do not copy and paste into your terminal from the internet,
pages can do all sorts of trickery to hide text

1. start the backend

        # from your favorite projects directory:
        virtualenv treeoflife-ve
        cd treeoflife-ve

        # from the virtualenv directory:
        git clone <tree-of-life clone url>
        cd tree-of-life

        # from the git repo directory:
        source ../bin/activate
        python setup.py develop  # (or python setup.py install, if you're a hater)
        treeoflife-server

2. start a frontend
    - mac: `<your favorite projects directory>/treeoflife-ve/tree-of-life/Popup.app`  
      this app doesn't like to be started before the backend, so make sure that's running first.

    - web: go to http://localhost:18082/ui.html - someday I'll explain the reasoning behind that port

the server (treeoflife-server) can safely be ctrl+c'd without data loss (it will
commit an internal git repo.)


Commands
--------

**todo: explain what makes treeoflife unique;** the following command list doesn't really demonstrate it

some commands to get you started:


- `task: something` creates a task called something and activates it
- `edit` opens up vim in iterm (depends on osx, vim, and iterm; working on making this more flexible)
- `save` saves the backend, so you can see the current tree in ~/.treeoflife/life
- `next` goes to the next task (need to make this more logically sensible)
- `stop` will shut down the backend (shutting down the backend includes saving and committing the life file.)


Disclaimers and Warnings
------------------------

While I'm proud of some of this code, a lot of it is quite messy due to having
been written in just-get-it-working mode. If I explicitly say I like some code
in this repo and you think it's bad code, *then* please tell me so; but for the
time being please assume I know that I'm a horrible programmer who needs to
clean everything up :)

License
-------

All of my code here is licensed MIT. I haven't marked the files I wrote as such in
their headers yet, but anything in this repository that has is copyright to me is
licensed MIT.

