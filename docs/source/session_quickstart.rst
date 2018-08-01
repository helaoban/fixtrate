.. _session-quickstart:


Session Quickstart
=====================

.. currentmodule:: fixation

This page should get you up to speed on the basics of the fixation
Session API.

First, make sure that fixation is :ref:`installed
<install>` and *up-to-date*

Connect to a FIX Endpoint
----------------------------

Begin by importing the session module::

    from fixation import session

Now, let's try connecting to a FIX server::

    fix_session = session.FixSession()

    async with fix_session.connect():
        await fix_session.logon()
        async for msg in fix_session:
            print(msg)

Now, we have a :class:`~fixation.session.FixSession` called ``fix_session``.
