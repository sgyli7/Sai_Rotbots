"""Compose hash-verified Blender inspection views without altering source geometry."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source = ROBOT / 'evidence/manual_wing_service_blender_views.json'
    report = json.loads(source.read_text())
    inputs = [source, Path(__file__)]
    for name, expected in report['source_hashes'].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Stale inspection input: {name}')
    views = {v['name']: v for v in report['views']}
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.4), facecolor='white')
    for ax, name, title in zip(axes, ['closed', 'open45', 'detail'],
            ['Closed service door', 'Open 45 degrees - thumb screw removed', 'Two integral hinges - detail']):
        view = views[name]
        path = ROBOT / view['path']
        if sha(path) != view['sha256']:
            raise ValueError(f'Changed Blender image: {path}')
        inputs.append(path)
        ax.imshow(mpimg.imread(path))
        ax.set_title(title, fontsize=11)
        ax.set_axis_off()
    fig.suptitle('GOOSE V0.1 | Actual manual wing service mechanism', fontsize=17, fontweight='bold', y=.98)
    fig.text(.5, .07, 'Actual CAD-derived quads. Orange highlights the moving door; inspection colours are not product colours.', ha='center', fontsize=10)
    fig.text(.5, .025, 'Seven finite service angles checked. Continuous sweep, whole assembly, final seam styling and manufacture remain unqualified.', ha='center', fontsize=9, color='#555555')
    fig.subplots_adjust(left=0, right=1, top=.89, bottom=.12, wspace=.04)
    output = ROBOT / 'images/manual_wing_service_geometry.png'
    fig.savefig(output, dpi=150, bbox_inches='tight')
    plt.close(fig)
    result = dict(schema='goose_manual_wing_service_figure_v2', image=str(output.relative_to(ROBOT)),
        image_sha256=sha(output), actual_blender_views_composed=True,
        actual_cad_derived_quad_geometry=True, geometry_modifiers=0, no_viewport_geometry_culling=True,
        whole_appearance_release=False, source_hashes={str(p.relative_to(ROOT)): sha(p) for p in inputs})
    (ROBOT / 'evidence/manual_wing_service_geometry_figure.json').write_text(json.dumps(result, indent=2) + '\n')
    print(output)

if __name__ == '__main__':
    main()
