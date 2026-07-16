import asyncio
import sys


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
        print("Exiting...")

    print("--- console ---")
    print("Commands: ban list, exit")
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

        parts = command_line.split()
        cmd = parts[0].lower()

        # TODO: add more commands here
        match cmd:
            case "ban":

                modifier = parts[1].lower()
                if modifier == "list":
                    print(f"Banned Users: {list(server_state["bans"]["usernames"])}")
                    print(f"Banned IPs: {list(server_state["bans"]["ips"])}")
                    print(f"Banned IDs: {list(server_state["bans"]["ids"])}")
                else:
                    print(f"Invalid subcommand '{modifier}'")

            case "exit":
                print("Shutting down server...")
                return
            case _:
                print(f"Unknown command: {cmd}")

        await newline()
