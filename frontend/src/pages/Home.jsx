import { useRef, useState } from "react";
import UploadFile from "../components/UploadFile";
import SequenceViewer from "../components/SequenceViewer";
import Results from "../components/Results";
import Sidebar from "../components/Sidebar";
import MobileActions from "../components/MobileActions";
import {
  createAnalysisTask,
  getTaskStatus,
} from "../api";
import { formatResultsAsText } from "../utils/formatResults";
import { downloadPdfFile } from "../utils/downloadResults";
import bgImage from "../assets/bg2.jpg";
import bgImage1 from "../assets/bgh.jpg";

function normalizeAnalysisType(endpoint) {
  const map = {
    all: "all",
    orfs: "orfs",
    promoters: "promoters",
    terminators: "terminators",
    "shine-dalgarno": "shine_dalgarno",
    "coding-orfs": "coding_orfs",
    "ranked-coding-orfs": "ranked_coding_orfs",
  };

  return map[endpoint] || endpoint;
}

function computeSequenceMeta(sequence, fileName = "") {
  const clean = (sequence || "").replace(/[^ATGCN]/gi, "").toUpperCase();
  const length = clean.length;

  if (!length) {
    return {
      fileName,
      length: 0,
      gcPercent: 0,
      atPercent: 0,
    };
  }

  const gcCount = (clean.match(/[GC]/g) || []).length;
  const atCount = (clean.match(/[AT]/g) || []).length;

  return {
    fileName,
    length,
    gcPercent: (gcCount / length) * 100,
    atPercent: (atCount / length) * 100,
  };
}

function shiftSimpleRangeFeature(feature, offset) {
  return {
    ...feature,
    start: feature.start + offset - 1,
    end: feature.end + offset - 1,
  };
}

function shiftPromoterFeature(feature, offset) {
  return {
    ...feature,
    box35_start: feature.box35_start + offset - 1,
    box35_end: feature.box35_end + offset - 1,
    box10_start: feature.box10_start + offset - 1,
    box10_end: feature.box10_end + offset - 1,
  };
}

function shiftTerminatorFeature(feature, offset) {
  return {
    ...feature,
    stem_left_start: feature.stem_left_start + offset - 1,
    stem_left_end: feature.stem_left_end + offset - 1,
    stem_right_start: feature.stem_right_start + offset - 1,
    stem_right_end: feature.stem_right_end + offset - 1,
    poly_t_start: feature.poly_t_start + offset - 1,
    poly_t_end: feature.poly_t_end + offset - 1,
  };
}

function shiftShineDalgarnoFeature(feature, offset) {
  return {
    ...feature,
    start: feature.start + offset - 1,
    end: feature.end + offset - 1,
    linked_start_position: feature.linked_start_position
      ? feature.linked_start_position + offset - 1
      : null,
  };
}

function shiftCodingOrfFeature(feature, offset) {
  return {
    ...feature,
    start: feature.start + offset - 1,
    end: feature.end + offset - 1,
  };
}

function shiftRankedCodingOrfEntry(entry, offset) {
  return {
    ...entry,
    orf: entry.orf ? shiftCodingOrfFeature(entry.orf, offset) : null,
    best_promoter: entry.best_promoter
      ? shiftPromoterFeature(entry.best_promoter, offset)
      : null,
    best_shine_dalgarno: entry.best_shine_dalgarno
      ? shiftShineDalgarnoFeature(entry.best_shine_dalgarno, offset)
      : null,
    best_terminator: entry.best_terminator
      ? shiftTerminatorFeature(entry.best_terminator, offset)
      : null,
  };
}

