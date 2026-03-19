import { useMemo } from "react";
import bgImage from "../assets/bgh.jpg";

const LINE_LENGTH = 100;

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
      return "bg-yellow-300 text-black rounded-sm";
    case "promoter10":
      return "bg-orange-300 text-black rounded-sm";
    case "terminatorLeft":
      return "bg-pink-300 text-black rounded-sm";
    case "terminatorRight":
      return "bg-fuchsia-300 text-black rounded-sm";
    case "polyT":
      return "bg-red-300 text-black rounded-sm";
    case "orf":
      return "bg-cyan-300 text-black rounded-sm";
    case "shineDalgarno":
      return "bg-lime-300 text-black rounded-sm";
    case "startCodon":
      return "bg-emerald-300 text-black rounded-sm";
    default:
      return "bg-sky-300 text-black rounded-sm";
  }
}

function complementBase(base) {
  const map = {
    A: "T",
    T: "A",
    G: "C",
    C: "G",
    N: "N",
  };
  return map[base] || base;
}

function buildMatchLine(line) {
  return line
    .split("")
    .map((char) => (/[ATGCN]/i.test(char) ? "|" : " "))
    .join("");
}

function chunkSequence(seq, chunkSize = LINE_LENGTH) {
  const chunks = [];
  for (let i = 0; i < seq.length; i += chunkSize) {
    chunks.push(seq.slice(i, i + chunkSize));
  }
  return chunks;
}

function formatSequenceForDisplay(seq, lineLength = LINE_LENGTH) {
  const clean = seq.replace(/[^ATGCN]/gi, "").toUpperCase();
  return chunkSequence(clean, lineLength).join("\n");
}

function buildForwardRuler(start, length) {
  const chars = Array(length).fill(" ");

  for (let pos = start; pos < start + length; pos++) {
    if (pos % 10 === 0) {
      const label = String(pos);
      const index = pos - start - label.length + 1;

      if (index >= 0) {
        for (let i = 0; i < label.length && index + i < chars.length; i++) {
          chars[index + i] = label[i];
        }
      }
    }
  }

  return chars.join("");
}

function buildReverseRuler(start, length) {
  const chars = Array(length).fill(" ");
  const end = start + length - 1;

  for (let pos = end; pos >= start; pos--) {
    if (pos % 10 === 0) {
      const label = String(pos);
      const index = end - pos;

      if (index + label.length <= chars.length) {
        for (let i = 0; i < label.length; i++) {
          chars[index + i] = label[i];
        }
      }
    }
  }

  return chars.join("");
}

function renderSequenceLine(line, startPos, highlights = []) {
  let currentPos = startPos;

  const rendered = line.split("").map((char, index) => {
    if (/[ATGCN]/i.test(char)) {
      const cls = getHighlightClass(currentPos, highlights);

      const element = (
        <span
          key={index}
          id={`base-${currentPos}`}
          title={`Position ${currentPos}`}
          className={`${cls} inline-block w-[1ch] text-center align-middle`}
        >
          {char}
        </span>
      );

      currentPos += 1;
      return element;
    }

    return (
      <span
        key={index}
        className="inline-block w-[1ch] text-center align-middle text-slate-400"
      >
        {char}
      </span>
    );
  });

  return {
    rendered,
    nextPos: currentPos,
  };
}

function renderComplementLine(line, startPos, highlights = []) {
  let currentPos = startPos;

  const rendered = line.split("").map((char, index) => {
    if (/[ATGCN]/i.test(char)) {
      const comp = complementBase(char.toUpperCase());
      const cls = getHighlightClass(currentPos, highlights);

      const element = (
        <span
          key={index}
          title={`Complement of position ${currentPos}`}
          className={`${cls} inline-block w-[1ch] text-center align-middle`}
        >
          {comp}
        </span>
      );

      currentPos += 1;
      return element;
    }

    return (
      <span
        key={index}
        className="inline-block w-[1ch] text-center align-middle text-slate-400"
      >
        {char}
      </span>
    );
  });

  return {
    rendered,
    nextPos: currentPos,
  };
}

