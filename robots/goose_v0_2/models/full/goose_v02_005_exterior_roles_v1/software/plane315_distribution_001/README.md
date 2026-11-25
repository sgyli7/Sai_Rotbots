# Source007 plane-mesh source overlay

This directory restores the isolated MJWarp source overlay without running pip or changing the shared environment. It includes292 package/metadata files (8,945,604 bytes), the original AUTHORS and LICENSE, the original and patched collision source, the official source reference, the single-file diff, and the zero-step first-article evidence. Python, MuJoCo native libraries, Warp, Torch/CUDA and GPU JIT caches are not included.

The source-only backport uses official commit [7670775909e8138b372a0e377bc19addd5b12e3b / PR1731](https://github.com/google-deepmind/mujoco_warp/commit/7670775909e8138b372a0e377bc19addd5b12e3b). Only `mujoco_warp/_src/collision_primitive.py` differs from the copied3.15 package; its SHA256 is `539cd69baaf104e604e6e0c06de5cebbc0a4a7b798fc3bf4c800ee94b151b534`. The version metadata remains3.15.0. Original wheel RECORD is provenance and does not verify that patched source item; `distribution_manifest.json` verifies the actual payload separately. The3.15 wheel's complete upstream build commit is not asserted.

From this directory, check the installed default overlay using standard-library Python only:

```bash
python restore_overlay.py --verify-only
```

If the default destination is absent, restore the exact source overlay:

```bash
python restore_overlay.py
```

Default destination: `/home/ethan/.local/share/sai_lab/runtime_overlays/goose_source007_plane315_001`. Existing differing directories are refused rather than overwritten. To inspect a separate recovery copy, use `--destination /ABSOLUTE/NEW_DIRECTORY`; a launcher used with another destination needs a correspondingly reviewed new environment lock. The current local launcher uses the default destination and the external, locked Python/mjlab160/upstream315 stack.

Use the companion `launch_native50_plane315.py` with `launcher_environment_lock_plane315_001.json`; it locks source hashes and actual module origins and sends `WARP_CACHE_PATH=/home/ethan/.cache/sai_lab/goose_source007_plane315_001` to the guarded subprocess. Warp adds its1.15.0 suffix. Cache contents are generated locally and are not distributed or treated as portable binaries.

The first article confirms matched contact geometry with zero time integrations. It does not by itself grant final100-tick GPU precision, training or Owner adoption. Those later receipts must remain independently bound to the final bundle.
