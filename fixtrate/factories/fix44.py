from fixtrate import (
    constants as fc, message as fm,
    utils
)

TAGS = fc.FixTag.FIX44


def heartbeat(test_request_id=None):
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.HEARTBEAT
    )
    if test_request_id:
        msg.append_pair(TAGS.TestReqID, test_request_id)
    return msg


def test_request(test_request_id=None):
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.TEST_REQUEST
    )
    if test_request_id is None:
        test_request_id = utils.gen_uuid()
    msg.append_pair(TAGS.TestReqID, test_request_id)
    return msg


def logoff():
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.LOGOUT,
        header=True
    )
    return msg


def logon(
        encrypt_method=fc.EncryptMethod.NONE,
        heartbeat_interval=30,
        reset_sequence=False
):
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.LOGON,
    )
    msg.append_pair(
        TAGS.EncryptMethod,
        encrypt_method,
        fc.EncryptMethod.NONE.value
    )
    msg.append_pair(
        TAGS.HeartBtInt,
        heartbeat_interval
    )
    if reset_sequence:
        msg.append_pair(TAGS.ResetSeqNumFlag, 'Y')
    return msg


def resend_request(start_sequence, end_sequence):
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.RESEND_REQUEST
    )
    msg.append_pair(TAGS.BeginSeqNo, start_sequence)
    msg.append_pair(TAGS.EndSeqNo, end_sequence)
    return msg


def sequence_reset(
        new_sequence_number,
        gap_fill=fc.GapFillFlag.YES
):
    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.RESEND_REQUEST
    )
    msg.append_pair(TAGS.NewSeqNo, new_sequence_number)
    msg.append_pair(TAGS.GapFillFlag, gap_fill)
    return msg


def security_list():
    msg = fm.FixMessage()
    uid = utils.gen_uuid()
    msg.append_pair(TAGS.SecurityReqID, uid)
    msg.append_pair(
        TAGS.SecurityListRequestType,
        b'0'
    )
    return msg


def market_data_request(
        symbols,
        entry_types,
        subscription_type=fc.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES,
        market_depth=fc.MarketDepth.TOP_OF_BOOK,
        update_type=fc.MDUpdateType.FULL_REFRESH,
        version=fc.FixVersion.FIX42
):
    tags = getattr(fc.FixTag, version.name)

    msg = fm.FixMessage()
    msg.append_pair(
        tags.MsgType,
        fc.FixMsgType.MARKET_DATA_REQUEST
    )
    msg.append_pair(tags.MDReqID, utils.gen_uuid())

    if subscription_type not in fc.SubscriptionRequestType:
        utils.raise_invalid_option(
            'subscription_type', fc.SubscriptionRequestType)

    msg.append_pair(
        tags.SubscriptionRequestType,
        subscription_type
    )

    if market_depth not in fc.MarketDepth:
        utils.raise_invalid_option(
            'market_depth', fc.MarketDepth)

    msg.append_pair(
        tags.MarketDepth,
        market_depth
    )

    if subscription_type == fc.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES:
        if update_type not in fc.MDUpdateType:
            utils.raise_invalid_option(
                'update_type', fc.MDUpdateType)

        msg.append_pair(
            tags.MDUpdateType,
            update_type
        )

    msg.append_pair(
        tags.NoMDEntryTypes,
        len(entry_types)
    )
    for entry_type in entry_types:
        msg.append_pair(
            tags.MDEntryType,
            entry_type
        )

    msg.append_pair(tags.NoRelatedSym, len(symbols))
    for symbol in symbols:
        msg.append_pair(
            tags.Symbol,
            symbol
        )

    return msg


def new_order(
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
    msg = fm.FixMessage()
    order_id = utils.gen_uuid()
    msg.append_pair(TAGS.ClOrdID, order_id)

    if ioi_id is not None:
        msg.append_pair(TAGS.IOIID, ioi_id)

    msg.append_pair(TAGS.OrderQty, quantity)

    if (
        exec_inst is not None
        and exec_inst == fc.ExecInst.SINGLE_EXECUTION_REQUESTED_FOR_BLOCK_TRADE
        and time_in_force == fc.TimeInForce.GOOD_TILL_CANCEL
    ):
        msg.append_pair(TAGS.MinQty, min_fill_qty)

    msg.append_pair(TAGS.OrdType, order_type)
    if order_type == fc.OrdType.LIMIT:
        msg.append_pair(TAGS.Price, price)

    msg.append_pair(TAGS.Side, side)
    msg.append_pair(TAGS.Symbol, symbol)
    msg.append_pair(TAGS.TimeInForce, time_in_force)
    return msg


def reject(
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

    msg = fm.FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.REJECT
    )
    msg.append_pair(TAGS.RefSeqNum, ref_sequence_number)
    msg.append_pair(TAGS.Text, reject_reason)
    msg.append_pair(TAGS.RefTagID, ref_tag)
    msg.append_pair(TAGS.RefMsgType, ref_message_type)
    msg.append_pair(TAGS.SessionRejectReason, rejection_type)