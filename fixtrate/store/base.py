import typing as t

if t.TYPE_CHECKING:
    from fixtrate.message import FixMessage
    from fixtrate.config import FixSessionConfig


__all__ = ("FixStore", )


class FixStore:

    def __init__(self, config: "FixSessionConfig"):
        self.config = config

    async def incr_local(self) -> int:
        """ Increment the local sequence number by 1.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        """
        raise NotImplementedError

    async def incr_remote(self) -> int:
        """ Increment the remote sequence number by 1.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        """
        raise NotImplementedError

    async def get_local(self) -> int:
        """ Get the local sequence number.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        """
        raise NotImplementedError

    async def get_remote(self) -> int:
        """ Get the remote sequence number.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        """
        raise NotImplementedError

    async def set_local(self, new_seq_num: int) -> None:
        """ Set the local sequence number to a new number.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        :param new_seq_num: The new sequence number.
        :type new_seq_num: int

        """
        raise NotImplementedError

    async def set_remote(self, new_seq_num: int) -> None:
        """ Set the remote sequence number to a new number.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        :param new_seq_num: The new sequence number.
        :type new_seq_num: int

        """
        raise NotImplementedError

    async def store_msg(self, *msgs: "FixMessage") -> None:
        """ Store a message in the store.

        :param session: The current session.
        :type session: :class:`~fix.session.FixSession`

        :param msg: The message to store.
        :type msg: :class:`~fix.message.FixMessage`

        :rtype str
        """
        raise NotImplementedError

    def get_sent(
        self,
        min: float = float("-inf"),
        max: float = float("inf"),
        limit: float = float("inf"),
    ) -> "t.AsyncIterator[FixMessage]":
        return self.get_msgs(min, max, limit, "sent")

    def get_received(
        self,
        min: float = float("-inf"),
        max: float = float("inf"),
        limit: float = float("inf"),
    ) -> "t.AsyncIterator[FixMessage]":
        return self.get_msgs(min, max, limit, "received")

    async def get_msgs(
        self,
        min: float = float("-inf"),
        max: float = float("inf"),
        limit: float = float("inf"),
        index: str = "by_time",
        sort: str = "ascending",
    ) -> "t.AsyncIterator[FixMessage]":
        """ Return all max sent and received in the
            current session. Allows slicing by datetime and
            by sequence number.

            :param session: The current session.
            :type session: :class:`~fix.session.FixSession`

            :param start: Beginning datetime. If specified, only returns
                messages sent or received on or after specified time.
            :type start: datetime

            :param end: Ending datetime.  If specified, only returns
                messages sent or received on or before specified time.
            :type end: datetime

            :param min: Minimum sequence number. If specified, only returns
                messages with a sequence number equal to or greater than
                specified sequence number.
            :type min: int

            :param max: Minimum sequence number. If specified, only returns
                messages with a sequence number equal to or less than
                specified sequence number.
            :type max: int

            :rtype AsyncIterator[:class:`FixMessage`]
        """
        # Force mypy to register this abtract method as a generator
        # (WE BE TRICKIN)
        if False:
            yield
        raise NotImplementedError

    async def reset(self) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
