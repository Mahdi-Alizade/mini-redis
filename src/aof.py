import os
from src.protocol import RESPParser


class AOFManager:
    def __init__(self, filename="appendonly.aof"):
        self.filename = filename
        self.file_handle = None
        self._open_file()

    def _open_file(self):
        try:
            self.file_handle = open(self.filename, "ab", buffering=0)
        except Exception as e:
            print("Failed to open AOF file:", e)
            self.file_handle = None

    def append_command(self, command_parts):
        if not self.file_handle:
            return

        serialized_bytes = RESPParser.serialize(command_parts)
        try:
            self.file_handle.write(serialized_bytes)
        except IOError as err:
            print("Write error on AOF:", err)

    def load_commands(self):
        commands = []
        if not os.path.exists(self.filename):
            return commands

        with open(self.filename, "rb") as f:
            buffer = f.read()

        cursor = 0
        total_len = len(buffer)
        while cursor < total_len:
            parsed_item, consumed = RESPParser.parse_one(buffer[cursor:])
            if consumed == 0:
                break
            cursor = cursor + consumed
            if parsed_item:
                commands.append(parsed_item)

        return commands

    def close(self):
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()