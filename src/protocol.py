"""RESP (Redis Serialization Protocol) Parser and Serializer."""

from typing import Any, Tuple, Union


class ProtocolError(Exception):
    """Raised when RESP parsing fails due to malformed input."""
    pass


class RESPParser:
    """Parses and serializes Redis Serialization Protocol (RESP2) payloads."""

    CRLF = b"\r\n"

    @classmethod
    def serialize_simple_string(cls, data: str) -> bytes:
        return f"+{data}\r\n".encode("utf-8")

    @classmethod
    def serialize_error(cls, message: str) -> bytes:
        return f"-ERR {message}\r\n".encode("utf-8")

    @classmethod
    def serialize_integer(cls, value: int) -> bytes:
        return f":{value}\r\n".encode("utf-8")

    @classmethod
    def serialize_bulk_string(cls, data: Union[str, bytes, None]) -> bytes:
        if data is None:
            return b"$-1\r\n"
        if isinstance(data, str):
            encoded = data.encode("utf-8")
        else:
            encoded = data
        return f"${len(encoded)}\r\n".encode("utf-8") + encoded + cls.CRLF

    @classmethod
    def serialize_array(cls, items: Union[list, tuple, None]) -> bytes:
        if items is None:
            return b"*-1\r\n"
        payload = [f"*{len(items)}\r\n".encode("utf-8")]
        for item in items:
            payload.append(cls.serialize(item))
        return b"".join(payload)

    @classmethod
    def serialize(cls, value: Any) -> bytes:
        """Serializes Python native data types to corresponding RESP binary format."""
        if value is None:
            return cls.serialize_bulk_string(None)
        if isinstance(value, bool):
            return cls.serialize_integer(1 if value else 0)
        if isinstance(value, int):
            return cls.serialize_integer(value)
        if isinstance(value, (str, bytes)):
            return cls.serialize_bulk_string(value)
        if isinstance(value, (list, tuple)):
            return cls.serialize_array(value)
        if isinstance(value, Exception):
            return cls.serialize_error(str(value))
        return cls.serialize_bulk_string(str(value))

    @classmethod
    def parse_one(cls, buffer: bytes) -> Tuple[Any, int]:
        """
        Parses a single RESP message from the buffer.
        Returns: (parsed_value, bytes_consumed)
        Returns (None, 0) if the buffer does not yet contain a complete message.
        """
        if not buffer:
            return None, 0

        prefix = buffer[0:1]

        if prefix == b"+":
            # Simple String
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0
            value = buffer[1:crlf_idx].decode("utf-8")
            return value, crlf_idx + 2

        elif prefix == b"-":
            # Simple Error
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0
            value = buffer[1:crlf_idx].decode("utf-8")
            return Exception(value), crlf_idx + 2

        elif prefix == b":":
            # Integer
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0
            value = int(buffer[1:crlf_idx].decode("utf-8"))
            return value, crlf_idx + 2

        elif prefix == b"$":
            # Bulk String
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0

            length = int(buffer[1:crlf_idx].decode("utf-8"))
            if length == -1:
                return None, crlf_idx + 2

            content_start = crlf_idx + 2
            content_end = content_start + length
            total_end = content_end + 2

            if len(buffer) < total_end:
                return None, 0

            if buffer[content_end:total_end] != cls.CRLF:
                raise ProtocolError("Missing CRLF at end of bulk string")

            value = buffer[content_start:content_end].decode("utf-8")
            return value, total_end

        elif prefix == b"*":
            # Array
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0

            num_elements = int(buffer[1:crlf_idx].decode("utf-8"))
            if num_elements == -1:
                return None, crlf_idx + 2

            cursor = crlf_idx + 2
            elements = []

            for _ in range(num_elements):
                item, consumed = cls.parse_one(buffer[cursor:])
                if consumed == 0:
                    return None, 0
                elements.append(item)
                cursor += consumed

            return elements, cursor

        else:
            # Inline command fallback (e.g. raw "PING\r\n")
            crlf_idx = buffer.find(cls.CRLF)
            if crlf_idx == -1:
                return None, 0
            line = buffer[:crlf_idx].decode("utf-8").strip()
            parts = line.split()
            return parts, crlf_idx + 2