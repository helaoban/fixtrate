=========================================================
Fixtrate: Tools for interacting with the FIX protocol.
=========================================================

.. image:: https://readthedocs.org/projects/fixtrate/badge/?version=latest
   :target: http://fixtrade.readthedocs.io/
   :alt: Latest Read The Docs

Getting Started
================

Session
--------

To connect to and receive messages from a FIX peer:

.. code-block:: python

    import asyncio
    from fixtrate import FixSession

    async def main():
        session = FixSession()
        async with session.connect():
            await session.logon()
            async for msg in session:
                print(msg)

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

Documentation
==============

https://fixtrate.readthedocs.io/

