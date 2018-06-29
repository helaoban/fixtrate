import simplefix
import sys

from fixation import utils, constants


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


class Message(simplefix.FixMessage):

    def __init__(self, conf):
        self.config = conf
        super().__init__()

    def encode(self, raw=False):
        if not raw:
            if not self.get(constants.FixTag.SendingTime):
                self.append_utc_timestamp(
                    constants.FixTag.SendingTime,
                    precision=6,
                    header=True
                )
        return super().encode(raw=raw)

    def append_standard_headers(
        self,
        sequence_number,
        msg_type,
        timestamp=None
    ):
        """
        Create a base message with standard headers set.
        BodyLength and Checksum are handled by SimpleFix

        :param sequence_number:
        :param msg_type:
        :return:
        """
        self.append_pair(constants.FixTag.BeginString, self.config.get('FIX_VERSION'), header=True)
        self.append_pair(constants.FixTag.MsgType, msg_type, header=True)
        self.append_pair(constants.FixTag.SenderCompID, self.config.get('FIX_SENDER_COMP_ID'), header=True)
        self.append_pair(constants.FixTag.TargetCompID, self.config.get('FIX_TARGET_COMP_ID'), header=True)
        self.append_pair(constants.FixTag.MsgSeqNum, sequence_number, header=True)

        if timestamp is not None:

            self.append_utc_timestamp(
                constants.FixTag.SendingTime,
                timestamp=timestamp,
                precision=6,
                header=True
            )

    def get(self, tag, *args, **kwargs):
        try:
            tag = tag.value
        except AttributeError:
            pass
        return super().get(tag, *args, **kwargs)

    @classmethod
    def create_heartbeat_message(
        cls,
        sequence_number,
        config,
        test_request_id=None
    ):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.Heartbeat,
        )
        if test_request_id:
            msg.append_pair(constants.FixTag.TestReqID, test_request_id)
        return msg

    @classmethod
    def create_test_request_message(
        cls,
        sequence_number,
        config,
    ):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.TestRequest,
        )
        test_request_id = utils.gen_uuid()
        msg.append_pair(constants.FixTag.TestReqID, test_request_id)
        return msg

    @classmethod
    def create_logoff_message(cls, sequence_number, config):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.Logout
        )
        return msg

    @classmethod
    def create_login_message(cls, sequence_number, config):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number=sequence_number,
            msg_type=constants.FixMsgType.Logon,
        )
        msg.append_pair(constants.FixTag.EncryptMethod, config.get('FIX_ENCRYPT_METHOD', constants.EncryptMethod.NONE.value))
        msg.append_pair(constants.FixTag.HeartBtInt, config.get('FIX_HEARTBEAT_INTERVAL'))

        if config.get('FIX_RESET_SEQUENCE'):
            msg.append_pair(constants.FixTag.ResetSeqNumFlag, 'Y')
        return msg

    @classmethod
    def create_security_list_request(cls, sequence_number, config):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.SecurityListRequest
        )
        uid = utils.gen_uuid()
        msg.append_pair(constants.FixTag.SecurityReqID, uid)
        msg.append_pair(constants.FixTag.SecurityListRequestType, b'0')
        return msg

    @classmethod
    def create_market_data_request_message(
        cls,
        sequence_number,
        config,
        symbols,
        entry_types,
        subscription_type='subscribe',
        update_type='full',
        market_depth='top',
    ):

        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.MarketDataRequest,
        )
        msg.append_pair(constants.FixTag.MDReqID, utils.gen_uuid())

        subscription_types = {
            'snapshot': constants.SubscriptionRequestType.SNAPSHOT,
            'subscribe': constants.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES,
            'unsubscribe': constants.SubscriptionRequestType.DISABLE_PREVIOUS_SNAPSHOT_PLUS_UPDATE_REQUEST,
        }
        subscription_type = utils.validate_option(
            subscription_type,
            subscription_types,
            'Subscription Type',
        )
        msg.append_pair(
            constants.FixTag.SubscriptionRequestType,
            subscription_type
        )

        market_depth_types = {
            'top': constants.MarketDepth.TOP_OF_BOOK,
            'full': constants.MarketDepth.FULL_BOOK,
        }
        market_depth_type = utils.validate_option(
            market_depth,
            market_depth_types,
            'Market Depth'
        )

        msg.append_pair(
            constants.FixTag.MarketDepth,
            market_depth_type
        )

        if subscription_type == constants.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES:

            update_types = {
                'full': constants.MDUpdateType.FULL_REFRESH,
                'incremental': constants.MDUpdateType.INCREMENTAL_REFRESH,
            }
            update_type = utils.validate_option(
                update_type,
                update_types,
                'Update Type'
            )
            msg.append_pair(
                constants.FixTag.MDUpdateType,
                update_type
            )

        msg.append_pair(
            constants.FixTag.NoMDEntries,
            len(entry_types)
        )
        for entry_type in entry_types:
            msg.append_pair(
                constants.FixTag.MDEntryType,
                entry_type
            )

        msg.append_pair(constants.FixTag.NoRelatedSym, len(symbols))
        for symbol in symbols:
            msg.append_pair(
                constants.FixTag.Symbol,
                symbol
            )

        return msg

    @classmethod
    def create_resend_request_message(
        cls,
        sequence_number,
        config,
        start_sequence,
        end_sequence
    ):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.ResendRequest
        )
        msg.append_pair(constants.FixTag.BeginSeqNo, start_sequence)
        msg.append_pair(constants.FixTag.EndSeqNo, end_sequence)
        return msg

    @classmethod
    def create_sequence_reset_message(
        cls,
        sequence_number,
        config,
        new_sequence_number,
        gap_fill=constants.GapFillFlag.YES
    ):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.ResendRequest
        )
        msg.append_pair(constants.FixTag.NewSeqNo, new_sequence_number)
        msg.append_pair(constants.FixTag.GapFillFlag, gap_fill)
        return msg

    @classmethod
    def create_new_order_message(
        cls,
        sequence_number,
        config,
        symbol,
        quantity,
        order_type,
        side,
        time_in_force=constants.TimeInForce.GOOD_TILL_CANCEL,
        ioi_id=None,
        exec_inst=None,
        price=None,
        min_fill_qty=None

    ):
        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.NewOrderSingle
        )

        order_id = utils.gen_uuid()
        msg.append_pair(constants.FixTag.ClOrdID, order_id)

        if ioi_id is not None:
            msg.append_pair(constants.FixTag.IOIID, ioi_id)

        msg.append_pair(constants.FixTag.OrderQty, quantity)

        if (
            exec_inst is not None
            and exec_inst == constants.ExecInst.SINGLE_EXECUTION_REQUESTED_FOR_BLOCK_TRADE
            and time_in_force == constants.TimeInForce.GOOD_TILL_CANCEL
        ):
            msg.append_pair(constants.FixTag.MinQty, min_fill_qty)

        msg.append_pair(constants.FixTag.OrdType, order_type)
        if order_type == constants.OrdType.LIMIT:
            msg.append_pair(constants.FixTag.Price, price)

        msg.append_pair(constants.FixTag.Side, side)
        msg.append_pair(constants.FixTag.Symbol, symbol)
        msg.append_pair(constants.FixTag.TimeInForce, time_in_force)

        return msg

    @classmethod
    def create_reject_message(
        cls,
        sequence_number,
        config,
        ref_sequence_number,
        ref_tag,
        ref_message_type,
        rejection_type,
        reject_reason
    ):
        """

        :param sequence_number: sequence number of this message
        :param config: FixConfig object
        :param ref_sequence_number: sequence number of message being referred to
        :param ref_tag: Tag number of field being referred to
        :param ref_message_type: Message type of message being rejected
        :param rejection_type: Code to identify reject reason
        :param reject_reason: Verbose explanation of rejection
        :return:
        """

        msg = cls(config)
        msg.append_standard_headers(
            sequence_number,
            constants.FixMsgType.Reject
        )
        msg.append_pair(constants.FixTag.RefSeqNum, ref_sequence_number)
        msg.append_pair(constants.FixTag.Text, reject_reason)
        msg.append_pair(constants.FixTag.RefTagID, ref_tag)
        msg.append_pair(constants.FixTag.RefMsgType, ref_message_type)
        msg.append_pair(constants.FixTag.SessionRejectReason, rejection_type)
