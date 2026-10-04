"""Electrical integrity of the independent, unqualified PCB candidate."""
import copy
import math

from .brake_chopper import validate_circuit


def validate_pcb_candidate(config):
    parts=config['components'];by_ref={p['ref']:p for p in parts}
    if len(parts)!=len(by_ref):raise ValueError('duplicate component reference')
    if len(parts)!=52:raise ValueError('incomplete PCB circuit inventory')
    expected={
        'R3':('825000 ohm','BRAKE_REQUEST','FEEDBACK_MID'),
        'R31':('825000 ohm','FEEDBACK_MID','SENSE'),
        'C16':('1 uF','BIAS_5V','GND'),'C17':('1 uF','BIAS_5V','GND'),
        'C18':('0.1 uF','BIAS_5V','GND'),'C19':('0.1 uF','BIAS_5V','GND'),
        'C20':('0.01 uF','BIAS_PG_DELAY','GND')}
    for ref,(value,a,b) in expected.items():
        p=by_ref[ref]
        if p['value']!=value or {k:v['net'] for k,v in p['pins'].items()}!={'1':a,'2':b}:
            raise ValueError('series feedback or local bypass circuit mismatch')
    if by_ref['U1']['pins']['7']['net']!='BIAS_PG_DELAY':raise ValueError('wrong LDO delay pin')
    if any(by_ref[ref]['sku']!='RT0603BRD07825KL' for ref in ['R3','R31']):
        raise ValueError('series feedback ordering code mismatch')
    mid=[(p['ref'],n) for p in parts for n,pin in p['pins'].items() if pin['net']=='FEEDBACK_MID']
    if set(mid)!={('R3','2'),('R31','1')}:raise ValueError('feedback midpoint must have no extra load')
    # Reuse the parent pin/polarity oracle after explicitly checking additions.
    equivalent=copy.deepcopy(config)
    equivalent['components']=[p for p in equivalent['components'] if p['ref'] not in expected or p['ref']=='R3']
    eq={p['ref']:p for p in equivalent['components']}
    eq['R3']['value']='1650000 ohm';eq['R3']['pins']['2']['net']='SENSE';eq['U1']['pins']['7']['net']=None
    validate_circuit(equivalent)
    for p in parts:
        if p['kind']=='external_resistor':continue
        ref=p['ref'];f=config['footprints'][p['footprint']]
        if {str(i['number']) for i in f['pads']}!=set(p['pins']):raise ValueError('footprint pin coverage')
        pos=config['placements_mm'][ref]
        if len(pos)!=2 or not all(math.isfinite(v) for v in pos):raise ValueError('invalid placement')
        for pad in f['pads']:
            x=pos[0]+pad['at_mm'][0];y=pos[1]+pad['at_mm'][1]
            sx,sy=pad['size_mm']
            if min(sx,sy)<=0 or x-sx/2<.5 or x+sx/2>79.5 or y-sy/2<.5 or y+sy/2>49.5:
                raise ValueError('pad outside board copper clearance')
        if p['footprint_release']:raise ValueError('footprint peer review is still pending')
    if config['footprints']['dgn8']['pads'][-1]['size_mm']!=[1.6,1.92]:
        raise ValueError('TPS fixed DGN footprint confused with DRB')
    if config['footprints']['dbv5']['pads'][0]['at_mm']!=[-1.3,-.95]:
        raise ValueError('TLV DBV footprint confused with DCK')
    if config['footprints']['f12']['max_height_mm']!=12.7:
        raise ValueError('cap maximum height omitted')
    return equivalent


def require_clean_drc(text):
    """Reject missing/truncated/error reports, not just successful API return."""
    import re
    counts={}
    for name,pattern in {'violations':r'\*\* Found (\d+) DRC violations',
        'unconnected':r'\*\* Found (\d+) unconnected pads',
        'footprint_errors':r'\*\* Found (\d+) Footprint errors'}.items():
        matches=re.findall(pattern,text)
        if len(matches)!=1:raise ValueError('missing or ambiguous native DRC report')
        counts[name]=int(matches[0])
    if any(counts.values()) or '** End of Report **' not in text or re.search(r'^\[',text,re.M):
        raise ValueError('native DRC rejects candidate')
    return counts
