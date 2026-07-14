import asyncio
from functools import partial
from pathlib import Path
import sys
import tomllib

from rich import print as pprint
import uvloop

from console import terminal_admin_console
from protocols import FastServerProtocol
from resources import DEFAULT_TOML, nested_get, prepare_config, warn


async def main():
    ###############################
    # PREPARE AND READ THE CONFIG #
    ###############################

    config_file: Path = Path("./config.toml")
    config_contents = prepare_config(config_file)

    if not config_contents:
        pprint(
            warn(
                "The config file is empty! Reverting to default configuration but continuing anyway."
            )
        )
        config_contents = DEFAULT_TOML

    # automatically create the config file if it doesn't exist already
    try:
        config: dict = tomllib.loads(config_contents)
    except tomllib.TOMLDecodeError as exc:
        # gracefully exit if there is an issue
        pprint(
            "[red]Error: there's a problem with the config file. "
            "Please fix the error [italic]or[/italic] delete (or move) the file "
            "to have a new config file created automatically.",
            f"\n\nThe config file is located at: {config_file.absolute()}\n",
        )
        pprint("The full error is printed below:\n\n", exc, "\n")
        pprint("Press [bold]enter[/] to exit.")
        input()
        sys.exit()

    ###############################
    # SETTING UP THE SERVER STATE #
    ###############################

    # NOTE: see ./server_state_schema for the schematic for this
    shared_server_state: dict = {
        "bans": {
            # "any": True,
            "usernames": set(nested_get(config, "user", "names", "banned", default=())),
            "ids": set(nested_get(config, "user", "ids", "banned", default=())),
            "ips": set(nested_get(config, "user", "ips", "banned", default=())),
        },
        "whitelists": {
            "active": nested_get(config, "config", "use_whitelist", default=False),
            "usernames": set(
                nested_get(config, "user", "names", "whitelist", default=())
            ),
            "ids": set(nested_get(config, "user", "ids", "whitelist", default=())),
            "ips": set(nested_get(config, "user", "ips", "whitelist", default=())),
        },
        "max_players": nested_get(config, "config", "max_players"),
        "users": set(),
    }

    #############################
    # PREPARE THE SERVER ITSELF #
    #############################

    loop = asyncio.get_running_loop()

    ### Game server!

    # get the IP address. Default to 0.0.0.0
    ip = nested_get(config, "network", "ip", default="0.0.0.0")
    # get the port. Default to 1027
    port = nested_get(config, "network", "port", default=1027)

    game_protocol_factory = partial(FastServerProtocol, shared_server_state)
    # NOTE: may have to set keep_alive to False
    game_server = await loop.create_server(game_protocol_factory, host=ip, port=port)
    print(f"Server active on {ip}:{port}...")

    # create the terminal as a task
    terminal_task = asyncio.create_task(terminal_admin_console(shared_server_state))
    # create the server as a task
    server_task = asyncio.create_task(game_server.serve_forever())

    ### running the server and the terminal at the same time

    # context manager for the game server
    async with game_server:
        # wait until either the server crashes or the user types exit in the console
        _, pending = await asyncio.wait(
            [server_task, terminal_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # shut everything down
        for task in pending:
            task.cancel()


if __name__ == "__main__":
    # use libuv in the background - should be much faster than base asyncio
    uvloop.run(main())
