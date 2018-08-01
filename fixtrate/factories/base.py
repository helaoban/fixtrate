import datetime as dt
from importlib import import_module

from .. import constants as fc


class FixMessageFactory:
    def __init__(self, conf):
        self.conf = conf
        self._mod = self.get_helper_mod()
        self.TAGS = getattr(fc.FixTag, conf.version.name)

    def get_helper_mod(self):
        version = self.conf.version.name.lower()
        mdl = import_module('.{}'.format(version, __name__))
        names = mdl.__dict__['__all__']
        for name in names:
            setattr(self, name, getattr(mdl, name))
    @staticmethod
    def __wrap_factory_func(func):
        def make(self, *args, **kwargs):
            msg = func(*args, **kwargs)
            self.append_standard_header(
                msg,
                kwargs.get('seq_num'),
                kwargs.get('timestamp')
            )
            return msg
        return make

    def append_standard_header(
        self,
        msg,
        seq_num=None,
        timestamp=None
    ):
        """
        Create a base message with standard headers set.
        BodyLength and Checksum are handled by SimpleFix

        :param msg:
        :param seq_num:
        :param timestamp:
        :return:
        """
        msg.append_pair(
            self.TAGS.BeginString,
            self.conf['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            self.TAGS.SenderCompID,
            self.conf['FIX_SENDER_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self.TAGS.TargetCompID,
            self.conf['FIX_TARGET_COMP_ID'],
            header=True
        )

        if seq_num:
            msg.append_pair(
                self.TAGS.MsgSeqNum,
                self.store.increment_local_sequence_number(),
                header=True
            )

        if timestamp is None:
            timestamp = dt.datetime.utcnow()

        msg.append_utc_timestamp(
            self.TAGS.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )