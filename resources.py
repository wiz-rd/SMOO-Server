from pathlib import Path

############################
# prepare the default toml #
############################

DEFAULT_TOML = """[config]

# turn this down to 6 to always have capture sync on. Over 8 disables capture sync entirely
max_players = 8

# let players see each other even if they're not at the same part of the story
merge_scenarios = true


[network]
# set IP to "0.0.0.0" (with quotes) unless you know what you're doing
ip = "0.0.0.0"
port = 1027

[users.names]
# ban specific names (even if they're on the whitelist)
banned = []
# allow only specific names
whitelist = []

[users.ids]
# same as usernames but for Switch or emulator profile IDs
banned = []
whitelisted = []

[user.ips]
# same as usernames but for IP addresses
banned = []
whitelisted = []


#######################
# NOT IMPLEMENTED YET #
#######################

[moons]
# also called "shines" in the game files

# sync moons between players
sync = true

# save moons between sessions
save = false

# the file to save the moons to
save_file = "./moons.json"

# some moons cause issues if they're synced up such as the
# moon that opens the door to the Inverted Pyramid in Sand Kingdom.
# to get around this, this moon won't be synced between players
excluded = [
    496
]

# TODO: make this note make more sense?
# This is different from your individual save files:
# this saves the moons to a file and reads from that file when the server restarts.
# It will then "catch up" all new players who join by giving them all the moons they are missing.

# missing features:
# shine (moon) sync
#   shine saving and re-syncing
# JSON API - unlikely
# Discord bot - almost certainly never

# these features are missing because this server is meant
# to be used almost exclusively for hide and seek, not moon syncing
"""


def nested_get(dictionary: dict, *keys, default=None):
    """Call `dictionary.get(key[i], {}).get(key[i+1], {})...` until `keys` is exhausted.
    
    Example:
    ```
    nested_get(config, "network", "ip", default = "0.0.0.0")
    ```"""
    if not isinstance(dictionary, dict):
        return default

    def recursive_get(_dict, key_index=0, default=default):
        # if it's a dictionary, keep going (so further down, if this is toml / json)
        if isinstance(_dict, dict):
            next_dict = _dict.get(keys[key_index], default)
        # otherwise, we've probably reached the "bottom" of the dictionary, so we can back out now
        else:
            return _dict

        return recursive_get(next_dict, key_index + 1, default=default)

    return recursive_get(dictionary)


def prepare_config(config_path: str | Path = Path("config.toml"), overwrite: bool = False) -> str:
    """Prepare a config file if it doesn't exist OR overwrite it with the default config if requested."""
    # if we should overwrite the file anyway or if the config file does not exist
    if overwrite or not config_path.exists():
        with open(config_path, "w+", encoding="utf-8") as f:
            # move the "cursor" to the beginning of the file
            f.seek(0)
            # write the default toml
            f.write(DEFAULT_TOML)

    return config_path.read_text()


def warn(string: str):
    """A really simple warning message to use with Rich."""
    return "[yellow]" + string + "[/yellow]"
