TCP / UDP data

16 bytes - UID
2 bytes - packet type (i/u16 bit int)
2 bytes - packet size (i/u16 bit int)

I suspect
remainder - packet contents, null bytes


Example packets:

Emulator connect packet (likely) (len 58):

19 1f 7c ae 9b 96 99 e7 cd a0 5c 60 26 00 00 00 ff f5 73 57 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

b'\x191\xf3|\x1a\xe0\x9b\td\x99\xeet\xcd\xaa\r\\\x06\x00&\x00\x00\x00\x00\x00\xff\xffTset\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

Remote init packet (likely) (len 22):

hex - 19 1f 7c ae 9b 96 99 e7 cd a0 5c 10 02 00 00
bytes - b'\x191\xf3|\x1a\xe0\x9b\td\x99\xeet\xcd\xaa\r\\\x01\x00\x02\x00\x08\x00'
