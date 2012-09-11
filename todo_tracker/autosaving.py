from __future__ import absolute_import

import os
import subprocess
from datetime import datetime, timedelta
import time

save_dir = os.path.realpath(os.path.expanduser("~/.todo_tracker"))
save_file = os.path.join(save_dir, "life")
autosave_file = os.path.join(save_dir, "_life_autosave_%s")
backup_file = os.path.join(save_dir, "_life_backup_%s")
timeformat = "%A %B %d %H:%M:%S %Y"

class Git(object):
    def __init__(self, path):
        self.path = path

    def init(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            self._git("init")

    def gitignore(self, names):
        if not os.path.exists(os.path.join(self.path, ".gitignore")):
            writer = open(os.path.join(self.path, ".gitignore"), "w")
            for name in names:
                writer.write("%s\n" % name)
            

    def add(self, *filenames):
        self._git("add", *filenames)

    def commit(self, message):
        self._git("commit", "-m", message)

    def _git(self, *args):
        process = subprocess.Popen(["git"] + list(args), cwd=self.path)
        return process.wait()

def load(tracker):
    try:
        reader = open(os.path.realpath(save_file), "r")
    except IOError:
        # what do?
        pass
    else:
        tracker.load(reader)

def full_save(tracker):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    git = Git(save_dir)

    git.init()

    tracker.save(open(save_file, "w"))
    git.add(save_file)

    git.gitignore(["_*"])
    git.add(".gitignore")

    git.commit("Full save %s" % datetime.now().strftime(timeformat))
    tracker._last_full_save = datetime.now()

def defattr(obj, name, default):
    res = getattr(obj, name, default)
    setattr(obj, name, res)
    return res

def auto_save(tracker):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        last_auto_save = getattr(tracker, "_last_auto_save")
    except AttributeError:
        pass
    else:
        if datetime.now() < last_auto_save + timedelta(minutes=5):
            return
    autosave_id = defattr(tracker, "_autosave_id", time.time())
    
    tracker.save(open(autosave_file % str(int(autosave_id)), "w"))
    tracker._last_auto_save = datetime.now()

    backup_save(tracker)

def backup_save(tracker):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        last_auto_save = getattr(tracker, "_last_backup_save")
    except AttributeError:
        pass
    else:
        if datetime.now() < last_auto_save + timedelta(minutes=30):
            return
    
    tracker.save(open(autosave_file % str(int(time.time())), "w"))
    tracker._last_backup_save = datetime.now()
