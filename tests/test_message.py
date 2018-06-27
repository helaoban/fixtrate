import pytest

import fixation.constants
from fixation import message


def test_reject_empty_value(client_config):
    msg = message.Message(config=client_config)
    with pytest.raises(ValueError):
        msg.append_pair(fixation.constants.FixTag.Text, b'')
