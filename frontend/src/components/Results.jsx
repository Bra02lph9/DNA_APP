import { useEffect, useState } from "react";
import bgImage from "../assets/bgh.jpg";

const ITEMS_PER_PAGE = 5;

function EmptyState({ text }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
      {text}
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function SectionCard({ title, count, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          {count}
        </span>
      </div>
      {children}
    </div>
  );
}

function paginateItems(items, currentPage, itemsPerPage = ITEMS_PER_PAGE) {
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  return items.slice(startIndex, endIndex);
}

function Pagination({
  currentPage,
  totalItems,
  itemsPerPage = ITEMS_PER_PAGE,
  onPageChange,
}) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  if (totalPages <= 1) return null;

  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    pages.push(i);
  }

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-slate-600">
        Page <span className="font-semibold">{currentPage}</span> of{" "}
        <span className="font-semibold">{totalPages}</span>
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>

        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`rounded-lg px-3 py-2 text-sm font-medium shadow-sm transition ${
              currentPage === page
                ? "border border-cyan-500 bg-cyan-500 text-white"
                : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {page}
          </button>
        ))}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function scoreToStars(score) {
  const numericScore = Number(score);

  if (Number.isNaN(numericScore)) return "N/A";
  if (numericScore >= 20) return "★★★★★";
  if (numericScore >= 15) return "★★★★☆";
  if (numericScore >= 10) return "★★★☆☆";
  if (numericScore >= 5) return "★★☆☆☆";
  return "★☆☆☆☆";
}

function StrandBadge({ strand }) {
  const value = strand || "N/A";
  const cls =
    value === "+"
      ? "bg-emerald-100 text-emerald-700"
      : value === "-"
      ? "bg-violet-100 text-violet-700"
      : "bg-slate-100 text-slate-700";

  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${cls}`}>
      Strand {value}
    </span>
  );
}

function getDisplayRange(item) {
  if (item?.strand === "-") {
    return {
      displayStart: item.end,
      displayEnd: item.start,
    };
  }

  return {
    displayStart: item.start,
    displayEnd: item.end,
  };
}

function getDisplayPair(start, end, strand) {
  if (start == null || end == null) {
    return { start, end };
  }

  if (strand === "-") {
    return { start: end, end: start };
  }

  return { start, end };
}

function getDisplayCodonRange(startPos, strand) {
  if (startPos == null) return null;

  if (strand === "-") {
    return `${startPos + 2}-${startPos}`;
  }

  return `${startPos}-${startPos + 2}`;
}

