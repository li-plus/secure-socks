import asyncio
import json
import socket
from pathlib import Path

from local import Local
from server import Server

LOCAL_PORT = 12345
SERVER_PORT = 23456
REMOTE_PORT = 34567

BUFFER_SIZE = 4096


async def remote_handle_client(loop: asyncio.AbstractEventLoop, client_sock: socket.socket):
    with client_sock:
        buffer = await loop.sock_recv(client_sock, BUFFER_SIZE)
        buffer = b'Reply: ' + buffer
        await loop.sock_sendall(client_sock, buffer)


async def remote_listen(loop: asyncio.AbstractEventLoop):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bind_sock:
        bind_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bind_sock.setblocking(False)
        bind_sock.bind(('127.0.0.1', REMOTE_PORT))
        bind_sock.listen(socket.SOMAXCONN)

        while True:
            client_sock, _ = await loop.sock_accept(bind_sock)
            asyncio.ensure_future(remote_handle_client(loop, client_sock))


async def async_test_e2e(loop: asyncio.AbstractEventLoop, password: str):
    local = Local(loop, password, '127.0.0.1', LOCAL_PORT, '127.0.0.1', SERVER_PORT)
    server = Server(loop, password, '127.0.0.1', SERVER_PORT)
    asyncio.ensure_future(local.listen())
    asyncio.ensure_future(server.listen())
    asyncio.ensure_future(remote_listen(loop))

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    await loop.sock_connect(client_sock, ('127.0.0.1', LOCAL_PORT))

    # greeting
    client_hello = bytes((0x05, 0x01, 0x00))
    await loop.sock_sendall(client_sock, client_hello)
    server_hello = await loop.sock_recv(client_sock, BUFFER_SIZE)
    assert server_hello == bytes((0x05, 0x00))
    # request: connect to remote 127.0.0.1:34567
    socks_request = bytes((0x05, 0x01, 0x00, 0x01, 0x7f, 0x00, 0x00, 0x01, 0x87, 0x07))
    await loop.sock_sendall(client_sock, socks_request)
    socks_response = await loop.sock_recv(client_sock, BUFFER_SIZE)
    assert socks_response == bytes((0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
    # pipe
    msg = b'hello world'
    await loop.sock_sendall(client_sock, msg)
    msg_reply = await loop.sock_recv(client_sock, BUFFER_SIZE)
    assert msg_reply == b'Reply: hello world'


def test_e2e():
    config_path = Path(__file__).resolve().parent.parent / 'src' / 'config.json'
    with open(config_path) as f:
        config = json.load(f)
    password = config['password']

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_test_e2e(loop, password))


if __name__ == '__main__':
    test_e2e()
