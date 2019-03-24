import os

import pytest

from fixtrate import (
    constants as fc,
    dictionary as fd
)
from fixtrate.factories import fix42

here = os.path.dirname(__file__)



@pytest.fixture
def fix_dict():
    return fd.FixDictionary.from_xml(os.path.join(here, 'gemini-fix-dictionary.xml'))


def test_correctly_validates_msg(fix_dict, order_request):
    fix_dict.validate_msg(order_request)

