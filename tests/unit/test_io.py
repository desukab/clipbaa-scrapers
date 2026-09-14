from scrapers.io import (
    atomic_write_json,
    atomic_write_text,
    ensure_dir,
    load_json,
    new_run_id,
    write_manifest,
)


def test_run_id_format():
    rid = new_run_id()
    assert len(rid) == len("20260914T123456Z")
    assert rid.endswith("Z")


def test_atomic_json_roundtrip(tmp_path):
    p = tmp_path / "a" / "b" / "data.json"
    atomic_write_json(p, {"x": [1, 2], "unicode": "₹"})
    data = load_json(p)
    assert data == {"x": [1, 2], "unicode": "₹"}
    assert not list(p.parent.glob(".tmp-*"))


def test_load_json_missing_returns_default(tmp_path):
    assert load_json(tmp_path / "nope.json", []) == []


def test_manifest_created(tmp_path):
    out = tmp_path / "data"
    path = write_manifest(str(out), "run-1", {"status": "ok"})
    assert path.exists()
    assert load_json(path)["status"] == "ok"


def test_failed_write_leaves_no_partial(tmp_path):
    p = tmp_path / "out.json"
    atomic_write_text(p, "ok")
    try:
        atomic_write_json(p, object())
    except Exception:
        pass
    with open(p, encoding="utf-8") as fh:
        assert fh.read() == "ok"