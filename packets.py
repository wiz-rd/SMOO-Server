# from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Protocol, ClassVar

from bidict import bidict
import struct

import constants
from math_classes import Vector3, Quaternion

"""
This file stores different types of packets to be used to hold, transfer, and serialize data.

The folder I'm referring to for this is:
https://github.com/Sanae6/SmoOnlineServer/tree/master/Shared/Packet/Packets
"""


class PacketType(IntEnum):
    UNKNOWN = 0
    INIT = 1
    PLAYER = 2
    CAP = 3
    GAME = 4
    TAG = 5
    CONNECT = 6
    DISCONNECT = 7
    COSTUME = 8
    SHINE = 9
    CAPTURE = 10
    CHANGE_STAGE = 11
    COMMAND = 12


# NOTE: this is one way to reverse the enum
# print(PacketType(1).name)


# useful as a sort of constant
class ConnectionTypes(IntEnum):
    FIRST_CONNECTION = 0
    RECONNECTING = 1


class TagUpdateTypes(IntEnum):
    NONE = 0
    TIME = 1
    STATE = 2
    BOTH = 3
    UNKNOWN04 = 4
    UNKNOWN05 = 5
    UNKNOWN06 = 6
    UNKNOWN07 = 7
    UNKNOWN08 = 8
    UNKNOWN09 = 9
    UNKNOWN10 = 10
    UNKNOWN11 = 11
    UNKNOWN12 = 12
    UNKNOWN13 = 13
    UNKNOWN14 = 14
    ALL = 15


class GamemodeTypes(IntEnum):
    NONE = -1
    LEGACY = 0
    HIDE_AND_SEEK = 1
    SARDINES = 2
    FREEZE_TAG = 3
    UNKNOWN04 = 4
    UNKNOWN05 = 5
    UNKNOWN06 = 6
    UNKNOWN07 = 7
    UNKNOWN08 = 8
    UNKNOWN09 = 9
    UNKNOWN10 = 10
    UNKNOWN11 = 11
    UNKNOWN12 = 12
    UNKNOWN13 = 13
    RESERVED = 14


# I wonder if this is useful? I'm not sure
class Packet(Protocol):
    """Base class to handle packets to and from the client."""

    # TODO: see if this would help (test the speed of the current server)
    # and see if it's only for instance vars or can be for class variables as well
    # __slots__ = ("NAME", "FORMAT", "SIZE")

    NAME: ClassVar[str]
    """The name of the packet in the backend."""

    FORMAT: ClassVar[str]
    """The format to be used with `struct.pack()`"""

    SIZE: ClassVar[int]
    """The expected size of this packet."""

    # going to use class attributes
    # @property
    # def size(self) -> int:
    #     """The expected size of this packet."""
    #     ...

    def serialize(self) -> bytes:
        """Convert this packet into bytes to be sent to the client."""
        raise NotImplementedError

    def deserialize(self, data: bytes) -> None:
        """Loads `data` into this packet object."""
        raise NotImplementedError


