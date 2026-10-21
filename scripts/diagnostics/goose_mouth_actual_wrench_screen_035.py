"""035 beam-only correction; retain exact034 shaft/needle/Fy applicability calculations."""
import hashlib
from pathlib import Path
import goose_mouth_actual_wrench_screen_034 as retained
import goose_mouth_actual_beam_screen_035 as corrected
for module,expected in [(retained,'6109d5d9439c3639bbbb6049b4efaf3e7aed34e4596422167958ae95319604b4'),(corrected,'ef48647a9fbac68b701b4030321dcd90ef0208f34f288880517a22f58b427347')]:
    if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()!=expected:raise ValueError('035 dependency identity mismatch')
def screen_contacts(points,qjaw_rad,table):
    result=retained.screen_contacts(points,qjaw_rad,{'sections':[]})
    beams=corrected.screen_beams(points,table)
    result['beam_sections']=beams['beam_sections']
    result['reasons']=sorted(set(result['reasons']+beams['reasons']))
    result['status']='WITHIN_CONDITIONAL_SCREEN' if not result['reasons'] else 'OUT_OF_CONDITIONAL_SCREEN'
    result['beam_correction_scope']=beams['scope']
    result['existing_geometry_only_no_hardware_or_MCI_change']=True
    return result
