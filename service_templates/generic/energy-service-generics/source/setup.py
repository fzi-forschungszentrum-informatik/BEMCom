#!/usr/bin/env python3
"""
"""
from setuptools import setup, find_packages
from distutils.util import convert_path

# Fetch version from file as suggested here:
# https://stackoverflow.com/a/24517154
main_ns = {}
ver_path = convert_path("esg/_version.py")
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

# fmt: off
setup(
    name="esg",
    version=main_ns["__version__"],
    packages=find_packages(),
)
# fmt: on
