import pytest

from fixtrate import constants as fc, message


def test_reject_empty_value():
    msg = message.FixMessage()
    with pytest.raises(ValueError):
        msg.append_pair(fc.FixTag.FIX44.Text, b'')