function GenomeMiniMap({ sequenceLength, features = [] }) {
  if (!sequenceLength) return null;

  const trackConfig = [
    { key: "orf", label: "ORF", color: "bg-cyan-400" },
    { key: "promoter35", label: "Promoter -35", color: "bg-yellow-400" },
    { key: "promoter10", label: "Promoter -10", color: "bg-orange-400" },
    { key: "terminatorLeft", label: "Terminator L", color: "bg-pink-400" },
    { key: "terminatorRight", label: "Terminator R", color: "bg-fuchsia-400" },
    { key: "polyT", label: "Poly-T", color: "bg-red-400" },
    { key: "shineDalgarno", label: "Shine-Dalgarno", color: "bg-lime-400" },
    { key: "startCodon", label: "Start codon", color: "bg-emerald-400" },
  ];

  const grouped = trackConfig.map((track) => ({
    ...track,
    features: features.filter((f) => f.type === track.key),
  }));

  const handleScrollToFeature = (feature) => {
    const el = document.getElementById(`base-${feature.start}`);
    if (el) {
      el.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "center",
      });
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Genome Mini Map</h3>
          <p className="text-xs text-slate-500">
            Interactive overview of selected genomic features
          </p>
        </div>

        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          {sequenceLength} nt
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between text-xs text-slate-500">
        <span>1</span>
        <span>{Math.floor(sequenceLength / 2)}</span>
        <span>{sequenceLength}</span>
      </div>

      <div className="space-y-3">
        {grouped.map((track) => (
          <div key={track.key} className="grid grid-cols-[120px_1fr] items-center gap-3">
            <div className="text-xs font-medium text-slate-600">
              {track.label}
            </div>

            <div className="relative h-5 rounded-full bg-slate-200/80 shadow-inner">
              {track.features.length === 0 ? (
                <div className="absolute inset-0 rounded-full border border-dashed border-slate-300" />
              ) : (
                track.features.map((feature, index) => {
                  const start = Math.max(1, feature.start);
                  const end = Math.max(start, feature.end);
                  const left = ((start - 1) / sequenceLength) * 100;
                  const width = Math.max(
                    ((end - start + 1) / sequenceLength) * 100,
                    1
                  );

                  return (
                    <button
                      key={`${feature.type}-${feature.start}-${feature.end}-${index}`}
                      type="button"
                      title={`${track.label}: ${feature.start}-${feature.end}`}
                      onClick={() => handleScrollToFeature(feature)}
                      className={`absolute top-0 h-5 rounded-full ${track.color} ring-1 ring-black/10 transition hover:scale-y-110 hover:shadow-md`}
                      style={{
                        left: `${left}%`,
                        width: `${width}%`,
                      }}
                    />
                  );
                })
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 border-t border-slate-200 pt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Legend
        </p>

        <div className="flex flex-wrap gap-2">
          {trackConfig.map((track) => (
            <div
              key={track.key}
              className="flex items-center gap-2 rounded-full bg-slate-50 px-3 py-1 text-xs text-slate-700"
            >
              <span className={`h-3 w-3 rounded-full ${track.color}`} />
              <span>{track.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DoubleStrandPreview({ sequence, highlights = [] }) {
  const cleanSequence = sequence.replace(/[^ATGCN]/gi, "").toUpperCase();

  if (!cleanSequence) {
    return (
      <div className="font-mono text-xs leading-6 text-slate-500">
        No sequence loaded.
      </div>
    );
  }

  const chunks = chunkSequence(cleanSequence, LINE_LENGTH);
  let biologicalPos = 1;

  return (
    <div className="max-h-96 overflow-y-auto overflow-x-auto rounded-lg bg-white/70 p-3 font-mono text-sm leading-6">
      {chunks.map((line, lineIndex) => {
        const top = renderSequenceLine(line, biologicalPos, highlights);
        const bottom = renderComplementLine(line, biologicalPos, highlights);
        const matchLine = buildMatchLine(line);
        const startLabel = biologicalPos;
        const endLabel = top.nextPos - 1;
        const topRuler = buildForwardRuler(startLabel, line.length);
        const bottomRuler = buildReverseRuler(startLabel, line.length);

        biologicalPos = top.nextPos;

        return (
          <div key={lineIndex} className="mb-4 min-w-max">
            <div className="whitespace-pre text-xs text-slate-400">
              <span className="mr-3 inline-block w-14 text-right"></span>
              <span className="mr-2"></span>
              {topRuler}
            </div>

            <div className="whitespace-pre">
              <span className="mr-3 inline-block w-14 text-right text-slate-500">
                {startLabel}
              </span>
              <span className="mr-2 text-slate-500">5&apos;</span>
              {top.rendered}
              <span className="ml-2 text-slate-500">3&apos;</span>
            </div>

            <div className="whitespace-pre text-slate-500">
              <span className="mr-3 inline-block w-14 text-right"></span>
              <span className="mr-2">  </span>
              <span className="inline-block">{matchLine}</span>
            </div>

            <div className="whitespace-pre">
              <span className="mr-3 inline-block w-14 text-right text-slate-500">
                {endLabel}
              </span>
              <span className="mr-2 text-slate-500">3&apos;</span>
              {bottom.rendered}
              <span className="ml-2 text-slate-500">5&apos;</span>
            </div>

            <div className="whitespace-pre text-xs text-slate-400">
              <span className="mr-3 inline-block w-14 text-right"></span>
              <span className="mr-2"></span>
              {bottomRuler}
            </div>
          </div>
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
    const seq = sequence.replace(/[^ATGCN]/gi, "").toUpperCase();
    const length = seq.length;
    const gcCount = (seq.match(/[GC]/g) || []).length;
    const atCount = (seq.match(/[AT]/g) || []).length;

    return {
      length,
      gc: length ? ((gcCount / length) * 100).toFixed(2) : "0.00",
      at: length ? ((atCount / length) * 100).toFixed(2) : "0.00",
    };
  }, [sequence]);

  const cleanSequence = useMemo(() => {
    return sequence.replace(/[^ATGCN]/gi, "").toUpperCase();
  }, [sequence]);

  const displaySequence = useMemo(() => {
    return formatSequenceForDisplay(sequence, LINE_LENGTH);
  }, [sequence]);

  const miniMapFeatures = useMemo(() => {
    return highlights.map((h, index) => ({
      id: `${h.type}-${index}`,
      start: h.start,
      end: h.end,
      type: h.type,
    }));
  }, [highlights]);

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
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
        value={displaySequence}
        onChange={(e) => {
          const raw = e.target.value.replace(/[^ATGCN]/gi, "");
          setSequence(raw.toUpperCase());
        }}
        rows={14}
        wrap="off"
        spellCheck={false}
        className="w-full overflow-x-auto rounded-xl border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-900 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
        placeholder="Paste DNA sequence here..."
      />

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <StatCard title="Length" value={stats.length} subtitle="nucleotides" />
        <StatCard title="GC%" value={stats.gc} subtitle="GC content" />
        <StatCard title="AT%" value={stats.at} subtitle="AT content" />
      </div>

      {cleanSequence.length > 0 && (
        <div className="mt-5">
          <GenomeMiniMap
            sequenceLength={cleanSequence.length}
            features={miniMapFeatures}
          />
        </div>
      )}

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-700">
            DNA Double Strand Preview
          </p>
        </div>

        <DoubleStrandPreview sequence={sequence} highlights={highlights} />
      </div>
    </section>
  );
}