class CapPacket(Packet):
    """Defines Cappy's position, rotation, and other information."""

    NAME: str = "CAP"
    NAME_SIZE: int = 0x30
    """The magic number from https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/CapPacket.cs#L19"""

    # semi-magic numbers courtesy of
    # https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/CapPacket.cs#L19
    # presumably, the 12 is the length of bytes needed for a Vector3 - 4 bytes per int, 3 times - x, y, and z
    # the 28 is the 16 from the quaternion - 4 ints * 4 bytes each
    # mapping each value to this, it's
    # rotation (3f), quaternion (4f), cap_out (?), buffer?* (3x), cap_anim ({self.NAME_SIZE}s, so 32s)
    FORMAT: str = f"<3f4f?3x{NAME_SIZE}s"
    """The format to be used with `struct.pack()`"""
    # * not sure why but it seems like the C# code has something similar to this

    SIZE: int = 0x50
    # should initialize to the right number and not waste resources..? hopefully
    TYPE: int = PacketType.CAP

    def __init__(
        self,
        position: Vector3 = Vector3(),
        rotation: Quaternion = Quaternion(),
        cap_out: bool = False,
        cap_anim: str = "",
    ):
        self.position = position
        self.rotation = rotation
        self.cap_out = cap_out
        self.cap_anim = cap_anim

    # NOTE: going to be using size as a class attribute instead of instance attribute,
    # especially since properties are probably slower
    # @property
    # def size(self):
    #     return 0x50

    def serialize(self) -> bytes:
        anim_bytes = bytes.fromhex(self.cap_anim)

        return struct.pack(
            CapPacket.FORMAT,
            # positions, but expanded (so x, y, z, just automatically)
            *self.position.dump(),
            # quaternion expanded, same as above but also has a "w"
            *self.rotation.dump(),
            self.cap_out,
            anim_bytes,
        )

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(CapPacket.FORMAT, data[: CapPacket.SIZE])

        self.position = Vector3(*unpacked[:3])
        self.rotation = Quaternion(*unpacked[3:7])
        self.cap_out = unpacked[7]
        # TODO: make sure this is properly reversable
        self.cap_anim = unpacked[8].hex().strip("00")


class CapturePacket(Packet):
    """Defines what capture the player is in, if any."""

    NAME = "CAPTURE"
    FORMAT = f"<{constants.COSTUME_NAME_SIZE}s"
    # this is redundant and may take resources we don't need to use:
    # SIZE = constants.COSTUME_NAME_SIZE
    TYPE: int = PacketType.CAPTURE

    def __init__(self, model_name: str = ""):
        self.model_name = model_name

    def serialize(self) -> bytes:
        """Convert this packet into bytes."""
        return struct.pack(CapturePacket.FORMAT, self.model_name.encode())

    def deserialize(self, data: bytes):
        """Deserialize `data` into this instance. Performs it in-place."""
        # this looks like a nightmare but it's basically just formatting this
        # according to the struct module, and then chopping off `data` at the
        # end of the alloted amount. Then converting the bytes given to a str
        # and removing null bytes at the end.
        self.model_name = (
            struct.unpack(CapturePacket.FORMAT, data[: constants.COSTUME_NAME_SIZE])[0]
            # NOTE: not using hex because we need to get the actual stage name,
            # not just convert the bytes to a string
            .decode("utf-8")
            .strip("00")
        )


class ChangeStagePacket(Packet):
    """Sent or received when a stage change occurs."""

    NAME: str = "CHANGE_STAGE"
    SIZE: int = 0x44
    TYPE: int = PacketType.CHANGE_STAGE

    ID_SIZE: int = 0x10
    STAGE_SIZE: int = 0x30

    FORMAT: str = f"<{STAGE_SIZE}s{ID_SIZE}siB"

    def __init__(
        self,
        stage: str = "",
        stage_id: str = "",
        scenario: int = 0,
        sub_scenario_type: int = 0,
    ):
        # string
        self.stage = stage
        # we have to have different names because id is a Python keyword
        # string
        self.id = stage_id
        # sbyte (signed byte)
        self.scenario = scenario
        # byte
        self.sub_scenario_type = sub_scenario_type

    def serialize(self) -> bytes:
        # NOTE: this one is a bit different than normal
        # TODO: make sure this works. URL:
        # https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/ChangeStagePacket.cs
        return struct.pack(ChangeStagePacket.FORMAT, *self.dump(encode=True))

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(
            ChangeStagePacket.FORMAT, data[: ChangeStagePacket.SIZE]
        )

        self.stage = unpacked[0].decode().strip("\x00")
        self.id = unpacked[1].decode().strip("\x00")
        self.scenario = unpacked[2]
        self.sub_scenario_type = unpacked[3]

    def dump(self, encode: bool = False):
        """Dump the attributes of this object in the following order:

        - stage
        - id
        - scenario
        - sub_scenario_type
        """
        if encode:
            return (
                self.stage.encode(),
                self.id.encode(),
                self.scenario,
                self.sub_scenario_type,
            )
        return self.stage, self.id, self.scenario, self.sub_scenario_type

    # TODO: add serialize and deserialize


