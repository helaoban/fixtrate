import hashlib


class FSID(object):

    def __init__(
        self,
        sender_comp_id,
        target_comp_id,
    ):

        key = ''.join([sender_comp_id, target_comp_id])
        self.__dict__['_fsid'] = hashlib.sha256(key.encode())

    def __eq__(self, other):
        if isinstance(other, FSID):
            return self._fsid.hexdigest() == other._fsid.hexdigest()
        return NotImplemented

    def __str__(self):
        return self._fsid.hexdigest()

    def __int__(self):
        return int(self._fsid.hexdigest(), 16)

    def __setattr__(self, name, value):
        raise TypeError('FSID objects are immutable')
