import json
import hashlib
from dataclasses import asdict
from macpkg_catalog.core import Package, validate
from macpkg_catalog.pipeline import generate, load_snapshot

def fixture():
    a=Package("homebrew","formula","wget")
    b=Package("macports","port","wget")
    relation={"source":a.identity,"target":b.identity,"type":"equivalent","confidence":1.0,"matching_method":"curated","evidence":["fixture"],"review_status":"automatic","source_catalog_versions":{"fixture":"1"}}
    return {"packages":[asdict(a),asdict(b)],"relations":[relation]}

def test_artifacts_roundtrip_and_checksums(tmp_path):
    source=tmp_path/"input.json"
    source.write_text(json.dumps(fixture()))
    output=tmp_path/"output"
    generated=generate(source,output)
    assert load_snapshot(output/"catalog.sqlite")==generated
    assert json.loads((output/"v1/relations/homebrew/formula/wget.json").read_text())["relations"]==generated["relations"]
    for line in (output/"checksums.txt").read_text().splitlines():
        digest,path=line.split("  ",1)
        assert hashlib.sha256((output/path).read_bytes()).hexdigest()==digest
    assert "catalog.json" in (output/"index.html").read_text()

def test_load_bare_relations_array(tmp_path):
    source=fixture()
    path=tmp_path/"relations.json"
    path.write_text(json.dumps(source["relations"]))
    assert load_snapshot(path,"relations")["relations"]==source["relations"]

def test_high_confidence_spelling_is_rejected():
    data=fixture()
    data["relations"][0]["matching_method"]="fuzzy"
    assert validate(data["packages"],data["relations"])

def test_negative_even_if_curated():
    data=fixture()
    data["packages"][0]["native_name"]="macs-fan-control"
    data["packages"][1]["native_name"]="qmail-spamcontrol"
    data["relations"][0]["source"]["native_name"]="macs-fan-control"
    data["relations"][0]["target"]["native_name"]="qmail-spamcontrol"
    assert validate(data["packages"],data["relations"])

def test_duplicate_and_missing_endpoint():
    data=fixture()
    assert validate(data["packages"]*2,data["relations"])
    assert validate(data["packages"][:1],data["relations"])
