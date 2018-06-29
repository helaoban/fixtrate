import simplefix
import sys

from fixation import utils, constants as fc


@utils.monkeypatch_module(simplefix.message)
def fix_val(value):

    # Enum support
    try:
        value = value.value
    except AttributeError:
        pass

    if isinstance(value, (bytes, str,)):
        if len(value) < 1:
            raise ValueError('FIX value cannot be empty!')
        try:
            value = value.encode()
        except AttributeError:
            pass
        return value
    else:
        return bytes(str(value), 'ASCII')


@utils.monkeypatch_module(simplefix.message)
def fix_tag(value):
    """Make a FIX tag value from string, bytes, integer, or Enum"""

    # Enum support
    try:
        value = value.value
    except AttributeError:
        pass

    if sys.version_info[0] == 2:
        return bytes(value)
    else:
        if type(value) == bytes:
            return value
        elif type(value) == str:
            return value.encode('ASCII')
        return str(value).encode('ASCII')


class FixMessage(simplefix.FixMessage):

    def encode(self, raw=False):
        if not raw:
            if not self.get(fc.FixTag.SendingTime):
                self.append_utc_timestamp(
                    fc.FixTag.SendingTime,
                    precision=6,
                    header=True
                )
        return super().encode(raw=raw)

    def get(self, tag, *args, **kwargs):
        try:
            tag = tag.value
        except AttributeError:
            pass
        return super().get(tag, *args, **kwargs)

    @classmethod
    def create_heartbeat_message(
        cls,
        test_request_id=None
    ):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.Heartbeat
        )
        if test_request_id:
            msg.append_pair(fc.FixTag.TestReqID, test_request_id)
        return msg

    @classmethod
    def create_test_request_message(
        cls,
        test_request_id=None,
    ):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.TestRequest
        )
        if test_request_id is None:
            test_request_id = utils.gen_uuid()
        msg.append_pair(fc.FixTag.TestReqID, test_request_id)
        return msg

    @classmethod
    def create_logoff_message(cls):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.Logout,
            header=True
        )
        return msg

    @classmethod
    def create_login_message(
        cls,
        encrypt_method=fc.EncryptMethod.NONE,
        heartbeat_interval=30,
        reset_sequence=False
    ):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.Logon,
        )
        msg.append_pair(
            fc.FixTag.EncryptMethod,
            encrypt_method,
            fc.EncryptMethod.NONE.value
        )
        msg.append_pair(
            fc.FixTag.HeartBtInt,
            heartbeat_interval
        )
        if reset_sequence:
            msg.append_pair(fc.FixTag.ResetSeqNumFlag, 'Y')
        return msg

    @classmethod
    def create_resend_request_message(
        cls,
        start_sequence,
        end_sequence
    ):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.ResendRequest
        )
        msg.append_pair(fc.FixTag.BeginSeqNo, start_sequence)
        msg.append_pair(fc.FixTag.EndSeqNo, end_sequence)
        return msg

    @classmethod
    def create_sequence_reset_message(
        cls,
        new_sequence_number,
        gap_fill=fc.GapFillFlag.YES
    ):
        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.ResendRequest
        )
        msg.append_pair(fc.FixTag.NewSeqNo, new_sequence_number)
        msg.append_pair(fc.FixTag.GapFillFlag, gap_fill)
        return msg

    @classmethod
    def create_security_list_request(cls):
        msg = cls()
        uid = utils.gen_uuid()
        msg.append_pair(fc.FixTag.SecurityReqID, uid)
        msg.append_pair(
            fc.FixTag.SecurityListRequestType,
            b'0'
        )
        return msg

    @classmethod
    def create_market_data_request_message(
        cls,
        symbols,
        entry_types,
        subscription_type=fc.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES,
        market_depth=fc.MarketDepth.TOP_OF_BOOK,
        update_type=fc.MDUpdateType.FULL_REFRESH,
    ):

        msg = cls()
        msg.append_pair(fc.FixTag.MDReqID, utils.gen_uuid())

        if subscription_type not in fc.SubscriptionRequestType:
            utils.raise_invalid_option(
                'subscription_type', fc.SubscriptionRequestType)

        msg.append_pair(
            fc.FixTag.SubscriptionRequestType,
            subscription_type
        )

        if market_depth not in fc.MarketDepth:
            utils.raise_invalid_option(
                'market_depth', fc.MarketDepth)

        msg.append_pair(
            fc.FixTag.MarketDepth,
            market_depth
        )

        if subscription_type == fc.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES:
            if update_type not in fc.MDUpdateType:
                utils.raise_invalid_option(
                    'update_type', fc.MDUpdateType)

            msg.append_pair(
                fc.FixTag.MDUpdateType,
                update_type
            )

        msg.append_pair(
            fc.FixTag.NoMDEntries,
            len(entry_types)
        )

        for entry_type in entry_types:
            msg.append_pair(
                fc.FixTag.MDEntryType,
                entry_type
            )

        msg.append_pair(fc.FixTag.NoRelatedSym, len(symbols))
        for symbol in symbols:
            msg.append_pair(
                fc.FixTag.Symbol,
                symbol
            )

        return msg

    @classmethod
    def create_new_order_message(
        cls,
        symbol,
        quantity,
        side,
        order_type,
        time_in_force=fc.TimeInForce.GOOD_TILL_CANCEL,
        ioi_id=None,
        exec_inst=None,
        price=None,
        min_fill_qty=None

    ):
        msg = cls()

        order_id = utils.gen_uuid()
        msg.append_pair(fc.FixTag.ClOrdID, order_id)

        if ioi_id is not None:
            msg.append_pair(fc.FixTag.IOIID, ioi_id)

        msg.append_pair(fc.FixTag.OrderQty, quantity)

        if (
            exec_inst is not None
            and exec_inst == fc.ExecInst.SINGLE_EXECUTION_REQUESTED_FOR_BLOCK_TRADE
            and time_in_force == fc.TimeInForce.GOOD_TILL_CANCEL
        ):
            msg.append_pair(fc.FixTag.MinQty, min_fill_qty)

        msg.append_pair(fc.FixTag.OrdType, order_type)

        if order_type == fc.OrdType.LIMIT:
            msg.append_pair(fc.FixTag.Price, price)

        msg.append_pair(fc.FixTag.Side, side)
        msg.append_pair(fc.FixTag.Symbol, symbol)
        msg.append_pair(fc.FixTag.TimeInForce, time_in_force)

        return msg

    @classmethod
    def create_reject_message(
        cls,
        ref_sequence_number,
        ref_tag,
        ref_message_type,
        rejection_type,
        reject_reason
    ):
        """
        :param ref_sequence_number: sequence number of message being referred to
        :param ref_tag: Tag number of field being referred to
        :param ref_message_type: Message type of message being rejected
        :param rejection_type: Code to identify reject reason
        :param reject_reason: Verbose explanation of rejection
        :return:
        """

        msg = cls()
        msg.append_pair(
            fc.FixTag.MsgType,
            fc.FixMsgType.Reject
        )
        msg.append_pair(fc.FixTag.RefSeqNum, ref_sequence_number)
        msg.append_pair(fc.FixTag.Text, reject_reason)
        msg.append_pair(fc.FixTag.RefTagID, ref_tag)
        msg.append_pair(fc.FixTag.RefMsgType, ref_message_type)
        msg.append_pair(fc.FixTag.SessionRejectReason, rejection_type)

