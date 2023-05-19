import logging

from socks5.server import Socks5
from socks5.server.sessions import AbstractWebSocketSession

logging.basicConfig(level=logging.DEBUG)

class WebSocketSession(AbstractWebSocketSession):
    proxy_url = "wss://ssh.shizuku.workers.dev/"


server = Socks5(port=8080, connect_session_class=WebSocketSession)

if __name__ == "__main__":
    server.run()
