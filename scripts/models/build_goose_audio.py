"""Generate original synthetic honk; no game soundtrack or voice is sampled."""
from pathlib import Path
import hashlib,json,subprocess,wave
import numpy as np
from sai_agent.paths import resource_root


def main():
    out=resource_root()/'robots/Goose_V0.1/models/full/audio';out.mkdir(parents=True,exist_ok=True)
    rate=44100;t=np.arange(round(.72*rate))/rate;frequency=225-38*t/.72+8*np.sin(2*np.pi*7*t)
    phase=2*np.pi*np.cumsum(frequency)/rate
    sound=sum(weight*np.sin(k*phase+.1*k) for k,weight in [(1,.65),(2,.25),(3,.38),(4,.11),(5,.17),(6,.08)])
    envelope=np.minimum(t/.04,1)*np.minimum((.72-t)/.12,1)*(1-.25*t/.72)
    sound=.35*sound/np.max(abs(sound))*np.clip(envelope,0,1)
    wav=out/'honk.wav'
    with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((sound*32767).astype('<i2').tobytes())
    mp3=out/'0001.mp3'
    subprocess.run(['/home/ethan/.local/bin/ffmpeg','-y','-loglevel','error','-i',str(wav),'-ac','1','-ar','44100','-b:a','64k',str(mp3)],check=True)
    result={'origin':'original oscillator synthesis; no borrowed audio','duration_s':.72,'sample_rate_Hz':rate,
        'speaker_output_verified':False,'dfplayer_card_path':'/mp3/0001.mp3',
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (wav,mp3)},
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'audio_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
