import dataclasses


@dataclasses.dataclass(frozen=True)
class Relation:
    first_username: str
    secondary_username: str
    first_is_friend: bool
    secondary_is_friend: bool
    secondary_is_blocked: bool


@dataclasses.dataclass(frozen=True)
class Message:
    sender: str
    receiver: str
    time_sent: int
    content: str
