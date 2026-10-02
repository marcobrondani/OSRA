import pytest

from com.brondani.osra import yamlio


def test_only_true_and_false_are_booleans():
    data = yamlio.loads("a: true\nb: false\nc: yes\nd: no\ne: on\nf: off\ng: True\n")
    assert data == {"a": True, "b": False, "c": "yes", "d": "no", "e": "on", "f": "off", "g": True}


def test_dates_and_timestamps_stay_strings():
    data = yamlio.loads("d: 2026-09-30\nt: 2026-09-30T14:00:00Z\n")
    assert data == {"d": "2026-09-30", "t": "2026-09-30T14:00:00Z"}


def test_numbers_still_resolve():
    assert yamlio.loads("a: 1\nb: 1.5\nc: '1.5'\n") == {"a": 1, "b": 1.5, "c": "1.5"}


def test_duplicate_keys_are_rejected_with_the_line():
    with pytest.raises(yamlio.YamlError) as exc:
        yamlio.loads("a: 1\nb: 2\na: 3\n")
    assert "duplicate key 'a'" in str(exc.value)
    assert exc.value.line == 3


def test_object_construction_is_refused():
    with pytest.raises(yamlio.YamlError):
        yamlio.loads("a: !!python/object/apply:os.system ['true']\n")


def test_invalid_utf8_is_reported(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"a: \xff\n")
    with pytest.raises(yamlio.YamlError, match="not valid UTF-8"):
        yamlio.load(path)


def test_pyyaml_safe_loader_is_unchanged():
    import yaml

    assert yaml.safe_load("a: yes") == {"a": True}
