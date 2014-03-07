Tree of Life
============

A tool for managing your life, working backwards from goals and tasks;
starting all the way back from The Task: life.


Setting Up
----------

note: as a matter of habit, do not copy and paste into your terminal from the internet,
pages can do all sorts of trickery to hide text

#### Download

    git clone https://github.com/lahwran/tree-of-life.git
    git submodule init
    git submodule update

#### install dependencies

*Note:* I haven't tested on windows yet, and installing dependencies is known to be
a pain on windows. You may have to install twisted manually if you don't use pypy,
and if you do use pypy, I have no idea whether this will work. Windows users get
to wing it for the time being, but please complain :)

- **Make sure you have virtualenv installed**.
  it varies, but there's a distro package on most linuxes that
  provides it. on mac, or on linux that doesn't provide it
  (`easy_install` assumed to be available):

        which pip || sudo easy_install pip
        which virtualenv || sudo pip install virtualenv

- **with `pypy` - optional, but highly recommended for speed;** can cause pain on
  windows and some linuxes. if so, try without it.

        # download the latest version for your operating system from http://pypy.org/download.html
        # extract somewhere; for example, you might extract it to ~/Downloads/pypy-2.2.1/
        cd ~/tree-of-life  # (where ever you git cloned to)`
        virtualenv -p ~/Downloads/pypy-2.2.1/ ve-pypy-2.7  # Create a virtualenv using that pypy; name it ve-<something>`
        source ve-pypy-2.7/bin/activate  # activate the virtualenv`

- **with your regular `python` - slower, but potentially more compatible**

        cd ~/tree-of-life  # (where ever you git cloned to)
        virtualenv ve-cpython-2.7  # Create a virtualenv using system python-2.7; name it ve-<something>
        source ve-cpython-2.7/bin/activate # activate the virtualenv

Now that you have a virtualenv (or, if you're on windows, are being brave and
trying without one), run:

    python setup.py develop
    # some people have moral issues with "develop"; if you do,
    # feel free to use "install" instead. it's less convenient, though.

#### Start the backend

    treeoflife-server

can safely be ctrl+c'd without data loss (it will
commit an internal git repo, ~/.treeoflife)

#### Start a frontend

- web: go to http://localhost:18082/ui.html - someday I'll explain the reasoning behind that port
- mac menu bar: `open ~/tree-of-life/Popup.app`.
  this app doesn't like to be started before the backend, so make sure that's running first. I'll
  get around to making it retry soon...

Commands
--------

**todo: explain what makes treeoflife unique;** the following command list doesn't really demonstrate it

some commands to get you started:


- `task: something` creates a task called something and activates it
- `edit` opens up an editor; by default, codemirror. use --editor=vim-iterm to the server to use vim in iterm, if you're on mac
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

