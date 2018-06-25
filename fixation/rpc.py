import asyncio
import errno
import logging
import os
import socket

from fixation import exceptions


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RPCServer(object):

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

    async def handle_socket_command(self, name, **kwargs):

        handler = {
            'place_order': self.session.place_order,
            'send_test_request': self.session.mock_send_test_request
        }.get(name)

        if handler:
            return handler(**kwargs)

        raise exceptions.UnknownCommand

    @staticmethod
    def parse_socket_command(data):

        lines = data.splitlines()
        name = lines[0]
        # remove 'done'
        arg_lines = lines[1: len(lines) - 1]

        kwargs = {}
        for line in arg_lines:
            items = line.split('\t')
            key = items[0]
            value = items[1:]

            if len(value) < 2:
                value = items[1]

            kwargs[key] = value

        return name, kwargs

    @staticmethod
    def validate_socket_command(data, args):
        return True

    async def handle_socket_client(self, reader, writer, timeout=10):
        print('client connected')
        buf = b''
        while True:
            try:
                buf += await asyncio.wait_for(reader.read(4096), timeout)
            except asyncio.TimeoutError:
                print('Timeout error!')
                writer.write(b'Timeout!')
                writer.close()
                return

            if buf == b'':
                print('client disconnected')
                return

            if b'done\n' in buf:
                break

        data = buf.decode()

        try:
            name, kwargs = self.parse_socket_command(data)
        except Exception as error:
            print(error)
            writer.write(b'error')
            return

        try:
            self.validate_socket_command(name, kwargs)
        except Exception as error:
            print(error)
            writer.write(b'error')
            return

        writer.write(b'ok\n')

        try:
            r = await self.handle_socket_command(name, **kwargs)
        except exceptions.UnknownCommand:
            writer.write(b'error\n')
            return
        except Exception as error:
            print(error)
            writer.write(b'error\n')
            return

        lines = []
        for k, v in r.items():
            if hasattr(v, '__iter__') and not isinstance(v, str):
                v = list(v)
            else:
                v = [v]

            line = '{}\n'.format('\t'.join([k, *v]))
            lines.append(line.encode())

        lines.append(b'done\n')
        writer.writelines(lines)

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
