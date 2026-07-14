import asyncio

import struct

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


# NOTE: remove the Cappy and Mario classes if this is slow
# swap to just a list and use a schematic to show what's what?
class Cappy:
    __slots__ = ("anim", "pos", "rot", "out")

    def __init__(
        self,
        position: Vector3 = Vector3(),
        rotation: Quaternion = Quaternion(),
        out: bool = False,
        animation: str = None,
    ):
        self.pos = position
        self.rot = rotation
        self.out = out
        self.anim = animation

    def dump(self):
        """Returns the `pos`, `rot`, `cap_out`, and `animation` attributes in that order."""
        return *self.pos.dump(), *self.rot.dump(), self.out, self.anim


class Mario:
    def __init__(self, head: str = None, body: str = None):
        self.head = head
        self.body = body

    def update(self, head: str, body: str):
        """Update the head and body of Mario."""
        self.head, self.body = head, body

    def dump(self):
        """Dump the head and body attributes in that order."""
        return self.head, self.body


# struct.pack(packets.CapPacket.FORMAT, *Cappy().dump())


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
        self.server_state = server_state
        self.transport = None
        # IP and port
        self.peername = None
        self.username = None
        self.user_id = None
        self.is_first_packet = True
        self.coordinates = Vector3()
        self.cappy = Cappy()

    # upon initial connection, the client expects what back?
    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info("peername")

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
        print(f"Client requested to connect: {self.peername}")

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
        uid, packet_type_id, _, payload = packets.load_header(data)

        packet_class = packets.PACKET_TYPES[int(packet_type_id)]

        # NOTE: debugging
        # print(f"we got uid: {uid}")
        # print(f"we got packet id: {packet_type_id}")
        # print(f"we got packet size: {packet_size}")
        # print(f"In the data: {data[: constants.TOTAL_HEADER]}")

        # print(f"Payload of {payload}")
        # print(f"{data=}")

        # print(f"Projected class: {packet_class}")
        # print(f"Projected name: {packet_class.NAME}")

        # if we don't have a class for it defined, so we're behind or it doesn't exist
        # TODO: handle this better
        if not packet_class:
            return

        packet = packet_class()
        packet.deserialize(payload)

        # TODO: make one of these for each type of packet OR determine a way to do this psuedo-dynamically (probably impossible)
        match packet_type_id:
            case packets.ConnectPacket():
                self.handle_connect(packet, uid)
            case packets.InitPacket():
                ...
            case packets.DisconnectPacket():
                self.disconnect_self()
            case _:
                # close the connection if it's not a real packet, for now
                # self.reject()
                # TODO: change this
                # NOTE: can use the UnhandledPacket object for this
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
    # PACKET HANDLING HERE #
    ########################

    def handle_connect(
        self, packet: packets.ConnectPacket, uid: str
    ) -> packets.InitPacket:
        """Handle connect packets from client by responding with an Init packet."""
        if (
            len(FastServerProtocol.active_connections)
            < self.server_state["max_players"]
        ):
            print(f"Client {self.username} tried to connect but the server is full!")
            return

        # give this connection the right UID if they don't already have it setup
        if not self.user_id:
            self.user_id = uid

        # give this connection the right username if they don't already have it setup
        if not self.username:
            self.username = packet.client_name

        if self.user_id in self.server_state["users"]:
            print(
                "Recieved connection request from already-connected client",
                self.username,
                self.user_id + "...",
            )

        ip_address = self.peername[0]

        # if their username is banned, reject it
        if self.username in self.server_state["bans"]["usernames"]:
            # TODO: add ignoring as opposed to outright disconnecting?
            print(
                f"Banned username {self.username} tried to join ({ip_address}). Disconnecting."
            )
            self.reject()
            return

        print(f"Player {self.username} connected.")

        # TODO: make sure this reply works
        serialized_packet = packets.prepare_packet(
            self.user_id, packets.InitPacket(self.server_state["max_players"])
        )

        # NOTE: delete this if we don't need it - test it first
        # partial_header = struct.pack(
        #     "<HH", PACKET_TYPES.inverse[packets.InitPacket], len(serialized_packet)
        # )

        # full_packet = partial_header + serialized_packet

        # send the Init packet to the client
        self.transport.write(serialized_packet)

        max_players = self.server_state["max_players"]

        # update all clients that someone connected
        for client in FastServerProtocol.active_connections:
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
                    self.user_id,
                    packets.ConnectPacket(
                        max_players=max_players,
                        client_name=client.username,
                    ),
                )
            )

    # def handle_init()

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

    def disconnect_self(self):
        """Update all clients that the given client disconnected."""
        FastServerProtocol.active_connections.remove(self)

        # generate a complete disconnect packet
        disc_packet = packets.prepare_packet(packets.DisconnectPacket())

        for client in FastServerProtocol.active_connections:
            client.transport.write(disc_packet)

        self.transport.write(disc_packet)
        self.transport.close()

    def connection_lost(self, exc):
        FastServerProtocol.active_connections.remove(self)
        print(f"Client disconnected: {self.peername}")

        if exc:
            print(f"due to error:\n\n{exc}")

    def reject(self, reason: str | bytes = None, ignore: bool = False):
        """Rejects a client for any reason. NOTE: For now, just closes the connection."""
        if reason:
            print("Rejected client,", self.peername, "for:", reason)

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


print("Testing Cappy dicts:")

for i in range(100):
    print(Cappy(animation=i).dump())
