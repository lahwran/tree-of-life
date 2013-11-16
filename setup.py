from setuptools import setup, find_packages

setup(
        name="treeoflife",
        description="A Tree of Life",
        version="0.2",
        packages=find_packages(),
        license='MIT',
        author="lahwran",
        author_email="lahwran0@gmail.com",
        scripts=["bin/todo-tracker"],
        install_requires=["twisted", "parsley", "pytest", "pep8", "txws",
            "raven"]
)
