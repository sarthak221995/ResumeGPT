from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import List
import logging
import aiofiles
import json
import uuid
import shutil
import re
from pathlib import Path
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# --- Internal Imports ---
from .config import settings
from .agents.document_extractor import DocumentExtractor
# from .agents.html_converter import HtmlResumeConverter 
from .agents.html_extract_and_convert import unified_processor
from .agents.html_modifier import HtmlModifier

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

# --- Directories ---
UPLOAD_DIR = Path("uploads")
TEMPLATES_UPLOAD_DIR = Path("templates")
UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATES_UPLOAD_DIR.mkdir(exist_ok=True)

# --- Models ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="user or ai")
    content: str

class ModifyRequest(BaseModel):
    html_code: str
    prompt: str
    history: List[ChatMessage] = Field(default_factory=list)

# --- Helper Functions ---
def preprocess_html_for_pdf(html_content: str) -> str:
    """
    Preprocesses HTML to be more compatible with WeasyPrint.
    Removes unsupported CSS properties and normalizes the structure.
    """
    # Remove problematic CSS properties that WeasyPrint doesn't support well
    unsupported_properties = [
        r'backdrop-filter\s*:\s*[^;]+;',
        r'transform\s*:\s*translate[^;]+;',
        r'filter\s*:\s*blur[^;]+;',
        r'clip-path\s*:\s*[^;]+;',
        r'mix-blend-mode\s*:\s*[^;]+;',
    ]
    
    for prop in unsupported_properties:
        html_content = re.sub(prop, '', html_content, flags=re.IGNORECASE)
    
    # Add print-specific CSS for better rendering
    print_css = """
    <style>
        @page {
            size: A4;
            margin: 0;
        }
        body {
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        * {
            box-sizing: border-box;
        }
    </style>
    """
    
    # Insert print CSS before closing </head> or at the beginning of <body>
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{print_css}</head>')
    elif '<body>' in html_content:
        html_content = html_content.replace('<body>', f'<body>{print_css}')
    else:
        html_content = print_css + html_content
    
    return html_content

# --- Routes ---

