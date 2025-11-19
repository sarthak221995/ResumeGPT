# Main FastAPI Application"

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import logging
from .agents.test_agent import TestAgent
from .agents.typst_modifier import TypstModifier
from .agents.document_extractor import DocumentExtractor
from .config import settings
from pathlib import Path
import aiofiles
from fastapi import Form
from pydantic import BaseModel
import uuid
import subprocess
import glob
from fastapi.responses import JSONResponse

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
    
@app.post("/process_typst")
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
            "typst_resume": typst_result.get("typst", "")
        }

    except HTTPException as he:
        return {"success": False, "error": he.detail}

    except Exception as e:
        return {
            "success": False,
            "error": f"Typst conversion error: {str(e)}"
        }

# @app.post("/compile-typst")
# async def compile_typst(
#     file: UploadFile = File(None),
#     content: str = Form(None)
# ):
#     """
#     Compile Typst content into a PDF.
#     Either upload a `.typ` file OR send raw Typst text in `content`.
#     """
#     print("🚀 /compile-typst called",content)
#     from .services.typst_pdf_compiler import TypstPDFCompiler
#     import uuid
#     if not file and not content:
#         raise HTTPException(
#             status_code=400,
#             detail="Provide either a .typ file or `content` text."
#         )

#     # STEP 1: Load Typst source code
#     if file:
#         if not file.filename.endswith(".typ"):
#             raise HTTPException(status_code=400, detail="Uploaded file must be a .typ file")

#         typst_text = (await file.read()).decode("utf-8")
#         original_name = Path(file.filename).stem

#     else:
#         typst_text = content
#         original_name = f"document-{uuid.uuid4().hex[:8]}"

#     # STEP 2: Compile Typst → PDF
#     try:
#         compiler = TypstPDFCompiler()
#         pdf_path_temp = await compiler.compile_typst(typst_text)

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Typst compilation error: {str(e)}"
#         )

#     # STEP 3: Persist PDF in UPLOAD_DIR
#     final_pdf_name = f"{original_name}.pdf"
#     final_pdf_path = UPLOAD_DIR / final_pdf_name

#     async with aiofiles.open(final_pdf_path, 'wb') as f:
#         async with aiofiles.open(pdf_path_temp, 'rb') as temp_pdf:
#             await f.write(await temp_pdf.read())

#     # STEP 4: Return metadata
#     return {
#         "success": True,
#         "pdf_filename": final_pdf_name,
#         "pdf_path": str(final_pdf_path),
#         "message": "PDF compiled and saved successfully"
#     }




# @app.post("/compile-typst")
# async def compile_typst(
#     file: UploadFile = File(None),
#     content: str = Form(None)
# ):
#     """Compile Typst content and return the PDF file stream."""
#     print("🚀 /compile-typst called")
#     from .services.typst_pdf_compiler import TypstPDFCompiler

#     if not file and not content:
#         raise HTTPException(status_code=400, detail="Provide .typ file or content")

#     # 1. Get Source
#     if file:
#         typst_text = (await file.read()).decode("utf-8")
#         original_name = Path(file.filename).stem
#     else:
#         typst_text = content
#         original_name = f"resume-{uuid.uuid4().hex[:8]}"

#     # 2. Compile
#     try:
#         compiler = TypstPDFCompiler()
#         pdf_path_temp = await compiler.compile_typst(typst_text) # Expects returns path string
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Typst error: {str(e)}")

#     # 3. Return File
#     return FileResponse(
#         path=pdf_path_temp, 
#         filename=f"{original_name}.pdf", 
#         media_type='application/pdf'
#     )



# @app.post("/compile-typst")
# async def compile_typst(
#     file: UploadFile = File(None),
#     content: str = Form(None),
#     format: str = Form("pdf")  # <--- NEW PARAMETER: 'pdf' or 'svg'
# ):
#     """
#     Compile Typst content to PDF (for download) or SVG (for preview).
#     """
#     print(f"🚀 /compile-typst called with format: {format}")
    
#     if not file and not content:
#         raise HTTPException(status_code=400, detail="Provide .typ file or content")

#     # 1. Get Source
#     if file:
#         typst_text = (await file.read()).decode("utf-8")
#         original_name = Path(file.filename).stem
#     else:
#         typst_text = content
#         original_name = f"resume-{uuid.uuid4().hex[:8]}"

#     # 2. Save Temp Typst File
#     input_filename = f"{original_name}.typ"
#     input_path = UPLOAD_DIR / input_filename
    
#     async with aiofiles.open(input_path, 'w') as f:
#         await f.write(typst_text)

#     # 3. Compile using Subprocess (Direct CLI access is more reliable for switching formats)
#     output_ext = "svg" if format == "svg" else "pdf"
#     output_filename = f"{original_name}.{output_ext}"
#     output_path = UPLOAD_DIR / output_filename
    