function shiftResultsToGlobal(result, offset) {
  if (!result || typeof result !== "object") return result;

  return {
    ...result,
    orfs: Array.isArray(result.orfs)
      ? result.orfs.map((item) => shiftSimpleRangeFeature(item, offset))
      : result.orfs,

    promoters: Array.isArray(result.promoters)
      ? result.promoters.map((item) => shiftPromoterFeature(item, offset))
      : result.promoters,

    terminators: Array.isArray(result.terminators)
      ? result.terminators.map((item) => shiftTerminatorFeature(item, offset))
      : result.terminators,

    shine_dalgarno: Array.isArray(result.shine_dalgarno)
      ? result.shine_dalgarno.map((item) =>
          shiftShineDalgarnoFeature(item, offset)
        )
      : result.shine_dalgarno,

    coding_orfs: Array.isArray(result.coding_orfs)
      ? result.coding_orfs.map((item) => shiftCodingOrfFeature(item, offset))
      : result.coding_orfs,

    best_coding_orf: result.best_coding_orf
      ? shiftCodingOrfFeature(result.best_coding_orf, offset)
      : result.best_coding_orf,

    ranked_coding_orfs: Array.isArray(result.ranked_coding_orfs)
      ? result.ranked_coding_orfs.map((item) =>
          shiftRankedCodingOrfEntry(item, offset)
        )
      : result.ranked_coding_orfs,

    best_ranked_coding_orf: result.best_ranked_coding_orf
      ? shiftRankedCodingOrfEntry(result.best_ranked_coding_orf, offset)
      : result.best_ranked_coding_orf,
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function Home() {
  const [sequence, setSequence] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadedFileName, setLoadedFileName] = useState("");
  const [folderFiles, setFolderFiles] = useState([]);
  const [mode, setMode] = useState("single");
  const [activeView, setActiveView] = useState("all");
  const [selectedHighlight, setSelectedHighlight] = useState([]);
  const [sequenceMeta, setSequenceMeta] = useState(null);

  const [taskId, setTaskId] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);

  const fullSequenceRef = useRef("");
  const latestWindowRequestIdRef = useRef(0);

  const setSingleSequenceState = (value) => {
    const clean = (value || "").replace(/[^ATGCN]/gi, "").toUpperCase();
    fullSequenceRef.current = clean;
    setSequence(clean);
    setSequenceMeta(computeSequenceMeta(clean, loadedFileName));
    setMode("single");
    setSelectedHighlight([]);
  };

  const pollTaskUntilDone = async (incomingTaskId) => {
    while (true) {
      const taskData = await getTaskStatus(incomingTaskId);
      setTaskStatus(taskData.status);

      if (taskData.status === "SUCCESS") {
        const finalResult = taskData.result?.result || taskData.result;
        return finalResult;
      }

      if (taskData.status === "FAILURE") {
        console.error("Celery task failure payload:", taskData);
        throw new Error(taskData.error || taskData.result || "Task failed");
      }

      await sleep(2000);
    }
  };

  const handleRunAnalysis = async (endpoint) => {
    try {
      const cleanedSequence = (
        fullSequenceRef.current || sequence || ""
      ).replace(/\s+/g, "").toUpperCase();

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

      const normalizedAnalysisType = normalizeAnalysisType(endpoint);

      setLoading(true);
      setResults(null);
      setSelectedHighlight([]);
      setActiveView(endpoint);
      setTaskId(null);
      setTaskStatus("QUEUED");

      const payload =
        mode === "folder" && folderFiles.length > 0
          ? {
              mode: "folder",
              files: folderFiles,
              analysis_type: normalizedAnalysisType,
              min_aa: 30,
            }
          : {
              mode: "single",
              sequence: cleanedSequence,
              analysis_type: normalizedAnalysisType,
              min_aa: 30,
            };

      const task = await createAnalysisTask(payload);
      setTaskId(task.task_id);
      setTaskStatus(task.status || "QUEUED");

      const data = await pollTaskUntilDone(task.task_id);
      setResults(data);
    } catch (error) {
      console.error(error);
      alert(error.message || "Error during analysis");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeWindow = async ({ sequence: windowSequence, start }) => {
    if (mode !== "single") return;
    if (!windowSequence) return;

    const endpoint = activeView || "all";
    const normalizedAnalysisType = normalizeAnalysisType(endpoint);
    const requestId = Date.now();
    latestWindowRequestIdRef.current = requestId;

    try {
      setLoading(true);
      setSelectedHighlight([]);
      setTaskStatus("QUEUED");

      const payload = {
        mode: "single",
        sequence: windowSequence,
        analysis_type: normalizedAnalysisType,
        min_aa: 30,
      };

      const task = await createAnalysisTask(payload);
      setTaskId(task.task_id);
      setTaskStatus(task.status || "QUEUED");

      const data = await pollTaskUntilDone(task.task_id);

      if (latestWindowRequestIdRef.current !== requestId) {
        return;
      }

      const shifted = shiftResultsToGlobal(data, start);
      setResults(shifted);
    } catch (error) {
      console.error(error);
      alert(error.message || "Error during window analysis");
    } finally {
      if (latestWindowRequestIdRef.current === requestId) {
        setLoading(false);
      }
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
    fullSequenceRef.current = "";
    setSequence("");
    setSequenceMeta(null);
    setResults(null);
    setLoadedFileName("");
    setFolderFiles([]);
    setMode("single");
    setActiveView("all");
    setSelectedHighlight([]);
    setTaskId(null);
    setTaskStatus(null);
  };

  const uploadProps = {
    setSequence: (value) => {
      setMode("single");
      setSequence(value);
      setSelectedHighlight([]);
      setTaskId(null);
      setTaskStatus(null);
    },
    setLoadedFileName: setLoadedFileName,
    setFolderFiles: (files) => {
      setFolderFiles(files);
      setSelectedHighlight([]);
      setTaskId(null);
      setTaskStatus(null);
    },
    setMode: setMode,
    setResults: (data) => {
      setResults(data);
      setSelectedHighlight([]);
      setTaskId(null);
      setTaskStatus(null);
    },
    setFullSequenceRef: (seq) => {
      fullSequenceRef.current = seq;
    },
    setSequenceMeta: setSequenceMeta,
  };

  const viewerProps = {
    sequence,
    setSequence: setSingleSequenceState,
    loadedFileName,
    folderFiles,
    mode,
    highlights: selectedHighlight,
    sequenceMeta,
    fullSequenceRef,
    onAnalyzeWindow: handleAnalyzeWindow,
  };

  const resultsProps = {
    results,
    loading,
    mode,
    activeView,
    onSelectFeature: handleSelectFeature,
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
              <UploadFile {...uploadProps} />
            </div>

            {loading && taskStatus && (
              <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
                <p className="text-sm text-slate-700">
                  <span className="font-medium">Background task status:</span>{" "}
                  {taskStatus}
                </p>
                {taskId && (
                  <p className="mt-1 text-xs text-slate-500">
                    Task ID: {taskId}
                  </p>
                )}
              </div>
            )}

            <div className="min-h-0 flex-1 overflow-hidden rounded-2xl">
              <div className="h-full overflow-y-auto pr-2">
                <SequenceViewer {...viewerProps} />
              </div>
            </div>
          </section>

          <section className="h-[calc(100vh-2rem)] min-h-0 overflow-hidden rounded-2xl">
            <div className="h-full overflow-y-auto pr-2">
              <Results {...resultsProps} />
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
            <UploadFile {...uploadProps} />
          </div>

          {loading && taskStatus && (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
              <p className="text-sm text-slate-700">
                <span className="font-medium">Background task status:</span>{" "}
                {taskStatus}
              </p>
              {taskId && (
                <p className="mt-1 text-xs text-slate-500">
                  Task ID: {taskId}
                </p>
              )}
            </div>
          )}

          <SequenceViewer {...viewerProps} />

          <Results {...resultsProps} />

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
