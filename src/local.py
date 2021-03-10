import argparse
import asyncio
import json
import logging
import socket

from secure_socket import SecureSocket, Cipher


class Local(SecureSocket):
    def __init__(self, loop: asyncio.AbstractEventLoop, password: str,
                 listen_ip: str, listen_port: int, server_ip: str, server_port: int) -> None:
        super().__init__(loop, Cipher(password))
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.server_ip = server_ip
        self.server_port = server_port

    async def listen(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as bind_sock:
            bind_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bind_sock.bind((self.listen_ip, self.listen_port))
            bind_sock.listen(socket.SOMAXCONN)
            bind_sock.setblocking(False)

            logging.info(f'Listening to {self.listen_ip}:{self.listen_port}')

            while True:
                client_sock, (client_ip, client_port) = await self.loop.sock_accept(bind_sock)
                logging.info(f'Accepted client from {client_ip}:{client_port} with socket {client_sock.fileno()}')
                asyncio.ensure_future(self.handle_client(client_sock))

    async def handle_client(self, client_sock: socket.socket) -> None:
        server_sock = None
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setblocking(False)
            await self.loop.sock_connect(server_sock, (self.server_ip, self.server_port))

            task = asyncio.gather(self.encrypt_copy(server_sock, client_sock),
                                  self.decrypt_copy(client_sock, server_sock))
            try:
                await task
            except ConnectionError:
                task.cancel()
        except Exception as e:
            logging.error(e)
        finally:
            if server_sock is not None:
                logging.info(f'Closing server socket {server_sock.fileno()}')
                server_sock.close()
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
    local = Local(loop, config['password'], config['local_ip'], config['local_port'],
                  config['server_ip'], config['server_port'])
    loop.run_until_complete(local.listen())


if __name__ == '__main__':
    main()