# this refers to https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/ConnectPacket.cs


class ConnectPacket(Packet):
    """Establishes a connection with a client."""

    NAME = "CONNECT"
    SIZE_OFFSET = 6
    SIZE = SIZE_OFFSET + constants.COSTUME_NAME_SIZE
    TYPE: int = PacketType.CONNECT
    # TYPE: int = 6

    # struct format:
    # i = 4-byte integer (ConnectionType)
    # H = 2-byte unsigned short (MaxPlayers)
    # s = char[] bytes padded/truncated to CLIENT_NAME_SIZE (ClientName)
    FORMAT: str = f"<iH{constants.CLIENT_NAME_SIZE}s"

    def __init__(
        self,
        connection_type: ConnectionTypes = ConnectionTypes.FIRST_CONNECTION,
        max_players: int = 0,
        client_name: str | None = None,
    ):
        self.connection_type = connection_type
        self.max_players = max_players
        self.client_name = client_name

    # @property
    # def size(self) -> int:
    #     return self.SIZE_OFFSET + constants.COSTUME_NAME_SIZE

    def serialize(self) -> bytes:
        if self.client_name is None:
            raise ValueError("The client name for this packet was never set!")

        # encode this to utf-8
        name_bytes = self.client_name.encode()

        # pack into a raw byte string
        return struct.pack(
            ConnectPacket.FORMAT,
            self.connection_type.value,
            self.max_players,
            name_bytes,
        )

    def deserialize(self, data: bytes):
        """Deserialize the data from the client to be readable.

        Sets the following values of this instance automatically:
        - connection_type
        - max_players
        - client_name
        """
        # unpack the data, cutting off at the max size allowed
        conn_type_raw, self.max_players, name_bytes = struct.unpack(
            ConnectPacket.FORMAT, data[: ConnectPacket.SIZE]
        )

        # convert it
        self.connection_type = ConnectionTypes(conn_type_raw)
        # convert and remove all null bytes at the end
        self.client_name = name_bytes.decode("utf-8").rstrip("\x00")


class CostumePacket(Packet):
    """Informs clients of a player's outfit."""

    NAME: str = "COSTUME"
    SIZE: int = constants.COSTUME_NAME_SIZE * 2
    FORMAT: str = f"<{constants.COSTUME_NAME_SIZE}s{constants.COSTUME_NAME_SIZE}s"
    TYPE: int = PacketType.COSTUME

    def __init__(self, body_name: str = "", cap_name: str = ""):
        self.body = body_name
        self.cap = cap_name

    def serialize(self) -> bytes:
        return struct.pack(CostumePacket.FORMAT, self.body.encode(), self.cap.encode())

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(CostumePacket.FORMAT, data)

        self.body, self.cap = (
            unpacked[0].decode().strip("\x00"),
            unpacked[1].decode().strip("\x00"),
        )


class DisconnectPacket(Packet):
    """Received when the client disconnects. TODO: fact-check this."""

    NAME: str = "DISCONNECT"
    SIZE: int = 0
    TYPE: int = PacketType.DISCONNECT
    FORMAT: str

    # should be an empty packet
    def serialize(self):
        return bytes(0)

    def deserialize(self, _: bytes):
        """Does nothing as this packet should be empty."""
        return


class GamePacket(Packet):
    """Not sure what this does..."""

    NAME: str = "GAME"
    SIZE: int = 0x42
    TYPE: int = PacketType.GAME
    STAGE_SIZE: int = 0x40

    FORMAT: str = f"<?B{STAGE_SIZE}s"

    def __init__(self, is_2d: bool = False, scenario_num: int = 0, stage: str = ""):
        self.is_2d = is_2d
        self.scenario_num = scenario_num
        self.stage = stage

    def serialize(self) -> bytes:
        # if this breaks, take a look at the formatting:
        # https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/GamePacket.cs
        # they're adding 2 for some reason, I'm not sure why
        return struct.pack(
            GamePacket.FORMAT, self.is_2d, self.scenario_num, self.stage.encode()
        )

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(GamePacket.FORMAT, data[: GamePacket.SIZE])
        self.is_2d, self.scenario_num = unpacked[:2]
        self.stage = unpacked[2].decode().strip("\x00")


