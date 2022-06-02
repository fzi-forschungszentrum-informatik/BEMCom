#!/usr/bin/env python3
"""
"""
from dotenv import load_dotenv, find_dotenv

# This import is all we need to make `esg.__version__` possible.
from esg._version import __version__  # NOQA


# dotenv allows us to load env variables from .env files which is
# convient for developing. If you set override to True tests
# may fail as the tests assume that the existing environ variables
# have higher priority over ones defined in the .env file.
load_dotenv(find_dotenv(), verbose=True, override=False)
