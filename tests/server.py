import asyncio
import datetime as dt
import logging

from fixation import (
    constants as fc,
    exceptions, parse,
    store as fix_store,
)
from fixation.factories import fix42

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(self, config=None, loop=None, store=None):
        self.reader = None
        self.writer = None
        self.store = store or fix_store.FixMemoryStore()
        self.config = config or {
            'FIX_HOST': 'localhost',
            'FIX_PORT': 8686,
            'FIX_SENDER_COMP_ID': 'FIXTEST',
            'FIX_VERSION': fc.FixVersion.FIX42,
            'FIX_TARGET_COMP_ID': 'TESTCLIENT',
        }
        self.loop = loop or asyncio.get_event_loop()
        self._closing = False

        self._last_message_time = None
        self.TAGS = getattr(fc.FixTag, self.config['FIX_VERSION'].name)

    def append_standard_header(
        self,
        msg,
        timestamp=None
    ):
        """
        Create a base message with standard headers set.
        BodyLength and Checksum are handled by SimpleFix

        :param msg:
        :param timestamp:
        :return:
        """
        msg.append_pair(
            self.TAGS.BeginString,
            self.config['FIX_VERSION'],
            header=True
        )
        msg.append_pair(
            self.TAGS.SenderCompID,
            self.config['FIX_SENDER_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self.TAGS.TargetCompID,
            self.config['FIX_TARGET_COMP_ID'],
            header=True
        )
        msg.append_pair(
            self.TAGS.MsgSeqNum,
            self.store.increment_local_sequence_number()
        )

        if timestamp is None:
            timestamp = dt.datetime.utcnow()

        msg.append_utc_timestamp(
            self.TAGS.SendingTime,
            timestamp=timestamp,
            precision=6,
            header=True
        )

    def reset_sequence_numbers(self, client_sequence_number):
        self.store.reset_local_sequence_number()
        self.store.set_remote_sequence_number(client_sequence_number)

    def send_message(self, msg):
        self.append_standard_header(msg)
        self.writer.write(msg.encode())

    def send_heartbeat(self, test_request_id=None):
        msg = fix42.heartbeat(
            test_request_id=test_request_id
        )
        self.send_message(msg)

    def send_login(self):
        login_msg = fix42.logon()
        self.send_message(login_msg)

    def send_reject(self, msg, tag, rejection_type, reason):
        ref_sequence_number = msg.get(self.TAGS.MsgSeqNum)
        ref_message_type = msg.get(self.TAGS.MsgType)
        msg = fix42.reject(
            ref_sequence_number=ref_sequence_number,
            ref_message_type=ref_message_type,
            ref_tag=tag,
            rejection_type=rejection_type,
            reject_reason=reason,
        )
        self.send_message(msg)

    def request_resend(self, start, end):
        msg = fix42.resend_request(
            start_sequence=start,
            end_sequence=end
        )
        self.send_message(msg)

    def check_sequence_integrity(self, msg):
        seq_num = msg.get(self.TAGS.MsgSeqNum)
        recorded_seq_num = self.store.get_remote_sequence_number()
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_message(self, msg):
        self._last_message_time = dt.datetime.utcnow()

        try:
            self.check_sequence_integrity(msg)
        except exceptions.SequenceGap:
            logger.error('Sequence gap!')
            self.handle_sequence_gap(msg)
            return

        self.store.increment_remote_sequence_number()
        self.dispatch(msg)

    def dispatch(self, msg):
        msg_type = msg.get(self.TAGS.MsgType)

        try:
            msg_type = fc.FixMsgType(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX value {}.'.format(msg_type))
            return

        handler = {
            fc.FixMsgType.Heartbeat: self.handle_heartbeat,
            fc.FixMsgType.Logon: self.handle_login,
            fc.FixMsgType.TestRequest: self.handle_test_request,
        }.get(msg_type)

        if handler is not None:
            handler(msg)

    def handle_heartbeat(self, msg):
        pass

    def handle_test_request(self, msg):
        test_request_id = msg.get(self.TAGS.TestReqID)
        self.send_heartbeat(test_request_id=test_request_id)

    def handle_sequence_gap(self, msg):
        pass

    def handle_login(self, msg):
        sequence_number = int(msg.get(self.TAGS.MsgSeqNum))
        heartbeat_interval = int(msg.get(self.TAGS.HeartBtInt))
        if heartbeat_interval != self.config['FIX_HEARTBEAT_INTERVAL']:
            self.send_reject(
                msg=msg,
                tag=self.TAGS.HeartBtInt,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='HeartBtInt must be {}'.format(
                    self.config['FIX_HEARTBEAT_INTERVAL'])
            )
            return

        target_comp_id = msg.get(self.TAGS.TargetCompID)
        if target_comp_id != self.config['FIX_SENDER_COMP_ID']:
            self.send_reject(
                msg=msg,
                tag=self.TAGS.TargetCompID,
                rejection_type=fc.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Target Comp ID is incorrect.'
            )
            return

        reset_seq_number = (
            msg.get(self.TAGS.ResetSeqNumFlag)
            or fc.ResetSeqNumFlag.NO
        )
        reset_seq_number = fc.ResetSeqNumFlag(reset_seq_number)
        if reset_seq_number == fc.ResetSeqNumFlag.YES:
            self.reset_sequence_numbers(sequence_number)
            self.send_login()
        else:
            stored_sequence_number = self.store.get_remote_sequence_number()
            sequence_diff = sequence_number - stored_sequence_number

            if sequence_diff > 0:
                self.send_login()
                self.request_resend(
                    start=stored_sequence_number,
                    end=b'0'
                )
            elif sequence_diff < 0:
                self.shutdown()
                return
            else:
                self.send_heartbeat()

        self.loop.create_task(self.monitor_connection())

    async def monitor_connection(self):
        try:

            while True:
                await asyncio.sleep(
                    self.config['FIX_HEARTBEAT_INTERVAL']
                )

                if self._last_message_time is None:
                    pass

                now = dt.datetime.utcnow()
                elapsed = now - self._last_message_time

                if elapsed.total_seconds() >= self.config['FIX_HEARTBEAT_INTERVAL']:
                    self.send_heartbeat()

        except asyncio.CancelledError:
            pass

    async def listen(self, reader, writer):
        self.reader = reader
        self.writer = writer

        parser = parse.FixParser(config=self.config)

        while not self._closing:
            data = await reader.read(100)
            parser.append_buffer(data)

            msg = parser.get_message()
            if msg is None:
                continue

            self.handle_message(msg)

    def shutdown(self):
        self._closing = True
        if self.writer:
            self.writer.close()

    def __call__(self):
        coro = asyncio.start_server(
            self.listen,
            host=self.config['FIX_HOST'],
            port=self.config['FIX_PORT'],
            loop=self.loop
        )
        asyncio.ensure_future(coro, loop=self.loop)
