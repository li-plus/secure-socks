# Secure Socks

A mini encrypted socks tunnel to bypass the firewall. Adapted from [lightsocks-python](https://github.com/linw1995/lightsocks-python) using async programming.

## Quick Start

Prepare a remote VPS outside the firewall. Your VPS should be running Linux with Python 3.6 or higher.

To generate a random password, type `python rand_pass.py` and copy its output to your config file.

Run the server on your remote VPS. It will listen to 0.0.0.0:8099 by default.

```sh
python server.py
```

Open `config.json` and change the server IP to that of your remote VPS. Then run local service on your PC to start a SOCKS5 proxy on localhost:1080.

```sh
python local.py
```

Enjoy the world of no firewall!

## Using SOCKS5 proxy

In terminal: some applications like `curl` have implemented SOCKS5 proxy. Test your proxy with `curl`.

```sh
curl --socks5 localhost:1080 https://www.google.com
```

In browser: modern browsers usually support SOCKS5 proxy

+ Chrome: Install [Proxy SwitchyOmega](https://chrome.google.com/webstore/detail/proxy-switchyomega/padekgcemlokbadohgkifijomclgjgif?hl=en) extension and set the default proxy as SOCKS5 on 127.0.0.1:1080
+ FireFox: Open Menu -> Options -> Network Settings -> Select "Manual proxy configuration" -> Set "SOCKS Host" as SOCKS v5 127.0.0.1:1080

In the entire system: Linux & macOS support system-wide SOCKS5 proxy settings, but Windows does not.

NOTE: Some helpful tools like `privoxy` can convert a SOCKS5 proxy into a HTTP proxy, which is well supported by all systems.
