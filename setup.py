import inspect
import os
import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup
from setuptools.command.test import test as TestCommand

__location__ = os.path.join(
    os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe()))
)

version = "1.0.0"

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def get_install_requirements(path):
    content = open(os.path.join(__location__, path)).read()
    requires = [req for req in content.split("\\n") if req != ""]
    return requires


setup(
    name="pagecache_tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=version,
    description="Set of tools to monitor memory activity.",
    author="Sergio Troiano",
    author_email="sergio_troiano@hotmail.com",
    packages=find_packages(),
    install_requires=get_install_requirements("requirements/requirements.txt"),
    test_suite="tests",
    zip_safe=False,
    entry_points={"console_scripts": ["pagecache_hit_miss=pagecache_tools.pagecache_hit_miss.cli:main"]},
)
