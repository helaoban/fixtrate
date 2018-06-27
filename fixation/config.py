import os

from fixation import version as fix_version, utils, constants


class FixConfig(object):
    def __init__(
        self,
        version,
        host,
        port,
        sender_comp_id,
        target_comp_id,
        heartbeat_interval=30,
        reset_sequence=True,
        encrypt_method=constants.EncryptMethod.NONE,
    ):
        self.version = version
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.heartbeat_interval = heartbeat_interval
        self.reset_sequence = reset_sequence
        self.host = host
        self.port = port

        self.encrypt_method = encrypt_method

    def validate(self):
        errors = {}

        try:
            self.version = fix_version.FixVersion(self.version)
        except ValueError:
            errors['version'] = '{} is not a valid FIX version'.format(self.version)

        try:
            utils.validate_ip_address(self.host)
        except ValueError:
            errors['host']: '{} is not a valid IP address'.format(self.host)

        try:
            utils.validate_port(self.port)
        except ValueError:
            errors['port']: '{} is not a valid port number'.format(self.port)


def get_config_from_env():

    required = [
        'FIX_VERSION',
        'FIX_HOST',
        'FIX_PORT',
        'FIX_SENDER_COMP_ID',
        'FIX_TARGET_COMP_ID'
    ]

    missing = []
    for var in required:
        if var not in os.environ:
            missing.append(var)

    if missing:
        raise ValueError('The following env vars are not set: {}'
                         ''.format(missing))

    values = {var: os.environ.get(var) for var in required}

    FixConfig(
        version=fix_version.FixVersion(values['FIX_VERSION']),
        host=values['FIX_HOST'],
        port=values['FIX_PORT'],
        sender_comp_id=values['FIX_SENDER_COMP_ID'],
        target_comp_id=values['FIX_TARGET_COMP_ID']
    )
