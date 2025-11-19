import React, { useState } from "react";
import axios from "axios";
import { 
  Upload, FileText, Download, Play, Loader2, 
  Layout, Settings, ChevronRight, Check
} from "lucide-react";

export default function App() {
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [typstCode, setTypstCode] = useState("");
  
  // NEW STATE: Holds the list of SVG filenames (e.g., ['resume-1.svg', 'resume-2.svg'])
  const [pageFilenames, setPageFilenames] = useState([]); 
  const [resumeBasename, setResumeBasename] = useState(null); // e.g., 'resume-a12813f8'
  
  // LOADING STATES
  const [isProcessing, setIsProcessing] = useState(false); // AI Extraction
  const [isPreviewing, setIsPreviewing] = useState(false); // SVG Generation/Fetching
  const [isDownloading, setIsDownloading] = useState(false); // PDF Generation
  
  // MODIFICATION STATE (New Feature)
  const [modificationPrompt, setModificationPrompt] = useState('');
  const [isModifying, setIsModifying] = useState(false);

  // Expanded Template Library
  const templates = [
    { id: 1, name: "Modern Minimal", desc: "Clean & whitespace-heavy", color: "bg-slate-800" },
    { id: 2, name: "Executive Serif", desc: "Traditional & authoritative", color: "bg-blue-900" },
    { id: 3, name: "Classic Two-Column", desc: "Balanced and organized", color: "bg-green-700" },
    { id: 4, name: "Creative Iconography", desc: "Uses font-awesome icons", color: "bg-indigo-600" },
  ];

  // --- 1. AI EXTRACTION (Upload -> Get Code) ---
  const handleExtractAndGenerate = async () => {
    if (!resumeFile || !selectedTemplate) return alert("Please select a template and upload a resume.");
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append("file", resumeFile);
      formData.append("template_id", selectedTemplate.id);

      const response = await axios.post("http://localhost:8000/process_typst", formData);
      if (response.data.success) {
        const typst = response.data.typst_resume;
        setTypstCode(typst);
        setStep(2);
        await handleCompileAndFetchPages(typst);
      } else {
        alert("Extraction failed: " + response.data.error);
      }
    } catch (err) {
      console.error(err);
      alert("Server error during processing. Check your backend console.");
    }
    setIsProcessing(false);
  };

  // --- 2. COMPILE + FETCH PAGES (Code -> Compile -> Get SVG Names) ---
  const handleCompileAndFetchPages = async (codeOverride) => {
    setIsPreviewing(true);
    try {
      // 1. Compile the Typst code into SVG files on the server
      const compileFormData = new FormData();
      compileFormData.append("content", codeOverride || typstCode);
      compileFormData.append("format", "svg"); 

      const compileResponse = await axios.post("http://localhost:8000/compile-typst", compileFormData);
      const basename = compileResponse.data.basename; // e.g., 'resume-a12813f8'
      setResumeBasename(basename);

      // 2. Get the list of generated SVG files
      const listResponse = await axios.get(`http://localhost:8000/list-svg-pages?basename=${basename}`);
      
      setPageFilenames(listResponse.data.pages);

    } catch (err) {
      console.error(err);
      alert("Preview compilation or file listing failed. Check backend logs.");
      setPageFilenames([]);
    }
    setIsPreviewing(false);
  };

  // --- 3. EXPORT TO PDF (Code -> Get PDF Blob for Download) ---
  const handleDownloadPDF = async () => {
    setIsDownloading(true);
    try {
      const formData = new FormData();
      formData.append("content", typstCode);
      formData.append("format", "pdf"); 

      const response = await axios.post("http://localhost:8000/compile-typst", formData, { responseType: "blob" });
      
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `Resume-${selectedTemplate.name.replace(" ", "-")}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (err) {
      console.error(err);
      alert("PDF Download failed.");
    }
    setIsDownloading(false);
  };

  // --- 4. NEW: MODIFICATION AGENT ---
  const handleModifyResume = async () => {
    if (!modificationPrompt || isModifying) return;
    setIsModifying(true);
    try {
      const payload = {
        typst_code: typstCode,
        prompt: modificationPrompt
      };
      
      // Call the NEW backend endpoint
      const response = await axios.post("http://localhost:8000/modify-typst", payload);

      if (response.data.success) {
        const newTypst = response.data.modified_typst;
        setTypstCode(newTypst); // Update the code
        setModificationPrompt(''); // Clear the prompt
        // Immediately refresh the preview with the new code
        await handleCompileAndFetchPages(newTypst); 
      } else {
        alert("Modification failed: " + response.data.error);
      }
    } catch (err) {
      console.error(err);
      alert("Server error during modification. Check your backend console.");
    }
    setIsModifying(false);
  };


  // --- RENDER ---
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 text-slate-900 font-sans">
      
      {/* SIDEBAR */}
      <aside className="w-20 bg-white border-r border-gray-200 flex flex-col items-center py-6 gap-6 z-10">
        <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg">R</div>
        <nav className="flex flex-col gap-4 mt-4">
          <button onClick={() => setStep(1)} className={`p-3 rounded-xl transition-all ${step === 1 ? 'bg-brand-50 text-brand-600' : 'text-gray-400 hover:bg-gray-50'}`}>
            <Layout className="w-6 h-6" />
          </button>
          <button onClick={() => step === 2 && setStep(2)} disabled={step === 1} className={`p-3 rounded-xl transition-all ${step === 2 ? 'bg-brand-50 text-brand-600' : 'text-gray-300'}`}>
            <Settings className="w-6 h-6" />
          </button>
        </nav>
      </aside>

      <main className="flex-1 flex">
        {/* LEFT PANE: Editor/Config */}
        <div className="w-[45%] flex flex-col border-r border-gray-200 bg-white shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10 overflow-y-auto">
          {step === 1 ? (
            <div className="p-10 max-w-xl mx-auto w-full flex flex-col gap-8 animate-in fade-in slide-in-from-left-4 duration-500">
              <div><h2 className="text-3xl font-bold text-slate-900 mb-2">Create Resume</h2><p className="text-slate-500">Upload your PDF and select a template style.</p></div>
              
              <div className="space-y-4">
                <label className="text-sm font-semibold text-slate-700">1. Template Library</label>
                <div className="grid grid-cols-2 gap-4">
                  {templates.map((t) => (
                    <div key={t.id} onClick={() => setSelectedTemplate(t)} className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedTemplate?.id === t.id ? "border-brand-600 ring-1 ring-brand-600 bg-brand-50" : "border-gray-200 hover:border-gray-300"}`}>
                      <div className={`w-full h-20 rounded-md mb-3 ${t.color} opacity-90 relative`}>
                        {/* Placeholder for template image preview */}
                      </div>
                      <div className="font-bold text-sm flex items-center justify-between">
                        {t.name}
                        {selectedTemplate?.id === t.id && <Check className="w-4 h-4 text-brand-600" />}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{t.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-sm font-semibold text-slate-700">2. Upload Source Document</label>
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:bg-gray-50 transition">
                  <Upload className="w-8 h-8 text-gray-400 mb-2" />
                  <span className="text-sm text-gray-600 font-medium">{resumeFile ? resumeFile.name : "Click to upload PDF"}</span>
                  <input type="file" className="hidden" accept="application/pdf" onChange={(e) => e.target.files?.[0] && setResumeFile(e.target.files[0])} />
                </label>
              </div>

              <button onClick={handleExtractAndGenerate} disabled={isProcessing || !selectedTemplate || !resumeFile} className="w-full py-4 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-bold shadow-lg shadow-brand-600/20 disabled:opacity-50 flex items-center justify-center gap-2">
                {isProcessing ? <Loader2 className="animate-spin" /> : <>Generate Resume <ChevronRight /></>}
              </button>
              
            </div>
          ) : (
            <div className="p-8 flex flex-col gap-6 h-full">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Modify & Refine</h2>
                
                {/* Current Template Info */}
                <div className="p-4 rounded-xl border border-gray-200 bg-gray-50 flex items-center gap-4">
                    <Settings className="w-6 h-6 text-brand-600" />
                    <div>
                        <p className="text-sm font-semibold text-slate-700">Current Template:</p>
                        <p className="text-md font-bold">{selectedTemplate.name}</p>
                    </div>
                    <button onClick={() => handleCompileAndFetchPages()} disabled={isPreviewing} className="ml-auto text-sm font-medium text-brand-600 hover:text-brand-700 flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-brand-50 transition-colors">
                        {isPreviewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Refresh
                    </button>
                </div>

                {/* Modification Agent (New Feature UI) */}
                <div className="flex flex-col gap-4">
                    <label className="text-sm font-semibold text-slate-700">Modification Agent (AI Prompt)</label>
                    <textarea 
                        value={modificationPrompt}
                        onChange={(e) => setModificationPrompt(e.target.value)}
                        placeholder="e.g., Change the font size of the name to 24pt and delete the 'Interests' section."
                        className="w-full p-3 h-32 border border-gray-300 rounded-xl resize-none focus:ring-brand-500 focus:border-brand-500"
                        disabled={isModifying}
                    />
                    <button 
                        onClick={handleModifyResume} 
                        disabled={isModifying || !modificationPrompt} 
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {isModifying ? <Loader2 className="animate-spin" /> : 'Apply AI Modification'}
                    </button>
                </div>
                
                {/* Invisible Code Container (Typst code is hidden but still updated) */}
                {/* <textarea value={typstCode} readOnly className="hidden" /> */}
                <div className="h-4"></div>
            </div>
          )}
        </div>

        {/* RIGHT PANE: Preview (SVG Viewer) */}
        <div className="flex-1 bg-gray-100/50 relative flex flex-col items-center justify-start p-8 overflow-y-auto">
          
          {/* Download Button (Floating) */}
          {step === 2 && (
            <div className="absolute top-6 right-8 z-20">
              <button 
                onClick={handleDownloadPDF}
                disabled={isDownloading || pageFilenames.length === 0}
                className="px-5 py-2.5 bg-slate-900 text-white text-sm font-medium rounded-lg shadow-xl hover:bg-black flex items-center gap-2 transition-transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} 
                Export PDF
              </button>
            </div>
          )}

          {/* The Preview Area */}
          <div className="max-w-4xl w-full mx-auto transition-all duration-300 ease-in-out space-y-8">
            {pageFilenames.length > 0 ? (
              // RENDER MULTIPLE PAGES
              pageFilenames.map((filename) => (
                <div key={filename} className="bg-white shadow-2xl">
                    <img 
                      src={`http://localhost:8000/get-svg-page?filename=${filename}`} 
                      alt={`Resume Page ${filename.split('-').pop().split('.')[0]}`} 
                      className="w-full h-auto" 
                    />
                </div>
              ))
            ) : (
              // PLACEHOLDER
              <div className="w-full h-[600px] flex flex-col items-center justify-center text-gray-400 border border-gray-200 border-dashed bg-white rounded-xl shadow-lg">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                  <FileText className="w-8 h-8 text-gray-300" />
                </div>
                <p className="font-medium">{step === 1 ? 'Select template and upload PDF to begin.' : 'Generating pages...'}</p>
              </div>
            )}
          </div>
          
          {/* Add padding at the bottom for easy scrolling of the last page */}
          <div className="h-20"></div> 
        </div>
      </main>
    </div>
  );
}