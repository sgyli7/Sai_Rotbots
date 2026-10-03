# Gorilla G7 tool and CAD route receipt

Actual aarch64 host. [Official Gmsh download](https://gmsh.info/) currently links Linux4.15.2; the actual executable ELF header obtained from its archive is e_machine62, x86-64. This checks that release, not every possible ARM distribution. Header/source receipt is official_release_probe.json; full archive was not downloaded, so no full archive hash is claimed.

Ubuntu noble universe provides arm64 Gmsh4.12.1+ds1-1.1build2.23 actual debs are independently extracted in tools/, all hashes recorded. No global apt install/update or projectvenv/lock change. Public noble versions were explicitly used for two unavailable ESM-authorized candidates. Actual CLI version, Python OCC box/cavity construction and3Dtet generation succeeded: netcube volume0.000875m3,4386tet, minSICN0.29784. Gmsh is [GPL2-or-later with upstream linking exception](https://gmsh.info/LICENSE.txt); extracted package copyright and dependency notices remain in tools/extract/usr/share/doc. Tool use alone does not certify output geometry/FE/physical behavior.

Route1 selected: originalG4 nominal parametric carrier rebuilt in true OpenCASCADE boxes/circles, actual closed6mm cavity and all journal/pin/keeper bores retained, exact solid/physical surface groups then two locally sizedtet meshes. This is a newsource, never an inheritedG4 material-gate pass.

Route2 fallback only if lawful parametric meshing remains inadequate: same wide load shell and local bosses partitioned at actual material interfaces into conformal CAD blocks; material volume/bores/interfaces must remain traceable. It is not deleting STLslivers or normal repair. The broader wide-shell/localboss cost fallback remains an architecture choice, not a qualified mass reduction. No topology optimization is run here.

New exact CAD already constructed: one OCCmaterial solid,0.004074563071672421m3 versus originalG4facet0.004073505650565652m3, +0.0259585% / +0.008300756688kg conditional7850kg/m3. Nominal dimensions and axis positions unchanged; mathematical-circle surfaces differ from64facet chords by explicitly recorded radial sag. Seven actual CADport groups exist in cad_source_manifest.json.
