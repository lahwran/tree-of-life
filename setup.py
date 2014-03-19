#!/usr/bin/env python
from setuptools import setup, find_packages

import platform
if platform.system() == "Windows":
    mainscript = "bin/treeoflife-server.py"
else:
    mainscript = "bin/treeoflife-server"

setup(
        name="treeoflife",
        description="A Tree of your Life (end-user application)",
        version="1",
        packages=find_packages(),
        license='MIT',
        author="lahwran",
        author_email="lahwran0@gmail.com",
        url="https://github.com/lahwran/tree-of-life",
        scripts=[mainscript],
        install_requires=[
            "twisted",
            "parsley",
            "pytest",
            "pep8",
            "txws",
            "raven",
            "sphinx",
        ],
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Web Environment',
            'Environment :: MacOS X',
            'Framework :: Twisted',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: MacOS :: MacOS X',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 2 :: Only',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Objective C',
            'Topic :: Office/Business :: Scheduling',
            'Topic :: Software Development :: Bug Tracking'
        ]
)
