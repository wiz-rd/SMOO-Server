import asyncio

from rich import print as pprint

import constants
import packets
from math_classes import Vector3, Quaternion

# NOTE: this is cool but I probably won't do it, it introduces a lot of extra coding work
# and forces you to use a separate terminal
# #################################
# # ADMINISTRATOR SERVER PROTOCOL #
# #################################
# #    do NOT open this to the    #
# #  public, for obvious reasons  #
# #################################

# class AdminProtocol(asyncio.Protocol):
#     def __init__(self, server_state):
#         """
#         Initialize the server, same as the client server,
#         so use the *same* shared state to update the clients.
#         """
#         self.server_state = server_state
#         self.transport = None

#     def connection_made(self, transport):
#         self.transport = transport
#         self.transport.write(b"Connected to console\n> ")

#     def data_received(self, data: bytes):
#         # decode commands and remove auxiliary data
#         command_line = data.decode().strip()

#         if not command_line:
#             self.transport.write(b"> ")
#             return

#         parts = command_line.split()
#         command = parts[0].lower()
#         response = ""

#         # NOTE: complete commands
#         if command in ("ban", "whitelist"):
#             modifier = parts[1].lower()

#         if command == "list":
#             self.transport.write(b"Connected users are: ...\n> ")
#             return


class Player:
    """This class houses all of the packets relevant to players for easy retrieval."""

    __slots__ = ("name", "packet", "cappy", "costume", "game")

    def __init__(
        self,
        name: str,
        packet=packets.PlayerPacket(),
        cappy=packets.CapPacket(),
        costume=packets.CostumePacket(),
        game=packets.GamePacket(),
    ):
        self.name = name
        self.packet = packet
        self.cappy = cappy
        self.costume = costume
        self.game = game


class Mario:
    __slots__ = ("head", "body")

    def __init__(self, head: str, body: str):
        self.head = head
        self.body = body

    def update(self, head: str, body: str):
        """Update the `head` and `body` of Mario."""
        self.head, self.body = head, body

    def dump(self) -> tuple[str, str]:
        """Dump the `head` and `body` attributes in that order."""
        return self.head, self.body


##########################
# CLIENT SERVER PROTOCOL #
##########################
#   for the mod client   #
##########################


