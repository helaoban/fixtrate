"""
    fixtrate.signals

    AsyncSignal shamelessly taken from:
    https://github.com/jucacrispim/asyncblink/blob/master/asyncblink.py
"""
from asyncio import ensure_future
import inspect

from blinker import Signal


class AsyncSignal(Signal):

    def __init__(self, *args, **kwargs):
        self.scheduler = kwargs.pop('scheduler', ensure_future)
        super().__init__(*args, **kwargs)

    def send(self, *sender, **kwargs):
        ret = []
        for receiver, value in super().send(*sender, **kwargs):
            if self._is_future(value):
                value = self.scheduler(value)

            ret.append((receiver, value))

        return ret

    def _is_future(self, val):
        return inspect.isawaitable(val)


class NamedAsyncSignal(AsyncSignal):

    def __init__(self, name, doc=None):
        super().__init__(doc)
        self.name = name

    def __repr__(self):
        base = super(NamedAsyncSignal, self).__repr__()
        return "%s; %r>" % (base[:-1], self.name)


class Namespace(dict):
    def signal(self, name, doc=None):
        try:
            return self[name]
        except KeyError:
            return self.setdefault(name, NamedAsyncSignal(name, doc))


_signals = Namespace()

message_received = _signals.signal('message-received')
message_sent = _signals.signal('message-sent')
sequence_gap = _signals.signal('sequence-gap')
