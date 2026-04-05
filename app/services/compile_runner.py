import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CompileError(Exception):
    """User-safe compile failure."""

    def __init__(self, public_message: str):
        self.public_message = public_message
        super().__init__(public_message)


def compile_latex_to_pdf_bytes(latex_source: str) -> bytes:
    settings = get_settings()
    tectonic = shutil.which("tectonic")
    if not tectonic:
        raise CompileError("PDF engine not available on this host")

    with tempfile.TemporaryDirectory(prefix="tectonic_") as tmp:
        tmp_path = Path(tmp)
        tex = tmp_path / "resume.tex"
        tex.write_text(latex_source, encoding="utf-8")
        outdir = tmp_path / "out"
        outdir.mkdir()
        cmd = [tectonic, "--chatter", "minimal", f"--outdir={outdir}", str(tex)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.tectonic_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("tectonic timed out after %ss", settings.tectonic_timeout_seconds)
            raise CompileError("PDF generation timed out") from None

        if proc.returncode != 0:
            logger.error("tectonic failed: %s", proc.stderr[:2000])
            raise CompileError("PDF generation failed")

        pdf = outdir / "resume.pdf"
        if not pdf.is_file():
            raise CompileError("PDF output missing")
        return pdf.read_bytes()
