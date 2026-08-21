import json, sys
import pathlib as _pl, sys as _sys
# The repo root, so fetch_all_data imports and the data paths resolve
# wherever this is run from. Derived rather than written down: these tests
# used to carry one developer's absolute path and ran nowhere else.
REPO = _pl.Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(REPO))
import fetch_all_data as F


def boom():
    raise RuntimeError("simulated upstream outage")


F.SOURCES = dict(F.SOURCES)
F.SOURCES["ptal"] = boom

# Write the manifest somewhere disposable.
#
# This test makes a source fail on purpose and then runs the real main(),
# which ends by writing the real data/meta/manifest.json. That file is
# committed and the public methodology page reads it, so running this test
# left the site reporting PTAL as failed with "simulated upstream outage" as
# the reason, against data that was present and correct. Under .cache/
# rather than the system temp directory, because write_manifest logs the
# path relative to the repo root and raises on anything outside it.
_tmp = REPO / ".cache" / "test_manifest_ptal.json"
_tmp.parent.mkdir(parents=True, exist_ok=True)
_tmp.unlink(missing_ok=True)
F.MANIFEST_PATH = _tmp

sys.argv = ["x", "--only", "imd", "ptal"]
F.main()

m = json.load(open(_tmp))
print("\n--- manifest ---")
print("last_run:", m["last_run"])
print("keys:", sorted(m["sources"]))
for k, v in sorted(m["sources"].items()):
    print(f"  {k:6} status={v['status']:7} rows={v['rows_written']:>7,} "
          f"path={v['output_path'] or '-'} err={v['error'][:40]}")
failed = sorted(k for k, v in m["sources"].items() if v.get("status") == "failed")
print("failing sources the workflow would report:", failed)