class InitPacket(Packet):
    """Initialize a connection with a client. Confusingly, it should not go first."""

    NAME: str = "INIT"
    SIZE: int = 2
    TYPE: int = PacketType.INIT
    FORMAT: str = "<H"

    def __init__(self, max_players: int = 0):
        self.max_players = max_players

    # @property
    # def size(self):
    #     return 2

    def serialize(self) -> bytes:
        """Serialize this init packet for delivery."""
        return struct.pack(InitPacket.FORMAT, self.max_players)

    def deserialize(self, data: bytes):
        """Decode an init packet from the client? I don't know if we'll need this."""
        self.max_players = struct.unpack(InitPacket.FORMAT, data[: InitPacket.SIZE])[0]


class PlayerPacket(Packet):
    """Contains data about the player's location, rotation, and animation."""

    NAME: str = "PLAYER"
    SIZE: int = 0x38
    TYPE: int = PacketType.PLAYER

    ACT_SIZE: int = 0x20
    SUB_ACT_SIZE: int = 0x10

    # 3 floats (Vector3), 4 floats (Quaternion),
    # 6 floats (animation blending), 2 ints (area + subarea)
    FORMAT: str = "<3f4f6fHH"

    def __init__(
        self,
        position: Vector3 = Vector3(),
        rotation: Quaternion = Quaternion(),
        # initialize this to nothing, too
        animation_blend_weights: list[float] = [0, 0, 0, 0, 0, 0],
        act: int = 0,
        sub_act: int = 0,
    ):
        self.pos = position
        self.rot = rotation
        # how animations are blended in SMO, to be passed across the wire
        self.anim_weights = animation_blend_weights

        # area and subarea
        self.act = act
        self.sub_act = sub_act

    def serialize(self) -> bytes:
        return struct.pack(PlayerPacket.FORMAT, *self.dump())

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(PlayerPacket.FORMAT, data[: PlayerPacket.SIZE])
        self.pos = Vector3(*unpacked[:3])
        self.rot = Quaternion(*unpacked[3:7])
        self.anim_weights = list(unpacked[7:13])
        self.act = unpacked[13]
        self.sub_act = unpacked[14]

    def dump(self):
        """Dumps the attributes of this object."""
        return (
            # position as x, y, z (all floats)
            *self.pos.dump(),
            # rotation as x, y, z, w (all floats)
            *self.rot.dump(),
            # allegedly, should be about 6 floats
            # this will pad it to 6 floats exactly
            *(self.anim_weights + [0.0] * 6)[:6],
            self.act,
            self.sub_act,
        )


class ShinePacket(Packet):
    NAME: str = "SHINE"
    SIZE: int = 4
    TYPE: int = PacketType.SHINE

    FORMAT: str = "<i"

    def __init__(self, shine_id: int):
        self.shine_id = shine_id

    def serialize(self) -> bytes:
        return struct.pack(ShinePacket.FORMAT, self.shine_id)

    def deserialize(self, data: bytes):
        self.shine_id = struct.unpack(ShinePacket.FORMAT, data[: ShinePacket.SIZE])[0]


