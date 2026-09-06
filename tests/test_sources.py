from macpkg_catalog.sources import normalize_homebrew, normalize_macports, parse_fink_index

def test_cask_identity_and_version():
    p=normalize_homebrew([{"token":"docker-desktop","name":["Docker Desktop"],"version":"4.0","old_tokens":["docker"]}],"cask","sha","date")[0]
    assert p["native_name"]=="docker-desktop"
    assert p["version"]=="4.0"
    assert p["historical_names"]==["docker"]
    assert p["aliases"]==[]

def test_macports_case_and_replacement():
    p=normalize_macports([{"name":"2Pong","version":"1","replaced_by":"pong"}],"sha","date")[0]
    assert p["native_name"]=="2Pong"
    assert p["renamed_by"]==["pong"]

def test_fink_control_metadata():
    text="Package: wget\nVersion: 1.2-3\nDescription: Download tool\n continuation\nProvides: downloader (>= 1), fetch\nHomepage: https://example.org/wget\n"
    p=parse_fink_index(text,"fixture","sha","date")[0]
    assert p["version"]=="1.2"
    assert p["revision"]=="3"
    assert p["provides"]==["downloader","fetch"]
    assert "continuation" in p["description"]
