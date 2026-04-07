"""Tests for G2P module."""
from speech_feedback.g2p import G2PConverter


def test_basic_conversion():
    g2p = G2PConverter("en-us")
    phones = g2p.convert("hello")
    assert isinstance(phones, list)
    assert len(phones) > 0
    assert all(isinstance(p, str) for p in phones)


def test_empty_input():
    g2p = G2PConverter("en-us")
    assert g2p.convert("") == []
    assert g2p.convert("   ") == []


def test_multi_word():
    g2p = G2PConverter("en-us")
    phones = g2p.convert("hello world")
    assert len(phones) > 4  # should have more phones than single word


def test_to_string():
    g2p = G2PConverter("en-us")
    s = g2p.convert_to_string("hello")
    assert isinstance(s, str)
    assert " " in s or len(s) > 0
