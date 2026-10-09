# SPDX-License-Identifier: CC-BY-NC-4.0
"""POSIX serial lamp client. Does not power, flash, or qualify a physical board."""
import argparse, fcntl, os, select, termios, time


def command_bytes(words):
    if words == ['OFF']:
        pass
    elif words and words[0] in ('SET', 'BREATH', 'FLASH'):
        limits = {'SET': [(0, 1000)], 'BREATH': [(200, 10000)],
                  'FLASH': [(20, 10000), (20, 10000)]}[words[0]]
        if len(words) != len(limits) + 1:
            raise ValueError('Wrong argument count')
        for s, (lo, hi) in zip(words[1:], limits):
            if not s.isascii() or not s.isdecimal() or len(s) > 5 or not lo <= int(s) <= hi:
                raise ValueError('Command argument outside firmware contract')
    else:
        raise ValueError('Unknown command')
    return (' '.join(words) + '\n').encode('ascii')


def request(device, words, timeout=1.0):
    payload = command_bytes(words)
    if not 0 < timeout <= 30:
        raise ValueError('Timeout must be 0..30 seconds')
    fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    original = None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = termios.tcgetattr(fd)
        config = list(original)
        config[6] = list(original[6])
        config[0] = config[1] = config[3] = 0
        config[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        config[4] = config[5] = termios.B115200
        config[6][termios.VMIN] = config[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, config)
        # Discard preceding ACKs. Only one outstanding request is supported.
        termios.tcflush(fd, termios.TCIOFLUSH)
        deadline = time.monotonic() + timeout
        sent = 0
        while sent < len(payload):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                raise TimeoutError('Serial write timeout; board state unknown')
            try:
                sent += os.write(fd, payload[sent:])
            except BlockingIOError:
                continue
        data = bytearray()
        while b'\n' not in data:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise TimeoutError('No ACK; command may have executed, board state unknown')
            chunk = os.read(fd, 64)
            if not chunk:
                raise OSError('Serial connection closed')
            data.extend(chunk)
            if len(data) > 64:
                raise ValueError('Oversized board reply')
        reply = bytes(data).split(b'\n', 1)[0].rstrip(b'\r')
        if reply != b'OK':
            raise ValueError('Board rejected command or unexpected reply: ' + repr(reply))
        return 'OK'
    finally:
        if original is not None:
            termios.tcsetattr(fd, termios.TCSANOW, original)
        os.close(fd)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('device'); p.add_argument('command', nargs='+')
    p.add_argument('--timeout', type=float, default=1)
    a = p.parse_args()
    try:
        print(request(a.device, a.command, a.timeout))
    except (OSError, ValueError, TimeoutError) as e:
        p.exit(1, str(e) + '\n')
