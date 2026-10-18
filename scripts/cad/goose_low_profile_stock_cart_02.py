"""Parametric low deck stock cart, mm. Robot 04 is not modified.

Derived from R2 public commit 577657ac41d377c11f3cb948cdad13239ca94a85.
Run with cadgen 0.7.21 Python; parameters are the maintained editable input.
The cart is a passive mechanism concept, not a certified load or drag result.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from cadgen import build123d as bd, step, glb, srgb

ROOT=Path(__file__).resolve().parents[2]
PARAMS=ROOT/'robots/goose_v0_2/cad/source/low_profile_stock_cart_02/parameters.json'
EXPORT='../../robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02'

def make_cart():
    p=json.loads(PARAMS.read_text());parts=[];mass=[];grip_z=p['drawhead_pivot_center'][2]
    density={k:v['density_kg_m3'] for k,v in p['materials'].items()}
    colors={'aluminium_frame':'#D5DEE2','aluminium_sheet':'#EFEAE0','steel':'#47525A','stainless':'#8C969C','nylon':'#536169','polyurethane':'#263138'}
    def add(shape,label,mat,color=None):
        # Real CAD rotation of every component downstream of the existing pitch pin.
        moving=('drawbar_main_', 'roll_bearing_', 'rotating_forward_', 'shaft_axial_', 'bite_yoke_', 'bite_core_', 'bite_304_', 'replaceable_bite_')
        if label.startswith(moving):
            shape=shape.rotate(bd.Axis(p['drawhead_pivot_center'],(0,1,0)),p['drawhead_pitch_deg'])
        shape.label=label;shape.color=srgb(color or colors[mat]);parts.append(shape)
        c=shape.center(bd.CenterOf.MASS)
        mass.append({'name':label,'material':mat,'volume_mm3':shape.volume,'mass_kg':shape.volume*1e-9*density[mat],'COM_mm':[c.X,c.Y,c.Z],'positive_volume':shape.volume>0,'valid_native':shape.is_valid})
        return shape
    def box(x,y,z,c):return bd.Pos(*c)*bd.Box(x,y,z)
    def cyl(r,h,c,axis='z'):
        s=bd.Cylinder(r,h)
        if axis=='y':s=s.rotate(bd.Axis.X,90)
        if axis=='x':s=s.rotate(bd.Axis.Y,90)
        return bd.Pos(*c)*s
    def tube(length,wy,hz,wall,c,axis='x'):
        if axis=='x':return box(length,wy,hz,c)-box(length+2,wy-2*wall,hz-2*wall,c)
        if axis=='y':return box(wy,length,hz,c)-box(wy-2*wall,length+2,hz-2*wall,c)
        return box(wy,hz,length,c)-box(wy-2*wall,hz-2*wall,length+2,c)
    def rod_between(a,b,r,inner=0):
        v=bd.Vector(b)-bd.Vector(a);L=v.length;plane=bd.Plane(origin=a,z_dir=v)
        sh=bd.Solid.make_cylinder(r,L,plane)
        if inner:sh=sh-bd.Solid.make_cylinder(inner,L,plane)
        return sh
    def screw(c,axis='z',length=22):
        return cyl(3,length,c,axis)+cyl(5,4,tuple(c[i]+(length/2+2 if (axis=='z' and i==2) or (axis=='x' and i==0) or (axis=='y' and i==1) else 0) for i in range(3)),axis)
    L=p['platform_length'];W=p['platform_width'];zf=p['frame_center_z']
    for y in [-205,205]:add(tube(L,20,30,p['frame_wall'],(325,y,zf)),f'longitudinal_rail_y{y}','aluminium_frame')
    for x in [10,215,435,640]:add(tube(390,20,30,p['frame_wall'],(x,0,zf),'y'),f'crossmember_x{x}','aluminium_frame')
    deck=box(L,W,1.5,(325,0,180.75))
    # Rounded-corner outer deck, eight slots are real drainage/hand-cleaning cuts.
    deck=bd.fillet(deck.edges().filter_by(bd.Axis.Z),radius=12)
    for x in [100,250,400,550]:
        for y in [-110,110]:
            slot=box(80,10,5,(x,y,180.75))+cyl(5,5,(x-40,y,180.75))+cyl(5,5,(x+40,y,180.75));deck=deck-slot
    add(deck,'deck_1p5mm_aluminium','aluminium_sheet')
    # Low removable shallow basket, no full heavy shell.
    for y in [-217,217]:
        add(tube(634,16,16,1.2,(325,y,282)),f'basket_top_rail_y{y}','aluminium_frame')
        panel=box(610,1,83,(325,y,231.5))
        for x in [75,175,275,375,475,575]:panel=panel-box(65,5,45,(x,y,234))
        add(panel,f'perforated_side_y{y}','aluminium_sheet')
    for x in [8,642]:
        add(tube(418,16,16,1.2,(x,0,282),'y'),f'basket_top_rail_x{x}','aluminium_frame')
        panel=box(1,410,83,(x,0,231.5))
        for y in [-150,-50,50,150]:panel=panel-box(5,65,45,(x,y,234))
        add(panel,f'perforated_end_x{x}','aluminium_sheet')
    for x in [8,642]:
        for y in [-217,217]:add(tube(100,16,16,1.2,(x,y,232),'z'),f'corner_post_{x}_{y}','aluminium_frame')
    # Caster and fixed fork interface candidates, not OEM part claims.
    for x in [80,570]:
      for y in [-190,190]:
        tag=f'{x}_{y}';swivel=x==80;kingx=x-25 if swivel else x
        add(cyl(62.5,p['wheel_width'],(x,y,62.5),'y')-cyl(52.5,p['wheel_width']+2,(x,y,62.5),'y'),'PU_tread_'+tag,'polyurethane')
        hub=cyl(52.5,23,(x,y,62.5),'y')-cyl(13,25,(x,y,62.5),'y')
        for angle in [0,60,120,180,240,300]:
            xx=x+33*math.cos(math.radians(angle));zz=62.5+33*math.sin(math.radians(angle));hub=hub-cyl(12,25,(xx,y,zz),'y')
        add(hub,'nylon_spoked_hub_'+tag,'nylon')
        for s in [-1,1]:add(cyl(13,8,(x,y+s*7.5,62.5),'y')-cyl(5,10,(x,y+s*7.5,62.5),'y'),f'wheel_6000_interface_{tag}_{s}','steel')
        add(cyl(5,52,(x,y,62.5),'y'),'axle_d10_'+tag,'steel')
        for s in [-1,1]:
            leg=box(52,2,68,((x+kingx)/2,y+s*23,92))-cyl(5.2,5,(x,y+s*23,62.5),'y')
            add(leg,f'fork_plate_{tag}_{s}','steel')
        add(box(60,49,2,(kingx,y,127)),'fork_bridge_'+tag,'steel')
        mount=box(68,60,3,(kingx,y,145.5))
        spreader=box(125,80,3,(kingx,y,148.5))
        for xx in [-24,24]:
            for yy in [-20,20]:
                mount=mount-cyl(3.3,6,(kingx+xx,y+yy,145.5))
                spreader=spreader-cyl(3.3,7,(kingx+xx,y+yy,148.5))
        add(mount,'mount_plate_'+tag,'steel')
        add(spreader,'load_spreader_3mm_'+tag,'aluminium_frame')
        for xx in [-24,24]:
            for yy in [-20,20]:add(screw((kingx+xx,y+yy,146)),f'M6_wheel_mount_{tag}_{xx}_{yy}','steel')
        if swivel:
            add(cyl(15,8,(kingx,y,135))-cyl(6,10,(kingx,y,135)),'caster_thrust_bearing_'+tag,'steel')
            for zz,hh in [(129.5,3),(141.5,5)]:add(cyl(15,hh,(kingx,y,zz))-cyl(6.2,hh+2,(kingx,y,zz)),f'caster_thrust_seat_{tag}_{zz}','steel')
            add(cyl(6,21,(kingx,y,136)),'caster_kingpin_'+tag,'steel')
        else:
            add(box(44,40,16,(kingx,y,136)),'fixed_fork_spacer_'+tag,'aluminium_frame')
            # Manual parking cam lever and compliant pad; setting force not qualified.
            add(box(48,30,4,(x+12,y,133)),'parking_pedal_'+tag,'steel','#E7AB3E')
            add(box(28,26,5,(x+12,y,123.5)),'parking_friction_pad_'+tag,'polyurethane')
    # Compact bolted mast. Base plate and gussets stay under/outside cargo face.
    base=box(110,100,5,(20,0,147.5))
    for x in [-20,60]:
        for y in [-35,35]:base=base-cyl(3.3,8,(x,y,147.5))
    add(base,'mast_base_plate_5mm','aluminium_frame')
    mast=tube(p['mast_top_z']-p['mast_bottom_z'],32,32,2,(-25,0,(p['mast_top_z']+p['mast_bottom_z'])/2),'z')
    for z in p['height_lock_holes_z']:mast=mast-cyl(3.3,40,(-25,0,z),'y')
    add(mast,'height_adjust_mast_32x32x2','aluminium_frame')
    for y in [-16,19]:
        # Geometry-defined triangular side gussets; bolted not weld-strength credited.
        poly=bd.Plane.XZ*bd.Polygon((-41,150),(-3,150),(-41,270),align=None)
        add(bd.Pos(0,y,0)*bd.extrude(poly,amount=3),f'mast_base_gusset_{y}','aluminium_frame')
    for x in [-20,60]:
        for y in [-35,35]:add(screw((x,y,154)),f'M6_mast_foot_{x}_{y}','steel')
    # Height lock carriage, vertical yaw pin, horizontal pitch pin.
    carriage=box(42,50,50,(-25,0,grip_z))-box(34,34,52,(-25,0,grip_z))-cyl(3.3,54,(-25,0,grip_z),'y')
    add(carriage,'height_lock_carriage','aluminium_frame')
    add(cyl(3,62,(-25,0,grip_z),'y'),'height_lock_pin_M6','steel')
    add(cyl(15,44,(-62,0,grip_z))-cyl(5,46,(-62,0,grip_z)),'yaw_housing','aluminium_frame')
    add(box(26,40,6,(-47,0,grip_z-24)),'yaw_lower_arm','aluminium_frame')
    add(box(26,40,6,(-47,0,grip_z+24)),'yaw_upper_arm','aluminium_frame')
    add(cyl(5,56,(-62,0,grip_z)),'yaw_pin_d10','steel')
    for y in [-17,17]:add(box(42,4,35,(-90,y,grip_z))-cyl(5.2,6,(-95,y,grip_z),'y'),f'pitch_clevis_{y}','aluminium_frame')
    add(box(12,38,35,(-73,0,grip_z)),'yaw_rotor_to_pitch_fork_bridge','aluminium_frame')
    add(cyl(5,45,(-95,0,grip_z),'y'),'pitch_pin_d10','steel')
    add(cyl(11,108,(-149,0,grip_z),'x')-cyl(9,110,(-149,0,grip_z),'x'),'drawbar_main_22x2','aluminium_frame')
    # Bearing sleeve allows axial roll instead of transmitting cart roll to head.
    housing=cyl(17,42,(-224,0,grip_z),'x')-cyl(9,44,(-224,0,grip_z),'x')
    for x in [-240.5,-207.5]:housing=housing-cyl(11.05,7.05,(x,0,grip_z),'x')
    add(housing,'roll_bearing_housing','aluminium_frame')
    for x in [-240.5,-207.5]:add(cyl(11,7,(x,0,grip_z),'x')-cyl(4,9,(x,0,grip_z),'x'),f'roll_bearing_608_interface_{x}','steel')
    add(cyl(4,110,(-250,0,grip_z),'x'),'rotating_forward_shaft_d8','steel')
    for x in [-245.5,-202.5]:add(cyl(6,3,(x,0,grip_z),'x')-cyl(4,5,(x,0,grip_z),'x'),f'shaft_axial_retaining_collar_{x}','steel')
    add(cyl(7,24,(-287,0,grip_z),'x')-cyl(4,26,(-287,0,grip_z),'x'),'bite_yoke_shaft_socket','aluminium_frame')
    # Hollow fork arms leave the bill its approach and opening volume.
    for y in [-85,85]:
        add(rod_between((-287,0,grip_z),(-350,y,grip_z),7,5.5),f'bite_yoke_tube_{y}','aluminium_frame')
        add(cyl(11,8,(-350,y,grip_z),'y')-cyl(4.1,10,(-350,y,grip_z),'y'),f'bite_core_support_{y}','aluminium_frame')
    add(cyl(4,178,(-350,0,grip_z),'y'),'bite_304_core_d8','stainless')
    add(cyl(6,160,(-350,0,grip_z),'y')-cyl(4,162,(-350,0,grip_z),'y'),'replaceable_bite_sleeve_d12','polyurethane','#DFAF43')
    # Torsion spring is an explicit geometric envelope + reserved purchase mass.
    add(cyl(12,9,(-95,25,grip_z),'y')-cyl(7,11,(-95,25,grip_z),'y'),'pitch_balance_spring_envelope','steel')
    # Misc fixing mass is listed separately, never hidden in solid density.
    assembly=bd.Compound(children=parts,label='goose_low_profile_stock_cart_02')
    return assembly,mass,p

@step(out=EXPORT+'.step')
@glb(out=EXPORT+'.glb',mesh_tolerance=0.001,mesh_angular_tolerance=0.25)
def goose_low_profile_stock_cart_02():
    shape,_,_=make_cart()
    return shape

if __name__=='__main__':
    goose_low_profile_stock_cart_02()
