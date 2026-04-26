from __future__ import annotations

import pytest

from compiler.search import _normalize_fts_query


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Pass-through: no operators at all.
        ("foo bar", "foo bar"),
        ("", ""),
        ("   ", "   "),
        ("plain keyword", "plain keyword"),
        # FTS5 booleans are case-sensitive — lowercase variants stay searchable.
        ("foo and bar", "foo and bar"),
        ("And", "And"),
        # Operator characters: escape and wrap as a phrase.
        ("foo-bar", '"foo-bar"'),
        ("yt-dlp", '"yt-dlp"'),
        ("a+b*c", '"a+b*c"'),
        ("(group)", '"(group)"'),
        ("col:value", '"col:value"'),
        # FTS5 also rejects raw `^`, `/`, and `.` outside phrases (verified on SQLite).
        ("^foo", '"^foo"'),
        ("foo/bar", '"foo/bar"'),
        ("path/to/file", '"path/to/file"'),
        ("foo.bar", '"foo.bar"'),
        ("alpha.beta.gamma", '"alpha.beta.gamma"'),
        # Bareword operators (uppercase only): escape and wrap.
        ("foo AND bar", '"foo AND bar"'),
        ("apple OR juice", '"apple OR juice"'),
        ("a NOT b", '"a NOT b"'),
        ("apple NEAR juice", '"apple NEAR juice"'),
        ("AND", '"AND"'),
        # Mixed: operator chars + bareword operator together.
        ("foo-bar AND baz", '"foo-bar AND baz"'),
        # Variable whitespace around bareword operators is still detected.
        ("  foo  AND  bar  ", '"  foo  AND  bar  "'),
        # Balanced phrase passes through untouched (user-driven FTS5 syntax).
        ('"foo bar"', '"foo bar"'),
        ('  "foo bar"  ', '  "foo bar"  '),
        ('"foo AND bar"', '"foo AND bar"'),
        # Unbalanced quotes never satisfy the phrase guard — escape via doubling.
        ('foo"bar', '"foo""bar"'),
        ('"unclosed', '"""unclosed"'),
        ('unclosed"', '"unclosed"""'),
        ('"', '""""'),
        ('""', '""'),
        # Mixed phrase + extra operator: phrase guard rejects (count != 2),
        # crash avoidance wins over preserving boolean semantics.
        ('"foo bar" -baz', '"""foo bar"" -baz"'),
        ('yt-dlp "tutorial"', '"yt-dlp ""tutorial"""'),
    ],
)
def test_normalize_fts_query(query: str, expected: str) -> None:
    assert _normalize_fts_query(query) == expected
