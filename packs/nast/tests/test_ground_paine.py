from packs.nast.brain.ground_paine import chunk_text, parse_grounded

def test_chunk_text_covers_and_bounds():
    text = "abcdefghij" * 100   # 1000 chars
    chunks = chunk_text(text, size=300, overlap=50)
    assert all(len(c) <= 300 for c in chunks)
    assert len(chunks) >= 4
    assert "".join(text[i] for i in range(0, 300)) in chunks[0] or chunks[0] == text[:300]

def test_parse_grounded_valid():
    raw = '```json\n{"event":"e","allegory_rationale":"r","image_prompt":"p"}\n```'
    assert parse_grounded(raw) == {"event": "e", "allegory_rationale": "r", "image_prompt": "p"}

def test_parse_grounded_rejects_empty_or_partial():
    assert parse_grounded("{}") is None
    assert parse_grounded('{"event":"e"}') is None
    assert parse_grounded("no json here") is None
