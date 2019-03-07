class SessionID:
    def __init__(
        self,
        begin_string,
        sender_comp_id,
        target_comp_id,
        qualifier=None
    ):
        self.begin_string = begin_string
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.qualifier = qualifier

    def __str__(self):
        return ':'.join(filter(None, (
            self.begin_string, self.sender_comp_id,
            self.target_comp_id, self.qualifier)))

    def __hash__(self):
        return hash(self.__str__())

    @property
    def target(self):
        return self.target_comp_id

    @property
    def sender(self):
        return self.sender_comp_id

    @property
    def fix_version(self):
        return self.begin_string

    @classmethod
    def from_dict(cls, dic):
        parts = {
            'begin_string',
            'sender_comp_id',
            'target_comp_id',
            'session_qualifier'
        }
        kw = {p: dic[p] for p in parts}
        return cls(**kw)

    @classmethod
    def from_str(cls, val, delimiter=':'):
        items = val.split(delimiter)[:4]
        return cls(*items)


