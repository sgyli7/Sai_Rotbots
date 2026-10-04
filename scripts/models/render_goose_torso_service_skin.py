"""Source-bound geometric inspection views of the bare repaired torso skins."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
manifest_path = R/'cad/exports/torso_service_skin/manifest.json'
manifest = json.loads(manifest_path.read_text())
parts = {}
source_hashes = {str(manifest_path.relative_to(ROOT)):hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
for part in manifest['parts']:
    if not part['name'].endswith('_right') and not '_right_' in part['name']:
        continue
    file = part['files']['npz']
    path = R/file['path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != file['sha256']:
        raise ValueError('Changed figure geometry')
    data = np.load(path)
    parts[part['name']] = [data['vertices']*1000, data['faces']]
    source_hashes[str(path.relative_to(ROOT))] = file['sha256']
fig = plt.figure(figsize=(14, 5.4), facecolor='white')
views = [(25, -53, 0, 'Closed - three-quarter'), (0, -90, 0, 'Closed - side'),
         (25, -53, -45, '45-degree geometric rotation')]
for index, (elev, azim, angle, title) in enumerate(views):
    ax = fig.add_subplot(1, 3, index+1, projection='3d')
    for name, (vertices, faces) in parts.items():
        v = vertices.copy()
        door = 'door' in name
        if door and angle:
            origin = np.array([0, -105, 367])
            a = np.radians(angle)
            rot = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
            v = (v-origin)@rot.T+origin
        color = '#e97c30' if door else '#ccd6dd' if 'aft' in name else '#aab9c4'
        # Show every source face; no geometric smoothing or subdivision.
        poly = Poly3DCollection(v[faces], facecolor=color, edgecolor='none', linewidths=0,
                                alpha=.93 if door else .82, rasterized=True)
        ax.add_collection3d(poly)
    ax.set_xlim(-185, 155)
    ax.set_ylim(-230, 15)
    ax.set_zlim(205, 435)
    ax.set_box_aspect([340, 245, 230])
    ax.view_init(elev=elev, azim=azim)
    fig.text((index+.5)/3, .84, title, ha='center', fontsize=11)
    ax.set_axis_off()
fig.suptitle('GOOSE V0.1 | Repaired shared CAD surfaces', fontsize=17, fontweight='bold', y=.96)
fig.text(.5, .10, 'Bare right-side skins only. Native self-interference and exchange gates passed.',
         ha='center', fontsize=11)
fig.text(.5, .055, 'Actual roof mounts, circular neck cut, hinge and latch are absent. Not an assembly or appearance release.',
         ha='center', fontsize=10, color='#555555')
fig.subplots_adjust(left=0, right=1, top=.89, bottom=.15, wspace=0)
output = R/'images/torso_service_skin_geometry.png'
fig.savefig(output, dpi=160, bbox_inches='tight')
plt.close(fig)
source_hashes[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(R/'evidence/torso_service_skin_geometry_figure.json').write_text(json.dumps(dict(
    schema='goose_torso_service_skin_geometry_figure_v1', image=str(output.relative_to(R)),
    image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), right_side_only=True,
    actual_cad_derived_quad_geometry=True, full_assembly_release=False, source_hashes=source_hashes), indent=2)+'\n')
print(output)