function ORFTable({ items = [], onSelectFeature }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [items]);

  if (!items.length) return <EmptyState text="No ORFs found." />;

  const paginatedItems = paginateItems(items, currentPage);

  const handleClickOrf = (orf) => {
    if (!onSelectFeature) return;

    onSelectFeature([
      {
        start: orf.start,
        end: orf.end,
        type: "orf",
        strand: orf.strand,
      },
    ]);
  };

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3 text-left">Strand</th>
              <th className="px-4 py-3 text-left">Frame</th>
              <th className="px-4 py-3 text-left">Start</th>
              <th className="px-4 py-3 text-left">End</th>
              <th className="px-4 py-3 text-left">Length</th>
              <th className="px-4 py-3 text-left">AA</th>
              <th className="px-4 py-3 text-left">Start / Stop</th>
            </tr>
          </thead>

          <tbody>
            {paginatedItems.map((orf, index) => {
              const { displayStart, displayEnd } = getDisplayRange(orf);

              return (
                <tr
                  key={index}
                  onClick={() => handleClickOrf(orf)}
                  className="cursor-pointer border-t border-slate-200 transition hover:bg-cyan-50"
                  title="Click to highlight this ORF in the sequence viewer"
                >
                  <td className="px-4 py-3">{orf.strand}</td>
                  <td className="px-4 py-3">{orf.frame}</td>
                  <td className="px-4 py-3">{displayStart}</td>
                  <td className="px-4 py-3">{displayEnd}</td>
                  <td className="px-4 py-3">{orf.length_nt}</td>
                  <td className="px-4 py-3">{orf.peptide_length_aa}</td>
                  <td className="px-4 py-3">
                    {orf.start_codon} / {orf.stop_codon}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={items.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function PromoterList({ items = [], onSelectFeature }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [items]);

  if (!items.length) {
    return <EmptyState text="No promoter-like region detected." />;
  }

  const paginatedItems = paginateItems(items, currentPage);

  const handleClickPromoter = (p) => {
    if (!onSelectFeature) return;

    const highlights = [];

    if (p.box35_start && p.box35_end) {
      highlights.push({
        start: p.box35_start,
        end: p.box35_end,
        type: "promoter35",
        strand: p.strand,
      });
    }

    if (p.box10_start && p.box10_end) {
      highlights.push({
        start: p.box10_start,
        end: p.box10_end,
        type: "promoter10",
        strand: p.strand,
      });
    }

    onSelectFeature(highlights);
  };

  return (
    <>
      <div className="space-y-3">
        {paginatedItems.map((p, index) => {
          const box35Display = getDisplayPair(
            p.box35_start,
            p.box35_end,
            p.strand
          );
          const box10Display = getDisplayPair(
            p.box10_start,
            p.box10_end,
            p.strand
          );

          return (
            <div
              key={index}
              onClick={() => handleClickPromoter(p)}
              className="cursor-pointer rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-cyan-300 hover:bg-cyan-50 hover:shadow-sm"
              title="Click to highlight this promoter in the sequence viewer"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold text-slate-900">
                  Promoter {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                </p>

                <div className="flex items-center gap-2">
                  <StrandBadge strand={p.strand} />
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
                    {scoreToStars(p.score)}
                  </span>
                </div>
              </div>

              <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                <p>
                  <span className="font-medium">Spacing:</span>{" "}
                  {p.spacing ?? "N/A"} nt
                </p>

                <p>
                  <span className="font-medium">Score:</span>{" "}
                  {p.score ?? "N/A"}
                </p>

                <p>
                  <span className="font-medium">-35 box:</span>{" "}
                  {p.box35_seq} ({box35Display.start}-{box35Display.end})
                </p>

                <p>
                  <span className="font-medium">-35 mismatches:</span>{" "}
                  {p.box35_mismatches}
                </p>

                <p>
                  <span className="font-medium">-10 box:</span>{" "}
                  {p.box10_seq} ({box10Display.start}-{box10Display.end})
                </p>

                <p>
                  <span className="font-medium">-10 mismatches:</span>{" "}
                  {p.box10_mismatches}
                </p>

                <p className="md:col-span-2">
                  <span className="font-medium">Spacer sequence:</span>{" "}
                  {p.spacer_seq ?? "-"}
                </p>

                <p className="md:col-span-2">
                  <span className="font-medium">Spacer AT fraction:</span>{" "}
                  {p.spacer_at_fraction ?? "N/A"}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={items.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function TerminatorList({ items = [], onSelectFeature }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [items]);

  if (!items.length) {
    return <EmptyState text="No rho-independent terminator detected." />;
  }

  const paginatedItems = paginateItems(items, currentPage);

  const handleClickTerminator = (t) => {
    if (!onSelectFeature) return;

    const highlights = [];

    if (t.stem_left_start && t.stem_left_end) {
      highlights.push({
        start: t.stem_left_start,
        end: t.stem_left_end,
        type: "terminatorLeft",
        strand: t.strand,
      });
    }

    if (t.stem_right_start && t.stem_right_end) {
      highlights.push({
        start: t.stem_right_start,
        end: t.stem_right_end,
        type: "terminatorRight",
        strand: t.strand,
      });
    }

    if (t.poly_t_start && t.poly_t_end) {
      highlights.push({
        start: t.poly_t_start,
        end: t.poly_t_end,
        type: "polyT",
        strand: t.strand,
      });
    }

    onSelectFeature(highlights);
  };

  return (
    <>
      <div className="space-y-3">
        {paginatedItems.map((t, index) => {
          const leftDisplay = getDisplayPair(
            t.stem_left_start,
            t.stem_left_end,
            t.strand
          );
          const rightDisplay = getDisplayPair(
            t.stem_right_start,
            t.stem_right_end,
            t.strand
          );
          const polyTDisplay = getDisplayPair(
            t.poly_t_start,
            t.poly_t_end,
            t.strand
          );

          return (
            <div
              key={index}
              onClick={() => handleClickTerminator(t)}
              className="cursor-pointer rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-cyan-300 hover:bg-cyan-50 hover:shadow-sm"
              title="Click to highlight this terminator in the sequence viewer"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold text-slate-900">
                  Terminator {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                </p>

                <div className="flex items-center gap-2">
                  <StrandBadge strand={t.strand} />
                  <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700">
                    {scoreToStars(t.score)}
                  </span>
                </div>
              </div>

              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>
                  <span className="font-medium">Left stem:</span>{" "}
                  {t.stem_left_seq} ({leftDisplay.start}-{leftDisplay.end})
                </p>
                <p>
                  <span className="font-medium">Loop:</span> {t.loop_seq || "-"}
                </p>
                <p>
                  <span className="font-medium">Right stem:</span>{" "}
                  {t.stem_right_seq} ({rightDisplay.start}-{rightDisplay.end})
                </p>
                <p>
                  <span className="font-medium">Poly-T:</span> {t.poly_t_seq} (
                  {polyTDisplay.start}-{polyTDisplay.end})
                </p>
                <p>
                  <span className="font-medium">Stem length:</span>{" "}
                  {t.stem_length ?? "N/A"}
                </p>
                <p>
                  <span className="font-medium">Loop length:</span>{" "}
                  {t.loop_length ?? "N/A"}
                </p>
                <p>
                  <span className="font-medium">Mismatches:</span>{" "}
                  {t.mismatches ?? "N/A"}
                </p>
                <p>
                  <span className="font-medium">GC fraction:</span>{" "}
                  {t.gc_fraction ?? "N/A"}
                </p>
                <p>
                  <span className="font-medium">Poly-T length:</span>{" "}
                  {t.poly_t_length ?? "N/A"}
                </p>
                <p>
                  <span className="font-medium">Score:</span>{" "}
                  {t.score ?? "N/A"}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={items.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function ShineDalgarnoList({ items = [], onSelectFeature }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [items]);

  if (!items.length) {
    return <EmptyState text="No Shine-Dalgarno site detected." />;
  }

  const paginatedItems = paginateItems(items, currentPage);

  const handleClickSD = (site) => {
    if (!onSelectFeature) return;

    const highlights = [
      {
        start: site.start,
        end: site.end,
        type: "shineDalgarno",
        strand: site.strand,
      },
    ];

    if (site.linked_start_position != null) {
      highlights.push({
        start: site.linked_start_position,
        end: site.linked_start_position + 2,
        type: "startCodon",
        strand: site.strand,
      });
    }

    onSelectFeature(highlights);
  };

  return (
    <>
      <div className="space-y-3">
        {paginatedItems.map((site, index) => {
          const siteDisplay = getDisplayPair(site.start, site.end, site.strand);
          const linkedStartDisplay = getDisplayCodonRange(
            site.linked_start_position,
            site.strand
          );

          return (
            <div
              key={index}
              onClick={() => handleClickSD(site)}
              className="cursor-pointer rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-cyan-300 hover:bg-cyan-50 hover:shadow-sm"
              title="Click to highlight this Shine-Dalgarno site in the sequence viewer"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold text-slate-900">
                  Site {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                </p>

                <div className="flex items-center gap-2">
                  <StrandBadge strand={site.strand} />
                  <span className="rounded-full bg-lime-100 px-2.5 py-1 text-xs font-semibold text-lime-700">
                    {scoreToStars(site.score)}
                  </span>
                </div>
              </div>

              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>
                  <span className="font-medium">Sequence:</span> {site.sequence}
                </p>

                <p>
                  <span className="font-medium">Position:</span>{" "}
                  {siteDisplay.start}-{siteDisplay.end}
                </p>

                <p>
                  <span className="font-medium">Mismatches:</span>{" "}
                  {site.mismatches}
                </p>

                <p>
                  <span className="font-medium">Linked start codon:</span>{" "}
                  {site.linked_start_codon
                    ? `${site.linked_start_codon} (${linkedStartDisplay})`
                    : "Not found"}
                </p>

                <p>
                  <span className="font-medium">Distance to start:</span>{" "}
                  {site.distance_to_start ?? "Not found"} nt
                </p>

                <p>
                  <span className="font-medium">Score:</span>{" "}
                  {site.score ?? "N/A"}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={items.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function FolderResults({ files = [] }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [files]);

  if (!files.length) return <EmptyState text="No folder analysis results." />;

  const paginatedItems = paginateItems(files, currentPage);

  return (
    <>
      <div className="space-y-6">
        {paginatedItems.map((file, index) => (
          <div
            key={index}
            className="rounded-2xl border border-slate-200 bg-white/85 p-6 shadow-sm backdrop-blur-md"
          >
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-slate-900">
                {file.file}
              </h3>
              <p className="text-sm text-slate-500">Length: {file.length} nt</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard title="ORFs" value={file.orfs?.length ?? 0} />
              <StatCard title="Promoters" value={file.promoters?.length ?? 0} />
              <StatCard
                title="Terminators"
                value={file.terminators?.length ?? 0}
              />
              <StatCard
                title="Shine-Dalgarno"
                value={file.shine_dalgarno?.length ?? 0}
              />
            </div>
          </div>
        ))}
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={files.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function RankedCodingORFList({ items = [], onSelectFeature }) {
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    setCurrentPage(1);
  }, [items]);

  if (!items.length) {
    return <EmptyState text="No ranked coding ORFs found." />;
  }

  const paginatedItems = paginateItems(items, currentPage);

  const handleClickRankedOrf = (item) => {
  if (!onSelectFeature) return;

  const orf = item.orf;
  if (!orf) return;

  const highlights = [];

  if (orf.strand === "+") {
    highlights.push({
      start: orf.start,
      end: orf.start + 2,
      type: "startCodon",
      strand: orf.strand,
    });
  } else {
    highlights.push({
      start: orf.end - 2,
      end: orf.end,
      type: "startCodon",
      strand: orf.strand,
    });
  }

  highlights.push({
    start: orf.start,
    end: orf.end,
    type: "orf",
    strand: orf.strand,
  });

  // 3) SD lié
  if (item.best_shine_dalgarno) {
    highlights.push({
      start: item.best_shine_dalgarno.start,
      end: item.best_shine_dalgarno.end,
      type: "shineDalgarno",
      strand: item.best_shine_dalgarno.strand,
    });
  }

  if (item.best_promoter) {
    highlights.push({
      start: item.best_promoter.box35_start,
      end: item.best_promoter.box35_end,
      type: "promoter35",
      strand: item.best_promoter.strand,
    });

    highlights.push({
      start: item.best_promoter.box10_start,
      end: item.best_promoter.box10_end,
      type: "promoter10",
      strand: item.best_promoter.strand,
    });
  }

  if (item.best_terminator) {
    highlights.push({
      start: item.best_terminator.stem_left_start,
      end: item.best_terminator.stem_left_end,
      type: "terminatorLeft",
      strand: item.best_terminator.strand,
    });

    highlights.push({
      start: item.best_terminator.stem_right_start,
      end: item.best_terminator.stem_right_end,
      type: "terminatorRight",
      strand: item.best_terminator.strand,
    });

    highlights.push({
      start: item.best_terminator.poly_t_start,
      end: item.best_terminator.poly_t_end,
      type: "polyT",
      strand: item.best_terminator.strand,
    });
  }

  onSelectFeature(highlights);
};

  return (
    <>
      <div className="space-y-3">
        {paginatedItems.map((item, index) => {
          const orf = item.orf || {};
          const { displayStart, displayEnd } = getDisplayRange(orf);

          return (
            <div
              key={index}
              onClick={() => handleClickRankedOrf(item)}
              className="cursor-pointer rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-fuchsia-300 hover:bg-fuchsia-50 hover:shadow-sm"
              title="Click to highlight this ranked coding ORF in the sequence viewer"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold text-slate-900">
                  Candidate {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                </p>

                <div className="flex items-center gap-2">
                  <StrandBadge strand={orf.strand} />
                  <span className="rounded-full bg-fuchsia-100 px-2.5 py-1 text-xs font-semibold text-fuchsia-700">
                    Score {item.total_score ?? "N/A"}
                  </span>
                </div>
              </div>

              <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                <p>
                  <span className="font-medium">Frame:</span> {orf.frame}
                </p>
                <p>
                  <span className="font-medium">Start codon:</span>{" "}
                  {orf.start_codon}
                </p>
                <p>
                  <span className="font-medium">Start:</span> {displayStart}
                </p>
                <p>
                  <span className="font-medium">End:</span> {displayEnd}
                </p>
                <p>
                  <span className="font-medium">Length:</span> {orf.length_nt} nt
                </p>
                <p>
                  <span className="font-medium">Peptide:</span>{" "}
                  {orf.peptide_length_aa} aa
                </p>
              </div>

              <div className="mt-4 grid gap-2 text-sm text-slate-700 md:grid-cols-2 xl:grid-cols-5">
                <p>
                  <span className="font-medium">Length score:</span>{" "}
                  {item.score_breakdown?.length_score ?? 0}
                </p>
                <p>
                  <span className="font-medium">Start score:</span>{" "}
                  {item.score_breakdown?.start_codon_score ?? 0}
                </p>
                <p>
                  <span className="font-medium">SD score:</span>{" "}
                  {item.score_breakdown?.shine_dalgarno_score ?? 0}
                </p>
                <p>
                  <span className="font-medium">Promoter score:</span>{" "}
                  {item.score_breakdown?.promoter_score ?? 0}
                </p>
                <p>
                  <span className="font-medium">Terminator score:</span>{" "}
                  {item.score_breakdown?.terminator_score ?? 0}
                </p>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    item.best_promoter
                      ? "bg-amber-100 text-amber-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {item.best_promoter ? "Promoter linked" : "No promoter"}
                </span>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    item.best_shine_dalgarno
                      ? "bg-lime-100 text-lime-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {item.best_shine_dalgarno ? "SD linked" : "No SD"}
                </span>

                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    item.best_terminator
                      ? "bg-rose-100 text-rose-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {item.best_terminator ? "Terminator linked" : "No terminator"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <Pagination
        currentPage={currentPage}
        totalItems={items.length}
        onPageChange={setCurrentPage}
      />
    </>
  );
}

function getItems(results, key) {
  if (Array.isArray(results)) return results;
  if (Array.isArray(results?.[key])) return results[key];
  return [];
}

function ResultsContainer({ children, className = "" }) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md ${className}`}
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      {children}
    </section>
  );
}

function ResultsHeader({ title, subtitle, className = "" }) {
  return (
    <div className={className}>
      <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
      {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
    </div>
  );
}

export default function Results({
  results,
  loading,
  mode,
  activeView,
  onSelectFeature,
}) {
  const renderLoading = () => (
    <ResultsContainer>
      <ResultsHeader title="Analysis Results" />
      <div className="mt-4 flex items-center gap-3 text-slate-600">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        <span className="text-sm">Running analysis...</span>
      </div>
    </ResultsContainer>
  );

  const renderEmpty = () => (
    <ResultsContainer>
      <ResultsHeader title="Analysis Results" className="mb-4" />
      <EmptyState text="Run an analysis to see results." />
    </ResultsContainer>
  );

  const renderFolderMode = () => (
    <ResultsContainer>
      <ResultsHeader title="Folder Results" className="mb-4" />
      <FolderResults files={Array.isArray(results) ? results : []} />
    </ResultsContainer>
  );

  const renderOrfs = () => {
    const items = getItems(results, "orfs");

    return (
      <ResultsContainer>
        <SectionCard title="ORF Results" count={items.length}>
          <ORFTable items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderCodingOrfs = () => {
    const items = Array.isArray(results?.coding_orfs)
      ? results.coding_orfs
      : Array.isArray(results)
      ? results
      : [];

    const best = results?.best_coding_orf ?? null;

    return (
      <ResultsContainer className="space-y-6">
        {best && (
          <SectionCard title="Best Candidate ORF" count={1}>
            <ORFTable items={[best]} onSelectFeature={onSelectFeature} />
          </SectionCard>
        )}

        <SectionCard title="Coding ORF Results" count={items.length}>
          <ORFTable items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderRankedCodingOrfs = () => {
    const items = Array.isArray(results?.ranked_coding_orfs)
      ? results.ranked_coding_orfs
      : Array.isArray(results)
      ? results
      : [];

    const best = results?.best_ranked_coding_orf ?? null;

    return (
      <ResultsContainer className="space-y-6">
        {best && (
          <SectionCard title="Best Ranked Coding ORF" count={1}>
            <RankedCodingORFList
              items={[best]}
              onSelectFeature={onSelectFeature}
            />
          </SectionCard>
        )}

        <SectionCard title="Ranked Coding ORFs" count={items.length}>
          <RankedCodingORFList
            items={items}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderPromoters = () => {
    const items = getItems(results, "promoters");

    return (
      <ResultsContainer>
        <SectionCard title="Promoter Results" count={items.length}>
          <PromoterList items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderTerminators = () => {
    const items = getItems(results, "terminators");

    return (
      <ResultsContainer>
        <SectionCard title="Terminator Results" count={items.length}>
          <TerminatorList
            items={items}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderShineDalgarno = () => {
    const items = getItems(results, "shine_dalgarno");

    return (
      <ResultsContainer>
        <SectionCard title="Shine-Dalgarno Results" count={items.length}>
          <ShineDalgarnoList items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </ResultsContainer>
    );
  };

  const renderAllResults = () => {
    const summary = {
      orfs: results.orfs?.length ?? 0,
      promoters: results.promoters?.length ?? 0,
      terminators: results.terminators?.length ?? 0,
      shine: results.shine_dalgarno?.length ?? 0,
    };

    return (
      <ResultsContainer className="space-y-6">
        <ResultsHeader
          title="Analysis Results"
          subtitle="Clear biological interpretation of detected features."
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard title="ORFs" value={summary.orfs} />
          <StatCard title="Promoters" value={summary.promoters} />
          <StatCard title="Terminators" value={summary.terminators} />
          <StatCard title="Shine-Dalgarno" value={summary.shine} />
        </div>

        <SectionCard title="ORFs" count={summary.orfs}>
          <ORFTable
            items={results.orfs || []}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>

        <SectionCard title="Promoters" count={summary.promoters}>
          <PromoterList
            items={results.promoters || []}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>

        <SectionCard title="Terminators" count={summary.terminators}>
          <TerminatorList
            items={results.terminators || []}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>

        <SectionCard title="Shine-Dalgarno" count={summary.shine}>
          <ShineDalgarnoList
            items={results.shine_dalgarno || []}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>
      </ResultsContainer>
    );
  };

  if (loading) return renderLoading();
  if (mode === "folder") return renderFolderMode();
  if (!results) return renderEmpty();

  switch (activeView) {
    case "orfs":
      return renderOrfs();

    case "coding-orfs":
      return renderCodingOrfs();

    case "ranked-coding-orfs":
      return renderRankedCodingOrfs();

    case "promoters":
      return renderPromoters();

    case "terminators":
      return renderTerminators();

    case "shine-dalgarno":
      return renderShineDalgarno();

    default:
      return renderAllResults();
  }
}
