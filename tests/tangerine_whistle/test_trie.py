import json
from typing import Any

from ethereum.tangerine_whistle.fork_types import Bytes
from ethereum.tangerine_whistle.trie import Trie, root, trie_set
from ethereum.utils.hexadecimal import (
    has_hex_prefix,
    hex_to_bytes,
    remove_hex_prefix,
)


def to_bytes(data: str) -> Bytes:
    if data is None:
        return b""
    return hex_to_bytes(data) if has_hex_prefix(data) else data.encode()


def test_trie_secure_hex() -> None:
    tests = load_tests("hex_encoded_securetrie_test.json")

    for (name, test) in tests.items():
        st: Trie[Bytes, Bytes] = Trie(secured=True, default=b"")
        for (k, v) in test.get("in").items():
            trie_set(st, to_bytes(k), to_bytes(v))
        result = root(st)
        expected = remove_hex_prefix(test.get("root"))
        assert result.hex() == expected, f"test {name} failed"


def test_trie_secure() -> None:
    tests = load_tests("trietest_secureTrie.json")

    for (name, test) in tests.items():
        st: Trie[Bytes, Bytes] = Trie(secured=True, default=b"")
        for t in test.get("in"):
            trie_set(st, to_bytes(t[0]), to_bytes(t[1]))
        result = root(st)
        expected = remove_hex_prefix(test.get("root"))
        assert result.hex() == expected, f"test {name} failed"


def test_trie_secure_any_order() -> None:
    tests = load_tests("trieanyorder_secureTrie.json")

    for (name, test) in tests.items():
        st: Trie[Bytes, Bytes] = Trie(secured=True, default=b"")
        for (k, v) in test.get("in").items():
            trie_set(st, to_bytes(k), to_bytes(v))
        result = root(st)
        expected = remove_hex_prefix(test.get("root"))
        assert result.hex() == expected, f"test {name} failed"


def test_trie() -> None:
    tests = load_tests("trietest.json")

    for (name, test) in tests.items():
        st: Trie[Bytes, Bytes] = Trie(secured=False, default=b"")
        for t in test.get("in"):
            trie_set(st, to_bytes(t[0]), to_bytes(t[1]))
        result = root(st)
        expected = remove_hex_prefix(test.get("root"))
        assert result.hex() == expected, f"test {name} failed"


def test_trie_any_order() -> None:
    tests = load_tests("trieanyorder.json")

    for (name, test) in tests.items():
        st: Trie[Bytes, Bytes] = Trie(secured=False, default=b"")
        for (k, v) in test.get("in").items():
            trie_set(st, to_bytes(k), to_bytes(v))
        result = root(st)
        expected = remove_hex_prefix(test.get("root"))
        assert result.hex() == expected, f"test {name} failed"


def load_tests(path: str) -> Any:
    with open(f"tests/fixtures/TrieTests/{path}") as f:
        tests = json.load(f)

    return tests
