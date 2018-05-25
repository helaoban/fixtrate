from . import tags


class FixAdapter(object):

    def __init__(self):
        self._handlers = {}

    def dispatch(self, message):
        msg_type = message.get(tags.FixTag.MsgType)
        handler = self._handlers.get(msg_type)
        if handler is not None:
            return handler(message)
        else:
            return message

    def register_handlers(self):
        pass
