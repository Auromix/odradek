# SPDX-License-Identifier: CC-BY-NC-4.0
"""Host transport tests with PTY emulator, not a physical lamp-board test."""
import os, pty, select, threading, unittest
from lamp_cli import command_bytes, request


class TransportTests(unittest.TestCase):
    def exchange(self, words, reply):
        master, slave = pty.openpty()
        received = []
        def emulator():
            data = bytearray()
            while b'\n' not in data:
                if not select.select([master], [], [], 2)[0]:
                    return
                data.extend(os.read(master, 128))
            received.append(bytes(data))
            if reply is not None:
                os.write(master, reply)
        worker = threading.Thread(target=emulator)
        worker.start()
        try:
            return request(os.ttyname(slave), words, .3), received
        finally:
            worker.join(3)
            os.close(slave); os.close(master)
            self.assertFalse(worker.is_alive())

    def test_ack(self):
        for words in (['OFF'], ['SET', '1000'], ['BREATH', '2000'], ['FLASH', '100', '200']):
            result, data = self.exchange(words, b'OK\n')
            self.assertEqual(result, 'OK'); self.assertEqual(data, [command_bytes(words)])

    def test_rejection(self):
        for reply in (b'ERR\n', b'noise\n', b'x' * 65):
            with self.assertRaises(ValueError):
                self.exchange(['OFF'], reply)

    def test_timeout(self):
        with self.assertRaises(TimeoutError):
            self.exchange(['OFF'], None)

    def test_invalid_before_open(self):
        for words in ([], ['SET', '-1'], ['SET', '1001'], ['SET', '0', '1'],
                      ['SET', '１２'], ['BREATH', '199'], ['FLASH', '20'], ['off']):
            with self.assertRaises(ValueError):
                request('/device-that-does-not-exist', words)


if __name__ == '__main__':
    unittest.main()
