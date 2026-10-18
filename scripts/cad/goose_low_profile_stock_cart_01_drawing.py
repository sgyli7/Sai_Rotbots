from pathlib import Path
import json
import cadgen
from cadgen.eng_drawing import Sheet,eng_drawing
from goose_low_profile_stock_cart_01 import PARAMS
W=Path(__file__).resolve().parents[2]

@eng_drawing(out='../../robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01_drawing.pdf')
def goose_low_profile_stock_cart_01_drawing():
    p=json.loads(PARAMS.read_text())
    part=cadgen.read_step(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01.step')
    sheet=Sheet('A2',scale=.2,title='GOOSE LOW STOCK CART',part_number='CART-01',material='Al frame/deck, steel pins, PU wheels',revision='CONCEPT 01',author='Sai_Rotbots',notes=['NOMINAL GEOMETRY / DESIGN REVIEW.', '20 kg PAYLOAD TARGET, NOT LOAD CERTIFIED.', 'BITE HEIGHT: 440-520, NOMINAL 480.', 'NO ROBOT DRAG OR BRAKE QUALIFICATION.'])
    top,front,right=sheet.three_views(part,gap=60)
    iso=sheet.view(part,'iso',at=(465,300),label='ISOMETRIC 1:10',scale=.1)
    top.overall();front.overall();right.overall()
    front.dim((0,0,p['deck_top_z']),(p['platform_length'],0,p['deck_top_z']),orientation='h')
    front.dim((80,-190,0),(-350,0,p['grip_center'][2]),orientation='v')
    front.dim((80,-190,62.5),(570,-190,62.5),orientation='h')
    top.dim((325,-225,p['deck_top_z']),(325,225,p['deck_top_z']),orientation='v')
    top.dim((-350,0,480),(0,0,p['deck_top_z']),orientation='h')
    return sheet

if __name__=='__main__':goose_low_profile_stock_cart_01_drawing()
