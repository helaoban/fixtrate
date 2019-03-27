from fixtrate import constants as fc, utils
from fixtrate.message import FixMessage


def heartbeat(test_request_id=None):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.HEARTBEAT,
        header=True
    )
    if test_request_id:
        msg.append_pair(fc.FixTag.TestReqID, test_request_id)
    return msg


def test_request(test_request_id=None):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.TEST_REQUEST,
        header=True
    )
    if test_request_id is None:
        test_request_id = utils.gen_uuid()
    msg.append_pair(fc.FixTag.TestReqID, test_request_id)
    return msg


def logout():
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.LOGOUT,
        header=True
    )
    return msg


def logon(
    hb_int=30,
    reset=False,
    encrypt_method=fc.EncryptMethod.NONE
):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType, fc.FixMsgType.LOGON, header=True)
    msg.append_pair(fc.FixTag.EncryptMethod, encrypt_method)
    msg.append_pair(fc.FixTag.HeartBtInt, hb_int)
    if reset:
        msg.append_pair(fc.FixTag.ResetSeqNumFlag, 'Y')
    return msg


def resend_request(start_sequence, end_sequence):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.RESEND_REQUEST,
        header=True
    )
    msg.append_pair(fc.FixTag.BeginSeqNo, start_sequence)
    msg.append_pair(fc.FixTag.EndSeqNo, end_sequence)
    return msg


def sequence_reset(
    new_sequence_number,
    gap_fill=True
):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.SEQUENCE_RESET,
        header=True
    )
    msg.append_pair(fc.FixTag.NewSeqNo, new_sequence_number)
    if gap_fill:
        msg.append_pair(fc.FixTag.GapFillFlag, fc.GapFillFlag.YES)
    else:
        msg.append_pair(fc.FixTag.GapFillFlag, fc.GapFillFlag.NO)
    return msg


def security_list():
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.SecurityListRequest,
        header=True
    )
    uid = utils.gen_uuid()
    msg.append_pair(fc.FixTag.SecurityReqID, uid)
    msg.append_pair(
        fc.FixTag.SecurityListRequestType,
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
        fc.FixTag.MsgType,
        fc.FixMsgType.MARKET_DATA_REQUEST,
        header=True
    )
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
        fc.FixTag.NoMDEntryTypes,
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
        fc.FixTag.MsgType,
        fc.FixMsgType.NEW_ORDER_SINGLE,
        header=True
    )
    msg.append_pair(fc.FixTag.Account, account)

    if cl_order_id is None:
        cl_order_id = utils.gen_uuid()
    msg.append_pair(fc.FixTag.ClOrdID, cl_order_id)

    if currency is not None:
        msg.append_pair(fc.FixTag.Currency, currency)

    msg.append_pair(fc.FixTag.Symbol, symbol)
    msg.append_pair(fc.FixTag.HandlInst, handl_inst)
    msg.append_pair(fc.FixTag.Side, side)
    msg.append_pair(fc.FixTag.OrderQty, quantity)
    msg.append_pair(fc.FixTag.OrdType, order_type)

    if order_type == fc.OrdType.LIMIT:
        msg.append_pair(fc.FixTag.Price, price)

    if time_in_force is not None:
        msg.append_pair(fc.FixTag.TimeInForce, time_in_force)

    if security_exchange is not None:
        msg.append_pair(fc.FixTag.SecurityExchange, security_exchange)

    if ex_destination is not None:
        msg.append_pair(fc.FixTag.ExDestination, ex_destination)

    msg.append_pair(fc.FixTag.CustomerOrFirm, customer_or_firm)

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
        fc.FixTag.MsgType,
        fc.FixMsgType.ORDER_CANCEL_REPLACE_REQEUST,
        header=True
    )
    msg.append_pair(fc.FixTag.Account, account)
    msg.append_pair(fc.FixTag.HandlInst, handle_inst)
    msg.append_pair(fc.FixTag.OrigClOrdID, orig_cl_order_id)
    if new_cl_order_id is None:
        new_cl_order_id = utils.gen_uuid()
    msg.append_pair(fc.FixTag.ClOrdID, new_cl_order_id)
    msg.append_pair(fc.FixTag.Symbol, symbol)
    msg.append_pair(fc.FixTag.Side, side)
    msg.append_pair(fc.FixTag.OrderQty, quantity)
    msg.append_pair(fc.FixTag.OrdType, order_type)

    if price is not None:
        msg.append_pair(fc.FixTag.Price, price)

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
        fc.FixTag.MsgType,
        fc.FixMsgType.ORDER_CANCEL_REQUEST,
        header=True
    )
    msg.append_pair(fc.FixTag.Account, account)
    if cl_order_id is None:
        cl_order_id = utils.gen_uuid()
    msg.append_pair(fc.FixTag.ClOrdID, cl_order_id)
    msg.append_pair(fc.FixTag.OrigClOrdID, orig_cl_order_id)
    msg.append_pair(fc.FixTag.Symbol, symbol)
    msg.append_pair(fc.FixTag.Side, side)
    msg.append_pair(fc.FixTag.OrderQty, quantity)

    return msg


def order_status(
    cl_order_id='*',
):
    msg = FixMessage()
    msg.append_pair(
        fc.FixTag.MsgType,
        fc.FixMsgType.ORDER_STATUS_REQUEST,
        header=True
    )
    msg.append_pair(fc.FixTag.ClOrdID, cl_order_id)
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
        fc.FixTag.MsgType,
        fc.FixMsgType.REJECT,
        header=True
    )
    msg.append_pair(fc.FixTag.RefSeqNum, ref_sequence_number)
    msg.append_pair(fc.FixTag.Text, reject_reason)
    msg.append_pair(fc.FixTag.RefTagID, ref_tag)
    msg.append_pair(fc.FixTag.RefMsgType, ref_message_type)
    msg.append_pair(fc.FixTag.SessionRejectReason, rejection_type)
    return msg