# TODO: finish this packet
# refer to https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/TagPacket.cs
class TagPacket(Packet):
    NAME: str = "TAG"
    SIZE: int = 5
    TYPE: int = PacketType.TAG

    # Game Mode + Tag Type (unsigned byte), is_it (bool), seconds (byte), minutes (ushort)
    FORMAT: str = "<B?BH"

    def __init__(
        self,
        game_mode: GamemodeTypes,
        tag_update: TagUpdateTypes,
        is_it: bool,
        seconds: int,
        minutes: int,
    ):
        self.game_mode = game_mode
        self.tag_update = tag_update
        self.is_it = is_it
        self.seconds = seconds
        self.minutes = minutes

    def serialize(self) -> bytes:
        # original C# code:
        # https://github.com/Sanae6/SmoOnlineServer/blob/master/Shared/Packet/Packets/TagPacket.cs
        #
        # NOTE: this is very unusual compared to the other packets
        # and requires a bit of understanding about bits and bytes
        # (which I do not have, so bear with me):
        #
        # a byte is 8 bits, 0000 0000. Half of of a byte is aptly
        # called a nibble - 0000. Traditionally, a byte can go up
        # to 255 if unsigned, 1111 1111, but we don't need a number
        # that large, I guess, so to save resources we're going to
        # split a single byte into two nibbles and merge those nibbles
        # together before sending them to the client. This means
        # upon recieving them, we'll have to decode them the opposite
        # of the way we encoded them, so we'll need to perform similar
        # bit-shifting math on them in `deserialize()`

        # F = 15 in hex, so essentially we're just writing 15 15.
        # & is a bitwise AND, which means we can essentially use it to
        # mask for specific values - like if we want to guarentee
        # one of the nibbles is all 0s
        # this line should convert game_mode from a traditional Python
        # int into it's 8-bit equivalent. This means -1 will turn into
        # 1111 1111, or 255, because bytes cannot really store negative
        # values unless they have a "space" dedicated for a sign: - or +
        game_mode_byte = self.game_mode.value & 0xFF
        # you can test this yourself by opening a Python instance and
        # running
        #
        # > -1 & 0xFF
        #
        # it should return 255

        # this is where things get interesting. a GameMode can only be from
        # -1 to 14, and the highest value a byte can store is 1111, or 15
        # so if the game mode is anything at all, it'll cap out at 15, or
        # *only* one nibble: the first half would be unused as 15 in binary
        # is just 1111. It would be 0000 1111, and the first half would never
        # be used. So in order to take advantage of that free space, we
        # can perform a bit shift - literally shift the bits one way or another.
        # so: bitshift to the left 4 spaces and 0000 1111 becomes 1111 0000
        game_mode_byte = game_mode_byte << 4

        # now, we can "add" the tag_update value to this byte
        # (we're limiting it to only be in the second nibble, just to be safe.
        # That's why it's 0x0F and not 0xFF)
        tag_update_byte = self.tag_update.value & 0x0F

        # now we merge the two using a bitwise OR. See the following (contrived) example:
        # 0000 0011
        # OR
        # 0010 0000
        # =
        # 0010 0011
        # so we successfully "merge" the two nibbles into one byte, but preserve their contents
        both = (game_mode_byte | tag_update_byte) & 0xFF
        # the final 0xFF is to make sure it's just a single byte long

        return struct.pack(
            TagPacket.FORMAT,
            both,
            self.is_it,
            self.seconds,
            self.minutes,
        )

    def deserialize(self, data: bytes):
        unpacked = struct.unpack(TagPacket.FORMAT, data[: TagPacket.SIZE])

        # see serialize() for the process here, but basically we do the inverse:
        # convert it to an 8-bit integer, "grab" the first nibble, and "grab" the second nibble.
        # convert it to an 8-bit int:
        both = unpacked[0] & 0xFF
        # "grab" the first nibble (remember that game mode is the first half of the byte)
        # so we mask away the second half and shift the four bits on the first half to the
        # right, thus giving it a number between 0 and 15
        first_nibble = (both & 0xF0) >> 4
        # but now we need to make it between -1 and 14
        # to explain this, we need to look at our number range and the problem really quickly.
        # when we hit 15, we want this code to "translate" that to -1. Now we COULD do that
        # with this fun and fancy modulo,
        #### game_mode_int = ((first_nibble + 1) % 16) - 1
        # OR we could do it with this simple and readable comparison. Since we're using Python
        # and value readability over optimizations that may never be used (since the client
        # maxes out at around 12 users anyway), we're just going to use a simple comparison
        if first_nibble == 15:
            self.game_mode = GamemodeTypes(-1)
        else:
            self.game_mode = GamemodeTypes(first_nibble)

        # NOW we can finally update the tag type
        # ---
        # just mask the bits to give us the latter half
        self.tag_update = TagUpdateTypes(both & 0x0F)

        self.is_it = unpacked[1]
        self.seconds = unpacked[2]
        self.minutes = unpacked[3]


