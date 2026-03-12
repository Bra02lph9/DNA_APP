import { useState } from "react";
import UploadFile from "../components/UploadFile";
import SequenceViewer from "../components/SequenceViewer";
import Results from "../components/Results";
import Sidebar from "../components/Sidebar";
import MobileActions from "../components/MobileActions";
import { runAnalysis } from "../api";
import { formatResultsAsText } from "../utils/formatResults";
import { downloadPdfFile } from "../utils/downloadResults";
import bgImage from "../assets/bg2.jpg";
import bgImage1 from "../assets/bgh.jpg";

export default function Home() {
  const [sequence, setSequence] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadedFileName, setLoadedFileName] = useState("");
  const [folderFiles, setFolderFiles] = useState([]);
  const [mode, setMode] = useState("single");
  const [activeView, setActiveView] = useState("all");
  const [selectedHighlight, setSelectedHighlight] = useState([]);

  const handleRunAnalysis = async (endpoint) => {
    try {
      const cleanedSequence = sequence.replace(/\s+/g, "").toUpperCase();

      if (mode === "folder") {
        if (!folderFiles.length) {
          alert("Please load a FASTA folder first.");
          return;
        }
      } else {
        if (!cleanedSequence) {
          alert("Please enter or import a DNA sequence first.");
          return;
        }
      }

      setLoading(true);
      setResults(null);
      setActiveView(endpoint);

      const payload =
        mode === "folder" && folderFiles.length > 0
          ? { mode: "folder", files: folderFiles }
          : { mode: "single", sequence: cleanedSequence };

      const data = await runAnalysis(endpoint, payload);
      setResults(data);
    } catch (error) {
      console.error(error);
      alert(error.message || "Error during analysis");
    } finally {
      setLoading(false);
    }
  };

  const downloadResults = () => {
    if (!results) {
      alert("No results to download.");
      return;
    }

    const content = formatResultsAsText(results, activeView);
    downloadPdfFile(content, "dna_analysis_results.txt");
  };

  const clearAll = () => {
    setSequence("");
    setResults(null);
    setLoadedFileName("");
    setFolderFiles([]);
    setMode("single");
    setActiveView("all");
    setSelectedHighlight([]);
  };

  return (
    <div
      className="relative min-h-screen bg-cover bg-center bg-fixed"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="absolute inset-0 bg-black/35 backdrop-blur-[2px]"></div>

      <div className="relative z-10">
        <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
          <Sidebar
            mode={mode}
            folderFiles={folderFiles}
            results={results}
            onRunAnalysis={handleRunAnalysis}
            onDownload={downloadResults}
            onClear={clearAll}
          />

          <main className="flex-1 space-y-6">
            <div
              className="relative overflow-hidden rounded-2xl border border-slate-200 p-6 shadow-sm"
              style={{
                backgroundImage: `url(${bgImage1})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              <UploadFile
                setSequence={setSequence}
                setLoadedFileName={setLoadedFileName}
                setFolderFiles={setFolderFiles}
                setMode={setMode}
                setResults={setResults}
              />
            </div>

            <div className="flex flex-col gap-6">
              <SequenceViewer
                sequence={sequence}
                setSequence={(value) => {
                  setMode("single");
                  setSequence(value);
                }}
                loadedFileName={loadedFileName}
                folderFiles={folderFiles}
                mode={mode}
                highlights={selectedHighlight}
              />

              <Results
                results={results}
                loading={loading}
                mode={mode}
                activeView={activeView}
                onSelectFeature={setSelectedHighlight}
              />
            </div>

            <MobileActions
              results={results}
              onRunAnalysis={handleRunAnalysis}
              onDownload={downloadResults}
              onClear={clearAll}
            />
          </main>
        </div>
      </div>
    </div>
  );
}
