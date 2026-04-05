import shutil

import pytest

from app.services.compile_runner import CompileError, compile_latex_to_pdf_bytes


@pytest.mark.skipif(not shutil.which("tectonic"), reason="tectonic not installed")
def test_tectonic_produces_pdf():
    tex = r"""\documentclass{article}
\begin{document}
Hello
\end{document}
"""
    pdf = compile_latex_to_pdf_bytes(tex)
    assert pdf[:4] == b"%PDF"


def test_compile_without_tectonic_raises():
    if shutil.which("tectonic"):
        pytest.skip("tectonic present")
    with pytest.raises(CompileError):
        compile_latex_to_pdf_bytes(r"\documentclass{article}\begin{document}x\end{document}")
