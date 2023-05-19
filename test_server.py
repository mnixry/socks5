from socks5.server import Socks5
from socks5.server.sessions import WebSocketSession
import logging

logging.basicConfig(level=logging.INFO)

server = Socks5(port=8080, connect_session_class=WebSocketSession)

if __name__ == "__main__":
    server.run()
