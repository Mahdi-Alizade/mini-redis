import os
import time
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

    def rewrite(self, current_data, current_expires):
        """
        Compacts the database state into a temporary file and atomically replaces
        the bloated append-only file.
        """
        temp_filename = self.filename + ".tmp"

        try:
            temp_file = open(temp_filename, "wb")
        except IOError as err:
            print("Failed to open temporary file for AOF rewrite:", err)
            return False

        current_time = time.time()

        for key, value in current_data.items():
            # Skip keys that are already expired
            if key in current_expires:
                remaining_ttl = current_expires[key] - current_time
                if remaining_ttl <= 0:
                    continue
            else:
                remaining_ttl = None

            cmd = None

            if isinstance(value, str):
                cmd = ["SET", str(key), str(value)]
                if remaining_ttl is not None:
                    cmd.extend(["EX", str(int(remaining_ttl))])

            elif isinstance(value, list):
                if len(value) > 0:
                    cmd = ["RPUSH", str(key)]
                    for item in value:
                        cmd.append(str(item))

            elif isinstance(value, set):
                if len(value) > 0:
                    cmd = ["SADD", str(key)]
                    for member in value:
                        cmd.append(str(member))

            elif isinstance(value, dict):
                if len(value) > 0:
                    cmd = ["HSET", str(key)]
                    for field, fval in value.items():
                        cmd.append(str(field))
                        cmd.append(str(fval))

            if cmd:
                temp_file.write(RESPParser.serialize(cmd))

            # Set expiration explicitly if key is not string with EX
            if remaining_ttl is not None and not isinstance(value, str):
                exp_cmd = ["EXPIRE", str(key), str(int(remaining_ttl))]
                temp_file.write(RESPParser.serialize(exp_cmd))

        temp_file.flush()
        temp_file.close()

        # Safely close old handle, replace file, and reopen
        self.close()

        try:
            if os.path.exists(self.filename):
                os.replace(temp_filename, self.filename)
            else:
                os.rename(temp_filename, self.filename)
        except OSError as e:
            print("Failed to replace AOF file with compacted version:", e)
            self._open_file()
            return False

        self._open_file()
        return True

    def close(self):
        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
            self.file_handle = None