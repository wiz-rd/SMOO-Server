import asyncio
import sys

from rich import print as pprint


class Command:
    """A class to help hold information about commands."""

    __slots__ = ("command", "help_msg", "modifiers", "examples", "verbs_required")

    def __init__(
        self,
        command: str,
        help_msg: str = "",
        modifiers: list[str] | None = None,
        examples: str | list[str] | None = None,
        verbs_required: bool = True,
    ):
        self.command = command.lower().strip()
        """The command itself."""
        self.help_msg: str = help_msg
        """The help message to be printed when `help` is called."""
        self.modifiers: list[str] = modifiers or []
        """Valid modifiers like `user` and `ID` in `ban <user>` or `ban <ID>`."""
        self.examples: str | list[str] = examples or []
        """Example ways that this command should be used."""
        self.verbs_required = verbs_required
        """Whether a verb is required or if the command can stand alone."""

    def usage(self) -> str:
        """Show the usage of the given command."""
        return f"""
HELP:
{self.help_msg}
\tExamples:
\t{"\n\t".join(self.examples)}
"""


UIDIP = ["user", "id", "ip"]
SUPPORTED_COMMANDS = {
    "ban": Command(
        "ban",
        "Ban the given user immediately. Change the config.toml to ban them on next restart.",
        UIDIP + ["list"],
        ["ban", "ban user <username>", "ban ip 127.0.0.1"],
    ),
    "crash": Command(
        "crash",
        "Crash a specified user.",
        UIDIP,
        ["crash id <id>", "crash user <username>"],
    ),
    "disconnect": Command(
        "disconnect",
        "Disconnect the specific user.",
        UIDIP + ["all"],
        ["disconnect id <id>", "disconnect user <username>", "disconnect all"],
    ),
    "exit": Command("exit", "Exits the server.", verbs_required=False),
    "help": Command(
        "help",
        "Lists all available commands and their arguments.",
        verbs_required=False,
    ),
    "list": Command(
        "list",
        "Lists all connected users.",
        UIDIP,
        ["list user", "list ip", "list id"],
        verbs_required=False,
    ),
    "unban": Command(
        "unban",
        "Unbans the specified user. They will need to restart their game.",
        UIDIP,
        ["unban user mario", "unban ip 127.0.0.1"],
    ),
    "uw": Command(
        "uw",
        "Un-whitelists a user.",
        UIDIP + ["all"],
        ["uw user <username>", "uw user mario", "uw all"],
    ),
    "whitelist": Command(
        "whitelist",
        "Add the specified user to the whitelist.",
        UIDIP + ["list"],
        ["whitelist list", "whitelist user <username>"],
    ),
}


def read_command(command_line: str, default: bool = True) -> tuple[Command, list[str]]:
    """Read in the command and return its type and the given `verbs`."""
    args = command_line.lower().strip().split()
    # assign what we can
    cmd: str = args[0]
    # type hint this
    # everything following the command. Not necessarily specifically modifiers
    verbs: list[str] | None

    if len(args) > 1:
        # let's cap this out at 50 verbs, just
        # to hopefully prevent some spamming
        verbs: list[str] = args[1:50]
    else:
        verbs: None = None

    c_obj = SUPPORTED_COMMANDS.get(
        cmd, Command(cmd, verbs_required=False) if default else None
    )

    return c_obj, verbs


def unknown_command(cmd: str = ""):
    if not cmd:
        pprint("[yellow]Unknown command.", flush=True)
    else:
        pprint(f"[yellow]Unknown command: '{cmd}'", flush=True)

    pprint("[yellow]Run [bold]help[/bold] for a list of commands.", flush=True)


def call(command_line: str, server_state: dict) -> None:
    """Perform the appropriate action for the given command.

    Args:
        - command_line (str): The whole command line.
        - server_state (dict): The actual server state itself so we can modify it.
    """
    command_type, verbs = read_command(command_line)

    if command_type is None:
        unknown_command()

    if command_type.verbs_required and not verbs:
        pprint(f"[red]Missing arguments for command '{command_type.command}'")
        pprint(command_type.usage())
        return

    match command_type.command:
        case "ban":
            # user, ID, IP
            scope = verbs[0]
            if scope == "list":
                pprint("Banned users are:", server_state["bans"])
        case "disconnect":
            ...
        case "exit":
            print("Shutting down server...", flush=True)
            return
        case "help":
            for cmd in SUPPORTED_COMMANDS.values():
                pprint(
                    f"[yellow]{cmd.command}",
                    cmd.help_msg,
                    "[blue]MODIFIERS:",
                    *cmd.modifiers,
                    "[green]EXAMPLES:",
                    *cmd.examples,
                    sep="\n\t",
                    flush=True,
                )
                print(flush=True)
        case _:
            unknown_command(command_type.command)


async def newline(flush: bool = True):
    """Simple function: prints a new line for the console."""
    print("> ", end="", flush=flush)


# let us access the terminal while asyncio is running
async def terminal_admin_console(server_state):
    """Reads input from the local terminal without blocking the asyncio loop."""
    # connect asyncio to standard input (stdin)
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    try:
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    except KeyboardInterrupt:
        # NOTE: this doesn't seem to work
        print("Exiting...")

    print("--- console ---")
    print("Commands: ban list, exit, disconnect")
    await newline()

    # using a while loop here with awaits to yield back to uvloop / asyncio
    # if we call an await, that registers as a "pause", which Python should
    # interpret as time to do other things.
    while True:
        # here is the await
        line_bytes = await reader.readline()

        # if nothing is sent, exit? I believe for ctrl + c
        if not line_bytes:
            break

        # decode the command
        command_line = line_bytes.decode().strip()

        # if no command given, continue
        if not command_line:
            await newline()
            continue

        call(command_line, server_state)
        # TODO: add more commands here

        # try:
        #     match cmd:
        #         case "ban":
        #             modifier = parts[1].lower()
        #             if modifier == "list":
        #                 print(
        #                     f"Banned Users: {list(server_state['bans']['usernames'])}"
        #                 )
        #                 print(f"Banned IPs: {list(server_state['bans']['ips'])}")
        #                 print(f"Banned IDs: {list(server_state['bans']['ids'])}")
        #             else:
        #                 print(f"Invalid subcommand '{modifier}'")
        #         case "disconnect":
        #             modifier = parts[1].lower()
        #         case "exit":
        #             print("Shutting down server...")
        #             return
        #         case _:
        #             print(f"Unknown command: {cmd}")
        # except IndexError:
        #     print(f"Invalid arguments for {cmd}")

        await newline()
