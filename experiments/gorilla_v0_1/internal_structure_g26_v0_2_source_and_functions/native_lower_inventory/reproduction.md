# Actual runtime and producers

Capture and native extraction used `/home/ethan/Softwares/blender-local/root/usr/bin/blender` 4.0.2, on CPU. The local bundled Blender needs explicit scripts/data/shared-library and Python stdlib paths. No runtime was installed and no dependency lock was changed.

```bash
CUDA_VISIBLE_DEVICES='' \
BLENDER_SYSTEM_SCRIPTS=/home/ethan/Softwares/blender-local/root/usr/share/blender/scripts \
BLENDER_SYSTEM_DATAFILES=/home/ethan/Softwares/blender-local/root/usr/share/blender/datafiles \
LD_LIBRARY_PATH=/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu:/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu/lapack:/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu/blas:/home/ethan/Softwares/blender-local/root/usr/lib \
PYTHONPATH=/usr/lib/python3.12/lib-dynload:/home/ethan/.local/share/uv/python/cpython-3.12-linux-aarch64-gnu/lib/python3.12/lib-dynload:/home/ethan/Softwares/blender-local/root/usr/share/blender/scripts/modules:/home/ethan/Projects/Sai_Rotbots/.venv/lib/python3.12/site-packages \
/home/ethan/Softwares/blender-local/root/usr/bin/blender \
--factory-startup --disable-autoexec --background \
--python .scratch/gorilla_internal_g26_v0_2_lower_source_inventory/extract_safe_blend.py
```

Rendering used the same environment and safe-load CLI with `render_native_four_view.py`; Cycles `device=CPU`, 8 threads, 32 samples, no evaluated modifiers. Existing Art drivers/scripts/texts were not executed. Use `compose_four_view.py` to build the four-view sheet. `summarize_native_inventory.py` derives actual world bounds and preserves explicit appearance hierarchy, then `write_checkpoint.py` captures targeted metadata and records the geometric lock. A reproduction must first copy the captured inputs and producer files into a **new** directory and change each producer's fixed output constant `O` to that directory, never rerun over this frozen evidence. The exact original bytes remain authoritative.

Failed startup and serialization logs are historical attempts. `extract_safe_blend_initial.py` produced a JSON serialization error after writing the meshes; its partial output `native_lower_scene_serialization_incomplete.json.txt` is not a scene. The subsequent producer converted NumPy bool to Python bool, then successfully generated `native_lower_scene.json` and all mesh NPZ. This is serialization-only correction, not a geometry/normal repair. First render brightness/samples changed in the final producer without material or geometry changes, and initial render bytes remain in `render_initial`.
