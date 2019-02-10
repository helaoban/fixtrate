"""
:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:copyright: (c) 2019 by Carlo Holl
"""
from fixtrate.transport.tcp import TCPTransport
from fixtrate.utils import urlparse


class DuplicateScheme(Exception):
    pass


class TransportRegistry(object):
    def __init__(self, transports=None):
        # setup a default list of senders
        self._schemes = {}
        self._transports = {}

        if transports:
            for transport in transports:
                self.register_transport(transport)

    def register_transport(self, transport):
        if (
            not hasattr(transport, 'scheme') or
            not hasattr(transport.scheme, '__iter__')
        ):
            raise AttributeError(
                'Transport %s must have a scheme list',
                transport.__class__.__name__)

        for scheme in transport.scheme:
            self.register_scheme(scheme, transport)

    def register_scheme(self, scheme, cls):
        """
        It is possible to inject new schemes at runtime
        """
        if scheme in self._schemes:
            raise DuplicateScheme()

        urlparse.register_scheme(scheme)
        self._schemes[scheme] = cls

    def supported_scheme(self, scheme):
        return scheme in self._schemes

    def get_transport_cls(self, scheme):
        return self._schemes[scheme]


default_transports = [
    TCPTransport
]
