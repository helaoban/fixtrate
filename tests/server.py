import asyncio
import datetime as dt
import logging

from fixation import (
    tags, constants, message,
    exceptions, parse,
    version, store as fix_store,
    utils
)

logger = logging.getLogger(__name__)


class MockFixServer(object):

    def __init__(self, config=None, loop=None, store=None):
        self.reader = None
        self.writer = None
        self.store = store or fix_store.FixMemoryStore()
        self.config = config or config.FixConfig(
            host='localhost',
            port=8686,
            sender_comp_id='FIXTEST',
            version=version.FixVersion.FIX42,
            target_comp_id='TESTCLIENT'
        )
        self.loop = loop or asyncio.get_event_loop()
        self._closing = False

        self._last_message_time = None

    def reset_sequence_numbers(self, client_sequence_number):
        self.store.reset_local_sequence_number()
        self.store.set_remote_sequence_number(client_sequence_number)

    def send_message(self, msg):
        encoded = msg.encode()
        self.writer.write(encoded)

    def send_heartbeat(self, test_request_id=None):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_heartbeat_message(
            sequence_number,
            self.config,
            test_request_id=test_request_id
        )
        self.send_message(msg)

    def send_login(self):
        sequence_number = self.store.increment_local_sequence_number()
        login_msg = message.Message.create_login_message(
            sequence_number, self.config
        )
        self.send_message(login_msg)

    def send_reject(self, message, tag, rejection_type, reason):
        sequence_number = self.store.increment_local_sequence_number()
        ref_sequence_number = message.get(tags.FixTag.RefSeqNum)
        ref_message_type = message.get(tags.FixTag.MsgType)
        msg = message.Message.create_reject_message(
            sequence_number=sequence_number,
            config=self.config,
            ref_sequence_number=ref_sequence_number,
            ref_message_type=ref_message_type,
            ref_tag=tag,
            rejection_type=rejection_type,
            reject_reason=reason,
        )
        self.send_message(msg)

    def request_resend(self, start, end):
        sequence_number = self.store.increment_local_sequence_number()
        msg = message.Message.create_resend_request_message(
            sequence_number=sequence_number,
            config=self.config,
            start_sequence=start,
            end_sequence=end
        )
        self.send_message(msg)

    def check_sequence_integrity(self, message):
        seq_num = message.get(tags.FixTag.MsgSeqNum)
        recorded_seq_num = self.store.get_remote_sequence_number()
        seq_diff = int(seq_num) - int(recorded_seq_num)
        if seq_diff != 1:
            raise exceptions.SequenceGap

    def handle_message(self, message):
        self._last_message_time = dt.datetime.utcnow()

        try:
            self.check_sequence_integrity(message)
        except exceptions.SequenceGap:
            logger.error('Sequence gap!')
            self.handle_sequence_gap(message)
            return

        self.store.increment_remote_sequence_number()
        self.dispatch(message)

    def dispatch(self, message):
        msg_type = message.get(tags.FixTag.MsgType)

        try:
            msg_type = constants.FixMsgType(msg_type)
        except ValueError:
            logger.error('Unrecognized FIX value {}.'.format(msg_type))
            return

        handler = {
            constants.FixMsgType.MsgType_Heartbeat: self.handle_heartbeat,
            constants.FixMsgType.MsgType_Logon: self.handle_login,
            constants.FixMsgType.MsgType_TestRequest: self.handle_test_request,
        }.get(msg_type)

        if handler is not None:
            handler(message)

    def handle_heartbeat(self, message):
        pass

    def handle_test_request(self, message):
        test_request_id = message.get(tags.FixTag.TestReqID)
        self.send_heartbeat(test_request_id=test_request_id)

    def handle_sequence_gap(self, message):
        pass

    def handle_login(self, message):
        sequence_number = int(message.get(tags.FixTag.MsgSeqNum))

        heartbeat_interval = int(message.get(tags.FixTag.HeartBtInt))
        if heartbeat_interval != self.config.heartbeat_interval:
            self.send_reject(
                message=message,
                tag=tags.FixTag.HeartBtInt,
                rejection_type=constants.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='HeartBtInt must be {}'.format(self.config.heartbeat_interval)
            )
            return

        target_comp_id = message.get(tags.FixTag.TargetCompID).decode()
        if target_comp_id != self.config.sender_comp_id:
            self.send_reject(
                message=message,
                tag=tags.FixTag.TargetCompID,
                rejection_type=constants.SessionRejectReason.VALUE_IS_INCORRECT,
                reason='Target Comp ID is incorrect.'
            )
            return

        reset_seq_number = constants.ResetSeqNumFlag(message.get(tags.FixTag.ResetSeqNumFlag))
        if reset_seq_number == constants.ResetSeqNumFlag.YES:
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
                    self.config.heartbeat_interval
                )

                if self._last_message_time is None:
                    pass

                now = dt.datetime.utcnow()
                elapsed = now - self._last_message_time

                if elapsed.total_seconds() >= self.config.heartbeat_interval:
                    await self.send_heartbeat()

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
        self.writer.close()

    def __call__(self):
        coro = asyncio.start_server(
            self.listen,
            host=self.config.host,
            port=self.config.port,
            loop=self.loop
        )
        asyncio.ensure_future(coro, loop=self.loop)
        # return self.loop.run_until_complete(coro)
