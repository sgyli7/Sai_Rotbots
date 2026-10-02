"""Correct the XC330 body and front horn; optional rear idler is not installed.

Native own envelope reconstructed from the official drawing. Connector and
fastener geometry remain separate unreleased candidates, not silently removed.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,cylinder
from goose_candidate_export import CandidateExport


def main():
    e=CandidateExport(R,'head_roll_envelope')
    shape=box([23,20,34],[81,0,578])+cylinder(8,3,[94,0,585.5],'x')
    e.emit('head_roll_catalog_envelope',shape,'head_pitch',rho=1,material='graphite',catalog_mass=.023,
        notes=['ROBOTIS XL,XC-330 drawing: body23mm depth, front3mm hornOD16; optional rear idler absent from selected BOM.',
               'Own reconstruction, not vendor CAD. Internal inertia unknown; connector and installation candidates retained.'])
    e.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py'],
        replaces=['head_roll_case','head_roll_front_case','head_roll_horn','head_roll_idler'],
        extra=dict(status='DOCUMENTED_CATALOG_ENVELOPE_NOT_MANUFACTURING_RELEASE',
                   source_url='https://www.robotis.com/service/download.php?no=1986',
                   replaces_mass_item='head_roll',manufacturer_body_depth_mm=23,optional_rear_idler_installed=False))


if __name__=='__main__':main()
