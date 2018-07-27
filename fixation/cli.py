import logging
import os
import threading
import time
import socket
import sys
import uuid

from . import utils, client


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CommandTicker(threading.Thread):

    def __init__(self):
        super().__init__()

        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):

        ticks = ['[.  ]', '[.. ]', '[...]', '[ ..]', '[  .]', '[   ]']
        i = 0
        first = True
        while True:
            self.stop_event.wait(0.25)
            if self.stop_event.isSet():
                break
            if i == len(ticks):
                first = False
                i = 0

            if not first:
                sys.stderr.write('\r{}\r'.format(ticks[i]))
                sys.stderr.flush()

            i += 1

            sys.stderr.flush()


class FixationCommand(object):

    class CouldNotConnectError(Exception): pass
    class BadConnectionError(Exception): pass
    class CommandError(Exception): pass

    def __init__(self, timeout=5):
        self.s = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM
        )
        self.s.settimeout(timeout)
        socket_path = os.path.expanduser(
            '~/.fixation/command_socket')
        try:
            self.s.connect(socket_path)
        except socket.error as error:
            raise self.CouldNotConnectError from error
        self.f = self.s.makefile('rwb', 4096)

    def close(self):
        self.f.close()
        self.s.close()

    def read(self):
        try:
            r = self.f.readline().decode().rstrip('\n')
        except socket.error:
            raise self.BadConnectionError

        if r == '':
            raise EOFError

        return r

    def send_command(self, name, timeout=30, **args):

        uid = str(uuid.uuid4())
        message = {
            'jsonrpc': '2.0',
            'method': name,
            'params': args,
            'id': uid
        }
        message = utils.pack_rpc_message(message)
        self.f.write(message)
        self.f.flush()

        ticker_thread = CommandTicker()
        ticker_thread.start()

        try:
            buf = b''
            t = time.time()
            while time.time() - t < timeout:
                buf += self.f.read(4096)
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
        finally:
            ticker_thread.stop()
            ticker_thread.join()

        if 'result' in resp:
            return resp['result']
        else:
            raise self.CommandError(resp['error'])

    def __getattr__(self, name):
        try:
            return super().__getattribute__(name)
        except Exception:
            def __command(**kwargs):
                try:
                    return self.send_command(name, **kwargs)
                except Exception as error:
                    print(error)
            self.__setattr__(name, __command)
            return __command

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


commands = {}
aliases = {}


def command(func):
    global command, aliases
    if not hasattr(func, '__doc__'):
        raise ValueError('All commands need valid docstrings')

    try:
        func = func.im_func
    except AttributeError:
        pass

    commands[func.__name__] = func
    return func


def requires_daemon_running(meth):
    def new_meth(*args, **kwargs):
        if is_daemon_running():
            return meth(*args, **kwargs)
        else:
            print('Daemon is not running!')
    new_meth.__name__ = meth.__name__
    new_meth.__doc__ = meth.__doc__
    return new_meth


def is_daemon_running():
    # pidfile = os.path.expanduser('~/.fixation/fixd.pid')
    # try:
    #     with open(pidfile, 'r') as f:
    #         pid = int(f.read())
    #     with open('/proc/{}/cmdline'.format(pid), 'r') as f:
    #         cmdline = f.read().lower()
    # except Exception:
    #     cmdline = ''
    #
    # return 'fixation' in cmdline
    return True


@command
@requires_daemon_running
def test(args):
    ARGS = ['arg1', 'arg2']
    kwargs = dict(zip(ARGS, args))

    with FixationCommand() as fc:
        try:
            r = fc.send_test_request(**kwargs)
        except Exception as error:
            print(error)
            return
        print(r)


@command
def start(argv):
    _client = client.FixClient()
    _client()


def usage(argv):
    print('You aint use this right.\n')


def _main(argv):
    global commands
    name = argv[1]
    args = argv[2:]

    if name not in commands:
        usage(argv)
        os._exit(0)
        return

    result = commands[name](args)
    return result


def main(argv=None):
    if argv is None:
        argv = sys.argv
    return _main(argv)


if __name__ == "__main__":
    response = main()
    if response is not None:
        sys.exit(response)


