import asyncio
import errno
import json
import jsonschema as js
import logging
import os
import socket

from fixation import exceptions, utils


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RPCServer(object):

    RPC_SCHEMA = {
        'type': 'object',
        'properties': {
            'jsonrpc': {'const': '2.0'},
            'method': {'type': 'string'},
            'params': {'type': ['array', 'object']},
            'id': {'type': ['number', 'string']}
        },
        'required': [
            'jsonrpc',
            'method',
            'id'
        ]
    }

    def __init__(self, fix_session, loop=None):
        self.config_path = '~/.fixation'
        self.session = fix_session
        self._socket_server = None
        self.loop = loop or asyncio.get_event_loop()

    def make_config_dir(self):
        path = os.path.expanduser(self.config_path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as error:
                if error.errno != errno.EEXIST:
                    raise
        return path

    def make_socket_file(self):
        config_dir = self.make_config_dir()
        path = os.path.join(config_dir, 'command_socket')

        try:
            os.remove(path)
        except OSError:
            pass

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)

        return path

    def dispatch_socket_command(self, data):
        return {
            'place_order': self.session.place_order,
            'send_test_request': self.session.mock_send_test_request
        }.get(data['method'])

    async def handle_rpc_request(self, message):
        try:
            data = json.loads(message.decode())
        except json.JSONDecodeError:
            raise exceptions.RPCParseError

        try:
            js.validate(data, self.RPC_SCHEMA)
        except js.ValidationError as error:
            raise exceptions.RPCInvalidRequest

        handler = await self.dispatch_socket_command(data)
        if not handler:
            raise exceptions.RPCMethodNotFound

        try:
            result = handler(**data['params'])
        # TODO need to inspect method members, or else we swallow
        # actual TypeErrors in method call.
        except TypeError:
            raise exceptions.RPCInvalidParams

        return {
            'result': result,
            'id': data['id']
        }

    async def handle_socket_client(self, reader, writer, timeout=30):
        buf = b''
        while True:
            try:
                buf += await asyncio.wait_for(reader.read(4096), timeout)
            except asyncio.TimeoutError as error:
                logger.exception(error)
                return
            if buf == b'0':
                logger.info('client disconnected')
                writer.close()
                return
            message, buf = utils.parse_rpc_message(buf)
            if message is None:
                continue
            try:
                response = await self.handle_rpc_request(message)
            except exceptions.RPCError as error:
                response = {
                    'code': error.code,
                    'message': error.message,
                    'data': error.meaning
                }

            response = utils.pack_rpc_message(response)
            writer.write(response)

    def shutdown(self):
        logger.info('Shutting down...')
        self._socket_server.cancel()

    def start(self):
        socket_path = self.make_socket_file()
        socket_coro = asyncio.start_unix_server(
            self.handle_socket_client,
            path=socket_path,
            loop=self.loop
        )
        self._socket_server = self.loop.create_task(socket_coro)
