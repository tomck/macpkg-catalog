from dataclasses import asdict
from macpkg_catalog.core import Package
from macpkg_catalog.mapping import match, near_hit

def test_exact_name_needs_review():
    packages=[asdict(Package("homebrew","formula","wget")),asdict(Package("macports","port","wget"))]
    assert all(r["review_status"]=="needs-review" for r in match(packages,{"test":"1"}))

def test_upstream_identity_and_ambiguity():
    packages=[asdict(Package("homebrew","formula","one",homepage="https://github.com/owner/repo")),asdict(Package("macports","port","two",homepage="https://github.com/owner/repo"))]
    assert all(r["review_status"]=="automatic" for r in match(packages,{"test":"1"}))
    packages.append(asdict(Package("macports","port","two-devel",homepage="https://github.com/owner/repo")))
    relations=match(packages,{"test":"1"})
    assert all(r["review_status"]=="needs-review" for r in relations if r["source"]["manager"]=="homebrew")

def test_negative_omitted():
    packages=[asdict(Package("homebrew","cask","macs-fan-control")),asdict(Package("macports","port","qmail-spamcontrol"))]
    assert match(packages,{"test":"1"})==[]

def test_near_hit_is_review_only_and_capped():
    source={"manager":"homebrew","package_type":"formula","native_name":"ansible@12"}
    target={"manager":"macports","package_type":"port","native_name":"py313-ansible"}
    relation=near_hit(source,target,[{"kind":"version-family","value":"ansible"}],"12.0","13.0")
    assert relation["review_status"] == "needs-review"
    assert relation["confidence"] == 0.78
    assert relation["matching_method"] == "version-family"

def test_match_emits_version_family_near_hit():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"ansible@12","version":"12.0"},
        {"manager":"macports","package_type":"port","native_name":"py313-ansible","version":"13.0"},
    ]
    relations=match(packages,{"fixture":"1"})
    assert relations[0]["matching_method"] == "version-family"
    assert relations[0]["review_status"] == "needs-review"

def test_python_version_family_matches_different_manager_naming():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"python@3.14","version":"3.14.0"},
        {"manager":"macports","package_type":"port","native_name":"python314","version":"3.14.1"},
    ]
    relations=match(packages,{"fixture":"1"})
    relations=[r for r in relations if r["source"]["manager"]=="homebrew"]
    assert len(relations)==1
    assert relations[0]["matching_method"] == "version-family"
    assert relations[0]["review_status"] == "needs-review"
    assert relations[0]["confidence"] == 0.94
    assert {e["kind"] for e in relations[0]["evidence"]} == {"version-family", "version-semantic"}

def test_python_version_family_does_not_cross_versions_or_legacy_fink():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"python@3.14"},
        {"manager":"homebrew","package_type":"formula","native_name":"python@3.13"},
        {"manager":"macports","package_type":"port","native_name":"python314"},
        {"manager":"macports","package_type":"port","native_name":"python313"},
        {"manager":"fink","package_type":"package","native_name":"python24"},
    ]
    relations=match(packages,{"fixture":"1"})
    pairs={(r["source"]["native_name"],r["target"]["native_name"]) for r in relations}
    assert ("python@3.14","python314") in pairs
    assert ("python@3.13","python313") in pairs
    assert not any("python24" in pair for pair in pairs)
    assert ("python@3.14","python313") not in pairs

def test_python_matching_uses_matching_description_version_as_extra_evidence():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"python@3.14","description":"Python 3.14 runtime"},
        {"manager":"macports","package_type":"port","native_name":"python314","description":"Python 3.14 interpreter"},
    ]
    relation=[r for r in match(packages,{"fixture":"1"}) if r["source"]["manager"]=="homebrew"][0]
    assert relation["confidence"] == 0.97
    assert {e["kind"] for e in relation["evidence"]} == {"version-family", "version-semantic", "description-version"}
    assert relation["review_status"] == "needs-review"

def test_version_anchored_node_tracks_current_major():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"node","version":"26.10.0"},
        {"manager":"macports","package_type":"port","native_name":"nodejs24","version":"24.19.0"},
        {"manager":"macports","package_type":"port","native_name":"nodejs26","version":"26.8.1"},
    ]
    relations=[r for r in match(packages,{"fixture":"1"}) if r["source"]["manager"]=="homebrew"]
    pairs={(r["target"]["native_name"],r["confidence"],r["review_status"]) for r in relations}
    assert ("nodejs26",0.78,"needs-review") in pairs
    assert not any(name=="nodejs24" for name,_,_ in pairs)
    anchored=[r for r in relations if r["target"]["native_name"]=="nodejs26"]
    assert anchored[0]["matching_method"] == "version-family"
    assert {e["kind"] for e in anchored[0]["evidence"]} == {"version-anchored"}

def test_version_anchored_reverse_direction():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"node","version":"24.19.0"},
        {"manager":"macports","package_type":"port","native_name":"nodejs24","version":"24.19.0"},
    ]
    relations=[r for r in match(packages,{"fixture":"1"}) if r["source"]["manager"]=="macports"]
    assert len(relations)==1
    assert relations[0]["target"]["native_name"]=="node"
    assert relations[0]["review_status"]=="needs-review"

def test_version_anchored_needs_versions_and_stays_single():
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"wget","version":"1.25"},
        {"manager":"macports","package_type":"port","native_name":"wget","version":"1.25"},
    ]
    relations=match(packages,{"fixture":"1"})
    assert len(relations)==2  # exact-name both directions, nothing anchored
    assert all(r["matching_method"]=="exact-name" for r in relations)
    packages=[
        {"manager":"homebrew","package_type":"formula","native_name":"node"},
        {"manager":"macports","package_type":"port","native_name":"nodejs26"},
    ]
    assert match(packages,{"fixture":"1"})==[]
