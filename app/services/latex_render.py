"""Jinja2 LaTeX template with allowlisted structure only."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.edit_validation import assert_safe_plaintext

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        variable_start_string="<<",
        variable_end_string=">>",
        block_start_string="<%",
        block_end_string="%>",
    )


def render_resume_latex(body_text: str) -> str:
    """Render fixed LaTeX template; body is escaped for LaTeX special chars."""
    safe = assert_safe_plaintext(body_text, field="resume_body")
    escaped = (
        safe.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )
    # Preserve paragraph breaks as LaTeX line breaks
    latex_body = escaped.replace("\n\n", "\n\n\\medskip\n\n").replace("\n", "\\\\\n")
    tpl = _env().get_template("resume.tex.j2")
    return tpl.render(resume_body=latex_body)
