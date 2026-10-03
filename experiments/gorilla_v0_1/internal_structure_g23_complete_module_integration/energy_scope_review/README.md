# G23 terminal scope review

Frozen module `8a61c09d992501eaf34ebbb70bc5dcbc19cd4eeb4f0b5adbe6abae1e1445b742` has 262 pieces, 19 complete Cu nets, and **78 finite-material parts**. `module_negative` and `module_positive` are net00 and net18 themselves: metadata overrides their generic role. They are **not additional duplicated terminal hardware**. Each complete net already unions collector, sensing/BMS connection, HV branch and lug.

Both are included exactly once in the flag-based finite/intersection checker and the 78-row moments/mass inventory. Their masses are 0.074111567092 and 0.073780962319 kg: total 0.147892529411 kg per module, 0.591570117644 kg for four. Independent all78 signed mass is **8.053641819729 kg**; complete upper remains **22.703641819729 kg** including 12.6 kg cell upper and 2.05 kg custom-function upper. No additional terminal mass should be added or subtracted. Lower/nominal cell and complete-module mass remain unknown.

The genuine coverage error is original native signed validation: producer selects generic role and omits these two, reporting 76 passes. This separate unchanged-source validation of both endpoints returns **True**. Independent endpoint-vs-other-finite positive-volume hits (>1e-12 m³): 0, from 65 actual AABB candidates. Original frozen files remain unchanged.

Root scene endpoint inventory: {"a": 8, "b": 8}; exact IDs and hashes are in report.json. Counts are consistent with 4×76 generic finite parts plus 8 endpoint finite parts, not an extra terminal duplication. These predicates do not qualify real polarity, interfaces, dielectric safety, drive/thermal operation, installation, or whole-machine mass/inertia.
