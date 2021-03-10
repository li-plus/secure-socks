import argparse
import asyncio
import json
import logging
import socket

from secure_socket import SecureSocket, Cipher


class Server(SecureSocket):
    def __init__(self, loop: asyncio.AbstractEventLoop, password: str,
                 listen_ip: str, listen_port: int) -> None:
        super().__init__(loop, Cipher(password))
        self.listen_ip = listen_ip
        self.listen_port = listen_port

    async def listen(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bind_sock:
            bind_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bind_sock.setblocking(False)
            bind_sock.bind((self.listen_ip, self.listen_port))
            bind_sock.listen(socket.SOMAXCONN)

            logging.info(f'Listening to {self.listen_ip}:{self.listen_port}')

            while True:
                client_sock, (client_ip, client_port) = await self.loop.sock_accept(bind_sock)
                logging.info(f'Accepted client from {client_ip}:{client_port} with socket {client_sock.fileno()}')
                asyncio.ensure_future(self.handle_client(client_sock))

    async def handle_client(self, client_sock: socket.socket) -> None:
        remote_sock = None
        try:
            buf = await self.decrypt_recv(client_sock)
            if not buf or buf[0] != 0x05:
                raise RuntimeError(f'Unexpected socks type {buf[0]}')

            await self.encrypt_send(client_sock, bytearray((0x05, 0x00)))

            buf = await self.decrypt_recv(client_sock)
            if len(buf) < 7:
                raise RuntimeError('Invalid socks request')

            if buf[1] != 0x01:
                raise RuntimeError(f'Invalid socks command {buf[1]}')

            remote_port = int(buf[-2:].hex(), 16)

            if buf[3] == 0x01:
                # ipv4
                remote_ip = socket.inet_ntop(socket.AF_INET, buf[4:4 + 4])
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.setblocking(False)
                await self.loop.sock_connect(remote_sock, (remote_ip, remote_port))
                logging.info(f'Connected to remote ipv4 address {remote_ip}:{remote_port}')
            elif buf[3] == 0x03:
                # domain
                remote_domain = buf[5:-2].decode()
                for res in await self.loop.getaddrinfo(remote_domain, remote_port):
                    remote_family, remote_type, remote_proto, _, remote_addr = res
                    try:
                        remote_sock = socket.socket(remote_family, remote_type, remote_proto)
                        remote_sock.setblocking(False)
                        await self.loop.sock_connect(remote_sock, remote_addr)
                        break
                    except OSError:
                        if remote_sock is not None:
                            remote_sock.close()
                            remote_sock = None

                if remote_sock is None:
                    raise RuntimeError(f'Cannot connect to remote domain {remote_domain}:{remote_port}')

                logging.info(f'Connected to remote domain {remote_domain}:{remote_port}')
            elif buf[3] == 0x04:
                # ipv6
                remote_ipv6 = socket.inet_ntop(socket.AF_INET6, buf[4:4 + 16])
                remote_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                remote_sock.setblocking(False)
                await self.loop.sock_connect(remote_sock, (remote_ipv6, remote_port))
                logging.info(f'Connected to remote ipv6 address [{remote_ipv6}]:{remote_port}')
            else:
                raise RuntimeError(f'Unexpected address type {buf[3]}')

            await self.encrypt_send(client_sock, bytearray(
                (0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)))

            task = asyncio.gather(self.decrypt_copy(remote_sock, client_sock),
                                  self.encrypt_copy(client_sock, remote_sock))
            try:
                await task
            except ConnectionError:
                task.cancel()

        except Exception as e:
            logging.error(e)
        finally:
            if remote_sock is not None:
                logging.info(f'Closing remote socket {remote_sock.fileno()}')
                remote_sock.close()
            logging.info(f'Closing client socket {client_sock.fileno()}')
            client_sock.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.json', help='Config file path')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format=r'[%(asctime)s %(levelname)s] %(message)s')

    with open(args.config) as f:
        config = json.load(f)

    loop = asyncio.get_event_loop()
    server = Server(loop, config['password'], '0.0.0.0', config['server_port'])
    loop.run_until_complete(server.listen())


if __name__ == '__main__':
    main()
