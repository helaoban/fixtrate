from .session import SessionID

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
