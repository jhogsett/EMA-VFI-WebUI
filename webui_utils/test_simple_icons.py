# import os
# import pytest # pylint: disable=import-error
from .test_shared import *
from .simple_icons import *

GOOD_EXAMPLES = [
    (SimpleIcons.SYMBOLS, 7, 9),
    (SimpleIcons.APP_ICONS, 40, 56)]

def test_SimpleIcons():
    for example, expected_items, expected_len in GOOD_EXAMPLES:
        assert len(example) == expected_items
        assert len(("").join(example)) == expected_len
