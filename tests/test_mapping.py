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
