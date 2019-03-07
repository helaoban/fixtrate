from . import constants as fix
from .session_id import SessionID
from .factories import fix42

SESSION_ID_FIELDS = (
    'begin_string',
    'sender_comp_id',
    'target_comp_id',
    'qualifier'
)


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

