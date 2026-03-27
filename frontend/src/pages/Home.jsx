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
      setSelectedHighlight([]);
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

  const handleSelectFeature = (highlights) => {
    setSelectedHighlight(highlights || []);

    if (!highlights || !highlights.length) return;

    const firstPosition = highlights[0]?.start;
    if (!firstPosition) return;

    setTimeout(() => {
      const targetBase = document.getElementById(`base-${firstPosition}`);
      if (targetBase) {
        targetBase.scrollIntoView({
          behavior: "smooth",
          block: "center",
          inline: "center",
        });
      }
    }, 80);
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
      className="relative min-h-screen bg-cover bg-center lg:bg-fixed lg:h-screen lg:overflow-hidden"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="absolute inset-0 bg-black/35 backdrop-blur-[2px]" />

      <div className="relative z-10 lg:h-full">
        <div className="mx-auto hidden h-full max-w-[1800px] gap-6 px-4 py-4 lg:grid lg:grid-cols-[220px_minmax(0,1.7fr)_minmax(0,1fr)]">
          <aside className="sticky top-4 h-[calc(100vh-2rem)] self-start">
            <div className="h-full overflow-hidden rounded-2xl">
              <Sidebar
                mode={mode}
                folderFiles={folderFiles}
                results={results}
                onRunAnalysis={handleRunAnalysis}
                onDownload={downloadResults}
                onClear={clearAll}
              />
            </div>
          </aside>

          <section className="flex h-[calc(100vh-2rem)] min-h-0 flex-col gap-6">
            <div
              className="relative overflow-hidden rounded-2xl border border-slate-200 p-6 shadow-sm"
              style={{
                backgroundImage: `url(${bgImage1})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              <UploadFile
                setSequence={(value) => {
                  setMode("single");
                  setSequence(value);
                  setSelectedHighlight([]);
                }}
                setLoadedFileName={setLoadedFileName}
                setFolderFiles={(files) => {
                  setFolderFiles(files);
                  setSelectedHighlight([]);
                }}
                setMode={setMode}
                setResults={(data) => {
                  setResults(data);
                  setSelectedHighlight([]);
                }}
              />
            </div>

            <div className="min-h-0 flex-1 overflow-hidden rounded-2xl">
              <div className="h-full overflow-y-auto pr-2">
                <SequenceViewer
                  sequence={sequence}
                  setSequence={(value) => {
                    setMode("single");
                    setSequence(value);
                    setSelectedHighlight([]);
                  }}
                  loadedFileName={loadedFileName}
                  folderFiles={folderFiles}
                  mode={mode}
                  highlights={selectedHighlight}
                />
              </div>
            </div>
          </section>

          <section className="h-[calc(100vh-2rem)] min-h-0 overflow-hidden rounded-2xl">
            <div className="h-full overflow-y-auto pr-2">
              <Results
                results={results}
                loading={loading}
                mode={mode}
                activeView={activeView}
                onSelectFeature={handleSelectFeature}
              />
            </div>
          </section>
        </div>

        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 lg:hidden">
          <div
            className="relative overflow-hidden rounded-2xl border border-slate-200 p-6 shadow-sm"
            style={{
              backgroundImage: `url(${bgImage1})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          >
            <UploadFile
              setSequence={(value) => {
                setMode("single");
                setSequence(value);
                setSelectedHighlight([]);
              }}
              setLoadedFileName={setLoadedFileName}
              setFolderFiles={(files) => {
                setFolderFiles(files);
                setSelectedHighlight([]);
              }}
              setMode={setMode}
              setResults={(data) => {
                setResults(data);
                setSelectedHighlight([]);
              }}
            />
          </div>

          <SequenceViewer
            sequence={sequence}
            setSequence={(value) => {
              setMode("single");
              setSequence(value);
              setSelectedHighlight([]);
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
            onSelectFeature={handleSelectFeature}
          />

          <MobileActions
            results={results}
            onRunAnalysis={handleRunAnalysis}
            onDownload={downloadResults}
            onClear={clearAll}
          />
        </div>
      </div>
    </div>
  );
}
