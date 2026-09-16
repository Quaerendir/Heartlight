"""heartlight.bas against the two-letter line codes the magazine printed for it
("Kody do Heartlighta i COS-u", TA 2/91, 2_91_kody.html), computed with tools/line_codes.py."""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import heartlight_extract  # noqa: E402
from line_codes import line_code  # noqa: E402

# Two entries of the printed table do not match the listing: 1060 is printed as "10", an
# obvious rendering of "IO" (the computed code) with digits; 11920 is printed KC where the
# listing gives KD, while the line's own hex checksum passes and no single-character
# variant of the line with a valid checksum yields KC, so the table entry is taken as a typo.
KNOWN = {1060: ('10', 'IO'), 11920: ('KC', 'KD')}


def printed_codes() -> dict[int, set[str]]:
    text = (ROOT / '2_91_kody.html').read_bytes().decode('iso-8859-2')
    text = html.unescape(re.sub(r'<[^>]+>', '', text))
    codes: dict[int, set[str]] = {}
    for code, no in re.findall(r'\b([A-Z0-9]{2})\s+(\d+)\b', text):
        codes.setdefault(int(no), set()).add(code)          # COS and Heartlight share line numbers
    return codes


def test_every_line_has_a_printed_code_and_matches():
    codes = printed_codes()
    lines = heartlight_extract.logical_lines((ROOT / 'heartlight.bas').read_text(encoding='utf-8'))
    assert len(lines) == 313
    mismatches = {}
    for no, body in lines:
        got = line_code(f'{no} {body}'.encode('latin-1'))
        assert no in codes, f'line {no} has no printed code'
        if got not in codes[no]:
            mismatches[no] = (got, codes[no])
    assert set(mismatches) == set(KNOWN)
    for no, (printed, computed) in KNOWN.items():
        assert printed in codes[no] and mismatches[no][0] == computed
