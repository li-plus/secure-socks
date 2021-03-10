import asyncio
import base64
import socket

BUFFER_SIZE = 4096


class Cipher(object):
    """Encrypt message with substitution cipher"""

    def __init__(self, password: str) -> None:
        self.encrypt_table = base64.b64decode(password)
        self.decrypt_table = bytearray(256)
        for plain, cipher in enumerate(self.encrypt_table):
            self.decrypt_table[cipher] = plain

    def encrypt(self, msg: bytearray) -> None:
        for i, plain in enumerate(msg):
            msg[i] = self.encrypt_table[plain]

    def decrypt(self, msg: bytearray) -> None:
        for i, cipher in enumerate(msg):
            msg[i] = self.decrypt_table[cipher]


class SecureSocket(object):
    def __init__(self, loop: asyncio.AbstractEventLoop, cipher: Cipher) -> None:
        self.loop = loop
        self.cipher = cipher

    async def decrypt_recv(self, sock: socket.socket) -> bytearray:
        msg = await self.loop.sock_recv(sock, BUFFER_SIZE)
        msg = bytearray(msg)
        self.cipher.decrypt(msg)
        return msg

    async def encrypt_send(self, sock: socket.socket, msg: bytearray) -> None:
        self.cipher.encrypt(msg)
        await self.loop.sock_sendall(sock, msg)

    async def encrypt_copy(self, dst: socket.socket, src: socket.socket) -> None:
        while True:
            msg = await self.loop.sock_recv(src, BUFFER_SIZE)
            if not msg:
                raise BrokenPipeError

            await self.encrypt_send(dst, bytearray(msg))

    async def decrypt_copy(self, dst: socket.socket, src: socket.socket) -> None:
        while True:
            msg = await self.decrypt_recv(src)
            if not msg:
                raise BrokenPipeError

            await self.loop.sock_sendall(dst, bytes(msg))
