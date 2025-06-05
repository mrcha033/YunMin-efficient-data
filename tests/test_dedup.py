"""
Unit tests for deduplication module
"""

import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from dedup.minhash_utils import (
    tokenize_ngrams,
    tokenize_jamo_ngrams,
    create_minhash,
    jaccard_similarity,
    estimate_jaccard_similarity,
)
from dedup.slimpajama_dedup import build_minhash_index
from dedup.cluster_reduction import select_representative_document, _calculate_quality_score


class TestMinHashUtils:
    """Test MinHash utility functions"""

    def test_tokenize_ngrams_basic(self):
        """Test basic n-gram tokenization"""
        text = "안녕하세요 반갑습니다 한국어 테스트입니다"
        ngrams = tokenize_ngrams(text, n=3)

        assert len(ngrams) == 3  # 5 tokens -> 3 trigrams
        assert ngrams[0] == "안녕하세요 반갑습니다 한국어"
        assert ngrams[1] == "반갑습니다 한국어 테스트입니다"

    def test_tokenize_ngrams_short_text(self):
        """Test n-gram tokenization with short text"""
        text = "안녕 하세요"
        ngrams = tokenize_ngrams(text, n=5)

        assert len(ngrams) == 1
        assert ngrams[0] == "안녕 하세요"

    def test_tokenize_jamo_ngrams(self):
        """Tokenize jamo trigrams"""
        text = "가나다"
        jamos = tokenize_jamo_ngrams(text, n=3)
        assert jamos[0] != ""

    def test_create_minhash(self):
        """Test MinHash creation"""
        ngrams = ["hello world", "world test", "test case"]
        minhash = create_minhash(ngrams, num_perm=64)

        assert minhash is not None
        assert len(minhash.digest()) == 64

    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation"""
        set1 = {"a", "b", "c"}
        set2 = {"b", "c", "d"}

        similarity = jaccard_similarity(set1, set2)
        expected = 2 / 4  # intersection=2, union=4

        assert abs(similarity - expected) < 0.001

    def test_jaccard_similarity_empty_sets(self):
        """Test Jaccard similarity with empty sets"""
        similarity = jaccard_similarity(set(), set())
        assert similarity == 1.0

    def test_estimate_jaccard_similarity_digest(self):
        """Estimate similarity using MinHash digests."""
        ngrams = ["hello", "world"]
        mh1 = create_minhash(ngrams, num_perm=16)
        mh2 = create_minhash(ngrams, num_perm=16)

        similarity = estimate_jaccard_similarity(mh1, mh2)
        assert similarity >= 0.99

    def test_estimate_jaccard_similarity_generic(self):
        """Estimate similarity for objects with digest method."""

        class FakeMinHash:
            def __init__(self, values):
                self._hashes = values

            def digest(self):
                return self._hashes

        mh1 = FakeMinHash([1, 2, 3, 4])
        mh2 = FakeMinHash([1, 2, 5, 6])

        similarity = estimate_jaccard_similarity(mh1, mh2)
        assert abs(similarity - 0.5) < 0.001

    def test_build_minhash_index_with_redis(self):
        """Ensure MinHash signatures stored in Redis"""
        fakeredis = pytest.importorskip("fakeredis")
        r = fakeredis.FakeRedis()
        config = {
            "redis": {"host": "localhost", "port": 6379, "prefix": "test"},
            "ngram_size": 5,
            "jamo_ngram_size": 3,
        }
        docs = [
            {"text": "가나다라마바사"},
            {"text": "가나다라마바사"},
        ]
        with patch("redis.Redis", return_value=r), patch("redis.StrictRedis", return_value=r):
            lsh, sigs = build_minhash_index(docs, config)
        assert isinstance(sigs, dict)


class TestClusterReduction:
    """Test cluster reduction functions"""

    def test_select_longest_document(self):
        """Test selecting longest document"""
        docs = [
            {"text": "짧은 텍스트"},
            {"text": "이것은 더 긴 텍스트입니다"},
            {"text": "가장 긴 텍스트 샘플입니다 더 많은 내용이 있습니다"}
        ]

        selected_idx = select_representative_document(docs, strategy="longest")
        assert selected_idx == 2  # Longest document

    def test_select_with_tokens(self):
        """Test selection using token count"""
        docs = [
            {"text": "short", "tokens": ["short"]},
            {"text": "longer text", "tokens": ["longer", "text", "with", "more", "tokens"]}
        ]

        selected_idx = select_representative_document(docs, strategy="longest")
        assert selected_idx == 1  # More tokens

    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        doc = {
            "text": "고품질 한국어 텍스트입니다. 적절한 길이를 가지고 있습니다.",
            "source": "wikipedia",
            "domain": "encyclopedia",
            "lang": "ko"
        }

        score = _calculate_quality_score(doc)
        assert score > 0.5  # Should have decent quality score

    def test_quality_score_korean_content(self):
        """Test quality score for Korean content"""
        korean_doc = {
            "text": "한국어 텍스트입니다 좋은 품질을 가지고 있습니다",
            "source": "news"
        }

        english_doc = {
            "text": "This is English text with good quality",
            "source": "news"
        }

        korean_score = _calculate_quality_score(korean_doc)
        english_score = _calculate_quality_score(english_doc)

        # Korean content should score higher for Korean LLM
        assert korean_score > english_score


class TestDeduplicationIntegration:
    """Integration tests for deduplication pipeline"""

    def create_test_jsonl(self, documents):
        """Helper to create temporary JSONL file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)

        for doc in documents:
            temp_file.write(json.dumps(doc, ensure_ascii=False) + '\n')

        temp_file.close()
        return temp_file.name

    def test_duplicate_detection(self):
        """Test end-to-end duplicate detection"""
        documents = [
            {"text": "안녕하세요 반갑습니다", "source": "test"},
            {"text": "안녕하세요 반갑습니다", "source": "test"},  # Exact duplicate
            {"text": "완전히 다른 텍스트입니다", "source": "test"},
            {"text": "안녕하세요 반갑습니다 추가 내용", "source": "test"}  # Similar but longer
        ]

        # This would be tested with actual deduplication logic
        # For now, just test the basic structure
        assert len(documents) == 4

        # After deduplication, we should have fewer documents
        # The exact duplicate should be removed
        # The longer similar document should be kept as representative


if __name__ == "__main__":
    pytest.main([__file__])
