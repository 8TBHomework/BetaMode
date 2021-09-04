import json
import sys
import struct


def get_message():
    raw_length = sys.stdin.buffer.read(4)

    if not raw_length:
        sys.exit(0)
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


# Encode a message for transmission, given its content.
def _encode_message(content):
    content_str = json.dumps(content).encode("utf-8")

    encoded_length = struct.pack('=I', len(content_str))
    encoded_content = struct.pack(str(len(content_str)) + "s", content_str)

    return encoded_length, encoded_content


# Send an encoded message to stdout.
def send_message(content):
    length, encoded = _encode_message(content)
    sys.stdout.buffer.write(length)
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()
