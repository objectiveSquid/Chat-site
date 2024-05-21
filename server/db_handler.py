from shared.config import SERVER_CONFIG

import dataclasses
import sqlite3
import hashlib
import random
import time
import enum
import os


class AddUserResult(enum.Enum):
    success = 0
    username_too_short = 1
    username_too_long = 2


@dataclasses.dataclass(frozen=True)
class Message:
    sender: str
    receiver: str
    content: str
    time_sent: int


class DBWrapper:
    def __init__(self) -> None:
        os.makedirs(
            os.path.split(SERVER_CONFIG["database"]["filepath"])[0], exist_ok=True
        )
        self.__conn = sqlite3.connect(
            str(SERVER_CONFIG["database"]["filepath"]),
            SERVER_CONFIG["database"]["connect_timeout"],
        )
        self.__cursor = self.__conn.cursor()

    def __del__(self) -> None:
        self.__cursor.close()
        self.__conn.close()

    def ensure_tables(self) -> None:
        self.__cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT,
                token_hash BLOB
            )"""
        )
        self.__cursor.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                sender_username TEXT,
                receiver_username TEXT,
                content TEXT,
                time_sent INTEGER
            )"""
        )

    def add_user(self, username: str) -> tuple[str | None, AddUserResult]:
        if username < SERVER_CONFIG["database"]["min_username_length"]:
            return None, AddUserResult.username_too_short
        if username > SERVER_CONFIG["database"]["max_username_length"]:
            return None, AddUserResult.username_too_long

        token = "".join(
            random.choices(
                SERVER_CONFIG["database"]["token_charset"],
                k=SERVER_CONFIG["database"]["token_length"],
            )
        )
        token_hash = hashlib.sha512(token.encode()).digest()

        self.__cursor.execute(
            "INSERT INTO users (username, token_hash) VALUES (?, ?)",
            [username, token_hash],
        )

        self.__conn.commit()
        return token, AddUserResult.success

    def check_token(self, token: str) -> tuple[bool, str | None]:
        self.__cursor.execute(
            "SELECT username FROM users WHERE token_hash = ?",
            [hashlib.sha512(token.encode()).digest()],
        )
        usernames = self.__cursor.fetchone()

        if usernames == None:
            return False, None  # token doesnt exist

        return True, usernames[0]

    def fetch_messages(
        self, first_user: str, second_user: str, time_back_secs: int
    ) -> list[Message]:
        self.__cursor.execute(
            "SELECT sender, content, time_sent FROM messages WHERE sender IN (?, ?) AND receiver IN (?, ?) AND time_sent >= ?",
            [
                first_user,
                second_user,
                first_user,
                second_user,
                int(time.time() - time_back_secs),
            ],
        )

        messages = [
            Message(
                sender,
                first_user if sender == second_user else first_user,
                content,
                time_sent,
            )
            for sender, content, time_sent in self.__cursor.fetchall()
        ]

        return messages

    def add_message(self, sender: str, receiver: str, content: str) -> None:
        self.__cursor.execute(
            "INSERT INTO messages (sender_username, receiver_username, content, time_sent) VALUES (?, ?, ?, ?)",
            [sender, receiver, content, int(time.time())],
        )

        self.__conn.commit()
