import bgImage from "../assets/bgh.jpg";

function SidebarButton({
  children,
  onClick,
  className = "",
  disabled = false,
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-slate-400 ${className}`}
    >
      {children}
    </button>
  );
}

export default function Sidebar({
  mode,
  folderFiles,
  results,
  onRunAnalysis,
  onDownload,
  onClear,
}) {
  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <div
        className="sticky top-0 h-screen rounded-2xl border border-slate-200/80 bg-cover bg-center p-4 shadow-sm"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <div className="h-full rounded-2xl bg-white/78 p-4 backdrop-blur-md">
          <div className="mb-4">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              DNA Analyzer
            </h1>
          </div>

          <div className="space-y-2">
            <SidebarButton
              onClick={() => onRunAnalysis("orfs")}
              className="bg-slate-900 hover:bg-slate-800"
            >
              Find ORFs
            </SidebarButton>

            <SidebarButton
              onClick={() => onRunAnalysis("coding-orfs")}
              className="bg-slate-900 hover:bg-slate-800"
            >
              Find Coding ORFs
            </SidebarButton>

            <SidebarButton
              onClick={() => onRunAnalysis("promoters")}
              className="bg-slate-900 hover:bg-slate-800"
            >
              Detect Promoters
            </SidebarButton>

            <SidebarButton
              onClick={() => onRunAnalysis("terminators")}
              className="bg-slate-900 hover:bg-slate-800"
            >
              Detect Terminators
            </SidebarButton>

            <SidebarButton
              onClick={() => onRunAnalysis("shine-dalgarno")}
              className="bg-slate-900 hover:bg-slate-800"
            >
              Detect Shine-Dalgarno
            </SidebarButton>

            <SidebarButton
              onClick={() => onRunAnalysis("ranked-coding-orfs")}
              className="bg-fuchsia-700 hover:bg-fuchsia-600"
            >
              Most Plausible Coding ORFs
            </SidebarButton>

            <div className="my-3 h-px bg-slate-200" />

            <SidebarButton
              onClick={() => onRunAnalysis("all")}
              className="bg-cyan-600 hover:bg-cyan-700"
            >
              Run Full Analysis
            </SidebarButton>

            <SidebarButton
              onClick={onDownload}
              disabled={!results}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              Download Results
            </SidebarButton>

            <SidebarButton
              onClick={onClear}
              className="bg-red-500 hover:bg-red-600"
            >
              Clear Data
            </SidebarButton>
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-white/70 p-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Mode
            </p>
            <p className="mt-1 text-sm text-slate-700">
              {mode === "folder"
                ? `Folder mode (${folderFiles.length} files)`
                : "Single sequence mode"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}