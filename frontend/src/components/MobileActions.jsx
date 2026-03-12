import bgImage from "../assets/bgh.jpg"

export default function MobileActions({
  results,
  onRunAnalysis,
  onDownload,
  onClear,
}) {
  return (
    <section className="sticky top-0 h-screen rounded-2xl border border-slate-200 backdrop-blur-md p-6 shadow-sm bg-cover bg-center lg:hidden"
      style={{ backgroundImage: `url(${bgImage})` }} >
      <h3 className="mb-4 text-lg font-semibold text-slate-900">
        Analysis Actions
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => onRunAnalysis("orfs")}
          className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white"
        >
          Find ORFs
        </button>
        <button
         onClick={() => onRunAnalysis("coding-orfs")}
          className="rounded-xl bg-slate-900  px-4 py-3 text-sm font-medium text-white"
        >
         Coding ORFs
        </button>

        <button
          onClick={() => onRunAnalysis("promoters")}
          className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white"
        >
          Promoters
        </button>

        <button
          onClick={() => onRunAnalysis("terminators")}
          className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white"
        >
          Terminators
        </button>

        <button
          onClick={() => onRunAnalysis("shine-dalgarno")}
          className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white"
        >
          Shine-Dalgarno
        </button>

        <button
          onClick={() => onRunAnalysis("all")}
          className="col-span-2 rounded-xl bg-cyan-600 px-4 py-3 text-sm font-medium text-white"
        >
          Run Full Analysis
        </button>

        <button
          onClick={onDownload}
          disabled={!results}
          className="col-span-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          Download Results
        </button>

        <button
          onClick={onClear}
          className="col-span-2 rounded-xl bg-red-500 px-4 py-3 text-sm font-medium text-white"
        >
          Clear Data
        </button>
      </div>
    </section>
  );
}
