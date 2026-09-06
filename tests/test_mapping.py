from dataclasses import asdict
from macpkg_catalog.core import Package
from macpkg_catalog.mapping import match

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
