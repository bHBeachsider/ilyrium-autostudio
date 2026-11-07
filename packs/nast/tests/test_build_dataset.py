from packs.nast.brain.build_dataset import parse_pair, to_message_row, SYSTEM

def test_parse_pair_strips_fences_and_validates():
    raw = '```json\n{"allegory_rationale":"r","image_prompt":"p"}\n```'
    pair = parse_pair(raw)
    assert pair == {"allegory_rationale": "r", "image_prompt": "p"}

def test_parse_pair_rejects_missing_keys():
    assert parse_pair('{"allegory_rationale":"r"}') is None
    assert parse_pair('not json') is None

def test_to_message_row_shape():
    row = to_message_row("Event: X happens.", {"allegory_rationale": "r", "image_prompt": "p"})
    msgs = row["messages"]
    assert msgs[0] == {"role": "system", "content": SYSTEM}
    assert msgs[1]["role"] == "user" and "X happens" in msgs[1]["content"]
    import json as _j
    assert _j.loads(msgs[2]["content"]) == {"allegory_rationale": "r", "image_prompt": "p"}
