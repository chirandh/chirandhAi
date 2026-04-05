"""Validate structured edit proposals and user-supplied text for LaTeX safety."""

import re
from typing import Any

# User-facing fields must not contain LaTeX control sequences (beyond simple escaped chars we inject).
_FORBIDDEN_LATEX = re.compile(
    r"\\(?:begin|end|input|include|usepackage|write|def|let|catcode|openin|openout|"
    r"immediate|special|pdfximage|pdfliteral|inputlineno|everypar|everymath)[\s\{]|"
    r"\$\$|\$|\\\\(?:input|include)",
    re.IGNORECASE,
)

_MAX_FIELD_LEN = 8000
_MAX_EDITS = 50
_ALLOWED_SECTIONS = frozenset(
    {
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "header",
        "other",
    }
)


class EditValidationError(Exception):
    def __init__(self, message: str, code: str = "validation_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def strip_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ord(ch) >= 32 or ch in "\n\t\r")


def assert_safe_plaintext(text: str, *, field: str) -> str:
    if len(text) > _MAX_FIELD_LEN:
        raise EditValidationError(f"{field} exceeds max length ({_MAX_FIELD_LEN})", "field_too_long")
    if _FORBIDDEN_LATEX.search(text):
        raise EditValidationError(f"{field} contains disallowed LaTeX-like content", "unsafe_latex")
    return strip_control_chars(text)


def validate_edit_item(item: dict[str, Any]) -> dict[str, Any]:
    section = item.get("section")
    if not isinstance(section, str) or section not in _ALLOWED_SECTIONS:
        raise EditValidationError("Invalid or missing section", "bad_section")
    before = item.get("before")
    after = item.get("after")
    rationale = item.get("rationale", "")
    if not isinstance(before, str) or not isinstance(after, str):
        raise EditValidationError("before/after must be strings", "bad_edit_shape")
    if not isinstance(rationale, str):
        raise EditValidationError("rationale must be a string", "bad_edit_shape")
    assert_safe_plaintext(before, field="before")
    assert_safe_plaintext(after, field="after")
    if rationale:
        assert_safe_plaintext(rationale, field="rationale")
    return {
        "section": section,
        "before": before,
        "after": after,
        "rationale": rationale,
        "keyword_hits": item.get("keyword_hits") if isinstance(item.get("keyword_hits"), list) else [],
    }


def validate_proposal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    edits = payload.get("edits")
    if not isinstance(edits, list):
        raise EditValidationError("edits must be a list", "bad_edits")
    if len(edits) > _MAX_EDITS:
        raise EditValidationError("Too many edits", "too_many_edits")
    score = payload.get("ats_score")
    if score is not None:
        if not isinstance(score, int) or score < 0 or score > 100:
            raise EditValidationError("ats_score must be int 0-100", "bad_score")
    validated = [validate_edit_item(e) for e in edits if isinstance(e, dict)]
    linkedin_draft = payload.get("linkedin_draft")
    email_draft = payload.get("email_draft")
    out: dict[str, Any] = {
        "edits": validated,
        "ats_score": score,
        "linkedin_draft": None,
        "email_draft": None,
    }
    if isinstance(linkedin_draft, str) and linkedin_draft:
        out["linkedin_draft"] = assert_safe_plaintext(linkedin_draft, field="linkedin_draft")
    if isinstance(email_draft, str) and email_draft:
        out["email_draft"] = assert_safe_plaintext(email_draft, field="email_draft")
    return out


def apply_edits_to_resume(resume_text: str, edits: list[dict[str, Any]], max_ratio: float = 0.35) -> str:
    """Apply minimal edits: replace first occurrence of each `before` with `after`."""
    current = resume_text
    total_delta = 0
    for e in edits:
        before = e["before"]
        after = e["after"]
        if before not in current:
            raise EditValidationError(
                f"Edit target not found in resume: {before[:80]!r}...",
                "edit_not_found",
            )
        current = current.replace(before, after, 1)
        total_delta += abs(len(after) - len(before))
    if len(resume_text) > 0 and total_delta / max(len(resume_text), 1) > max_ratio:
        raise EditValidationError("Combined edits change resume too much", "diff_too_large")
    return current
