#!/usr/bin/env python3
"""
Enable pytest to show differences and help on assert failures
as suggested here:
https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting
"""
import sys
import pytest

# This emits a warning (Module already imported so cannot be
# rewritten: esg.test) It's actually not a problem but apparently
# cannot be captured here.
pytest.register_assert_rewrite("esg.test")
