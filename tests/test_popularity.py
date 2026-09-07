from macpkg_catalog.sources import fetch_analytics

def test_analytics_items_are_normalized(monkeypatch):
    monkeypatch.setattr("macpkg_catalog.sources._get", lambda url: {"items":[{"formula":"node","count":"211,317","number":1,"percent":"2.3"}]})
    assert fetch_analytics("install", "30d")["node"] == {"count":211317,"rank":1,"percent":2.3}
