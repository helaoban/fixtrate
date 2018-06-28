from distutils.util import strtobool
import os

from fixation import utils, constants

REQUIRED = [
    ('FIX_VERSION', constants.FixVersion),
    ('FIX_HOST', str),
    ('FIX_PORT', int),
    ('FIX_SENDER_COMP_ID', str),
    ('FIX_TARGET_COMP_ID', str),
    ('FIX_ACCOUNT', str),
    ('FIX_HEARTBEAT_INTERVAL', int),
    ('FIX_RESET_SEQUENCE', bool),
]


def validate_config(config):
    for name, _type in REQUIRED:
        if name not in config:
            raise ValueError(
                'Missing required config variable: {}'
                ''.format(name))

        if not isinstance(config[name], _type):
            print(_type)
            raise TypeError(
                'Expected {} to be {}, but instead was {}'
                ''.format(name, _type, type(config[name]))
            )

    try:
        config['FIX_VERSION'] = constants.FixVersion(config['FIX_VERSION'])
    except ValueError:
        raise ValueError(
            '{} is not a valid FIX version'
            ''.format(config['FIX_VERSION']))

    try:
        utils.validate_ip_address(config['FIX_HOST'])
    except ValueError:
        raise ValueError(
            '{} is not a valid IP address'
            ''.format(config['FIX_HOST']))

    try:
        utils.validate_port(config['FIX_PORT'])
    except ValueError:
        raise ValueError(
            '{} is not a valid port number'
            ''.format(config['FIX_PORT']))


def get_config_from_env():

    missing = []
    config = {}
    for name, _type in REQUIRED:
        try:
            val = os.environ[name]
        except KeyError:
            missing.append(name)
            continue

        if _type == bool:
            val = bool(strtobool(val))
        else:
            val = _type(val)

        config[name] = val

    if missing:
        raise ValueError('The following env vars are not set: {}'
                         ''.format(missing))

    validate_config(config)
    return config