class UnhandledPacket:
    NAME: str = "UNKNOWN"
    SIZE: int = 0
    TYPE: int = PacketType.UNKNOWN

    def __init__(self, data: bytes):
        self.data = data

    # TODO: serialize and deserialize?


# NOTE: we're using the packet types from PacketType
# to avoid magic numbers and make this readable.
# This means you should be able to make changes to the Enum
# at the top of this file and it should automatically populate everywhere.
#
# I may remove the enum entirely in the future, but for now
# I like it for how readable it makes the code. But it
# does seem excessive since each packet now has a NAME attribute.
# But to be fair, there also probably is almost no lookup-time because
# it's not in a dictionary and essentially should be similar to
# hard-coding the integers themselves, but just more readable
PACKET_TYPES = bidict(
    {
        # TODO: update COMMAND once I know what that entails
        PacketType.UNKNOWN: UnhandledPacket,
        PacketType.INIT: InitPacket,
        PacketType.PLAYER: PlayerPacket,
        PacketType.CAP: CapPacket,
        PacketType.GAME: GamePacket,
        PacketType.TAG: TagPacket,
        PacketType.CONNECT: ConnectPacket,
        PacketType.DISCONNECT: DisconnectPacket,
        PacketType.COSTUME: CostumePacket,
        PacketType.SHINE: ShinePacket,
        PacketType.CAPTURE: CapturePacket,
        PacketType.CHANGE_STAGE: ChangeStagePacket,
        PacketType.COMMAND: "COMMAND",
    }
)


def load_header(data: bytes) -> tuple[str, int, int, bytes, bytes]:
    """Deserializes the header from `data`. I hope.

    Args:
        data (bytes): The data from the client *without*
            the TCP header and other network data.
        return_remnant_data (bool): Whether or not to return
            the data remaining after `packet_size`.

    Return pieces of the packet in the following order:
    - `uid`
    - `packet_type`
    - `packet_size`
    - `payload`
        - The data in the packet up until `packet_size`.
    - `remaining_data`
        - All data remaining - even after `packet_size`. Probably
            mostly null bytes.
    """
    # Typical packet headers follow:
    #
    # 16 bytes - UID
    # 2 bytes - packet type (i/u16 bit int)
    # 2 bytes - packet size (i/u16 bit int)
    #
    # packet_header =/= TCP header

    packet_header = data[: constants.TOTAL_HEADER]
    uid, packet_type, packet_size = struct.unpack(
        constants.HEADER_FORMAT, packet_header
    )

    return (
        uid.hex(),
        packet_type,
        packet_size,
        data[constants.TOTAL_HEADER : constants.TOTAL_HEADER + packet_size],
        # remnant data
        data[: constants.TOTAL_HEADER + packet_size],
    )


def generate_header(uid: str | bytes, packet: Packet) -> bytes:
    """Generates the appropriate header for the given packet. Refers to its `SIZE` attribute."""
    if isinstance(uid, str):
        uid = uid.encode()

    return struct.pack(
        constants.HEADER_FORMAT,
        uid,
        # this is using the bidict library so Pylance doesn't understand it
        PACKET_TYPES.inv[type(packet)],  # type: ignore
        packet.SIZE,
    )


def prepare_packet(uid: str | bytes | None, packet: Packet) -> bytes:
    """Prepares and serializes a whole packet, header and all."""
    if uid is None:
        raise ValueError("UID cannot be None. A UID is needed to serialize a packet.")

    if isinstance(uid, str):
        uid = uid.encode()

    header = generate_header(uid, packet)
    return header + packet.serialize()
