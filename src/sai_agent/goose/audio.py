"""DFPlayer UART packets and nonblocking honk events.

Packet/checksum facts: official DFRobotDFPlayerMini.cpp, V1.0.6. This original
implementation sends commands only; sending is not proof of card/playback or
sound level. Readiness and safe maximum volume require the physical audio gate.
"""
from __future__ import annotations
import time


def dfplayer_packet(command:int,parameter:int=0,ack=True)->bytes:
    if not isinstance(command,int) or not 0<=command<=255:raise ValueError('Invalid command')
    if not isinstance(parameter,int) or not 0<=parameter<=65535:raise ValueError('Invalid parameter')
    payload=bytes([0xff,6,command,int(bool(ack)),parameter>>8,parameter&255])
    checksum=(-sum(payload))&65535
    return b'\x7e'+payload+checksum.to_bytes(2,'big')+b'\xef'


class HonkAudio:
    def __init__(self,serial_writer,commissioning:dict):
        if commissioning.get('audio_playback_passed') is not True:
            raise ValueError('Card, speaker and supply commissioning required')
        cap=commissioning.get('maximum_safe_volume')
        if not isinstance(cap,int) or not 0<=cap<=30:raise ValueError('Invalid commissioned volume')
        self.writer=serial_writer;self.cap=cap;self.pending=[];self.last_write=-1.;self.last_honk=-10.

    def request_honk(self,volume=8,now_s=None):
        now=time.monotonic() if now_s is None else now_s
        if now-self.last_honk<1.2:return False
        if not isinstance(volume,int) or not 0<=volume<=self.cap:raise ValueError('Volume exceeds commissioned cap')
        self.pending.extend([dfplayer_packet(6,volume),dfplayer_packet(0x12,1)])
        self.last_honk=now;return True

    def tick(self,now_s=None):
        now=time.monotonic() if now_s is None else now_s
        if self.pending and now-self.last_write>=.02:
            packet=self.pending.pop(0)
            if self.writer.write(packet)!=len(packet):raise OSError('Incomplete audio UART write')
            self.last_write=now