#     # Command: typst compile input.typ output.pdf (or .svg)
#     # Ensure 'typst' is installed in your system PATH
#     try:
#         cmd = ["typst", "compile", str(input_path), str(output_path)]
#         if format == "svg":
#              # SVGs need a root path for images if you have them, usually defaults work
#              pass

#         result = subprocess.run(cmd, capture_output=True, text=True)
        
#         if result.returncode != 0:
#             raise Exception(result.stderr)
            
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

#     # 4. Return File
#     media_type = "image/svg+xml" if format == "svg" else "application/pdf"
    
#     return FileResponse(
#         path=output_path, 
#         filename=output_filename, 
#         media_type=media_type
#     )

import shutil
@app.post("/compile-typst")
async def compile_typst(
    file: UploadFile = File(None),
    content: str = Form(None),
    format: str = Form("pdf") # Can be 'pdf' or 'svg'
):
    print(f"🚀 /compile-typst called with format: {format}")
    
    # Ensure typst is installed (Good debug practice from previous step)
    if not shutil.which("typst"):
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: 'typst' is not installed or not in PATH."
        )

    if not file and not content:
        raise HTTPException(status_code=400, detail="Provide .typ file or content")

    # 1. Save Source File
    if file:
        typst_text = (await file.read()).decode("utf-8")
        original_name = Path(file.filename).stem
    else:
        typst_text = content
        original_name = f"resume-{uuid.uuid4().hex[:8]}"

    input_filename = f"{original_name}.typ"
    input_path = UPLOAD_DIR / input_filename
    
    async with aiofiles.open(input_path, 'w') as f:
        await f.write(typst_text)

    # 2. Configure Command and Output Path
    output_ext = "svg" if format == "svg" else "pdf"
    
    # Determine the compilation command based on format
    if format == "svg":
        # Use {p} placeholder for multi-page SVG output
        output_template = str(UPLOAD_DIR / f"{original_name}-{{p}}.{output_ext}")
        # When generating SVG, we return success + the base name
        return_data = {"success": True, "type": "svg", "basename": original_name}
        cmd = ["typst", "compile", str(input_path), output_template, "--root", str(UPLOAD_DIR)]
    else: # PDF
        final_output_path = UPLOAD_DIR / f"{original_name}.{output_ext}"
        return_data = None # Will return the file stream later
        cmd = ["typst", "compile", str(input_path), str(final_output_path), "--root", str(UPLOAD_DIR)]
        
    print(f"🛠️ Command: {' '.join(cmd)}")
    
    # 3. Run Compilation
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ Typst Compilation Failed:\n{result.stderr}")
            raise Exception(f"Typst Error: {result.stderr}")
            
        print(f"✅ Success! Compiled {format}")

    except Exception as e:
        print(f"❌ Python Error during compilation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")

    # 4. Handle Return based on Format
    if format == "svg":
        # For SVG, compilation is done. Now the client needs to fetch the pages.
        return JSONResponse(return_data)
    else:
        # For PDF, return the file stream directly for download.
        media_type = "application/pdf"
        return FileResponse(
            path=final_output_path, 
            filename=final_output_path.name, 
            media_type=media_type
        )
    
@app.get("/get-svg-page")
async def get_svg_page(filename: str):
    """Retrieves a single SVG page by filename."""
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists() or not file_path.name.endswith(".svg"):
        raise HTTPException(status_code=404, detail="SVG page not found")
        
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='image/svg+xml'
    )

@app.get("/list-svg-pages")
async def list_svg_pages(basename: str):
    """Lists all generated SVG page files for a resume."""
    
    # Find all files matching the pattern: basename-*.svg
    pattern = str(UPLOAD_DIR / f"{basename}-*.svg")
    
    # The list contains full paths, e.g., ['uploads/resume-1.svg', 'uploads/resume-2.svg']
    svg_files = glob.glob(pattern)
    
    # Extract only the filenames and sort them by page number
    page_filenames = sorted([Path(f).name for f in svg_files], key=lambda x: int(x.split('-')[-1].split('.')[0]))
    
    if not page_filenames:
        raise HTTPException(status_code=404, detail="No SVG pages found for this resume.")
        
    return {"success": True, "pages": page_filenames}

@app.post("/modify-typst")
async def modify_typst(payload: dict):
    """Allows a user to modify the Typst code via a natural language prompt."""
    
    typst_code = payload.get("typst_code")
    prompt = payload.get("prompt")
    
    if not typst_code or not prompt:
        raise HTTPException(status_code=400, detail="Missing typst_code or prompt.")
    
    try:
        modifier = TypstModifier()
        result = await modifier.modify_typst(typst_code=typst_code, prompt=prompt)
        
        if result["success"]:
            return {"success": True, "modified_typst": result["modified_typst"]}
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"❌ /modify-typst exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server failed to process modification: {str(e)}")