class FixStoreInterface:

    async def connect(self, engine):
        raise NotImplementedError

    async def close(self, engine):
        raise NotImplementedError


class FixStore:

    async def incr_local(self, session_id):
        """ Increment the local sequence number by 1.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        """
        raise NotImplementedError

    async def incr_remote(self, session_id):
        """ Increment the remote sequence number by 1.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        """
        raise NotImplementedError

    async def get_local(self, session_id):
        """ Get the local sequence number.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        """
        raise NotImplementedError

    async def get_remote(self, session_id):
        """ Get the remote sequence number.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        """
        raise NotImplementedError

    async def set_local(self, session_id, new_seq_num):
        """ Set the local sequence number to a new number.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        :param new_seq_num: The new sequence number.
        :type new_seq_num: int

        """
        raise NotImplementedError

    async def set_remote(self, session_id, new_seq_num):
        """ Set the remote sequence number to a new number.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        :param new_seq_num: The new sequence number.
        :type new_seq_num: int

        """
        raise NotImplementedError

    async def store_message(self, session_id, msg):
        """ Store a message in the store.

        :param session: The current session.
        :type session: :class:`~fixtrate.session.FixSession`

        :param msg: The message to store.
        :type msg: :class:`~fixtrate.message.FixMessage`
        """
        raise NotImplementedError

    async def get_sent(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        raise NotImplementedError

    async def get_received(
        self,
        session_id,
        min=float('-inf'),
        max=float('inf'),
        limit=None
    ):
        raise NotImplementedError

    async def get_messages(
        self,
        session_id,
        start=float('-inf'),
        end=float('inf'),
        limit=None,
    ):
        """ Return all messages sent and received in the
            current session. Allows slicing by datetime and
            by sequence number.

            :param session: The current session.
            :type session: :class:`~fixtrate.session.FixSession`

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
        raise NotImplementedError

    async def reset(self):
        raise NotImplementedError

