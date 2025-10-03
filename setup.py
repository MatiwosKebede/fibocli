# setup.py
from setuptools import setup, find_packages

setup(
    name="fibocli",
    version="0.1",
    py_modules=["cli", "algorithms", "models", "db", "settings", "utils", "seeds", "output", "tests"],
    install_requires=[
        "click",
    ],
    entry_points={
        "console_scripts": [
            "fibocli=cli:cli",
        ],
    },
)

