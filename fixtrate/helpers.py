import typing as t
import uuid

from . import exceptions as exc
from .message import FixMessage
from .fixt import data as VALUES
from .fixt.types import FixTag as TAG

if t.TYPE_CHECKING:
    from .store.base import FixStore
    from .config import FixSessionConfig


MTYPE = VALUES.MsgType


ADMIN_MESSAGES = {
    MTYPE.LOGON,
    MTYPE.LOGOUT,
    MTYPE.HEARTBEAT,
    MTYPE.TEST_REQUEST,
    MTYPE.RESEND_REQUEST,
    MTYPE.SEQUENCE_RESET,
}


def get_or_raise(msg: "FixMessage", tag: TAG) -> str:
    val = msg.get_raw(tag)
    if val is None:
        raise exc.MissingRequiredTagError(msg, tag)
    return val


def is_admin(msg: "FixMessage") -> bool:
    return msg.msg_type in ADMIN_MESSAGES


def is_duplicate_admin(msg: "FixMessage") -> bool:
    if not msg.is_duplicate:
        return False
    admin_msgs = ADMIN_MESSAGES.difference({
        MTYPE.SEQUENCE_RESET})
    return msg.msg_type in admin_msgs


def make_gap_fill(seq_num: int, new_seq_num: int) -> "FixMessage":
    msg = make_sequence_reset(new_seq_num, gap_fill=True)
    msg.append_pair(TAG.MsgSeqNum, seq_num, header=True)
    return msg


async def get_resend_msgs(
    store: "FixStore",
    start: float,
    end: float,
) -> t.AsyncIterator["FixMessage"]:
    gap = []

    async for msg in store.get_sent(min=start, max=end):
        if msg.msg_type in ADMIN_MESSAGES:
            gap.append(msg)
        else:
            if gap:
                gap_fill = make_gap_fill(
                    gap[0].seq_num, gap[-1].seq_num + 1)
                yield gap_fill
                gap.clear()

            msg.remove(TAG.PossDupFlag)
            msg.append_pair(TAG.PossDupFlag, "Y", header=True)
            yield msg

    if gap:
        gap_fill = make_gap_fill(
            gap[0].seq_num, gap[-1].seq_num + 1)
        yield gap_fill


HEADER_REQUIRED = (
    TAG.BeginString,
    TAG.BodyLength,
    TAG.TargetCompID,
    TAG.SenderCompID,
    TAG.SendingTime,
    TAG.MsgSeqNum,
    TAG.MsgType
)


def validate_header(msg: "FixMessage", config: "FixSessionConfig"):
    for tag in HEADER_REQUIRED:
        if tag not in msg:
            raise exc.MissingRequiredTagError(msg, tag)
    for tag, expected in (
        (TAG.BeginString,  config.version),
        (TAG.TargetCompID,  config.sender),
        (TAG.SenderCompID,  config.target)
    ):
        actual = get_or_raise(msg, tag)
        if actual != expected:
            raise exc.IncorrectTagValueError(
                msg, tag, expected, actual)


def is_gap_fill(msg: "FixMessage") -> bool:
    gf_flag = msg.get_raw(TAG.GapFillFlag)
    return gf_flag == "Y"


def is_reset(msg: "FixMessage") -> bool:
    reset_seq = msg.get_raw(TAG.ResetSeqNumFlag)
    return reset_seq == "Y"


def is_reset_mode(msg: "FixMessage") -> bool:
    is_seq_reset = msg.msg_type == MTYPE.SEQUENCE_RESET
    return is_seq_reset and not is_gap_fill(msg)


def is_logon_reset(msg: "FixMessage") -> bool:
    is_logon = msg.msg_type == MTYPE.LOGON
    return is_logon and is_reset(msg)


def make_heartbeat_msg(test_request_id: t.Optional[str] = None) -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType,
        MTYPE.HEARTBEAT,
        header=True
    )
    if test_request_id:
        msg.append_pair(TAG.TestReqID, test_request_id)
    return msg


def make_test_request_msg(
    test_request_id: t.Optional[str] = None
) -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType,
        MTYPE.TEST_REQUEST,
        header=True
    )
    if test_request_id is None:
        test_request_id = str(uuid.uuid4())
    msg.append_pair(TAG.TestReqID, test_request_id)
    return msg


def make_logout_msg() -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType,
        MTYPE.LOGOUT,
        header=True
    )
    return msg


def make_logon_msg(
    hb_int: int = 30,
    reset: bool = False,
    encrypt_method: int = VALUES.EncryptMethod.NONE_OTHER
) -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType, MTYPE.LOGON, header=True)
    msg.append_pair(TAG.EncryptMethod, encrypt_method)
    msg.append_pair(TAG.HeartBtInt, hb_int)
    if reset:
        msg.append_pair(TAG.MsgSeqNum, 1)
        msg.append_pair(TAG.ResetSeqNumFlag, 'Y')
    return msg


def make_resend_request(start_sequence: int, end_sequence: int) -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType,
        MTYPE.RESEND_REQUEST,
        header=True
    )
    msg.append_pair(TAG.BeginSeqNo, start_sequence)
    msg.append_pair(TAG.EndSeqNo, end_sequence)
    return msg


def make_sequence_reset(
    new_sequence_number: int,
    gap_fill: bool = False,
) -> FixMessage:
    msg = FixMessage()
    msg.append_pair(
        TAG.MsgType,
        MTYPE.SEQUENCE_RESET,
        header=True
    )
    msg.append_pair(TAG.NewSeqNo, new_sequence_number)
    if gap_fill:
        msg.append_pair(TAG.GapFillFlag, "Y")
    else:
        msg.append_pair(TAG.GapFillFlag, "N")
    return msg


def make_reject_msg_from_error(error: exc.InvalidMessageError) -> FixMessage:
    return make_reject_msg(
        ref_sequence_number=error.fix_msg.seq_num,
        ref_message_type=error.fix_msg.msg_type,
        ref_tag=error.tag,
        rejection_type=error.reject_type,
        reject_reason=str(error)
    )


def make_reject_msg(
    ref_sequence_number: int,
    ref_tag: TAG,
    ref_message_type: str,
    rejection_type: int,
    reject_reason: str
) -> FixMessage:
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
        TAG.MsgType,
        VALUES.MsgType.REJECT,
        header=True
    )
    msg.append_pair(TAG.RefSeqNum, ref_sequence_number)
    msg.append_pair(TAG.Text, reject_reason)
    msg.append_pair(TAG.RefTagID, ref_tag)
    msg.append_pair(TAG.RefMsgType, ref_message_type)
    msg.append_pair(TAG.SessionRejectReason, rejection_type)
    return msg
