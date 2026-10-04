"""Package only the frozen Goose M0 entry; verify every extracted input."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ROBOT = "robots/Goose_V0.1"
ENTRY = f"{ROBOT}/configs/task_proxy_11_v1_entry.json"
CONTRACT = f"{ROBOT}/configs/task_proxy_11_v1_contract.json"
MODEL = f"{ROBOT}/models/task_proxy_11_v1/robot.xml"
PLANT = f"{ROBOT}/models/task_proxy_11_v1/native_plant.json"
ACCEPTANCE = f"{ROBOT}/evidence/task_proxy_11_v1_acceptance.json"
FILTER_POLICY = f"{ROBOT}/configs/task_proxy_11_v1_collision_filter.json"
FILTER_ACCEPTANCE = f"{ROBOT}/evidence/task_proxy_11_v1_collision_filter_acceptance.json"
MANIFEST = "handoff_manifest.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_binding(root):
    entry = json.loads((root / ENTRY).read_text())
    contract = json.loads((root / CONTRACT).read_text())
    report = json.loads((root / ACCEPTANCE).read_text())
    if not (entry["candidate_id"] == contract["candidate"] == report["candidate_id"]
            == "goose_task_proxy_11_v1"):
        raise ValueError("Candidate identity mismatch")
    if not (entry["engineering_entry_qualified"] and report["engineering_entry_pass"]):
        raise ValueError("M0 entry has not passed")
    if entry["full_task_success_claim"] or report["full_task_success_claim"]:
        raise ValueError("This archive cannot claim learned task qualification")
    for name, path in (("model", MODEL), ("contract", CONTRACT), ("plant", PLANT)):
        if report[name + "_sha256"] != digest((root / path).read_bytes()):
            raise ValueError("Acceptance identity mismatch: " + name)
    for name, sha in contract["asset_sha256"].items():
        if sha != digest((root / Path(MODEL).parent / name).read_bytes()):
            raise ValueError("Collision asset identity mismatch: " + name)
    for name, sha in contract["source_module_sha256"].items():
        if sha != digest((root / "src/sai_agent/goose" / name).read_bytes()):
            raise ValueError("Runtime identity mismatch: " + name)
    filters = json.loads((root / FILTER_ACCEPTANCE).read_text())
    for key, path in (("model", MODEL), ("contract", CONTRACT),
                      ("native_plant", PLANT), ("collision_policy", FILTER_POLICY),
                      ("evaluator", "scripts/evaluation/check_goose_collision_filters.py")):
        if filters[key + "_sha256"] != digest((root / path).read_bytes()):
            raise ValueError("Collision filter identity mismatch: " + key)
    for path, expected in filters["receiver_source_sha256"].items():
        if expected != digest((root / path).read_bytes()):
            raise ValueError("Collision receiver changed: " + path)
    if filters["native_binary_sha256"] != report["environment"]["native_binary_sha256"]:
        raise ValueError("Filter and dynamics probes used different receivers")
    if set(filters["results"]) != {"source", "standalone_rapier"} or not all(
            r["passed"] and r["total_fixtures"] == 97 for r in filters["results"].values()):
        raise ValueError("Both source and target collision filters must pass")


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text())
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Unsafe package path: " + name)
        data = path.read_bytes()
        if len(data) != expected["bytes"] or digest(data) != expected["sha256"]:
            raise ValueError("Package file changed: " + name)
    check_binding(root)
    return {"candidate_id": manifest["candidate_id"],
            "verified_files": len(manifest["files"]),
            "input_sha256_verified": True, "engineering_scope": "M0 only"}


def package(out):
    check_binding(ROOT)
    selected = [ENTRY, CONTRACT, ACCEPTANCE, FILTER_POLICY, FILTER_ACCEPTANCE,
                "LICENSE", "THIRD_PARTY_NOTICES.md",
                f"{ROBOT}/evidence/task_proxy_11_v1_physical_identity.json",
                f"{ROBOT}/evidence/task_proxy_11_v1_rejected_variants.json",
                f"{ROBOT}/evidence/task_action_domain_v1.json",
                f"{ROBOT}/evidence/microduck_game_collision_baseline_v1.json",
                f"{ROBOT}/design/task_proxy_11_v1.md",
                f"{ROBOT}/images/task_proxy_11_v1_colliders.png",
                "src/sai_agent/__init__.py", "src/sai_agent/goose/__init__.py",
                "tests/test_goose_task_proxy.py",
                "tests/test_goose_collision_filters.py",
                "scripts/evaluation/check_goose_task_proxy.py",
                "scripts/evaluation/check_goose_collision_filters.py",
                "scripts/models/build_goose_task_proxy.py",
                "scripts/models/render_goose_task_proxy.py",
                "scripts/models/package_goose_task_proxy.py"]
    for name in ("stage_one_gravity", "task_goal", "task_proxy_runtime",
                 "convex_support", "task_collision"):
        selected.append(f"src/sai_agent/goose/{name}.py")
    for directory in (f"{ROBOT}/models/task_proxy_11_v1",
                      f"{ROBOT}/source/task_proxy_11_v1",
                      "integrations/bevy/goose_task_proxy",
                      "third_party/rapier3d_goose_contact"):
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or any(p in ("target", "__pycache__", ".git")
                                         for p in path.relative_to(ROOT).parts):
                continue
            selected.append(path.relative_to(ROOT).as_posix())
    contents = {name: (ROOT / name).read_bytes() for name in sorted(set(selected))}
    contents["README.md"] = (
        "Unique entry: [Goose task proxy](" + ENTRY + ").\n\n"
        + (ROOT / "integrations/bevy/goose_task_proxy/README.md").read_text()
    ).encode()
    manifest = dict(schema="goose_task_proxy_portable_handoff_v1",
                    candidate_id="goose_task_proxy_11_v1", unique_entry=ENTRY,
                    scope="Verified M0 engineering entry; no learned task or hardware release",
                    hardware_source_files_included=False,
                    files={name: dict(sha256=digest(data), bytes=len(data))
                           for name, data in sorted(contents.items())})
    contents[MANIFEST] = (json.dumps(manifest, indent=2) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return dict(zip=str(out.resolve()), sha256=digest(out.read_bytes()),
                bytes=out.stat().st_size, packaged_files=len(contents),
                manifest_does_not_hash_itself=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/Goose_V0.1/goose_task_proxy_11_v1.zip")
    parser.add_argument("--verify", type=Path, help="Verify an extracted package root")
    args = parser.parse_args()
    print(json.dumps(verify(args.verify) if args.verify else package(args.out), indent=2))


if __name__ == "__main__":
    main()
