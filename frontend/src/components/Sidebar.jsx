import bgImage from "../assets/bgh.jpg"
export default function Sidebar({
  mode,
  folderFiles,
  results,
  onRunAnalysis,
  onDownload,
  onClear,
}) {
  return (
    <aside className="hidden w-72 shrink-0 lg:block">
     <div
       className="sticky top-0 h-screen rounded-2xl border border-slate-200 backdrop-blur-md p-6 shadow-sm bg-cover bg-center"
       style={{ backgroundImage: `url(${bgImage})` }}
       >
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">DNA Analyzer</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Analyse ORFs, promoters, terminators and Shine-Dalgarno motifs.
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => onRunAnalysis("orfs")}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Find ORFs
          </button>

          <button
            onClick={() => onRunAnalysis("coding-orfs")}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Find Coding ORFs
          </button>

          <button
            onClick={() => onRunAnalysis("promoters")}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Detect Promoters
          </button>

          <button
            onClick={() => onRunAnalysis("terminators")}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Detect Terminators
          </button>

          <button
            onClick={() => onRunAnalysis("shine-dalgarno")}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Detect Shine-Dalgarno
          </button>

          <button
            onClick={() => onRunAnalysis("all")}
            className="w-full rounded-xl bg-cyan-600 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-cyan-700"
          >
            Run Full Analysis
          </button>

          <button
            onClick={onDownload}
            disabled={!results}
            className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            Download Results
          </button>

          <button
            onClick={onClear}
            className="w-full rounded-xl bg-red-500 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-red-600"
          >
            Clear Data
          </button>
        </div>

        <div className="mt-6 rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Mode
          </p>
          <p className="mt-2 text-sm text-slate-700">
            {mode === "folder"
              ? `Folder mode (${folderFiles.length} files)`
              : "Single sequence mode"}
          </p>
        </div>
      </div>
    </aside>
  );
}