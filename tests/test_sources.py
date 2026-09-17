from macpkg_catalog.sources import normalize_homebrew, normalize_macports, parse_fink_index, parse_fink_info, parse_portindex

def portindex_entry(name, body):
    # Real PortIndex framing: "name charcount" then the body lines, where the
    # count covers the body plus its newlines.
    if isinstance(body, bytes):
        return ("%s %d\n" % (name, len(body.decode("utf-8", "replace")) + 1)).encode() + body + b"\n"
    return "%s %d\n%s\n" % (name, len(body) + 1, body)

def test_parse_local_portindex():
    body="description {Internet file retriever} homepage https://example.test version 1.2 revision 0 portdir net/wget"
    rows=parse_portindex(portindex_entry("wget", body), "PortIndex", "r1", "now")
    assert rows[0]["native_name"] == "wget"
    assert rows[0]["description"] == "Internet file retriever"

def test_parse_portindex_skips_wrapped_description_fragments():
    # A body containing a newline accumulates into one record; the fragment
    # lines must not desync later entries into garbage names (weekly run
    # 35284729163 probed words like "Also" and "DANGER:" as ports).
    wrapped="description {line one\nAlso line two} version 1.24 revision 0 portdir net/wget"
    good="description {curl} version 8.0 revision 0 portdir net/curl"
    text=portindex_entry("wget", wrapped) + portindex_entry("curl", good)
    rows=parse_portindex(text, "PortIndex", "r1", "now")
    assert {row["native_name"] for row in rows} == {"wget", "curl"}
    assert [row["version"] for row in rows if row["native_name"] == "curl"] == ["8.0"]

def test_parse_portindex_recovers_entry_with_stale_byte_count():
    # The shipped file occasionally carries a wrong count (arangodb): the
    # header name is still trustworthy, so the next line becomes its body.
    body="description {stale} version 2.0 revision 1 portdir net/stale"
    rows=parse_portindex("stale 5\n%s\n" % body, "PortIndex", "r1", "now")
    assert rows[0]["native_name"] == "stale"
    assert rows[0]["version"] == "2.0"

def test_parse_portindex_counts_characters_not_bytes():
    # Counts are Tcl string lengths: multibyte characters count once, so
    # verification must run on decoded characters, not raw bytes.
    body="description {caf\u00e9} version 1.0 revision 0 portdir net/cafe"
    rows=parse_portindex(portindex_entry("mport", body.encode("utf-8")), "PortIndex", "r1", "now")
    assert rows[0]["native_name"] == "mport"
    assert rows[0]["version"] == "1.0"

def test_parse_fink_info_relationships():
    row=parse_fink_info("Package: demo\nVersion: 1.2\nProvides: virtual-demo, demo-api\nConflicts: old-demo\nReplaces: demo-old\n", "fink.info", "r1", "now")
    assert row["provides"] == ["virtual-demo", "demo-api"]
    assert row["conflicts"] == ["old-demo"]
    assert row["replaces"] == ["demo-old"]

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