@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "ready", "mode": "HTML/CSS"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Extract text from uploaded file (PDF/DOCX/etc.) using Responses API."""
    logger.info(f"📄 Upload request: {file.filename}")

    allowed_ext = {".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"}
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    try:
        file_bytes = await file.read()

        extractor = DocumentExtractor()
        result = await extractor.extract_from_bytes(file_bytes, file.filename)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))

        # FIXED: Ensure consistency in keys
        return {
            "filename": file.filename,
            "success": True,
            "extracted_text": result["extracted_data"], # This is the key we need to access
            "processing_time": result["execution_time"],
            "method": result["method"],
        }

    except Exception as e:
        logger.exception("❌ Error during in-memory upload processing")
        raise HTTPException(status_code=500, detail=str(e))


# @app.post("/process_html")
# async def process_resume_html(
#     file: UploadFile = File(...),
#     template_id: str = Form("1")
# ):
#     """Merges extracted resume data into an HTML Template."""
#     # 1. Extract Data
#     upload_res = await upload_file(file)
    
#     # FIXED: Correctly access the data from the upload_res dictionary
#     # The upload_file function returns 'extracted_text', not 'extraction' -> 'extracted_data'
#     extracted_data = upload_res.get("extracted_text", "")
    
#     if not extracted_data:
#         logger.error("Failed to extract data: extracted_data is empty")
#         raise HTTPException(400, detail="Failed to extract data from resume")

#     try:
#         # 2. Load HTML Template
#         template_path = TEMPLATES_UPLOAD_DIR / f"{template_id}.html"
#         if not template_path.exists():
#             # Try without extension if id includes it or different naming
#             template_path = TEMPLATES_UPLOAD_DIR / template_id
#             if not template_path.exists(): 
#                  # Fallback to 1.html if specific template fails
#                  template_path = TEMPLATES_UPLOAD_DIR / "1.html"

#         if not template_path.exists():
#              raise HTTPException(404, detail=f"Template {template_id} not found")
        
#         async with aiofiles.open(template_path, mode="r", encoding="utf-8") as f:
#             html_template = await f.read()

#         # 3. AI Conversion
#         converter = HtmlResumeConverter()
#         result = await converter.convert_to_html(
#             html_template=html_template,
#             json_data=extracted_data
#         )

#         if not result.get("success"):
#             raise HTTPException(500, detail=result.get("error"))

#         # 4. Save Result
#         output_filename = f"{Path(file.filename).stem}.html"
#         output_path = UPLOAD_DIR / output_filename
        
#         async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
#             await f.write(result.get("html", ""))

#         return {
#             "success": True,
#             "html_code": result.get("html", ""),
#             "extracted_data": extracted_data
#         }

#     except Exception as e:
#         logger.error(f"HTML Process Error: {e}")
#         raise HTTPException(500, detail=str(e))



@app.post("/process_html")
async def process_html(
    file: UploadFile = File(...),
    template_id: str = Form(...)
):
    """
    UNIFIED ENDPOINT:
    Takes Resume (PDF/Img) + Template ID -> Returns Filled HTML.
    Uses 'agents/unified_processor.py'
    """
    # Pass the TEMPLATES_UPLOAD_DIR global constant to the processor
    result = await unified_processor.process(file, template_id, TEMPLATES_UPLOAD_DIR)
    
    if not result["success"]:
        return {"success": False, "error": result["error"]}
        
    return {
        "success": True,
        "html_code": result["html_code"]
    }


@app.post("/generate-pdf")
async def generate_pdf(
    html_content: str = Form(...),
):
    """Converts HTML string to PDF using WeasyPrint with preprocessing."""
    try:
        output_filename = f"resume-{uuid.uuid4().hex[:8]}.pdf"
        output_path = UPLOAD_DIR / output_filename

        # Preprocess HTML for better PDF compatibility
        processed_html = preprocess_html_for_pdf(html_content)
        
        logger.info("Generating PDF with WeasyPrint...")
        
        # Configure font handling
        font_config = FontConfiguration()
        
        # Convert HTML string to PDF with font configuration
        HTML(string=processed_html).write_pdf(
            output_path,
            font_config=font_config
        )
        
        logger.info(f"PDF generated successfully: {output_path}")

        return FileResponse(
            path=output_path,
            filename="resume.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"PDF Generation Error: {e}", exc_info=True)
        raise HTTPException(500, detail=f"PDF Generation failed: {str(e)}")


@app.post("/modify-resume")
async def modify_resume(req: ModifyRequest):
    """AI Chat to modify the HTML code with timeout protection."""
    logger.info(f"🔄 Modify request received. Prompt: {req.prompt[:100]}...")
    
    try:
        modifier = HtmlModifier()
        result = await modifier.modify_html(
            html_code=req.html_code,
            prompt=req.prompt,
            history=req.history
        )
        
        if result["success"]:
            logger.info("✅ Modification successful")
            return {
                "success": True, 
                "html_code": result["modified_html"],
                "reply_text": result["reply_text"]
            }
        else:
            logger.error(f"❌ Modification failed: {result.get('error')}")
            raise HTTPException(500, detail=result.get("error"))
    
    except Exception as e:
        logger.error(f"❌ Modify endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(500, detail=f"Modification failed: {str(e)}")


@app.get("/templates")
async def list_templates():
    """Lists available HTML templates."""
    templates = []
    for file_path in TEMPLATES_UPLOAD_DIR.glob("*.html"):
        templates.append({
            "id": file_path.stem, 
            "name": file_path.stem.replace("_", " ").title(),
            "filename": file_path.name
        })
    return {"templates": templates}

@app.post("/preview-pdf-bytes")
async def preview_pdf_bytes(
    html_content: str = Form(...),
):
    """
    Generates PDF but returns raw bytes with 'inline' disposition 
    so the browser displays it instead of downloading.
    """
    try:
        # Preprocess HTML (Same as your generate-pdf logic)
        processed_html = preprocess_html_for_pdf(html_content)
        
        # Configure font handling
        font_config = FontConfiguration()
        
        # Render to bytes in memory
        pdf_bytes = HTML(string=processed_html).write_pdf(font_config=font_config)
        
        # Return as inline content
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=preview.pdf"}
        )
    except Exception as e:
        logger.error(f"PDF Preview Error: {e}", exc_info=True)
        raise HTTPException(500, detail=f"PDF Preview generation failed: {str(e)}")
    
@app.get("/templates/get-raw-code")
async def get_raw_template_code(filename: str):
    """
    Returns the rendered HTML of a template for preview.
    """
    file_path = TEMPLATES_UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
        
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content = await f.read()
    
    return HTMLResponse(content=content)