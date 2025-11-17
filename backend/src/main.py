# Main FastAPI Application"

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from .agents.test_agent import TestAgent
from .agents.document_extractor import DocumentExtractor
from .config import settings
from pathlib import Path
import aiofiles

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
TEMPLATES_UPLOAD_DIR = Path("latex_resume_templates")
UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATES_UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "ready"
    }

@app.get("/health")
async def health():
    "Health check endpoint"
    return {"status": "healthy"}

@app.get("/test-agent")
async def test_agent():
    "Endpoint to test the TestAgent connection"
    agent = TestAgent()
    result = await agent.test_connection()
    return result
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Endpoint to upload and extract data from a resume file"""
    
    allowed_extensions = {".pdf", ".docx", ".txt", ".doc", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}"
        )
    
    contents = await file.read()
    
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    file_path = UPLOAD_DIR / file.filename
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(contents)
        
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        print(f"✅ File saved: {file_path} ({len(contents)} bytes)")
        
        extractor = DocumentExtractor()
        result = await extractor.extract_from_file(str(file_path))
        
        print(f"📊 Extraction completed: {result.get('success', False)}")
        
        return {
            "filename": file.filename,
            "size": len(contents),
            "extraction": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"🗑️ Cleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file: {e}")

@app.post("/process")
async def process_resume(file: UploadFile = File(...),template_id: int = 1):
    """Endpoint to process the uploaded resume and convert to LaTeX"""
    from .agents.latex_converter import LaTeXConverter

    
    content = await upload_file(file)
    content = content.get("extraction", {})
    if not content.get("success", False):
        return {"success": False, "error": content.get("error", "Unknown upload error")}
    content = content.get("extracted_data", {})
    
    try:
        latex_file_path = TEMPLATES_UPLOAD_DIR / f"{template_id}.tex"
        async with aiofiles.open(latex_file_path, mode='r') as f:
            latex_template = await f.read()
   
        converter = LaTeXConverter()
        latex_result = await converter.convert_to_latex(latex_template=latex_template,json_data=content)
        
        if not latex_result.get("success", False):
            return {
                     "success": False,
                     "error": f"Error: {str(e)}",
                 }
           
        else:
            latex_filename = f"{Path(file.filename).stem}.tex"
            latex_path = UPLOAD_DIR / latex_filename
            async with aiofiles.open(latex_path, 'w') as latex_file:
                await latex_file.write(latex_result.get("latex", ""))

            return {
                "success": True,
                "original_filename": file.filename,
                "extracted_data": content,
                "latex_filename": latex_filename,
                "lates_path": str(latex_path),
                "latex_preview": latex_result.get("latex", "")[:500]  # First 500 chars
            }
    except HTTPException:
        return {"success": False, "error": he.detail}
    except Exception as e:
        return {"success": False, "error": f"LaTeX conversion error: {str(e)}"}
    
@app.post("/process-typst")
async def process_resume_typst(
    file: UploadFile = File(...),
    template_id: int = 1
):
    """Process uploaded resume and convert to Typst."""

    from .agents.typst_converter import TypstConverter

    # Step 1: Extract content from the uploaded file
    content = await upload_file(file)
    content = content.get("extraction", {})
    if not content.get("success", False):
        return {
            "success": False,
            "error": content.get("error", "Unknown upload error")
        }

    extracted_json = content.get("extracted_data", {})

    try:
        # Step 2: Read the Typst template file
        typst_file_path = TEMPLATES_UPLOAD_DIR / f"{template_id}.typ"
        async with aiofiles.open(typst_file_path, mode="r") as f:
            typst_template = await f.read()

        # Step 3: Run Typst conversion
        converter = TypstConverter()
        typst_result = await converter.convert_to_typst(
            typst_template=typst_template,
            json_data=extracted_json
        )

        if not typst_result.get("success", False):
            return {
                "success": False,
                "error": typst_result.get("error", "Unknown Typst conversion error"),
            }

        # Step 4: Save .typ output file
        typst_filename = f"{Path(file.filename).stem}.typ"
        typst_output_path = UPLOAD_DIR / typst_filename

        async with aiofiles.open(typst_output_path, "w") as typst_file:
            await typst_file.write(typst_result.get("typst", ""))

        # Step 5: Final response
        return {
            "success": True,
            "original_filename": file.filename,
            "extracted_data": extracted_json,
            "typst_filename": typst_filename,
            "typst_path": str(typst_output_path),
            "typst_preview": typst_result.get("typst", "")[:500]  # First 500 chars
        }

    except HTTPException as he:
        return {"success": False, "error": he.detail}

    except Exception as e:
        return {
            "success": False,
            "error": f"Typst conversion error: {str(e)}"
        }


@app.post("/compile-typst")
async def compile_typst(
    file: UploadFile = File(None),
    content: str = None
):
    """
    Compile Typst content into a PDF.
    Either upload a `.typ` file OR send raw Typst text in `content`.
    """
    from .services.typst_pdf_compiler import TypstPDFCompiler
    import uuid
    if not file and not content:
        raise HTTPException(
            status_code=400,
            detail="Provide either a .typ file or `content` text."
        )

    # STEP 1: Load Typst source code
    if file:
        if not file.filename.endswith(".typ"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a .typ file")

        typst_text = (await file.read()).decode("utf-8")
        original_name = Path(file.filename).stem

    else:
        typst_text = content
        original_name = f"document-{uuid.uuid4().hex[:8]}"

    # STEP 2: Compile Typst → PDF
    try:
        compiler = TypstPDFCompiler()
        pdf_path_temp = await compiler.compile_typst(typst_text)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Typst compilation error: {str(e)}"
        )

    # STEP 3: Persist PDF in UPLOAD_DIR
    final_pdf_name = f"{original_name}.pdf"
    final_pdf_path = UPLOAD_DIR / final_pdf_name

    async with aiofiles.open(final_pdf_path, 'wb') as f:
        async with aiofiles.open(pdf_path_temp, 'rb') as temp_pdf:
            await f.write(await temp_pdf.read())

    # STEP 4: Return metadata
    return {
        "success": True,
        "pdf_filename": final_pdf_name,
        "pdf_path": str(final_pdf_path),
        "message": "PDF compiled and saved successfully"
    }
