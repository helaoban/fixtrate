from . import constants as fix, exceptions as exc
from .session_id import SessionID
from .factories import fix42


ADMIN_MESSAGES = {
    fix.FixMsgType.LOGON,
    fix.FixMsgType.LOGOUT,
    fix.FixMsgType.HEARTBEAT,
    fix.FixMsgType.TEST_REQUEST,
    fix.FixMsgType.RESEND_REQUEST,
    fix.FixMsgType.SEQUENCE_RESET,
}

SESSION_ID_FIELDS = (
    'begin_string',
    'sender_comp_id',
    'target_comp_id',
    'qualifier'
)


def is_duplicate_admin(msg):
    if not msg.is_duplicate:
        return False
    admin_msgs = ADMIN_MESSAGES.difference({
        fix.FixMsgType.SEQUENCE_RESET})
    return msg.msg_type in admin_msgs


def parse_session_id_from_conf(conf):
    kw = {f: conf.get(f) for f in SESSION_ID_FIELDS}
    conf = {
        k: v for k, v in conf.items()
        if k not in SESSION_ID_FIELDS
    }
    return SessionID(**kw), conf


def make_reject_msg(msg, tag, rejection_type, reason):
    return fix42.reject(
        ref_sequence_number=msg.seq_num,
        ref_message_type=msg.msg_type,
        ref_tag=tag,
        rejection_type=rejection_type,
        reject_reason=reason,
    )


def make_logon_msg(hb_int=30, reset=False):
    msg = fix42.logon(hb_int=hb_int, reset=reset)
    if reset:
        msg.append_pair(
            fix.FixTag.MsgSeqNum, 1)
    return msg


def make_logout_msg():
    return fix42.logout()


def make_resend_request(start, end):
    return fix42.resend_request(start, end)


def make_sequence_reset(new_seq_num):
    return fix42.sequence_reset(
        new_seq_num, gap_fill=False)


def make_gap_fill(seq_num, new_seq_num):
    msg = fix42.sequence_reset(new_seq_num)
    msg.append_pair(
        fix.FixTag.MsgSeqNum, seq_num, header=True)
    return msg


def prepare_msgs_for_resend(msgs):
    gap_start = None
    gap_end = None
    rv = []
    for msg in msgs:
        if msg.msg_type in ADMIN_MESSAGES:
            if gap_start is None:
                gap_start = msg.seq_num
            gap_end = msg.seq_num + 1
        else:
            if gap_end is not None:
                gap_fill = make_gap_fill(gap_start, gap_end)
                rv.append(gap_fill)
                gap_start, gap_end = None, None

            dup_flag = msg.get(fix.FixTag.PossDupFlag)
            if dup_flag != fix.PossDupFlag.YES:
                if dup_flag is not None:
                    msg.remove(fix.FixTag.PossDupFlag)
                msg.append_pair(
                    fix.FixTag.PossDupFlag,
                    fix.PossDupFlag.YES,
                    header=True
                )

            rv.append(msg)

    if gap_start is not None:
        gap_fill = make_gap_fill(gap_start, gap_end)
        rv.append(gap_fill)

    return rv


def append_send_time(msg, timestamp=None):
    msg.append_utc_timestamp(
        fix.FixTag.SendingTime,
        timestamp=timestamp,
        precision=6,
        header=True
    )


def validate_tag_value(msg, tag, expected, type_):
    actual = msg.get(tag)
    try:
        actual = type_(msg.get(tag))
    except (TypeError, ValueError) as error:
        raise exc.InvalidTypeError(
            msg, tag, actual, type_) from error
    if actual != expected:
        raise exc.IncorrectTagValueError(
            msg, tag, expected, actual)



HEADER_REQUIRED = (
    fix.FixTag.BeginString,
    fix.FixTag.BodyLength,
    fix.FixTag.TargetCompID,
    fix.FixTag.SenderCompID,
    fix.FixTag.SendingTime,
    fix.FixTag.MsgSeqNum,
    fix.FixTag.MsgType
)


def validate_header(msg, session_id):
    for tag in HEADER_REQUIRED:
        if tag not in msg:
            raise exc.MissingRequiredTagError(msg, tag)
    for tag, value, type_ in (
        (fix.FixTag.BeginString,  session_id.begin_string, str),
        (fix.FixTag.TargetCompID,  session_id.sender, str),
        (fix.FixTag.SenderCompID,  session_id.target, str)
    ):
        validate_tag_value(msg, tag, value, type_)


def is_gap_fill(msg):
    gf_flag = msg.get(fix.FixTag.GapFillFlag)
    return gf_flag == fix.GapFillFlag.YES


def is_reset(msg):
    reset_seq = msg.get(fix.FixTag.ResetSeqNumFlag)
    return reset_seq == fix.ResetSeqNumFlag.YES


def is_reset_mode(msg):
    is_seq_reset = msg.msg_type == fix.FixMsgType.SEQUENCE_RESET
    return is_seq_reset and not is_gap_fill(msg)


def is_logon_reset(msg):
    is_logon = msg.msg_type == fix.FixMsgType.LOGON
    return is_logon and is_reset(msg)

