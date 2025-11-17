
import tempfile
import asyncio
from pathlib import Path

class PDFCompiler:
    async def compile_latex(self, latex_content: str) -> Path:
        """Compile LaTeX code to PDF and return the PDF file path."""

        # Create a temporary working directory
        temp_dir = Path(tempfile.mkdtemp())
        tex_file = temp_dir / "document.tex"
        pdf_file = temp_dir / "document.pdf"

        # Write LaTeX content to .tex file
        tex_file.write_text(latex_content, encoding="utf-8")

        # Run pdflatex command (needs to be installed on system)
        process = await asyncio.create_subprocess_exec(
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_file.name,
            cwd=temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(
                f"LaTeX compilation failed:\nSTDOUT:\n{stdout.decode()}\n\nSTDERR:\n{stderr.decode()}"
            )

        # Check that PDF was created
        if not pdf_file.exists():
            raise FileNotFoundError("PDF file was not generated.")

        return pdf_file
      