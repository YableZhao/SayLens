"""Tests for phoneme comparator."""
from speech_feedback.comparator import PhonemeComparator


def test_exact_match():
    comp = PhonemeComparator()
    result = comp.compare(["h", "ə", "l", "oʊ"], ["h", "ə", "l", "oʊ"])
    assert all(r.match_type == "correct" for r in result)
    assert comp.accuracy(result) == 1.0


def test_substitution():
    comp = PhonemeComparator()
    result = comp.compare(["h", "ə", "l", "oʊ"], ["h", "ɛ", "l", "oʊ"])
    match_types = [r.match_type for r in result]
    assert "substitution" in match_types
    assert "correct" in match_types
    assert comp.accuracy(result) == 0.75


def test_deletion():
    comp = PhonemeComparator()
    result = comp.compare(["h", "ə", "l", "oʊ"], ["h", "l", "oʊ"])
    match_types = [r.match_type for r in result]
    assert "deletion" in match_types


def test_insertion():
    comp = PhonemeComparator()
    result = comp.compare(["h", "l"], ["h", "ə", "l"])
    match_types = [r.match_type for r in result]
    assert "insertion" in match_types


def test_empty_sequences():
    comp = PhonemeComparator()
    assert comp.accuracy([]) == 0.0
