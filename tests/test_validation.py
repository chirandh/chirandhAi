import pytest

from app.services.edit_validation import (
    EditValidationError,
    assert_safe_plaintext,
    validate_proposal_payload,
)


def test_safe_plaintext_blocks_latex():
    with pytest.raises(EditValidationError):
        assert_safe_plaintext(r"\input{evil}", field="x")


def test_validate_proposal_ok():
    payload = {
        "edits": [
            {
                "section": "skills",
                "before": "Python",
                "after": "Python (FastAPI)",
                "rationale": "keyword",
                "keyword_hits": ["FastAPI"],
            }
        ],
        "ats_score": 72,
    }
    out = validate_proposal_payload(payload)
    assert out["ats_score"] == 72
    assert len(out["edits"]) == 1


def test_validate_proposal_bad_section():
    with pytest.raises(EditValidationError):
        validate_proposal_payload({"edits": [{"section": "nope", "before": "a", "after": "b"}]})
