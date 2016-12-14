import socketserver
from mysql_wire_framework.server import FrameworkServer


def start_server(host, port):
    server = socketserver.TCPServer((host, port), FrameworkServer)
