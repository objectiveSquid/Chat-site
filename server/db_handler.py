from shared.config import SERVER_CONFIG
from shared.items import Relation, Message

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


SQLITE3_TRUE = b"\xFF"
SQLITE3_FALSE = b"\x00"


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
                username TEXT NOT NULL,
                token_hash BLOB NOT NULL
            )"""
        )
        self.__cursor.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                sender_username TEXT NOT NULL,
                receiver_username TEXT NOT NULL,
                content TEXT NOT NULL,
                time_sent INTEGER NOT NULL
            )"""
        )
        self.__cursor.execute(
            """CREATE TABLE IF NOT EXISTS relations (
                first_user TEXT NOT NULL,
                secondary_user TEXT NOT NULL,
                first_is_friend BLOB NOT NULL,
                secondary_is_friend BLOB NOT NULL,
                secondary_is_blocked BLOB NOT NULL
            )"""
        )

    def get_relation(self, first_username: str, secondary_username: str) -> Relation:
        self.__cursor.execute(
            "SELECT * FROM relations WHERE first_user == ? AND secondary_user == ?",
            [first_username, secondary_username],
        )
        relation = self.__cursor.fetchone()
        return Relation(*relation)

    def get_all_relations(self, first_username: str) -> list[Relation]:
        self.__cursor.execute(
            "SELECT * FROM relations WHERE first_user == ?", [first_username]
        )
        relations = self.__cursor.fetchall()

        return [
            Relation(
                relation[0],
                relation[1],
                relation[2] == SQLITE3_TRUE,
                relation[3] == SQLITE3_TRUE,
                relation[4] == SQLITE3_TRUE,
            )
            for relation in relations
        ]

    def get_messages(
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

    def add_friend(self, first_user: str, secondary_user: str) -> bool:
        if first_user == secondary_user:
            return False
        if not self.check_user_exists(secondary_user):
            return False

        self.__cursor.execute(
            "SELECT first_is_friend FROM relations WHERE first_user == ? AND secondary_user == ?",
            [first_user, secondary_user],
        )
        first_is_friend = self.__cursor.fetchone()

        self.__cursor.execute(
            "SELECT first_is_friend FROM relations WHERE first_user == ? AND secondary_user == ?",
            [secondary_user, first_user],
        )
        secondary_is_friend = self.__cursor.fetchone() != None

        if first_is_friend == None:
            self.__cursor.execute(
                "INSERT INTO relations (first_user, secondary_user, first_is_friend, secondary_is_friend, secondary_is_blocked) VALUES (?, ?, ?, ?, ?)",
                [
                    first_user,
                    secondary_user,
                    SQLITE3_TRUE,
                    SQLITE3_FALSE,
                    SQLITE3_FALSE,
                ],
            )
        else:
            self.__cursor.execute(
                "UPDATE relations SET first_is_friend = ? WHERE first_user == ? AND secondary_user == ?",
                [SQLITE3_TRUE, first_user, secondary_user],
            )
        if secondary_is_friend == None:
            self.__cursor.execute(
                "INSERT INTO relations (first_user, secondary_user, first_is_friend, secondary_is_friend, secondary_is_blocked) VALUES (?, ?, ?, ?, ?)",
                [
                    secondary_user,
                    first_user,
                    SQLITE3_FALSE,
                    SQLITE3_TRUE,
                    SQLITE3_FALSE,
                ],
            )
        else:
            self.__cursor.execute(
                "UPDATE relations SET secondary_is_friend = ? WHERE first_user == ? AND secondary_user == ?",
                [SQLITE3_TRUE, secondary_user, first_user],
            )

        self.__conn.commit()
        return True

    def remove_friend(self, first_user: str, secondary_user: str) -> bool:
        if first_user == secondary_user:
            return False
        if not self.check_user_exists(secondary_user):
            return False

        self.__cursor.execute(
            "SELECT first_is_friend FROM relations WHERE first_user == ? AND secondary_user == ?",
            [first_user, secondary_user],
        )
        first_is_friend = self.__cursor.fetchone()

        self.__cursor.execute(
            "SELECT first_is_friend FROM relations WHERE first_user == ? AND secondary_user == ?",
            [secondary_user, first_user],
        )
        secondary_is_friend = self.__cursor.fetchone() != None

        if first_is_friend == None:
            self.__cursor.execute(
                "INSERT INTO relations (first_user, secondary_user, first_is_friend, secondary_is_friend, secondary_is_blocked) VALUES (?, ?, ?, ?, ?)",
                [
                    first_user,
                    secondary_user,
                    SQLITE3_FALSE,
                    SQLITE3_FALSE,
                    SQLITE3_FALSE,
                ],
            )
        else:
            self.__cursor.execute(
                "UPDATE relations SET first_is_friend = ? WHERE first_user == ? AND secondary_user == ?",
                [SQLITE3_FALSE, first_user, secondary_user],
            )
        if secondary_is_friend == None:
            self.__cursor.execute(
                "INSERT INTO relations (first_user, secondary_user, first_is_friend, secondary_is_friend, secondary_is_blocked) VALUES (?, ?, ?, ?, ?)",
                [
                    secondary_user,
                    first_user,
                    SQLITE3_FALSE,
                    SQLITE3_FALSE,
                    SQLITE3_FALSE,
                ],
            )
        else:
            self.__cursor.execute(
                "UPDATE relations SET secondary_is_friend = ? WHERE first_user == ? AND secondary_user == ?",
                [SQLITE3_FALSE, secondary_user, first_user],
            )

        self.__conn.commit()
        return True

    def check_user_exists(self, username: str) -> bool:
        self.__cursor.execute(
            "SELECT username FROM users WHERE username == ?", [username]
        )
        username = self.__cursor.fetchone()

        return username != None

    def check_token(self, token: str) -> tuple[bool, str | None]:
        self.__cursor.execute(
            "SELECT username FROM users WHERE token_hash == ?",
            [hashlib.sha512(token.encode()).digest()],
        )
        usernames = self.__cursor.fetchone()

        if usernames == None:
            return False, None  # token doesnt exist

        return True, usernames[0]

    def add_message(self, sender: str, receiver: str, content: str) -> None:
        self.__cursor.execute(
            "INSERT INTO messages (sender_username, receiver_username, content, time_sent) VALUES (?, ?, ?, ?)",
            [sender, receiver, content, int(time.time())],
        )

        self.__conn.commit()
