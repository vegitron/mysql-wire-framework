import socketserver
from importlib import import_module
from commonconf import settings
import sys

class FrameworkServer(socketserver.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        self._load_backend()
        super(FrameworkServer, self).__init__(*args, **kwargs)

    def _load_backend(self):
        module = settings.MYSQL_WIRE_SERVER_IMPLEMENTATION
        module, attr = module.rsplit('.', 1)

        mod = import_module(module)
        backend = getattr(mod, attr)

        self._backend = backend()


    def handle(self):
        self.sequence = 0

        self.handle_handshake()

        data = self.request.recv(1024)
        self.process_response(data)

        # No authorization yet!
        self.send_ok_packet()

        self.sequence = 0
        data = self.request.recv(1024)
        while data:
            length = data[:3]
            seq = data[3:4]
            command = ord(data[4:5])

            if command == 0x03: # text protocol
                self.get_sequence()
                query = data[5:]
                self.handle_query(query)

            self.sequence = 0
            data = self.request.recv(1024)


    def process_response(self, data):
        self.get_sequence()

    def get_sequence(self):
        val = self.sequence
        self.sequence += 1
        if self.sequence > 255:
            self.sequence = 0
        return val

    def handle_handshake(self):
        protocol_version = 0x0a
        server_version = self._backend.get_display_version()
        connection_id = 993


        handshake = bytearray()
        handshake.append(protocol_version)

        for c in server_version:
            handshake.append(ord(c))
        handshake.append(0x00)

        for c in connection_id.to_bytes(4, byteorder=sys.byteorder):
            handshake.append(c)
        handshake.append(0x00)

        for i in range(8):
            handshake.append(0x00)

        for i in range(2):
            handshake.append(0x00)


        self.send_packet(handshake)

    def send_ok_packet(self):
        ok = bytearray()
        ok.append(0x00) # OK
        ok.append(0x00) # affected rows
        ok.append(0x00) # last insert id
        ok.append(0x02) # Say autocommit was set
        ok.append(0x00)
        ok.append(0x00) # No warnings
        ok.append(0x00)

        self.send_packet(ok)


    def send_packet(self, byte_value):
        length = len(byte_value).to_bytes(3, byteorder=sys.byteorder)
        seq = self.get_sequence().to_bytes(1, byteorder=sys.byteorder)
        value = length + seq + byte_value

        self.request.sendall(value)


    def handle_query(self, query):
        data = self._backend.handle_query(query)

        self.send_length_encoded_packet(len(data["headers"]))

        for header in data["headers"]:
            self.send_data_header_packet(header)

        self.send_eof_packet()

        for row in data["rows"]:
            self.send_data_row_packet(row)
        self.send_eof_packet()

    def lenenc(self, value):
        if value > 250:
            raise Exception("Too lazy for larger values yet")

        return value.to_bytes(1, byteorder=sys.byteorder)

    def lenenc_str(self, value):
        enc = bytearray()
        enc.extend(self.lenenc(len(value)))
        enc.extend(value.encode("utf-8"))
        return enc

    def send_data_header_packet(self, header):
        packet = bytearray()
        character_set = 33 # utf8_general_ci
        max_col_length = 1024  # This is totally made up.  it shouldn't be

        column_type = 0xfd # Fallback to varchar?
        if header["type"] == int:
            column_type = 0x09
        elif header["type"] == str:
            column_type = 0xfd

        packet.extend(self.lenenc_str("def"))
        packet.extend(self.lenenc_str(header["name"]))
        packet.extend(self.lenenc_str("virtual_table"))
        packet.extend(self.lenenc_str("physical_table"))
        packet.extend(self.lenenc_str(header["name"]))
        packet.extend(self.lenenc_str(header["name"]))
        packet.append(0x0c) # Length of the reset of the packet
        packet.extend(character_set.to_bytes(2, byteorder=sys.byteorder))
        packet.extend(max_col_length.to_bytes(4, byteorder=sys.byteorder))
        packet.extend(column_type.to_bytes(1, byteorder=sys.byteorder))

        packet.append(0x00) # Flags?
        packet.append(0x00)

        packet.append(0x00) # Only doing ints/static strings now

        packet.append(0x00) # Filler
        packet.append(0x00)
        self.send_packet(packet)

    def send_data_row_packet(self, row):
        packet = bytearray()
        for value in row:
            packet.extend(self.lenenc_str(str(value)))
        self.send_packet(packet)

    def send_eof_packet(self):
        packet = bytearray()
        packet.append(0xfe) # EOF Header
        packet.append(0x00) # warnings
        packet.append(0x00)
        packet.append(0x02) # status flags
        packet.append(0x00)

        self.send_packet(packet)


    def send_length_encoded_packet(self, value):
        packet = bytearray()
        packet.extend(self.lenenc(value))
        self.send_packet(packet)
