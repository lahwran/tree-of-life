from setuptools import setup, find_packages

setup(
        name="todo_tracker",
        version="0.1.dev0",
        packages=find_packages(),
        scripts=["bin/todo-tracker"],
        install_requires=["twisted", "parsley", "pytest", "pep8"]
)
