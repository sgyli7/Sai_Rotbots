"""A continuous authored head surface, rather than fused exterior seams."""
import numpy as np
from build123d import Axis, Solid, Face, import_step, export_brep
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.BRepFill import BRepFill
from OCP.TopoDS import TopoDS
from OCP.ShapeFix import ShapeFix_Solid

from build_goose_manufacturing_skins import head_grid
from goose_nurbs_skin import surface
from build_goose_cad import box, cylinder, holes, transform


def build_continuous_head(scene, optical, rotation, construction_path, cfg, camera_source, vendor_rotation, vendor_translation, evidence_path):
    outer, inside = head_grid(scene)
    # Preserve the existing authored lower-cheek/crank relief at every node.
    for points in (outer, inside):
        x, z = points[:, :, 0], points[:, :, 2]
        rise = np.clip((x-110)/8, 0, 1); rise = rise*rise*(3-2*rise)
        fall = np.clip((174-x)/16, 0, 1); fall = fall*fall*(3-2*fall)
        low = np.clip((605-z)/20, 0, 1); low = low*low*(3-2*low)
        points[:, :, 1] += np.sign(points[:, :, 1])*3*rise*fall*low
        rise = np.clip((x-135)/10, 0, 1); rise = rise*rise*(3-2*rise)
        fall = np.clip((176-x)/10, 0, 1); fall = fall*fall*(3-2*fall)
        low = np.clip((580-z)/15, 0, 1); low = low*low*(3-2*low)
        points[:, :, 2] -= 4*rise*fall*low
    phi = np.linspace(-np.pi/2, 3*np.pi/2, 65)
    def ring(ry, rz):
        return np.column_stack((np.full(65, .4),
            ry*np.sign(np.cos(phi))*np.abs(np.cos(phi))**(2/2.8),
            rz*np.sign(np.sin(phi))*np.abs(np.sin(phi))**(2/2.8))) @ rotation.T + optical
    def extend(grid, front):
        rear = grid[-1]
        tangent = grid[-1]-grid[-2]
        m0 = tangent*((front[:, 0]-rear[:, 0])/tangent[:, 0])[:, None]
        m1 = front-rear
        t = np.linspace(0., 1., 13)[1:, None, None]
        blend = ((2*t**3-3*t**2+1)*rear + (t**3-2*t**2+t)*m0
                 + (-2*t**3+3*t**2)*front + (t**3-t**2)*m1)
        return np.concatenate([grid, blend])
    outer, inside = extend(outer, ring(27., 24.)), extend(inside, ring(25.6, 22.6))
    # Smooth roof allowance is authored into the same outer/inner NURBS
    # grids. Its endpoint weight is zero, so camera mounting plane is fixed.
    start, end = cfg['roof_bump_ring_interval']
    u = np.clip((np.arange(len(outer))-start)/(end-start), 0., 1.)
    longitudinal = np.sin(np.pi*u)**2
    for points in (outer, inside):
        top = np.clip((points[:,:,2]-610.)/10.,0.,1.)
        top = top*top*(3.-2.*top)
        points[:,:,2] += cfg['roof_clearance_bump_mm']*longitudinal[:,None]*top
    construction_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(construction_path, outer=outer, inner=inside)
    so, si = surface(outer), surface(inside)
    sewing = BRepBuilderAPI_Sewing(1e-5)
    # Four patches share exact curves of one continuous NURBS surface. No
    # duplicate angular wall is inserted at the closed perimeter boundary.
    for j in range(4):
        a, b = j/4, (j+1)/4
        for s in (so, si):
            sewing.Add(BRepBuilderAPI_MakeFace(s, 0., 1., a, b, 1e-7).Face())
        for u in (0., 1.):
            edges = [BRepBuilderAPI_MakeEdge(s.UIso(u), a, b).Edge() for s in (so, si)]
            sewing.Add(BRepFill.Face_s(*edges))
    sewing.Perform()
    wrapped = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid()
    fix = ShapeFix_Solid(wrapped); fix.Perform()
    shell = Solid(fix.Solid())
    if not shell.is_valid or len(shell.solids()) != 1:
        raise ValueError('Continuous head skin is not a single native solid')
    shell -= box([1000., 1000., 1000.], [-399.25, 0., 600.])
    # Under-head installation opening, outside the four front screw lands.
    # The primary exterior remains a single print; no visible side seam.
    chin = box(cfg['chin_installation_opening_size_mm'], cfg['chin_installation_opening_center_mm'])
    shell -= chin.fillet(4., chin.edges())
    for radius, angle in [(14.5, 0.), (14.5, 90.), (17., 300.)]:
        t = np.deg2rad(angle)
        shell -= cylinder(3.8, 7., [160+radius*np.cos(t), -32.5, 576+radius*np.sin(t)], 'y')
    land = box([1.2, 52., 46.], [.3, 0., 0.])
    land = land.fillet(9., land.edges().filter_by(Axis.X))
    land -= cylinder(6.5, 12., [.3, 0., 0.], 'x')
    land = holes(land, [[.3, y, z] for y in [-19., 19.] for z in [-12., 12.]], 2.4, 12., 'x')
    for y in (-14., 14.):
        for z in (-14., 14.):
            land -= cylinder(2.15, 2., [.3, y, z], 'x')
    shell += transform(land, rotation, optical)
    supplier = import_step(camera_source)
    group = next(c for c in supplier.children if c.label == cfg['camera_open_group'])
    reliefs = []
    for index in cfg['camera_relief_original_shell_indices']:
        original = group.shells()[index]
        bb = original.bounding_box(optimal=False)
        lo, hi = np.array(tuple(bb.min)), np.array(tuple(bb.max))
        cutter = transform(box(hi-lo+2*cfg['camera_relief_source_margin_mm'], (lo+hi)/2), vendor_rotation, vendor_translation)
        distances = [Face(BRepBuilderAPI_MakeFace(so,0.,1.,j/4,(j+1)/4,1e-7).Face()).distance_to(cutter) for j in range(4)]
        if min(distances) < cfg['minimum_outer_to_camera_relief_distance_mm']:
            raise ValueError(('Camera relief would make outer wall too thin',index,min(distances)))
        path = construction_path.parent / ('camera_relief_source_shell_'+str(index)+'.brep')
        export_brep(cutter,path)
        shell -= cutter
        reliefs.append(dict(original_shell_index=index,original_faces=len(original.faces()),source_margin_mm=cfg['camera_relief_source_margin_mm'],
            source_bounds_min_mm=lo.tolist(),source_bounds_max_mm=hi.tolist(),outer_surface_separation_mm=min(distances),cutter_path=str(path)))
    evidence_path.write_text(__import__('json').dumps(dict(original_group=group.label,original_group_closed=False,all_original_source_shells=len(group.shells()),
        all_original_source_faces=len(group.faces()),roof_bump_mm=cfg['roof_clearance_bump_mm'],camera_optical_plane_unchanged=True,local_reliefs=reliefs),indent=2)+'\n')
    if not shell.is_valid or len(shell.solids()) != 1:
        raise ValueError('Continuous head openings or front land broke native closure')
    return shell
