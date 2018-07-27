from distutils.util import strtobool
import os

from fixation import utils, constants

REQUIRED = [
    ('VERSION', constants.FixVersion),
    ('HOST', str),
    ('PORT', int),
    ('SENDER_COMP_ID', str),
    ('TARGET_COMP_ID', str),
    ('ACCOUNT', str),
    ('HEARTBEAT_INTERVAL', int),
]


class Config(dict):

    def validate(self):
        for name, _type in REQUIRED:
            if name not in self:
                raise ValueError(
                    'Missing required config variable: {}'
                    ''.format(name))

            if not isinstance(self[name], _type):
                raise TypeError(
                    'Expected {} to be {}, but instead was {}'
                    ''.format(name, _type, type(self[name]))
                )

        try:
            self['VERSION'] = constants.FixVersion(self['VERSION'])
        except ValueError:
            raise ValueError(
                '{} is not a valid FIX version'
                ''.format(self['VERSION']))

        try:
            utils.validate_ip_address(self['HOST'])
        except ValueError:
            raise ValueError(
                '{} is not a valid IP address'
                ''.format(self['HOST']))

        try:
            utils.validate_port(self['PORT'])
        except ValueError:
            raise ValueError(
                '{} is not a valid port number'
                ''.format(self['PORT']))

    @classmethod
    def from_env(cls, namespace='FIX_'):
        missing = []
        config = cls()
        for name, _type in REQUIRED:
            try:
                val = os.environ[namespace + name]
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
        config.validate()
        return config
