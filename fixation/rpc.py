import asyncio
import errno
import json
import jsonschema as js
import logging
import os
import socket
import time
import uuid

from fixation import constants as fc, exceptions, utils


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
            'cance_replace_order': self.fix_client.cancel_replace_order,
            'send_test_request': self.fix_client.send_test_request
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

        handler = self.dispatch_socket_command(data)
        if not handler:
            raise exceptions.RPCMethodNotFound

        try:
            if utils.is_coro(handler):
                result = await handler(**data['params'])
            else:
                result = handler(**data['params'])
        # TODO need to inspect method members, or else we swallow
        # actual TypeErrors in method call.
        except TypeError:
            raise exceptions.RPCInvalidParams

        return {
            'result': result,
            'id': data['id']
        }

    async def handle_socket_client(self, reader, writer, timeout=10):
        buf = b''
        while True:
            try:
                buf += await asyncio.wait_for(reader.read(4096), timeout)
            except asyncio.TimeoutError as error:
                logger.exception(error)
                return
            if buf == b'':
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

    async def stop(self):
        logger.info('Shutting down...')
        self._socket_server.close()
        await self._socket_server.wait_close()

    async def start(self):
        sock = self.make_socket_file()
        self._socket_server = await asyncio.start_unix_server(
            self.handle_socket_client,
            sock=sock,
            loop=self.loop
        )


class RPCClient:

    class CouldNotConnectError(Exception): pass
    class BadConnectionError(Exception): pass
    class CommandError(Exception): pass

    def __init__(self, timeout=5):
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
            raise self.CouldNotConnectError
        self.socket_file = self.socket.makefile('rwb', 4096)

    def close(self):
        self.socket_file.close()
        self.socket.close()

    def read(self):
        try:
            r = self.socket_file.readline().decode().rstrip('\n')
        except socket.error:
            raise self.BadConnectionError

        if r == '':
            raise EOFError

        return r

    def send_command(self, name, timeout=30, **kwargs):

        uid = uuid.uuid4()
        message = {
            'jsonrpc': '2.0',
            'method': name,
            'params': kwargs,
            'id': uid
        }
        message = utils.pack_rpc_message(message)
        self.socket_file.write(message)
        self.socket_file.flush()

        try:
            buf = b''
            t = time.time()
            while time.time() - t < timeout:
                buf += self.socket_file.read(4096)
                resp, buf = utils.parse_rpc_message(buf)
                if resp is not None:
                    break
            else:
                raise TimeoutError
        except KeyboardInterrupt:
            raise self.BadConnectionError()
        except TimeoutError:
            print('Timeout!')
            raise
        except Exception as error:
            logger.exception(error)
            return

        if 'result' in resp:
            return resp['result']
        else:
            raise self.CommandError(resp['error'])
