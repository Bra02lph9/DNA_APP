import { useEffect, useMemo, useState } from "react";
import bgImage from "../assets/bgh.jpg";

const LINE_LENGTH = 60;
const LEFT_INDEX_WIDTH = "w-14";
const SIDE_LABEL_WIDTH = "w-6";
const DEFAULT_WINDOW_SIZE = 3000;
const MIN_MINIMAP_WINDOW = 200;

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

function complementBase(base) {
  const map = { A: "T", T: "A", G: "C", C: "G", N: "N" };
  return map[base] || base;
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

function buildHighlightLookup(highlights, visibleStart, visibleEnd) {
  const lookup = new Map();

  for (const h of highlights) {
    if (h?.start == null || h?.end == null) continue;

    const start = Math.max(h.start, visibleStart);
    const end = Math.min(h.end, visibleEnd);

    if (start > end) continue;

    for (let pos = start; pos <= end; pos++) {
      if (!lookup.has(pos)) {
        lookup.set(pos, []);
      }
      lookup.get(pos).push(h);
    }
  }

  return lookup;
}

function getHighlightClass(pos, highlightLookup) {
  const hits = highlightLookup.get(pos) || [];
  if (!hits.length) return "text-slate-800";

  const priority = [
    "startCodon",
    "shineDalgarno",
    "promoter35",
    "promoter10",
    "terminatorLeft",
    "terminatorRight",
    "polyT",
    "orf",
  ];

  hits.sort((a, b) => priority.indexOf(a.type) - priority.indexOf(b.type));
  const hit = hits[0];

  switch (hit.type) {
    case "startCodon":
      return "bg-blue-600 text-white rounded px-[2px] shadow-sm";
    case "shineDalgarno":
      return "bg-lime-300 text-black rounded px-[2px] shadow-sm";
    case "promoter35":
      return "bg-yellow-300 text-black rounded px-[2px] shadow-sm";
    case "promoter10":
      return "bg-orange-300 text-black rounded px-[2px] shadow-sm";
    case "terminatorLeft":
      return "bg-pink-300 text-black rounded px-[2px] shadow-sm";
    case "terminatorRight":
      return "bg-rose-300 text-black rounded px-[2px] shadow-sm";
    case "polyT":
      return "bg-red-300 text-black rounded px-[2px] shadow-sm";
    case "orf":
      return "bg-cyan-300 text-black rounded px-[2px] shadow-sm";
    default:
      return "text-slate-800";
  }
}

function renderRulerLine(start, length) {
  const chars = Array(length).fill("");

  for (let pos = start; pos < start + length; pos++) {
    if (pos % 10 === 0) {
      const label = String(pos);
      const column = pos - start;
      const labelStart = column - label.length + 1;

      if (labelStart >= 0) {
        for (let i = 0; i < label.length; i++) {
          if (labelStart + i < length) {
            chars[labelStart + i] = label[i];
          }
        }
      }
    }
  }

  return chars.map((char, index) => (
    <span
      key={index}
      className="inline-block w-[1ch] text-center align-middle text-slate-400"
    >
      {char || " "}
    </span>
  ));
}

function renderMatchLine(line) {
  return line.split("").map((char, index) => (
    <span
      key={index}
      className="inline-block w-[1ch] text-center align-middle text-slate-500"
    >
      {/[ATGCN]/i.test(char) ? "|" : " "}
    </span>
  ));
}

function renderSequenceLine(line, startPos, highlightLookup) {
  let currentPos = startPos;

  const rendered = line.split("").map((char, index) => {
    if (/[ATGCN]/i.test(char)) {
      const cls = getHighlightClass(currentPos, highlightLookup);

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

  return { rendered, nextPos: currentPos };
}

function renderComplementLine(line, startPos, highlightLookup) {
  let currentPos = startPos;

  const rendered = line.split("").map((char, index) => {
    if (/[ATGCN]/i.test(char)) {
      const comp = complementBase(char.toUpperCase());
      const cls = getHighlightClass(currentPos, highlightLookup);

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

  return { rendered, nextPos: currentPos };
}

function SequenceRow({ leftLabel, leftTag, content, rightTag }) {
  return (
    <div className="flex min-w-max items-center whitespace-nowrap">
      <span
        className={`mr-3 inline-block ${LEFT_INDEX_WIDTH} text-right text-slate-500`}
      >
        {leftLabel}
      </span>
      <span
        className={`mr-2 inline-block ${SIDE_LABEL_WIDTH} text-slate-500`}
      >
        {leftTag || ""}
      </span>
      <div className="inline-block">{content}</div>
      <span
        className={`ml-2 inline-block ${SIDE_LABEL_WIDTH} text-slate-500`}
      >
        {rightTag || ""}
      </span>
    </div>
  );
}

function DoubleStrandPreview({
  sequence,
  highlights = [],
  globalStart = 1,
}) {
  const cleanSequence = sequence.replace(/[^ATGCN]/gi, "").toUpperCase();
  const visibleEnd = globalStart + cleanSequence.length - 1;

  const highlightLookup = useMemo(
    () => buildHighlightLookup(highlights, globalStart, visibleEnd),
    [highlights, globalStart, visibleEnd]
  );

  if (!cleanSequence) {
    return (
      <div className="font-mono text-xs leading-6 text-slate-500">
        No sequence loaded.
      </div>
    );
  }

  const chunks = chunkSequence(cleanSequence, LINE_LENGTH);
  let biologicalPos = globalStart;

  return (
    <div className="max-h-96 overflow-auto rounded-lg bg-white/70 p-3 font-mono text-sm leading-6">
      {chunks.map((line, lineIndex) => {
        const top = renderSequenceLine(line, biologicalPos, highlightLookup);
        const bottom = renderComplementLine(line, biologicalPos, highlightLookup);

        const startLabel = biologicalPos;
        const endLabel = top.nextPos - 1;

        const topRuler = renderRulerLine(startLabel, line.length);
        const bottomRuler = renderRulerLine(startLabel, line.length);
        const matchLine = renderMatchLine(line);

        biologicalPos = top.nextPos;

        return (
          <div key={lineIndex} className="mb-4">
            <SequenceRow leftLabel="" leftTag="" content={topRuler} rightTag="" />
            <SequenceRow
              leftLabel={startLabel}
              leftTag="5'"
              content={top.rendered}
              rightTag="3'"
            />
            <SequenceRow leftLabel="" leftTag="" content={matchLine} rightTag="" />
            <SequenceRow
              leftLabel={startLabel}
              leftTag="3'"
              content={bottom.rendered}
              rightTag="5'"
            />
            <SequenceRow leftLabel="" leftTag="" content={bottomRuler} rightTag="" />

            <div className="mt-1 flex justify-between text-[11px] text-slate-400">
              <span>Range: {startLabel.toLocaleString()}</span>
              <span>{endLabel.toLocaleString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function GenomeMiniMap({
  sequenceLength,
  features = [],
  onJumpToFeature,
  zoomStart,
  zoomWindowSize,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  onPanTo,
}) {
  if (!sequenceLength) return null;

  const zoomEnd = Math.min(sequenceLength, zoomStart + zoomWindowSize - 1);

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

  const colorByType = Object.fromEntries(
    trackConfig.map((item) => [item.key, item.color])
  );
  const labelByType = Object.fromEntries(
    trackConfig.map((item) => [item.key, item.label])
  );

  const visibleFeatures = features.filter((feature) => {
    if (feature?.start == null || feature?.end == null) return false;
    return !(feature.end < zoomStart || feature.start > zoomEnd);
  });

  const handleTrackClick = (e) => {
    if (!onPanTo) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const clickedPos = Math.round(zoomStart + ratio * (zoomWindowSize - 1));
    onPanTo(clickedPos);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Genome Mini Map</h3>
          <p className="text-xs text-slate-500">
            Zoomable overview of genomic features
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onZoomIn}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            Zoom +
          </button>

          <button
            type="button"
            onClick={onZoomOut}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            Zoom -
          </button>

          <button
            type="button"
            onClick={onResetZoom}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
        <span>{zoomStart.toLocaleString()}</span>
        <span>Window: {zoomWindowSize.toLocaleString()} nt</span>
        <span>{zoomEnd.toLocaleString()}</span>
      </div>

      <div
        className="relative h-6 cursor-pointer overflow-hidden rounded-full bg-slate-200/80 shadow-inner"
        onClick={handleTrackClick}
        title="Click to pan inside the zoomed region"
      >
        {visibleFeatures.length === 0 ? (
          <div className="absolute inset-0 rounded-full border border-dashed border-slate-300" />
        ) : (
          visibleFeatures.map((feature, index) => {
            const localStart = Math.max(feature.start, zoomStart);
            const localEnd = Math.min(feature.end, zoomEnd);

            const left = ((localStart - zoomStart) / zoomWindowSize) * 100;
            const width = Math.max(
              ((localEnd - localStart + 1) / zoomWindowSize) * 100,
              0.3
            );

            return (
              <button
                key={`${feature.type}-${feature.start}-${feature.end}-${index}`}
                type="button"
                title={`${labelByType[feature.type] || feature.type}: ${feature.start}-${feature.end}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onJumpToFeature?.(feature);
                }}
                className={`absolute top-0 h-6 ${
                  colorByType[feature.type] || "bg-sky-400"
                } ring-1 ring-black/10 transition hover:scale-y-110 hover:shadow-md`}
                style={{ left: `${left}%`, width: `${width}%` }}
              />
            );
          })
        )}
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

export default function SequenceViewer({
  sequence,
  setSequence,
  loadedFileName,
  folderFiles,
  mode,
  highlights = [],
  sequenceMeta = null,
  fullSequenceRef = null,
}) {
  const [viewStart, setViewStart] = useState(1);
  const [windowSize, setWindowSize] = useState(DEFAULT_WINDOW_SIZE);
  const [miniMapStart, setMiniMapStart] = useState(1);
  const [miniMapWindowSize, setMiniMapWindowSize] = useState(DEFAULT_WINDOW_SIZE);

  const fullSequence = fullSequenceRef?.current || sequence || "";
  const cleanFullSequence = useMemo(
    () => fullSequence.replace(/[^ATGCN]/gi, "").toUpperCase(),
    [fullSequence]
  );

  const totalLength = sequenceMeta?.length || cleanFullSequence.length;

  useEffect(() => {
    setViewStart(1);
    setMiniMapStart(1);
  }, [loadedFileName]);

  useEffect(() => {
    if (totalLength > 0) {
      setMiniMapWindowSize(Math.min(DEFAULT_WINDOW_SIZE, totalLength));
      setMiniMapStart(1);
    }
  }, [totalLength, loadedFileName]);

  const visibleSequence = useMemo(() => {
    if (!cleanFullSequence) return "";
    const startIdx = Math.max(0, viewStart - 1);
    const endIdx = Math.min(cleanFullSequence.length, startIdx + windowSize);
    return cleanFullSequence.slice(startIdx, endIdx);
  }, [cleanFullSequence, viewStart, windowSize]);

  const visibleEnd = useMemo(() => {
    if (!visibleSequence.length) return viewStart;
    return viewStart + visibleSequence.length - 1;
  }, [viewStart, visibleSequence]);

  const stats = useMemo(() => {
    const seq = cleanFullSequence;
    const length = seq.length;
    const gcCount = (seq.match(/[GC]/g) || []).length;
    const atCount = (seq.match(/[AT]/g) || []).length;

    return {
      length,
      gc: length ? ((gcCount / length) * 100).toFixed(2) : "0.00",
      at: length ? ((atCount / length) * 100).toFixed(2) : "0.00",
    };
  }, [cleanFullSequence]);

  const displaySequence = useMemo(() => {
    return formatSequenceForDisplay(visibleSequence, LINE_LENGTH);
  }, [visibleSequence]);

  const miniMapFeatures = useMemo(() => {
    return highlights
      .filter((h) => h?.start != null && h?.end != null)
      .map((h, index) => ({
        id: `${h.type}-${index}`,
        start: h.start,
        end: h.end,
        type: h.type,
      }));
  }, [highlights]);

  const clampMiniMapWindow = (size) => {
    if (!totalLength) return DEFAULT_WINDOW_SIZE;
    return Math.max(MIN_MINIMAP_WINDOW, Math.min(size, totalLength));
  };

  const clampMiniMapStart = (start, currentWindowSize) => {
    if (!totalLength) return 1;
    const maxStart = Math.max(1, totalLength - currentWindowSize + 1);
    return Math.max(1, Math.min(start, maxStart));
  };

  const syncMiniMapToView = (startPos, currentWindowSize = miniMapWindowSize) => {
    const newStart = clampMiniMapStart(startPos, currentWindowSize);
    setMiniMapStart(newStart);
  };

  const jumpToPosition = (position) => {
    if (!totalLength) return;

    const safePos = Math.min(Math.max(1, position), totalLength);
    const half = Math.floor(windowSize / 2);
    let newStart = safePos - half;

    if (newStart < 1) newStart = 1;
    if (newStart + windowSize - 1 > totalLength) {
      newStart = Math.max(1, totalLength - windowSize + 1);
    }

    setViewStart(newStart);
    syncMiniMapToView(newStart);

    requestAnimationFrame(() => {
      const el = document.getElementById(`base-${safePos}`);
      if (el) {
        el.scrollIntoView({
          behavior: "smooth",
          block: "center",
          inline: "center",
        });
      }
    });
  };

  const handleJumpToFeature = (feature) => {
    if (!feature?.start) return;
    jumpToPosition(feature.start);
  };

  const handleWindowSizeChange = (e) => {
    const newSize = Number(e.target.value);
    if (!Number.isFinite(newSize) || newSize <= 0) return;
    setWindowSize(newSize);
  };

  const zoomMiniMap = (factor) => {
    if (!totalLength) return;

    const center = miniMapStart + Math.floor(miniMapWindowSize / 2);
    const newWindow = clampMiniMapWindow(Math.round(miniMapWindowSize * factor));
    const newStart = clampMiniMapStart(
      center - Math.floor(newWindow / 2),
      newWindow
    );

    setMiniMapWindowSize(newWindow);
    setMiniMapStart(newStart);
  };

  const zoomInMiniMap = () => zoomMiniMap(0.5);
  const zoomOutMiniMap = () => zoomMiniMap(2);

  const resetMiniMapZoom = () => {
    if (!totalLength) return;
    setMiniMapWindowSize(totalLength);
    setMiniMapStart(1);
  };

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
          <p className="mb-2 text-sm font-medium text-slate-800">Files in folder</p>
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

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Length"
          value={stats.length.toLocaleString()}
          subtitle="nucleotides"
        />
        <StatCard title="GC%" value={stats.gc} subtitle="GC content" />
        <StatCard title="AT%" value={stats.at} subtitle="AT content" />
      </div>

      <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-medium text-slate-800">Visible window</p>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => jumpToPosition(Math.max(1, viewStart - windowSize))}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
            >
              Prev
            </button>

            <button
              type="button"
              onClick={() =>
                jumpToPosition(Math.min(totalLength, viewStart + windowSize))
              }
              className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
            >
              Next
            </button>

            <select
              value={windowSize}
              onChange={handleWindowSizeChange}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700"
            >
              <option value={1000}>1000 nt</option>
              <option value={3000}>3000 nt</option>
              <option value={5000}>5000 nt</option>
              <option value={10000}>10000 nt</option>
              <option value={50000}>50000 nt</option>
            </select>
          </div>
        </div>

        <p className="text-sm text-slate-600">
          Showing positions <span className="font-medium">{viewStart.toLocaleString()}</span> to{" "}
          <span className="font-medium">{visibleEnd.toLocaleString()}</span>
        </p>
      </div>

      {totalLength > 0 && (
        <div className="mt-5">
          <GenomeMiniMap
            sequenceLength={totalLength}
            features={miniMapFeatures}
            onJumpToFeature={handleJumpToFeature}
            zoomStart={miniMapStart}
            zoomWindowSize={miniMapWindowSize}
            onZoomIn={zoomInMiniMap}
            onZoomOut={zoomOutMiniMap}
            onResetZoom={resetMiniMapZoom}
            onPanTo={(position) => {
              const half = Math.floor(miniMapWindowSize / 2);
              const newStart = clampMiniMapStart(
                position - half,
                miniMapWindowSize
              );
              setMiniMapStart(newStart);
              jumpToPosition(position);
            }}
          />
        </div>
      )}

      <label className="mt-5 mb-2 block text-sm font-medium text-slate-900">
        DNA Sequence Window
      </label>

      <textarea
        value={displaySequence}
        readOnly
        rows={14}
        wrap="off"
        spellCheck={false}
        className="w-full overflow-x-auto rounded-xl border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-900 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200"
        placeholder="DNA sequence window..."
      />

      <p className="mt-2 text-xs text-slate-600">
        This viewer is read-only. Use feature clicks and the mini map to navigate long sequences safely.
      </p>

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-700">
            DNA Double Strand Preview
          </p>
        </div>

        <DoubleStrandPreview
          sequence={visibleSequence}
          highlights={highlights}
          globalStart={viewStart}
        />
      </div>
    </section>
  );
}
