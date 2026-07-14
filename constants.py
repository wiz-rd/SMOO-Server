# what even is this? I don't know
COSTUME_NAME_SIZE = 0x20
# the name of the client. Different from the UID.
CLIENT_NAME_SIZE = COSTUME_NAME_SIZE

########
# header information
########

UID_SIZE = 0x10  # 16 in bytes
PACKET_TYPE = 0x02
PACKET_SIZE = 0x02

TOTAL_HEADER = UID_SIZE + PACKET_TYPE + PACKET_SIZE
HEADER_FORMAT = f"<{UID_SIZE}sHH"
