from distutils.util import strtobool
import os

from . import utils, constants

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
    """
    Wraps `dict` and adds some helpful methods for fetching config values
    from different sources and for validating.
    """

    def validate(self):
        """
        Validate config values

        :return:
        :raises: `ValueError` if incorrect value, `TypeError` if incorrect
            type.
        """
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
        """
        Build a :class:`~.fixtrate.config.Config` object from ENV variables.
        Will only fetch variables prepended with a given namespace string.

        :param namespace: (optional) The namespace used to look for appropriate
            ENV vars. Defaults to `'FIX_'`.
        :type namespace: str
        :return: :class:`~fixtrate.config.Config` object
        """
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
                             ''.format(['{}{}'.format(namespace, m) for m in missing]))
        config.validate()
        return config
