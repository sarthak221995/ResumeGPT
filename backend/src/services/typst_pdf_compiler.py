import tempfile
import asyncio
from pathlib import Path

class TypstPDFCompiler:
    async def compile_typst(self, typst_content: str) -> Path:
        """Compile Typst (.typ) code to PDF and return the PDF file path."""

        # Create a temporary working directory
        temp_dir = Path(tempfile.mkdtemp())
        typ_file = temp_dir / "document.typ"
        pdf_file = temp_dir / "document.pdf"

        # Write Typst content to .typ file
        typ_file.write_text(typst_content, encoding="utf-8")

        # Run typst compile command
        # REQUIREMENT: typst CLI must be installed on the system
        process = await asyncio.create_subprocess_exec(
            "typst",
            "compile",
            typ_file.name,
            pdf_file.name,
            cwd=temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(
                f"Typst compilation failed:\n"
                f"STDOUT:\n{stdout.decode()}\n\n"
                f"STDERR:\n{stderr.decode()}"
            )

        # Verify PDF creation
        if not pdf_file.exists():
            raise FileNotFoundError("Typst PDF file was not generated.")

        return pdf_file