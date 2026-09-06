from macpkg_catalog.core import Package, validate
def test_negative_example():
    a=Package("macports","port","macs-fan-control"); b=Package("fink","package","qmail-spamcontrol")
    assert validate([a,b],[{"source":a.identity,"target":b.identity,"confidence":.2,"review_status":"needs-review"}])
def test_weak_automatic_rejected():
    a=Package("homebrew","formula","wget"); b=Package("macports","port","wget")
    assert validate([a,b],[{"source":a.identity,"target":b.identity,"confidence":.5,"review_status":"automatic"}])
