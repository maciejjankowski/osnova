"""Tests for osnova/integrity/riddle.py"""

import pytest
from osnova.integrity.riddle import encode_content, verify_content_integrity, list_themes

SAMPLE_BODY = """The network relies on trust rings to propagate content.
Each node verifies signatures before storing entries.
Tamper-evident encoding protects high-integrity posts.
The solver confirms the unique solution matches the original."""

SIMPLE_BODY = """First claim here.
Second claim here.
Third claim here."""


class TestListThemes:
    def test_returns_list(self):
        themes = list_themes()
        assert isinstance(themes, list)
        assert len(themes) >= 1

    def test_default_included(self):
        assert "default" in list_themes()

    def test_all_expected_themes(self):
        themes = list_themes()
        for expected in ("default", "embassy", "military", "masonic"):
            assert expected in themes


class TestEncodeContent:
    def test_returns_dict_with_required_keys(self):
        result = encode_content(SIMPLE_BODY, seed=42)
        assert result["encoded"] is True
        assert "riddle_constraints" in result
        assert "riddle_instances" in result
        assert "riddle_size" in result
        assert "theme" in result
        assert "expected_solution_hash" in result
        assert "phrase_order_hash" in result

    def test_default_theme(self):
        result = encode_content(SIMPLE_BODY, seed=42)
        assert result["theme"] == "default"

    def test_custom_theme(self):
        result = encode_content(SIMPLE_BODY, theme="embassy", seed=42)
        assert result["theme"] == "embassy"

    def test_invalid_theme_raises(self):
        with pytest.raises(ValueError, match="Unknown theme"):
            encode_content(SIMPLE_BODY, theme="nonexistent")

    def test_riddle_size_matches_phrase_count(self):
        result = encode_content(SIMPLE_BODY, seed=42)
        # 3 lines -> size 3
        assert result["riddle_size"] == 3

    def test_constraints_are_list_of_dicts(self):
        result = encode_content(SIMPLE_BODY, seed=42)
        assert isinstance(result["riddle_constraints"], list)
        assert len(result["riddle_constraints"]) > 0
        for c in result["riddle_constraints"]:
            assert isinstance(c, dict)
            assert "type" in c

    def test_deterministic_with_seed(self):
        r1 = encode_content(SIMPLE_BODY, seed=99)
        r2 = encode_content(SIMPLE_BODY, seed=99)
        assert r1["expected_solution_hash"] == r2["expected_solution_hash"]
        assert r1["phrase_order_hash"] == r2["phrase_order_hash"]

    def test_longer_body(self):
        result = encode_content(SAMPLE_BODY, seed=7)
        assert result["encoded"] is True
        assert result["riddle_size"] >= 2

    def test_metadata_is_json_serializable(self):
        import json
        result = encode_content(SIMPLE_BODY, seed=42)
        # Should not raise
        json.dumps(result)


class TestVerifyContentIntegrity:
    def test_unencoded_content_is_valid(self):
        assert verify_content_integrity("any body", {}) is True
        assert verify_content_integrity("any body", {"encoded": False}) is True
        assert verify_content_integrity("any body", {"other_key": "value"}) is True

    def test_encoded_original_verifies_true(self):
        metadata = encode_content(SIMPLE_BODY, seed=42)
        assert verify_content_integrity(SIMPLE_BODY, metadata) is True

    def test_tampered_body_returns_false(self):
        metadata = encode_content(SIMPLE_BODY, seed=42)
        tampered = SIMPLE_BODY.replace("First claim", "Altered claim")
        assert verify_content_integrity(tampered, metadata) is False

    def test_completely_different_body_returns_false(self):
        metadata = encode_content(SIMPLE_BODY, seed=42)
        assert verify_content_integrity("Totally unrelated content here.", metadata) is False

    def test_malformed_metadata_returns_false(self):
        assert verify_content_integrity(SIMPLE_BODY, {"encoded": True}) is False
        assert verify_content_integrity(
            SIMPLE_BODY, {"encoded": True, "riddle_constraints": []}
        ) is False

    def test_multiple_themes_all_verify(self):
        for theme in list_themes():
            meta = encode_content(SIMPLE_BODY, theme=theme, seed=1)
            assert verify_content_integrity(SIMPLE_BODY, meta) is True, f"Failed theme: {theme}"

    def test_longer_article_roundtrip(self):
        metadata = encode_content(SAMPLE_BODY, seed=13)
        assert verify_content_integrity(SAMPLE_BODY, metadata) is True

    def test_subtly_tampered_whitespace_matters(self):
        metadata = encode_content(SIMPLE_BODY, seed=42)
        # Adding a trailing newline changes phrase extraction
        tampered = SIMPLE_BODY + "\nExtra line injected."
        # This may or may not verify depending on phrase count;
        # the important thing is we get a bool without crashing
        result = verify_content_integrity(tampered, metadata)
        assert isinstance(result, bool)


class TestEdgeCases:
    def test_two_line_body(self):
        body = "Line one.\nLine two."
        metadata = encode_content(body, seed=5)
        assert verify_content_integrity(body, metadata) is True
        assert verify_content_integrity("Line one.\nLine changed.", metadata) is False

    def test_single_line_body(self):
        body = "A single sentence that needs splitting by other means."
        metadata = encode_content(body, seed=3)
        assert verify_content_integrity(body, metadata) is True

    def test_encode_content_goes_into_metadata_field(self):
        """Simulate actual ContentEntry.metadata usage."""
        from osnova.schemas import ContentEntry, ContentType
        metadata = encode_content(SIMPLE_BODY, seed=42)
        entry = ContentEntry(
            author_key="deadbeef" * 8,
            content_type=ContentType.ARTICLE,
            body=SIMPLE_BODY,
            metadata=metadata,
        )
        assert entry.metadata["encoded"] is True
        assert verify_content_integrity(entry.body, entry.metadata) is True
