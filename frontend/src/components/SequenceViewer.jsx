import { useMemo } from "react";
import bgImage from "../assets/bgh.jpg"

function StatCard({ title, value, subtitle }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

function getHighlightClass(pos, highlights) {
  const hit = highlights.find((h) => pos >= h.start && pos <= h.end);

  if (!hit) return "text-slate-800";

  switch (hit.type) {
    case "promoter35":
      return "bg-yellow-300 text-black rounded px-[1px]";
    case "promoter10":
      return "bg-orange-300 text-black rounded px-[1px]";
    case "terminatorLeft":
      return "bg-pink-300 text-black rounded px-[1px]";
    case "terminatorRight":
      return "bg-fuchsia-300 text-black rounded px-[1px]";
    case "polyT":
      return "bg-red-300 text-black rounded px-[1px]";
    case "orf":
      return "bg-cyan-300 text-black rounded px-[1px]";
    default:
      return "bg-lime-300 text-black rounded px-[1px]";
  }
}

function reverseComplement(sequence) {
  const map = {
    A: "T",
    T: "A",
    G: "C",
    C: "G",
    N: "N",
  };

  return sequence
    .split("")
    .reverse()
    .map((base) => map[base] || "N")
    .join("");
}

function SequencePreview({ preview, highlights = [] }) {
  if (!preview) {
    return (
      <div className="font-mono text-xs leading-6 text-slate-500">
        No sequence loaded.
      </div>
    );
  }

  return (
    <div className="max-h-80 overflow-y-auto overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs leading-6">
      {preview.split("").map((char, index) => {
        if (char === ".") {
          return (
            <span key={index} className="text-slate-400">
              {char}
            </span>
          );
        }

        const pos = index + 1;
        const cls = getHighlightClass(pos, highlights || []);

        return (
          <span key={index} className={cls}>
            {char}
          </span>
        );
      })}
    </div>
  );
}

export default function SequenceViewer({
  sequence,
  setSequence,
  loadedFileName,
  folderFiles,
  mode,
  highlights = [],
}) {
  const stats = useMemo(() => {
    const seq = sequence.replace(/\s+/g, "").toUpperCase();
    const length = seq.length;
    const gcCount = (seq.match(/[GC]/g) || []).length;
    const atCount = (seq.match(/[AT]/g) || []).length;

    return {
      length,
      gc: length ? ((gcCount / length) * 100).toFixed(2) : "0.00",
      at: length ? ((atCount / length) * 100).toFixed(2) : "0.00",
    };
  }, [sequence]);

  const cleanSequence = sequence.replace(/\s+/g, "").toUpperCase();
  const reverseSeq = reverseComplement(cleanSequence);

  const forwardPreview =
    cleanSequence.length > 3000
      ? `${cleanSequence.slice(0, 3000)}...`
      : cleanSequence;

  const reversePreview = reverseSeq.length > 3000 ? `${reverseSeq.slice(0, 3000)}...` : reverseSeq;

  const selectedStrand = highlights?.[0]?.strand ?? "+";

  const forwardHighlights =
    selectedStrand === "+" || !highlights.length ? highlights : [];

 const reverseHighlights =
  selectedStrand === "-"
    ? highlights.map((h) => ({
        ...h,
        start: cleanSequence.length - h.end + 1,
        end: cleanSequence.length - h.start + 1,
      }))
    : [];

  return (
    <section  className="rounded-2xl border border-slate-200 backdrop-blur-md p-6 shadow-sm bg-cover bg-center"
  style={{ backgroundImage: `url(${bgImage})` }}>
      <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
        <span className="font-medium">Loaded source:</span>{" "}
        {loadedFileName || "No file selected"}
      </div>

      {mode === "folder" && folderFiles.length > 0 && (
        <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="mb-2 text-sm font-medium text-slate-800">
            Files in folder
          </p>
          <div className="max-h-36 space-y-2 overflow-auto">
            {folderFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
              >
                {file.name}
              </div>
            ))}
          </div>
        </div>
      )}

      <label className="mb-2 block text-sm font-medium text-slate-900">
        DNA Sequence
      </label>

      <textarea
        value={sequence}
        onChange={(e) => setSequence(e.target.value.toUpperCase())}
        rows={14}
        spellCheck={false}
        className="w-full rounded-xl border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-900 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
        placeholder="Paste DNA sequence here..."
      />

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <StatCard title="Length" value={stats.length} subtitle="nucleotides" />
        <StatCard title="GC%" value={stats.gc} subtitle="GC content" />
        <StatCard title="AT%" value={stats.at} subtitle="AT content" />
      </div>

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-700">
            Forward Sequence Preview (5' → 3')
          </p>
        </div>

        <SequencePreview
          preview={forwardPreview}
          highlights={forwardHighlights}
        />
      </div>

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-700">
            Reverse Complement Preview (5' → 3')
          </p>
        </div>

        <SequencePreview
          preview={reversePreview}
          highlights={reverseHighlights}
        />
      </div>
    </section>
  );
}
