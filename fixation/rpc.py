import asyncio
import errno
import json
import jsonschema as js
import logging
import os
import socket
import time
import uuid

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

    def __init__(self, fix_client, loop=None):
        self.config_path = '~/.fixation'
        self.fix_client = fix_client
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
        return s

    def dispatch_socket_command(self, data):
        return {
            'place_order': self.fix_client.place_order,
            'cancel_order': self.fix_client.cancel_order,
            'cancel_replace_order': self.fix_client.cancel_replace_order,
            'send_test_request': self.fix_client.send_test_request
        }.get(data['method'])

    async def handle_rpc_request(self, msg):
        try:
            js.validate(msg, self.RPC_SCHEMA)
        except js.ValidationError as error:
            raise exceptions.RPCInvalidRequest from error

        handler = self.dispatch_socket_command(msg)
        if not handler:
            raise exceptions.RPCMethodNotFound

        try:
            if utils.is_coro(handler):
                result = await handler(**msg['params'])
            else:
                result = handler(**msg['params'])
        # TODO need to inspect method members, or else we swallow
        # actual TypeErrors in method call.
        except TypeError as error:
            raise exceptions.RPCInvalidParams from error

        return {
            'result': result,
            'id': msg['id']
        }

    async def handle_socket_client(self, reader, writer):
        buf = b''
        while not writer.transport.is_closing():
            buf += await reader.read(4096)
            if buf == b'':
                logger.info('client disconnected')
                writer.close()
                return
            msg, buf = utils.parse_rpc_message(buf)
            if msg is None:
                continue

            try:
                msg = json.loads(msg.decode())
            except json.JSONDecodeError:
                raise exceptions.RPCParseError

            try:
                response = await self.handle_rpc_request(msg)
            except exceptions.RPCError as error:
                response = {
                    'jsonrpc': '2.0',
                    'id': msg['id'],
                    'error': {
                        'code': error.code,
                        'message': error.message,
                        'data': error.meaning
                    }
                }

            response = utils.pack_rpc_message(response)
            writer.write(response)

    async def stop(self):
        logger.info('Shutting down...')
        self._socket_server.close()
        await self._socket_server.wait_closed()

    async def start(self):
        sock = self.make_socket_file()
        self._socket_server = await asyncio.start_unix_server(
            self.handle_socket_client,
            sock=sock,
            loop=self.loop
        )


class RPCClient:

    def __init__(self):
        self.socket = None
        self.reader = None
        self.writer = None

    async def connect(self, timeout=5):
        self.socket = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM
        )
        self.socket.settimeout(timeout)
        try:
            self.socket.connect(
                os.path.expanduser(
                    '~/.fixation/command_socket'
                )
            )
        except socket.error:
            raise exceptions.RPCCouldNotConnectError
        self.reader, self.writer = await asyncio.open_connection(
            sock=self.socket)

    def close(self):
        self.writer.close()
        self.socket.close()

    async def read(self):
        try:
            r = await self.reader.read(4096)
        except socket.error:
            raise exceptions.RPCBadConnectionError
        if r == b'':
            raise EOFError
        return r

    async def send_command(self, name, timeout=30, **kwargs):

        uid = str(uuid.uuid4())
        message = {
            'jsonrpc': '2.0',
            'method': name,
            'params': kwargs,
            'id': uid
        }
        message = utils.pack_rpc_message(message)
        self.writer.write(message)
        await self.writer.drain()

        try:
            buf = b''
            t = time.time()
            while time.time() - t < timeout:
                buf += await self.read()
                resp, buf = utils.parse_rpc_message(buf)
                if resp is not None:
                    break
            else:
                raise TimeoutError
        except KeyboardInterrupt:
            raise exceptions.RPCBadConnectionError()
        except TimeoutError:
            print('Timeout!')
            raise
        except Exception as error:
            logger.exception(error)
            return

        resp = json.loads(resp.decode())

        if 'result' in resp:
            return resp['result']
        else:
            raise exceptions.RPCCommandError(resp['error'])
