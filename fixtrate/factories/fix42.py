from fixtrate import constants as fc, utils
from fixtrate.message import FixMessage

TAGS = fc.FixTag.FIX42


def heartbeat(test_request_id=None):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.HEARTBEAT,
        header=True
    )
    if test_request_id:
        msg.append_pair(TAGS.TestReqID, test_request_id)
    return msg


def test_request(test_request_id=None):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.TEST_REQUEST,
        header=True
    )
    if test_request_id is None:
        test_request_id = utils.gen_uuid()
    msg.append_pair(TAGS.TestReqID, test_request_id)
    return msg


def logoff():
    msg = FixMessage()
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
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.LOGON,
        header=True
    )
    msg.append_pair(
        TAGS.EncryptMethod,
        encrypt_method,
    )
    msg.append_pair(
        TAGS.HeartBtInt,
        heartbeat_interval
    )
    if reset_sequence:
        msg.append_pair(TAGS.ResetSeqNumFlag, 'Y')
    return msg


def resend_request(start_sequence, end_sequence):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.RESEND_REQUEST,
        header=True
    )
    msg.append_pair(TAGS.BeginSeqNo, start_sequence)
    msg.append_pair(TAGS.EndSeqNo, end_sequence)
    return msg


def sequence_reset(
        new_sequence_number,
        gap_fill=fc.GapFillFlag.YES
):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.SEQUENCE_RESET,
        header=True
    )
    msg.append_pair(TAGS.NewSeqNo, new_sequence_number)
    msg.append_pair(TAGS.GapFillFlag, gap_fill)
    return msg


def security_list():
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.SecurityListRequest,
        header=True
    )
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
):

    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.MARKET_DATA_REQUEST,
        header=True
    )
    msg.append_pair(TAGS.MDReqID, utils.gen_uuid())

    if subscription_type not in fc.SubscriptionRequestType:
        utils.raise_invalid_option(
            'subscription_type', fc.SubscriptionRequestType)

    msg.append_pair(
        TAGS.SubscriptionRequestType,
        subscription_type
    )

    if market_depth not in fc.MarketDepth:
        utils.raise_invalid_option(
            'market_depth', fc.MarketDepth)

    msg.append_pair(
        TAGS.MarketDepth,
        market_depth
    )

    if subscription_type == fc.SubscriptionRequestType.SNAPSHOT_PLUS_UPDATES:
        if update_type not in fc.MDUpdateType:
            utils.raise_invalid_option(
                'update_type', fc.MDUpdateType)

        msg.append_pair(
            TAGS.MDUpdateType,
            update_type
        )

    msg.append_pair(
        TAGS.NoMDEntryTypes,
        len(entry_types)
    )
    for entry_type in entry_types:
        msg.append_pair(
            TAGS.MDEntryType,
            entry_type
        )

    msg.append_pair(TAGS.NoRelatedSym, len(symbols))
    for symbol in symbols:
        msg.append_pair(
            TAGS.Symbol,
            symbol
        )

    return msg


def new_order(
        account,
        symbol,
        quantity,
        side,
        order_type=fc.OrdType.LIMIT,
        handl_inst=2,
        cl_order_id=None,
        price=None,
        currency=None,
        security_exchange=None,
        ex_destination=None,
        customer_or_firm=fc.CustomerOrFirm.Customer,
        time_in_force=None
):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.NEW_ORDER_SINGLE,
        header=True
    )
    msg.append_pair(TAGS.Account, account)

    if cl_order_id is None:
        cl_order_id = utils.gen_uuid()
    msg.append_pair(TAGS.ClOrdID, cl_order_id)

    if currency is not None:
        msg.append_pair(TAGS.Currency, currency)

    msg.append_pair(TAGS.Symbol, symbol)
    msg.append_pair(TAGS.HandlInst, handl_inst)
    msg.append_pair(TAGS.Side, side)
    msg.append_pair(TAGS.OrderQty, quantity)
    msg.append_pair(TAGS.OrdType, order_type)

    if order_type == fc.OrdType.LIMIT:
        msg.append_pair(TAGS.Price, price)

    if time_in_force is not None:
        msg.append_pair(TAGS.TimeInForce, time_in_force)

    if security_exchange is not None:
        msg.append_pair(TAGS.SecurityExchange, security_exchange)

    if ex_destination is not None:
        msg.append_pair(TAGS.ExDestination, ex_destination)

    msg.append_pair(TAGS.CustomerOrFirm, customer_or_firm)

    return msg


def cancel_replace(
    account,
    orig_cl_order_id,
    symbol,
    side,
    quantity,
    order_type,
    new_cl_order_id=None,
    price=None,
    handle_inst=2,
):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.ORDER_CANCEL_REPLACE_REQEUST,
        header=True
    )
    msg.append_pair(TAGS.Account, account)
    msg.append_pair(TAGS.HandlInst, handle_inst)
    msg.append_pair(TAGS.OrigClOrdID, orig_cl_order_id)
    if new_cl_order_id is None:
        new_cl_order_id = utils.gen_uuid()
    msg.append_pair(TAGS.ClOrdID, new_cl_order_id)
    msg.append_pair(TAGS.Symbol, symbol)
    msg.append_pair(TAGS.Side, side)
    msg.append_pair(TAGS.OrderQty, quantity)
    msg.append_pair(TAGS.OrdType, order_type)

    if price is not None:
        msg.append_pair(TAGS.Price, price)

    return msg


def cancel(
    account,
    orig_cl_order_id,
    symbol,
    side,
    quantity,
    cl_order_id=None,
):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.ORDER_CANCEL_REQUEST,
        header=True
    )
    msg.append_pair(TAGS.Account, account)
    if cl_order_id is None:
        cl_order_id = utils.gen_uuid()
    msg.append_pair(TAGS.ClOrdID, cl_order_id)
    msg.append_pair(TAGS.OrigClOrdID, orig_cl_order_id)
    msg.append_pair(TAGS.Symbol, symbol)
    msg.append_pair(TAGS.Side, side)
    msg.append_pair(TAGS.OrderQty, quantity)

    return msg


def order_status(
    cl_order_id='*',
):
    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.ORDER_STATUS_REQUEST,
        header=True
    )
    msg.append_pair(TAGS.ClOrdID, cl_order_id)
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

    msg = FixMessage()
    msg.append_pair(
        TAGS.MsgType,
        fc.FixMsgType.REJECT,
        header=True
    )
    msg.append_pair(TAGS.RefSeqNum, ref_sequence_number)
    msg.append_pair(TAGS.Text, reject_reason)
    msg.append_pair(TAGS.RefTagID, ref_tag)
    msg.append_pair(TAGS.RefMsgType, ref_message_type)
    msg.append_pair(TAGS.SessionRejectReason, rejection_type)
    return msg