# hopefully, this server is fast...
class FastServerProtocol(asyncio.Protocol):
    active_connections = set()

    def __init__(self, server_state):
        # initialize everything
        self.server_state: dict = server_state
        self.transport: asyncio.BaseTransport | None = None
        # IP and port
        self.peername: tuple[str, int] | None = None
        self.username: str | None = None
        self.user_id: str | None = None
        self.is_first_packet: bool = True
        self.coordinates: Vector3 = Vector3()

    # upon initial connection, the client expects what back?
    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info("peername")

        if self.peername is None:
            raise ConnectionError(
                "Client attempt failed. No extra info as to why but we can't get IP or port."
            )

        ip_address = self.peername[0]  # (ip, port)

        # make sure they're not banned
        if ip_address in self.server_state["bans"]["ips"]:
            print("Blocking banned IP:", ip_address)
            self.reject()
            return

        # make sure they're on the whitelist if the whitelist is active
        if (
            self.server_state["whitelists"]["active"]
            and ip_address not in self.server_state["whitelists"]["ips"]
        ):
            print("Blocking IP not on whitelist:", ip_address)
            self.reject()
            return

        # TODO: delete this data to have a bit more privacy for clients?
        pprint(f"Client requested to connect: [yellow]{self.peername}")

    def data_received(self, data: bytes):
        """Process recieved data - parse the SMOO packet header and call the proper method."""

        # data is raw incoming bytes.
        if len(data) < constants.TOTAL_HEADER:
            # incomplete header
            # TODO: make sure this is right
            return

        # TODO: update this
        if self.is_first_packet:
            self.is_first_packet = False

        # get and dissect the header packet
        # we're discarding packet size and the data after the payload
        uid, packet_type_id, db_packet_size, payload, _ = packets.load_header(data)

        # if we don't already have one, set this user_id up
        if not self.user_id:
            self.user_id = uid

        if self.user_id != uid:
            print(
                "The UID of this transaction has changed. Something very weird is going on."
            )
            print("Deleting this connection and (hopefully) resetting.")
            self.reject()

        packet_class: packets.Packet = packets.PACKET_TYPES[int(packet_type_id)]  # type: ignore

        # # TODO: delete debugging
        # pprint(
        #     "Recieved data:",
        #     {
        #         "uid": uid,
        #         "id": packet_type_id,
        #         "size": db_packet_size,
        #         "class": packet_class,
        #         "name": packet_class.NAME,
        #     },
        # )

        # if we don't have a class for it defined, so we're behind or it doesn't exist
        # TODO: handle this better
        if not packet_class:
            return

        # create an instance of this object.
        # packet_class is just the class itself,
        # not an actual object yet, so we can't
        # assign some of the stuff we normally do to it
        packet = packet_class()
        # load the packet data into itself
        # so if it's a CapturePacket, load the
        # capture name into packet.model_name, for example
        packet.deserialize(payload)

        # TODO: make one of these for each type of packet OR determine a way to do this psuedo-dynamically (probably impossible)
        match packet:
            case packets.CapPacket():
                self.handle_cap(packet)
            case packets.ConnectPacket():
                self.handle_connect(packet)
            case packets.CostumePacket():
                self.handle_costume(packet)
            case packets.DisconnectPacket():
                self.handle_disconnect(packet)
            case packets.GamePacket():
                self.handle_game(packet)
            case packets.InitPacket():
                # I have yet to confirm it but I suspect that
                # we should not be receiving packets of this type
                self.handle_init(packet)
            case packets.PlayerPacket():
                self.handle_player(packet)
            case packets.ShinePacket():
                self.handle_shine()
            case packets.TagPacket():
                self.handle_tag()
            case packets.UnhandledPacket():
                self.handle_unhandled()
            case _:
                # close the connection if it's not a real packet, for now
                # self.reject()
                # TODO: change this
                # NOTE: can use the UnhandledPacket object for this
                print("Packet not setup yet or is not valid.")
                return

        # if self.is_first_packet:
        #     self.is_first_packet = False

        #     # TODO: respond with appropriate data here
        #     # TODO: see if username is given in first packet - I think it is

        #     if self.username in self.server_state["bans"]["usernames"]:
        #         print(f"Blocking banned username: '{self.username}'")
        #         self.reject()
        #         return

        #     if (
        #         self.server_state["whitelists"]["active"]
        #         and self.username not in self.server_state["whitelists"]["usernames"]
        #     ):
        #         print("Blocking username not on whitelist:", self.username)
        #         self.reject()
        #         return

        # self.handle_custom_packet(data)

    ########################
    # UTILITY METHODS HERE #
    ########################

    def get_player(self, generate_anew: bool = True) -> Player | None:
        """Get player data if it exists in the shared state and generate a new player if it doesn't."""
        # refer to ./server_state_schema for this
        # type hint to use this variable easier
        # get a player if they exist or make a new one if they don't
        return self.server_state["users"].get(
            self.user_id,
            # make a new player if requested, otherwise don't
            Player(self.username) if generate_anew else None,
        )

    def set_player(
        self,
        player: Player,
        broadcast_packet: packets.Packet = None,
        include_self: bool = False,
    ):
        """Sets the player in the shared state. Broadcasts `packet` if requested."""
        self.server_state["users"][self.user_id] = player

        if broadcast_packet:
            self.broadcast(broadcast_packet, include_self)

    ########################
    # PACKET HANDLING HERE #
    ########################

    ######
    # CONNECT
    ######

    def handle_connect(self, packet: packets.ConnectPacket) -> None:
        """Handle connect packets from client by responding with an Init packet."""
        if (
            len(FastServerProtocol.active_connections)
            >= self.server_state["max_players"]
        ):
            print(
                "Client",
                self.username if self.username else self.peername[0],
                "tried to connect but the server is full!",
            )
            print(self.server_state)
            return

        # if we have no connection at all (mostly for type checking)
        if self.transport is None:
            return

        # give this connection the right username if they don't already have it setup
        if not self.username:
            self.username = packet.client_name

        if self.user_id in self.server_state["users"]:
            print(
                "Recieved connection request from already-connected client",
                self.username,
                self.user_id + "...",
            )

        if self.peername:
            ip_address = self.peername[0]
        else:
            self.peername = self.transport.get_extra_info("peername")

            raise ConnectionError("Unable to determine IP address.")

        # if their username is banned, reject it
        if self.username in self.server_state["bans"]["usernames"]:
            # TODO: add ignoring as opposed to outright disconnecting?
            print(
                f"Banned username {self.username} tried to join ({ip_address}). Disconnecting."
            )
            self.reject()
            return

        pprint(f"[green]Player [blue]{self.username}[/blue] connected.")

        # TODO: make sure this reply works
        # NOTE: Tested, it does seem to work.
        serialized_packet = packets.prepare_packet(
            self.user_id, packets.InitPacket(self.server_state["max_players"])
        )

        FastServerProtocol.active_connections.add(self)

        # TODO: delete debugging
        pprint(self.server_state)

        # send the Init packet to the client
        self.transport.write(serialized_packet)

        max_players = self.server_state["max_players"]

        # update all clients that someone connected
        for client in FastServerProtocol.active_connections:
            if client == self:
                continue

            client.transport.write(
                packets.prepare_packet(
                    self.user_id,
                    packets.ConnectPacket(
                        max_players=max_players,
                        client_name=self.username,
                    ),
                )
            )

            # current progress in the server file:
            # https://github.com/Sanae6/SmoOnlineServer/blob/master/Server/Server.cs#L300

            # update this connection of all other players
            self.transport.write(
                packets.prepare_packet(
                    client.user_id,
                    packets.ConnectPacket(
                        max_players=max_players,
                        client_name=client.username,
                    ),
                )
            )

    ######
    # CAP
    ######

    # all of these are in alphabetical order EXCEPT
    # I put them below the connect() method because
    # it's so much longer than the rest

    def handle_cap(self, packet: packets.CapPacket):
        """Handles cap packets and broadcasts them."""
        player = self.get_player()
        player.cappy = packet
        self.set_player(player, broadcast_packet=packet)

    ######
    # COSTUME
    ######

    def handle_costume(self, packet: packets.CostumePacket):
        """Handles costume packets and broadcasts them as needed."""
        # see self.handle_player() for how this function works
        # and server_state_schema for the layout
        player: Player = self.get_player()
        player.costume = packet
        # not sure why but it seems like clients include themselves
        # when broadcasting their outfit
        self.set_player(player, broadcast_packet=packet, include_self=True)

    ######
    # DISCONNECT
    ######

    def handle_disconnect(self, packet: packets.DisconnectPacket):
        """Handles disconnecting for clients."""
        # NOTE: this could just be moved up to the match-case statement
        self.broadcast(packet, True)
        # close the connection with the disconnecting client
        # TODO: make sure this is right
        self.transport.close()

    ######
    # GAME
    ######

    def handle_game(self, packet: packets.GamePacket):
        """Handles the game packet and broadcasts it as needed."""
        # see self.handle_player() for step-by-step comments
        # not going to type hint anymore because get_player()
        # only returns two types anyway
        player = self.get_player()
        player.game = packet
        self.set_player(player, broadcast_packet=packet)

    ######
    # INIT
    ######

    def handle_init(self, packet: packets.InitPacket):
        """Does nothing for now - not sure this is needed."""
        return

    ######
    # PLAYER
    ######

    def handle_player(self, packet: packets.PlayerPacket):
        """Handle the player packet. It's expected to already be serialized."""
        # the packet should already have a lot of the information we need
        # already loaded into it because of the serialize method
        # so first, let's get the shared state if it exists
        # let's refer to the ./server_state_schema file for this
        # type hint to use this variable easier
        # ---
        player: Player = self.get_player()
        # # invert the y packet because for some reason Mario is upside down?
        # packet.rot = packet.rot.y * -1

        # update the player packet itself
        # essentially, we're discarding old player packet data BUT
        # retaining old Cappy and costume data, if they exist
        player.packet = packet

        # TODO: determine - do we even need to *store* the player location in RAM?
        # Obviously, we need to temporarily to pass it on to other players, but
        # why store it at all beyond that? Should take hardly any additional RAM
        # and add nice redundancy if players disconnect temporarily, but almost all
        # player data should be updated upon a reconnect anyway, so
        self.set_player(player)
        # broadcast=True would also work, but I'm leaving it off
        # to have slightly cleaner comments in this method

        # announce to everyone the new details of the player
        self.broadcast(player.packet)

    ######
    # SHINE
    ######

    def handle_shine(self, packet: packets.ShinePacket):
        """Handle shine (moon) packets."""
        # TODO: make sure that this is right
        self.broadcast(packet)

    ######
    # TAG
    ######

    def handle_tag(self, packet: packets.TagPacket):
        """Handle the tag packets. For now, just broadcast this to all clients."""
        # TODO: make sure this is right
        self.broadcast(packet)

    ######
    # UNHANDLED
    ######

    def handle_unhandled(self, packet: packets.UnhandledPacket):
        """For now, do nothing."""
        print("Unhandled packet recieved.")

    ####################
    # REST OF PROTOCOL #
    ####################
    def broadcast(self, packet: packets.Packet, include_self: bool = False):
        """Update all clients with the packet `packet`."""
        if not include_self:
            for client in FastServerProtocol.active_connections:
                # skip ourselves
                if client.user_id == self.user_id:
                    continue

                client.transport.write(packets.prepare_packet(self.user_id, packet))
                # TODO: finish this
                # NOTE: this type of method probably can't exist since
                # I'd need to send a specific packet type, and this is
                # agnostic to the type of packet to send
        else:
            for client in FastServerProtocol.active_connections:
                client.transport.write(packets.prepare_packet(self.user_id, packet))

    def connection_lost(self, exc):
        if self in FastServerProtocol.active_connections:
            FastServerProtocol.active_connections.remove(self)
            print(f"Client disconnected: {self.peername}")
        else:
            # NOTE: this shouldn't happen often, hence the confusion
            print("Connection lost after not being truly established?\t", end="")

        if exc:
            print(f"due to error:\n\n{exc}")

    def reject(self, reason: str | bytes = "", ignore: bool = False):
        """Rejects a client for any reason. NOTE: For now, just closes the connection."""
        if reason:
            print("Rejected client,", self.peername, "for:", reason)

        if self in FastServerProtocol.active_connections:
            FastServerProtocol.active_connections.remove(self)

        if not ignore:
            self.transport.close()
        # TODO: support ignoring
        else:
            # in the C# code, ignored clients are kept connected but not stored
            # removing it from `active_connections` should have this effect
            # self.transport.close()
            pass

        return

    def update_server_state(self, flush: bool = True):
        """Dumps this connection's data to the server state."""
        # TODO: determine if doing all of this at once has a significant performance impact
        # refers to ./server_state_schema for structure
        if flush:
            self.server_state["users"].add(
                {
                    "id": self.user_id,
                    "data": {
                        "username": self.username,
                        "coordinates": self.coordinates,
                        "cappy": self.cappy,
                    },
                }
            )


# the TCP server
# NOTE: may be highly redundant
class TCPServerProtocol(FastServerProtocol, asyncio.Protocol):
    # everything should be identical to the FastServer protocol, just TCP
    # except this should be used if the user wants UDP?
    # NOTE: fact check this - that the TCP server should behave differently
    # if UDP is used
    ...


# TODO: remove this? there is a special handshake for UDP and most packets are still sent
# over TCP
# the UDP server
class UDPServerProtocol(FastServerProtocol, asyncio.DatagramProtocol):
    # same as above just UDP
    ...
