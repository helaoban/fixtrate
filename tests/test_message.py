import pytest

from fixation import message, tags


def test_reject_empty_value(client_config):
    msg = message.Message(config=client_config)
    with pytest.raises(ValueError):
        msg.append_pair(tags.FixTag.Text, b'')
