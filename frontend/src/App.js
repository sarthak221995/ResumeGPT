import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { 
  Upload, Download, Loader2, 
  Layout, ChevronRight, CheckCircle2, RefreshCw,
  Send, Bot, User, Sparkles, FileCode, AlertCircle,
  FileText, Wand2, ArrowLeft, History, Cpu, Layers, Zap, Undo,
  Command 
} from "lucide-react";

const API_BASE_URL = "http://localhost:8000";
axios.defaults.timeout = 120000; 

export default function App() {
  // --- APP STATE ---
  const [step, setStep] = useState(1);
  
  // --- DATA STATE ---
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const [htmlCode, setHtmlCode] = useState("");
  
  // --- PDF PREVIEW STATE ---
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);

  // --- CHAT / MODIFIER STATE ---
  const [chatMessages, setChatMessages] = useState([]);
  const [userPrompt, setUserPrompt] = useState("");
  const [isModifying, setIsModifying] = useState(false);
  const [modifyError, setModifyError] = useState(null);
  const chatEndRef = useRef(null);
  
  // --- HISTORY STATE ---
  const [codeHistory, setCodeHistory] = useState([]); 
  const [currentCodeVersionId, setCurrentCodeVersionId] = useState(null); 

  // --- UI/LOADING STATE ---
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGenerationDone, setIsGenerationDone] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // --- EFFECTS ---
  useEffect(() => {
    fetchTemplates();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // --- API FUNCTIONS ---
  const fetchTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/templates`);
      const templateList = response.data.templates || [];

      const templatesWithContent = await Promise.all(
        templateList.map(async (t) => {
          try {
            // Supports both '1.html' or 'modern.html' style filenames
            const contentRes = await axios.get(`${API_BASE_URL}/templates/get-raw-code?filename=${t.filename}`);
            return { ...t, rawHtml: contentRes.data };
          } catch (e) {
            console.error(`Error fetching content for ${t.filename}`, e);
            return { ...t, rawHtml: "" };
          }
        })
      );
      
      setTemplates(templatesWithContent);
    } catch (err) {
      console.error("Failed to load templates", err);
    }
    setIsLoadingTemplates(false);
  };

  // --- HELPER: Generate Thumbnail HTML (Step 1 Only) ---
  // UPDATED: Injects CSS to strip margins/shadows so the preview fills the card
  const getThumbnailHtml = (rawHtml) => {
    if (!rawHtml) return "";
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            /* Reset body to remove gray background and default margins */
            body { 
                margin: 0 !important; 
                padding: 0 !important; 
                overflow: hidden; 
                background: white !important; 
                transform-origin: top left; 
            }
            /* Override the template's internal page container */
            .page { 
                margin: 0 !important; 
                box-shadow: none !important; 
                width: 100% !important; 
                height: auto !important;
                border: none !important;
            }
            /* Ensure text scales cleanly */
            html { -webkit-font-smoothing: antialiased; }
          </style>
        </head>
        <body>${rawHtml}</body>
      </html>
    `;
  };

  // --- HELPER: PDF Preview ---
  const updatePdfPreview = async (codeToRender) => {
    setIsGeneratingPreview(true);
    try {
      const formData = new FormData();
      formData.append("html_content", codeToRender);

      const response = await axios.post(`${API_BASE_URL}/preview-pdf-bytes`, formData, {
        responseType: "blob", 
      });

      const blobUrl = URL.createObjectURL(response.data);
      setPdfUrl(blobUrl);
    } catch (err) {
      console.error("Preview generation failed", err);
    }
    setIsGeneratingPreview(false);
  };

  // --- RESTORED: Revert Logic ---
  const handleRevertRequest = async () => {
    if (isModifying) return;

    const prevVersionId = currentCodeVersionId - 1;

    if (prevVersionId < 1) {
      setChatMessages(prev => [...prev, { 
        role: "ai", 
        content: "Can't revert. This is the first version." 
      }]);
      return;
    }
    
    setIsModifying(true);
    
    const previousVersion = codeHistory.find(v => v.id === prevVersionId);
    
    if (previousVersion) {
      setCurrentCodeVersionId(prevVersionId);
      setHtmlCode(previousVersion.code);
      await updatePdfPreview(previousVersion.code);
      
      setChatMessages(prev => [
        ...prev, 
        { role: "user", content: "Undo last change" },
        { 
          role: "ai", 
          content: `✅ Reverted to version ${prevVersionId}.`, 
          codeVersionId: prevVersionId 
        }
      ]);
    } else {
      setChatMessages(prev => [...prev, { 
        role: "user", 
        content: "revert" 
      }, { 
        role: "ai", 
        content: "Error: Previous version not found in history." 
      }]);
    }
    setIsModifying(false);
  };

  const handleExtractAndGenerate = async () => {
    if (!resumeFile || !selectedTemplate) {
      alert("Please select a template and upload a resume.");
      return;
    }
    
    setIsProcessing(true);
    setIsGenerationDone(false);

    try {
      const formData = new FormData();
      formData.append("file", resumeFile);
      formData.append("template_id", selectedTemplate.id); 

      const response = await axios.post(`${API_BASE_URL}/process_html`, formData);
      
      if (response.data.success) {
        const initialCode = response.data.html_code;
        const initialVersion = { id: 1, code: initialCode };
        setCodeHistory([initialVersion]);
        setCurrentCodeVersionId(1);
        setHtmlCode(initialCode);
        setStep(2); 
        await updatePdfPreview(initialCode);
        setChatMessages([{ role: "ai", content: "I've generated your PDF resume! The preview on the right is the exact file you will download. What would you like to change?", codeVersionId: 1 }]);
        
        setIsGenerationDone(true);
      } else {
        alert("Extraction failed: " + (response.data.error || "Unknown error"));
        setIsProcessing(false);
      }
    } catch (err) {
      console.error("Extract error:", err);
      alert("Server error during generation.");
      setIsProcessing(false);
    }
  };

  const handleOverlayComplete = () => {
    setIsProcessing(false);
    setIsGenerationDone(false);
  };

  const handleSendMessage = async () => {
    if (!userPrompt.trim()) return;
    
    const currentPrompt = userPrompt;
    setUserPrompt(""); 
    setModifyError(null);
    
    if (currentPrompt.toLowerCase().includes("revert") || currentPrompt.toLowerCase().includes("undo")) {
      await handleRevertRequest();
      return; 
    }

    setIsModifying(true); 
    
    const newUserMessage = { role: "user", content: currentPrompt };
    const updatedMessages = [...chatMessages, newUserMessage];
    setChatMessages(updatedMessages);
    
    const conversationHistory = updatedMessages.map(msg => ({ role: msg.role, content: msg.content }));
    const currentCode = codeHistory.find(v => v.id === currentCodeVersionId)?.code || htmlCode;

    try {
      const response = await axios.post(`${API_BASE_URL}/modify-resume`, {
        html_code: currentCode,
        prompt: currentPrompt,
        history: conversationHistory.slice(-5) 
      });

      if (response.data.success) {
        const newCode = response.data.html_code;
        const agentReply = response.data.reply_text;
        const isCodeChanged = newCode !== currentCode; 
        const newVersionId = isCodeChanged ? currentCodeVersionId + 1 : currentCodeVersionId;
        
        if (isCodeChanged) {
          setCodeHistory(prev => [...prev, { id: newVersionId, code: newCode }]);
          setCurrentCodeVersionId(newVersionId);
          setHtmlCode(newCode);
          updatePdfPreview(newCode);
        }
        
        setChatMessages(prev => [...prev, { role: "ai", content: agentReply, codeVersionId: newVersionId }]);
      } else {
        setChatMessages(prev => [...prev, { role: "ai", content: "Sorry, I couldn't process that." }]);
      }
    } catch (err) {
      console.error("Modify error:", err);
      setChatMessages(prev => [...prev, { role: "ai", content: "Error contacting AI server." }]);
    }
    setIsModifying(false);
  };

  const handleDownloadPDF = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      // Uses the friendly template name for the file download
      link.download = `Resume-${selectedTemplate?.name || "Custom"}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // --- UI COMPONENT: SYNCHRONIZED PROCESSING OVERLAY ---
  const ProcessingOverlay = ({ isDone, onComplete }) => {
    const [progress, setProgress] = useState(0);
    const [activeStage, setActiveStage] = useState(0);
    const [duration, setDuration] = useState(0);

    const stages = [
      { id: 1, label: "Uploading document...", icon: Upload, duration: 4000, target: 10 },
      { id: 2, label: "Extracting text data...", icon: FileText, duration: 15000, target: 35 },
      { id: 3, label: "Analyzing structure & skills...", icon: Cpu, duration: 25000, target: 65 },
      { id: 4, label: "Applying design layout...", icon: Layers, duration: 25000, target: 85 },
      { id: 5, label: "Finalizing PDF...", icon: Sparkles, duration: 40000, target: 98 }
    ];

    useEffect(() => {
        if (isDone) {
            setActiveStage(stages.length); 
            setDuration(500); 
            requestAnimationFrame(() => setProgress(100));
            const timer = setTimeout(() => {
                onComplete();
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [isDone, onComplete]);

    useEffect(() => {
      if (isDone) return; 

      let currentTimeout;
      const runStages = (index) => {
        if (index >= stages.length) return;
        
        const stage = stages[index];
        setActiveStage(index);
        setDuration(stage.duration); 
        requestAnimationFrame(() => setProgress(stage.target));

        currentTimeout = setTimeout(() => {
          runStages(index + 1);
        }, stage.duration);
      };

      runStages(0);
      return () => clearTimeout(currentTimeout);
    }, [isDone]);

    return (
      <div className="fixed inset-0 z-[100] bg-white/90 backdrop-blur-xl flex items-center justify-center p-4 animate-in fade-in duration-300">
        <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl shadow-slate-300/50 border border-slate-100 p-8 flex flex-col items-center relative overflow-hidden">
          <div className="relative w-24 h-24 mb-8">
             <div className="absolute inset-0 bg-blue-500/10 rounded-full animate-ping opacity-75"></div>
             <div className="absolute inset-0 border-4 border-slate-50 rounded-full"></div>
             <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
             {isDone ? (
                <div className="absolute inset-2 bg-blue-600 rounded-full shadow-sm flex items-center justify-center z-10 animate-in zoom-in duration-300">
                    <CheckCircle2 className="w-10 h-10 text-white" />
                </div>
             ) : (
                <div className="absolute inset-2 bg-white rounded-full shadow-sm flex items-center justify-center z-10 border border-slate-50">
                    <Zap className="w-8 h-8 text-blue-600 fill-blue-600 animate-pulse" />
                </div>
             )}
          </div>
          <div className="text-center w-full mb-8 z-10">
            <h2 className="text-xl font-bold text-slate-900 mb-2">{isDone ? "Resume Ready!" : "Generating Resume"}</h2>
            <p className="text-slate-500 text-sm">{isDone ? "Redirecting to editor..." : "Please keep this tab open while we process."}</p>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full mb-8 overflow-hidden z-10">
            <div 
              className="h-full bg-blue-600 rounded-full ease-linear" 
              style={{ 
                  width: `${progress}%`,
                  transitionProperty: "width",
                  transitionDuration: `${duration}ms`,
                  transitionTimingFunction: isDone ? "ease-out" : "linear"
              }}
            />
          </div>
          <div className="w-full space-y-3 z-10">
            {stages.map((stage, idx) => {
              const isActive = idx === activeStage && !isDone;
              const isFinished = idx < activeStage || isDone;
              const isPending = idx > activeStage && !isDone;
              
              return (
                <div key={stage.id} className={`flex items-center gap-3 transition-all duration-500 ${isPending ? 'opacity-40 grayscale' : 'opacity-100'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border transition-colors duration-300 ${isFinished ? 'bg-blue-600 border-blue-600 text-white' : isActive ? 'bg-white border-blue-600 text-blue-600' : 'bg-slate-50 border-slate-200 text-slate-300'}`}>
                    {isFinished ? <CheckCircle2 size={12} /> : isActive ? <Loader2 size={12} className="animate-spin" /> : <div className="w-1.5 h-1.5 rounded-full bg-slate-300" />}
                  </div>
                  <span className={`text-sm font-medium ${isActive ? 'text-blue-700' : isFinished ? 'text-slate-700' : 'text-slate-400'}`}>
                      {stage.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // --- UI COMPONENTS ---

  const Sidebar = () => (
    <aside className="w-[72px] bg-white border-r border-slate-200 flex flex-col items-center py-6 gap-6 z-30 flex-shrink-0">
      {/* LOGO */}
      <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-200/50">
        <Command className="w-5 h-5 text-white" />
      </div>

      <nav className="flex flex-col gap-2 w-full px-2 mt-4">
        <button 
          onClick={() => setStep(1)} 
          className={`group relative flex items-center justify-center w-full aspect-square rounded-xl transition-all duration-200 ${step === 1 ? 'bg-slate-100 text-slate-900' : 'text-slate-400 hover:bg-white hover:text-slate-600'}`}
        >
          <Layout className="w-5 h-5" />
          {step === 1 && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-slate-900 rounded-r-full" />}
          <div className="absolute left-14 bg-slate-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Templates</div>
        </button>
        
        <button 
          onClick={() => step === 2 && setStep(2)} 
          disabled={step === 1} 
          className={`group relative flex items-center justify-center w-full aspect-square rounded-xl transition-all duration-200 ${step === 2 ? 'bg-slate-100 text-blue-600' : 'text-slate-300'}`}
        >
          <Sparkles className="w-5 h-5" />
          {step === 2 && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-blue-600 rounded-r-full" />}
          <div className="absolute left-14 bg-slate-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Editor</div>
        </button>
      </nav>
      <div className="mt-auto flex flex-col gap-4 items-center pb-4">
        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <User size={16} />
        </div>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 text-slate-900 font-sans selection:bg-blue-100 selection:text-blue-900">
      
      {/* OVERLAY LOADER */}
      {isProcessing && <ProcessingOverlay isDone={isGenerationDone} onComplete={handleOverlayComplete} />}

      <Sidebar />

      <main className="flex-1 flex overflow-hidden">
        
        {/* === LEFT PANEL: CONTROLS === */}
        <div className="w-[420px] flex flex-col border-r border-slate-200 bg-white shadow-2xl shadow-slate-200/50 z-20 relative">
          
          {step === 1 ? (
            /* --- STEP 1: UPLOAD & CONFIGURE --- */
            <div className="flex flex-col h-full">
               <div className="p-8 pb-4 border-b border-slate-100">
                <h2 className="text-xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
                    <FileText className="w-5 h-5 text-slate-400" />
                    Create Resume
                </h2>
                <p className="text-slate-500 text-sm mt-2 leading-relaxed">
                    Upload your existing resume and choose a professional template to get started.
                </p>
              </div>

              <div className="flex-1 overflow-y-auto p-8 space-y-8">
                {/* 1. FILE UPLOAD */}
                <div className="space-y-3">
                  <div className="flex justify-between items-baseline">
                      <label className="text-xs font-semibold text-slate-900 uppercase tracking-wider">Source File</label>
                      {resumeFile && <button onClick={() => setResumeFile(null)} className="text-[10px] text-red-500 hover:text-red-600 font-medium">Remove</button>}
                  </div>
                  
                  <label className={`group relative flex flex-col items-center justify-center w-full h-40 border border-dashed rounded-xl cursor-pointer transition-all duration-300 ease-out ${resumeFile ? 'border-blue-500 bg-blue-50/30' : 'border-slate-300 hover:border-slate-400 hover:bg-slate-50'}`}>
                    {resumeFile ? (
                      <div className="flex flex-col items-center text-blue-600 animate-in zoom-in-50 duration-300">
                        <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center mb-3">
                            <CheckCircle2 className="w-6 h-6 text-blue-600" />
                        </div>
                        <span className="text-sm font-semibold text-slate-900">{resumeFile.name}</span>
                        <span className="text-xs text-slate-500 mt-1">{(resumeFile.size / 1024).toFixed(0)} KB</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-slate-400 group-hover:text-slate-600 transition-colors">
                        <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Upload className="w-5 h-5" />
                        </div>
                        <span className="text-sm font-medium text-slate-700">Click to upload</span>
                        <span className="text-xs text-slate-400 mt-1">PDF or DOCX</span>
                      </div>
                    )}
                    <input type="file" className="hidden" accept=".pdf,.docx,.doc" onChange={(e) => e.target.files?.[0] && setResumeFile(e.target.files[0])} />
                  </label>
                </div>

                {/* 2. TEMPLATE INDICATOR */}
                <div className="space-y-3">
                  <div className="flex justify-between items-baseline">
                      <label className="text-xs font-semibold text-slate-900 uppercase tracking-wider">Selected Layout</label>
                      {!selectedTemplate && <span className="text-[10px] text-amber-600 font-medium animate-pulse">Required</span>}
                  </div>
                  
                  {selectedTemplate ? (
                    <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm flex items-center gap-4 group hover:border-blue-300 transition-colors">
                      <div className="w-12 h-12 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 group-hover:text-blue-600 group-hover:bg-blue-50 transition-colors">
                          <Layout size={20} />
                      </div>
                      <div>
                          <div className="font-semibold text-sm text-slate-900">{selectedTemplate.name}</div>
                          <div className="text-xs text-slate-500 mt-0.5">ID: {selectedTemplate.id}</div>
                      </div>
                      <div className="ml-auto text-blue-600">
                          <CheckCircle2 size={18} />
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 border border-slate-200 border-dashed rounded-xl bg-slate-50 flex items-center gap-3 text-slate-400">
                        <AlertCircle size={18} />
                        <span className="text-sm">Select a template from the right panel</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="p-6 border-t border-slate-100 bg-white">
                <button 
                    onClick={handleExtractAndGenerate} 
                    disabled={isProcessing || !resumeFile || !selectedTemplate} 
                    className="w-full h-12 bg-slate-900 hover:bg-black text-white rounded-lg font-medium shadow-lg shadow-slate-200 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                >
                    {isProcessing ? (
                        <>
                            <Loader2 className="animate-spin w-4 h-4" />
                            <span>Processing...</span>
                        </>
                    ) : (
                        <>
                            <span>Generate Resume</span>
                            <ChevronRight size={16} />
                        </>
                    )}
                </button>
              </div>
            </div>
          ) : (
            /* --- STEP 2: CHAT EDITOR --- */
            <div className="flex flex-col h-full bg-white">
              {/* HEADER (REMOVED CODE TOGGLE) */}
              <div className="h-14 border-b border-slate-100 flex items-center justify-between px-5 bg-white shrink-0">
                <div className="flex items-center gap-2">
                    <button onClick={() => setStep(1)} className="text-slate-400 hover:text-slate-700 transition-colors"><ArrowLeft size={16} /></button>
                    <span className="h-4 w-[1px] bg-slate-200 mx-1"></span>
                    <span className="font-semibold text-slate-700 text-sm flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-500" /> 
                        AI Editor
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    {currentCodeVersionId > 1 && (
                        <div className="text-[10px] font-mono text-slate-400 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                            v{currentCodeVersionId}
                        </div>
                    )}
                </div>
              </div>

              {/* CHAT MESSAGES */}
              <div className="flex-1 overflow-y-auto p-5 space-y-6 scroll-smooth">
                {chatMessages.length === 0 && (
                    <div className="text-center mt-10">
                        <div className="w-12 h-12 bg-indigo-50 text-indigo-500 rounded-full flex items-center justify-center mx-auto mb-3">
                            <Wand2 size={20} />
                        </div>
                        <p className="text-slate-500 text-sm">Describe changes to modify your resume.</p>
                    </div>
                )}

                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border shadow-sm ${msg.role === 'user' ? 'bg-white border-slate-200 text-slate-600' : 'bg-indigo-600 border-indigo-600 text-white'}`}>
                        {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                    </div>
                    <div className={`group px-4 py-3 rounded-2xl text-[13px] leading-relaxed max-w-[85%] shadow-sm ${msg.role === 'user' ? 'bg-slate-100 text-slate-800 rounded-tr-none' : 'bg-white border border-slate-100 text-slate-600 rounded-tl-none'}`}>
                        {msg.content}
                        {msg.codeVersionId && (
                            <div className="mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-400 font-mono flex items-center gap-1">
                                <History size={10} /> Saved as version {msg.codeVersionId}
                            </div>
                        )}
                    </div>
                  </div>
                ))}

                {(isModifying || isGeneratingPreview) && (
                   <div className="flex gap-3">
                     <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center border border-indigo-600 shrink-0"><Bot size={14}/></div>
                     <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex gap-3 items-center">
                        <Loader2 className="animate-spin w-3.5 h-3.5 text-indigo-500" />
                        <span className="text-xs text-slate-500 font-medium">
                           {isModifying ? "Refining layout..." : "Rendering preview..."}
                        </span>
                     </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* INPUT AREA */}
              <div className="p-4 bg-white border-t border-slate-100 shrink-0">
                <div className="relative flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-xl p-2 focus-within:ring-2 focus-within:ring-indigo-100 focus-within:border-indigo-400 transition-all shadow-sm">
                  <textarea 
                    value={userPrompt} 
                    onChange={(e) => setUserPrompt(e.target.value)} 
                    onKeyDown={(e) => {
                        if(e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            if(!isModifying) handleSendMessage();
                        }
                    }} 
                    placeholder="Ask to bold text, change fonts, or fix spacing..." 
                    className="w-full bg-transparent border-none focus:ring-0 text-sm text-slate-800 placeholder:text-slate-400 resize-none py-2 px-2 max-h-32 min-h-[44px]"
                    disabled={isModifying} 
                  />
                  
                  {/* UNDO BUTTON */}
                  <button 
                    onClick={handleRevertRequest} 
                    disabled={isModifying || !currentCodeVersionId || currentCodeVersionId <= 1} 
                    title="Undo last change"
                    className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg disabled:opacity-30 disabled:hover:bg-transparent transition-colors mb-0.5"
                  >
                    <Undo className="w-4 h-4" />
                  </button>

                  {/* SEND BUTTON */}
                  <button 
                    onClick={handleSendMessage} 
                    disabled={isModifying || !userPrompt.trim()} 
                    className="p-2 bg-slate-900 text-white rounded-lg hover:bg-black disabled:opacity-30 disabled:hover:bg-slate-900 transition-colors mb-0.5"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
                <div className="text-[10px] text-center text-slate-300 mt-2 font-medium">
                    AI can make mistakes. Review the PDF before downloading.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* === RIGHT PANEL: MAIN CANVAS === */}
        <div className="flex-1 bg-slate-100/50 relative flex flex-col">
          
          {/* HEADER (Contextual) */}
          <div className="h-16 px-8 flex items-center justify-between shrink-0 z-10">
              <div className="flex items-center gap-2">
                  <h1 className="text-lg font-semibold text-slate-800">
                      {step === 1 ? 'Template Gallery' : 'Live Preview'}
                  </h1>
                  {step === 2 && <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">Ready</span>}
              </div>

              {step === 2 && (
                <div className="flex gap-3">
                   <button 
                    onClick={handleDownloadPDF}
                    className="px-4 py-2 bg-slate-900 text-white text-xs font-medium rounded-lg shadow-lg shadow-slate-200 hover:bg-black hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center gap-2"
                  >
                    <Download className="w-3.5 h-3.5" /> 
                    <span>Download PDF</span>
                  </button>
                </div>
              )}
          </div>

          {/* CONTENT AREA */}
          <div className="flex-1 w-full overflow-hidden relative">
            {step === 1 ? (
              /* --- MARKETPLACE GRID --- */
              <div className="absolute inset-0 overflow-y-auto p-8 pt-2">
                  <div className="max-w-6xl mx-auto pb-20">
                    <div className="flex items-center justify-between mb-6">
                        <div className="text-sm text-slate-500">Choose a layout to begin customization</div>
                        <button onClick={fetchTemplates} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-white rounded-full transition-all"><RefreshCw size={16} /></button>
                    </div>
                    
                    {isLoadingTemplates ? (
                        <div className="flex flex-col items-center justify-center mt-32">
                            <Loader2 className="w-10 h-10 animate-spin text-slate-300 mb-4" />
                            <p className="text-slate-400 text-sm font-medium">Loading templates...</p>
                        </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {templates.map((t) => (
                          <div 
                            key={t.id} 
                            onClick={() => setSelectedTemplate(t)} 
                            className={`group relative flex flex-col cursor-pointer transition-all duration-300 ${selectedTemplate?.id === t.id ? 'translate-y-[-4px]' : 'hover:translate-y-[-4px]'}`}
                          >
                            {/* Card Container */}
                            <div className={`relative rounded-xl overflow-hidden bg-white border aspect-[1/1.414] shadow-sm transition-all duration-300 ${selectedTemplate?.id === t.id ? 'border-blue-500 ring-2 ring-blue-500 shadow-xl shadow-blue-500/10' : 'border-slate-200 group-hover:shadow-lg group-hover:border-slate-300'}`}>
                               
                               {/* HTML Thumbnail iframe */}
                               <div className="absolute inset-0 bg-white pointer-events-none">
                                   <iframe 
                                    srcDoc={getThumbnailHtml(t.rawHtml)}
                                    title={t.name}
                                    className="w-[400%] h-[400%] scale-[0.25] border-none origin-top-left"
                                    tabIndex="-1" 
                                    scrolling="no"
                                   />
                               </div>

                               {/* Hover Overlay */}
                               <div className={`absolute inset-0 bg-slate-900/0 transition-colors duration-300 ${selectedTemplate?.id === t.id ? 'bg-indigo-900/10' : 'group-hover:bg-slate-900/5'}`} />
                               
                               {/* Selected Checkmark */}
                               {selectedTemplate?.id === t.id && (
                                   <div className="absolute top-4 right-4 z-10 animate-in zoom-in-50 duration-300">
                                       <div className="bg-blue-600 text-white w-8 h-8 rounded-full shadow-lg flex items-center justify-center">
                                           <CheckCircle2 size={16} />
                                       </div>
                                   </div>
                               )}
                            </div>
                            
                            <div className="mt-4 flex items-center justify-between px-1">
                                <h3 className={`font-semibold text-sm ${selectedTemplate?.id === t.id ? 'text-blue-600' : 'text-slate-700'}`}>{t.name}</h3>
                                {selectedTemplate?.id === t.id && <span className="text-[10px] font-bold tracking-wider text-blue-600 uppercase">Selected</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
              </div>
            ) : (
              /* --- PDF PREVIEWER --- */
              <div className="absolute inset-0 flex flex-col items-center justify-center p-8 bg-slate-200/50">
                 {isGeneratingPreview && !pdfUrl ? (
                    <div className="flex flex-col items-center animate-pulse">
                        <div className="w-16 h-20 bg-white rounded shadow-sm border border-slate-200 mb-4 flex items-center justify-center">
                            <Loader2 className="w-6 h-6 animate-spin text-indigo-500"/>
                        </div>
                        <p className="text-slate-500 font-medium text-sm">Rendering PDF...</p>
                    </div>
                 ) : pdfUrl ? (
                   <div className="relative w-full h-full max-w-3xl shadow-2xl shadow-slate-300/50 rounded-lg overflow-hidden border border-slate-300 bg-white animate-in zoom-in-95 duration-500">
                       <iframe 
                          src={`${pdfUrl}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`} 
                          className="w-full h-full"
                          title="PDF Preview"
                       />
                   </div>
                 ) : (
                    <div className="text-slate-400 text-sm">Waiting for generation...</div>
                 )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}