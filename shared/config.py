from typing import TypeAlias, Mapping, Any
import yaml


config_type: TypeAlias = Mapping[str, Any] | Mapping[str, "config_type"]
config_structure_type: TypeAlias = (
    Mapping[str, type] | Mapping[str, "config_structure_type"]
)


def load_config_file(filepath: str, sub_config: str | None = None) -> Any:
    with open(filepath, "r") as config_fd:
        config = yaml.safe_load(config_fd)
        if config == None and sub_config == None:
            return {}
        if sub_config == None:
            return config
        else:
            return config[sub_config]


def safely_load_config_file(
    filepath: str, structure: config_structure_type, sub_config: str | None = None
) -> Any:
    config = load_config_file(filepath)
    check_config_structure(config, structure, filepath)
    return config[sub_config] if sub_config != None else config


def check_config_structure(
    config: config_type, structure: config_structure_type, config_name: str
) -> None:
    for expected_key, expected_item_type in structure.items():
        if expected_key not in config.keys():
            raise KeyError(f"key '{expected_key}' must be in {config_name}")

        if isinstance(expected_item_type, Mapping):
            check_config_structure(
                config[expected_key],
                expected_item_type,
                config_name + f"/{expected_key}",
            )
            continue
        if not isinstance(config[expected_key], expected_item_type):  # type: ignore
            raise TypeError(
                f"the type of key '{expected_key}' must be '{expected_item_type}'"
            )


SERVER_CONFIG_STRUCTURE = {
    "database": {
        "filepath": str,
        "connect_timeout": float | int,
        "token_length": int,
        "token_charset": str,
        "min_username_length": int,
        "max_username_length": int,
    },
    "connection": {
        "listen_address": str,
        "listen_port": int,
        "wait_for_authentication_timeout_secs": int,
    },
}

SHARED_CONFIG_STRUCTURE = {
    "packets": {
        "packet_type_bytes": int,
        "packet_id_bytes": int,
        "packet_data_length_bytes": int,
    },
}

CLIENT_CONFIG_STRUCTURE = {
    "connection": {
        "connect_address": str,
        "connect_port": int,
    },
    "user": {
        "token": str,
    },
}


SERVER_CONFIG = safely_load_config_file("server_config.yml", SERVER_CONFIG_STRUCTURE)
SHARED_CONFIG = safely_load_config_file("shared_config.yml", SHARED_CONFIG_STRUCTURE)
CLIENT_CONFIG = safely_load_config_file("client_config.yml", CLIENT_CONFIG_STRUCTURE)
