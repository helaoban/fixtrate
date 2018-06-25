import os
import socket
import sys
import threading

from fixation.client import FixClient


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
        try:
            self.s.connect(
                os.path.expanduser(
                    '~/.fixation/command_socket'
                )
            )
        except socket.error as error:
            print(error)
            raise self.CouldNotConnectError
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

    def send_command(self, name, **args):
        self.f.write('{}\n'.format(name).encode())

        lines = []
        for k, v in args.items():

            if hasattr(v, '__iter__') and not isinstance(v, str):
                v = list(v)
            else:
                v = [v]

            line = '{}\n'.format('\t'.join([k, *v]))
            lines.append(line.encode())

        self.f.writelines(lines)
        self.f.write('done\n'.encode())
        self.f.flush()

        ticker_thread = CommandTicker()
        ticker_thread.start()

        try:
            ok = self.read() == 'ok'
        except KeyboardInterrupt:
            raise self.BadConnectionError()
        except Exception as error:
            raise
        finally:
            ticker_thread.stop()
            ticker_thread.join()

        if ok:
            r = {}
            for i in range(21):
                if i == 20:
                    raise Exception('close this connection')

                line = self.read()
                if line == 'done':
                    break
                argval = line.split('\t')
                r[argval[0]] = argval[1:]

            return r
        else:
            problems = []
            for i in range(21):
                if i == 20:
                    raise Exception('close this connection!')

                line = self.read()
                if line == 'done':
                    break

                problems.append(line)

            raise self.CommandError('\n'.join(problems))

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
            r = fc.send_test_request(**kwargs).get('response', ['No response'])[0]
        except Exception as error:
            print(error)
            return
        print(r)


@command
def start(argv):
    client = FixClient()
    client()


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


