import ipaddress


def validate_ip_address(address):
    ipaddress.ip_address(address)


def validate_port(port):
    port = str(port)
    if not port.isdigit():
        raise ValueError
    if int(port) not in range(1, 65535 + 1):
        raise ValueError


def validate_option(key, options, label):

    val = options.get(key)
    if val is None:
        raise ValueError(
            'Invalid {} type, expected one of: {}'
            ''.format(label, options)
        )
    return val
