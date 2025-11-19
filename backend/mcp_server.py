# mcp_servers/resume_mcp_server.py
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from pathlib import Path

# <-- YOUR real implementations (adjust import paths if needed) -->
from src.agents.document_extractor import DocumentExtractor
from src.agents.typst_converter import TypstConverter
from src.services.typst_pdf_compiler import TypstPDFCompiler

app = FastMCP()


# -----------------------------
# ARG MODELS
# -----------------------------
class ExtractArgs(BaseModel):
    file_path: str


class ConvertArgs(BaseModel):
    json_data: dict
    template_path: str


class CompileArgs(BaseModel):
    typst_content: str


# -----------------------------
# TOOL: extract_file
# -----------------------------
@app.tool()
async def extract_file(args: ExtractArgs):
    """
    Input: {"file_path": "..."}
    Output: {"success": bool, "extracted_data": {...}, "error": "..."}
    """
    extractor = DocumentExtractor()
    result = await extractor.extract_from_file(args.file_path)
    return result


# -----------------------------
# TOOL: convert_to_typst
# -----------------------------
@app.tool()
async def convert_to_typst(args: ConvertArgs):
    """
    Input: {"json_data": {...}, "template_path": "/abs/path/to/1.typ"}
    Output: {"success": bool, "typst": "...", "error": "..."}
    """
    template_path = Path(args.template_path)
    if not template_path.exists():
        return {"success": False, "error": "template-not-found", "template_path": args.template_path}

    typst_template = template_path.read_text(encoding="utf-8")
    converter = TypstConverter()
    result = await converter.convert_to_typst(typst_template=typst_template, json_data=args.json_data)
    return result


# -----------------------------
# TOOL: compile_typst
# -----------------------------
@app.tool()
async def compile_typst(args: CompileArgs):
    """
    Input: {"typst_content": "..."}
    Output: {"success": bool, "pdf_path": "/abs/path/to/pdf", "error": "..."}
    """
    compiler = TypstPDFCompiler()
    pdf_path = await compiler.compile_typst(args.typst_content)
    return {"success": True, "pdf_path": str(pdf_path)}


if __name__ == "__main__":
    # runs an MCP server over stdio (FastMCP uses Model Context Protocol)
    app.run()
