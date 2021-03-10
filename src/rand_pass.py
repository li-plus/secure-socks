import base64
import random


def main():
    table = bytearray(range(256))
    random.shuffle(table)
    password = base64.b64encode(table)
    print(password.decode('ascii'))


if __name__ == '__main__':
    main()
