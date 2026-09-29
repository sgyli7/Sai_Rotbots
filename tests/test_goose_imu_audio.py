import numpy as np
import pytest
from sai_agent.goose.imu import WitParser
from sai_agent.goose.audio import dfplayer_packet,HonkAudio


def test_binary_imu_recovers_split_noisy_corrupted_stream():
    parser=WitParser();acc=bytes.fromhex('55 51 00 00 00 00 00 08 C4 09 7B')
    gyro=bytes.fromhex('55 52 00 20 00 C0 00 00 00 00 87')
    assert not parser.feed(b'noise'+acc[:7],.01)
    broken=bytearray(gyro);broken[-1]^=1
    out=parser.feed(acc[7:]+bytes(broken)+gyro,.02)
    assert [f.type_code for f in out]==[0x51,0x52]
    assert np.allclose(out[0].values,[0,0,9.81]) and out[0].auxiliary==25
    assert np.allclose(out[1].values,[500*np.pi/180,-1000*np.pi/180,0])
    assert parser.bad_checksums>=1


def test_imu_stale_and_uncommissioned_rotation_are_invalid():
    parser=WitParser();parser.feed(bytes.fromhex('55 52 00 20 00 C0 00 00 00 00 87'),.02)
    parser.feed(bytes.fromhex('55 53 00 40 00 E0 00 00 D2 04 9E'),.02)
    with pytest.raises(ValueError):parser.controller_imu(.025,{})
    calibration={'attitude_mapping_verified':True,'euler_convention':'active_zyx_world_from_sensor',
                 'rotation_body_from_sensor':np.eye(3).tolist()}
    result=parser.controller_imu(.025,calibration)
    assert np.linalg.norm(result['gravity_body_unit'])==pytest.approx(1.)
    with pytest.raises(TimeoutError):parser.controller_imu(.08,calibration)
    assert parser.latest[0x53].auxiliary==1234


def test_audio_packet_and_retrigger_are_bounded():
    assert dfplayer_packet(0x12,1).hex()=='7eff0612010001fee7ef'
    class Writer:
        def __init__(self):self.packets=[]
        def write(self,p):self.packets.append(p);return len(p)
    writer=Writer()
    with pytest.raises(ValueError):HonkAudio(writer,{})
    audio=HonkAudio(writer,{'audio_playback_passed':True,'maximum_safe_volume':8})
    assert audio.request_honk(now_s=0)
    assert not audio.request_honk(now_s=.2)
    audio.tick(0);audio.tick(.01);assert len(writer.packets)==1
    audio.tick(.03);assert len(writer.packets)==2
    with pytest.raises(ValueError):audio.request_honk(9,2.)
