from distutils.util import strtobool
import os

from .utils.validators import validate_ip_address, validate_port
from .constants import FixVersion


default_config = {
    'VERSION': FixVersion.FIX42,
    'HEARTBEAT_INTERVAL': 30,
}


class Config(dict):
    """
    Wraps `dict` and adds some helpful methods for fetching config values
    from different sources and for validating.
    """

    OPTIONS = {
        ('VERSION', str, True),
        ('SENDER_COMP_ID', str, True),
        ('TARGET_COMP_ID', str, True),
        ('HOST', str, False),
        ('PORT', int, False),
        ('HEARTBEAT_INTERVAL', int, False),
        ('SESSION_QUALIFIER', int, False),
    }

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})

    def validate(self):
        """
        Validate config values

        :return:
        :raises: `ValueError` if incorrect value, `TypeError` if incorrect
            type.
        """
        missing = []
        for name, _type, required in self.OPTIONS:
            if name not in self:
                if required:
                    missing.append(name)
            continue

            if not isinstance(self[name], _type):
                raise TypeError(
                    'Expected {} to be {}, but instead was {}'
                    ''.format(name, _type, type(self[name]))
                )

        if missing:
            raise ValueError(
                'Missing required config variables: {}'
                ''.format(', '.join(missing)))

        try:
            self['VERSION'] = FixVersion(self['VERSION'])
        except ValueError:
            raise ValueError(
                '{} is not a valid FIX version'
                ''.format(self['VERSION']))

        if 'HOST' in self:
            try:
                validate_ip_address(self['HOST'])
            except ValueError:
                raise ValueError(
                    '{} is not a valid IP address'
                    ''.format(self['HOST']))

        if 'PORT' in self:
            try:
                validate_port(self['PORT'])
            except ValueError:
                raise ValueError(
                    '{} is not a valid port number'
                    ''.format(self['PORT']))

    def from_env(self, namespace='FIX_'):
        """Update the config object from ENV variables. Will only fetch variables
        prepended with a given namespace string.

        :param namespace: (optional) The namespace used to look for appropriate
            ENV vars. Defaults to `'FIX_'`.
        :type namespace: str
        :return: None
        """
        for name, _type, _ in self.OPTIONS:
            val = os.environ.get(namespace + name)
            if val is None:
                continue
            if _type == bool:
                val = bool(strtobool(val))
            else:
                val = _type(val)
            self[name] = val
