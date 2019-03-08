from . import constants as fix
from .session_id import SessionID
from .factories import fix42

TAGS = fix.FixTag.FIX42

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
    msg = fix42.logon(
        heartbeat_interval=hb_int,
        reset_sequence=reset
    )
    if reset:
        msg.append_pair(
            fix.FixTag.FIX42.MsgSeqNum, 1)
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
        fix.FixTag.FIX42.MsgSeqNum, seq_num, header=True)
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

            dup_flag = msg.get(TAGS.PossDupFlag)
            if dup_flag != fix.PossDupFlag.YES:
                if dup_flag is not None:
                    msg.remove(TAGS.PossDupFlag)
                msg.append_pair(
                    TAGS.PossDupFlag,
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
        TAGS.SendingTime,
        timestamp=timestamp,
        precision=6,
        header=True
    )


async def append_standard_header(
    msg,
    sid,
    seq_num=None,
    timestamp=None,
    headers=None
):
    if msg.get(TAGS.MsgSeqNum) is None:
        if seq_num is None:
            raise ValueError(
                'MsgSeqNum is not set on msg, and '
                'no seq_num was given'
            )
        msg.append_pair(TAGS.MsgSeqNum, seq_num)

    headers = list(headers or [])
    headers.extend([
        (TAGS.BeginString, sid.begin_string),
        (TAGS.SenderCompID, sid.sender),
        (TAGS.TargetCompID, sid.target)
    ])

    for tag, val in headers:
        existing = msg.get(tag)
        if existing is None:
            msg.append_pair(tag, val, header=True)

    send_time = msg.get(TAGS.SendingTime)
    if timestamp is not None or send_time is None:
        append_send_time(msg, timestamp=timestamp)

