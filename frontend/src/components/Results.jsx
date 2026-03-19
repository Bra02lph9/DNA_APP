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
            {paginatedItems.map((orf, index) => (
              <tr
                key={index}
                onClick={() => handleClickOrf(orf)}
                className="cursor-pointer border-t border-slate-200 transition hover:bg-cyan-50"
                title="Click to highlight this ORF in the sequence viewer"
              >
                <td className="px-4 py-3">{orf.strand}</td>
                <td className="px-4 py-3">{orf.frame}</td>
                <td className="px-4 py-3">{orf.start}</td>
                <td className="px-4 py-3">{orf.end}</td>
                <td className="px-4 py-3">{orf.length_nt}</td>
                <td className="px-4 py-3">{orf.peptide_length_aa}</td>
                <td className="px-4 py-3">
                  {orf.start_codon} / {orf.stop_codon}
                </td>
              </tr>
            ))}
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
        {paginatedItems.map((p, index) => (
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
                {p.box35_seq} ({p.box35_start}-{p.box35_end})
              </p>

              <p>
                <span className="font-medium">-35 mismatches:</span>{" "}
                {p.box35_mismatches}
              </p>

              <p>
                <span className="font-medium">-10 box:</span>{" "}
                {p.box10_seq} ({p.box10_start}-{p.box10_end})
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
        ))}
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
        {paginatedItems.map((t, index) => (
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
                <span className="font-medium">Left stem:</span> {t.stem_left_seq} (
                {t.stem_left_start}-{t.stem_left_end})
              </p>
              <p>
                <span className="font-medium">Loop:</span> {t.loop_seq || "-"}
              </p>
              <p>
                <span className="font-medium">Right stem:</span>{" "}
                {t.stem_right_seq} ({t.stem_right_start}-{t.stem_right_end})
              </p>
              <p>
                <span className="font-medium">Poly-T:</span> {t.poly_t_seq} (
                {t.poly_t_start}-{t.poly_t_end})
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
        ))}
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
        {paginatedItems.map((site, index) => (
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
                {site.start}-{site.end}
              </p>

              <p>
                <span className="font-medium">Mismatches:</span>{" "}
                {site.mismatches}
              </p>

              <p>
                <span className="font-medium">Linked start codon:</span>{" "}
                {site.linked_start_codon
                  ? `${site.linked_start_codon} (${site.linked_start_position})`
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
        ))}
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

function getItems(results, key) {
  if (Array.isArray(results)) return results;
  if (Array.isArray(results?.[key])) return results[key];
  return [];
}

export default function Results({
  results,
  loading,
  mode,
  activeView,
  onSelectFeature,
}) {
  if (loading) {
    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <h3 className="text-xl font-semibold text-slate-900">
          Analysis Results
        </h3>
        <p className="mt-3 text-sm text-slate-600">Running analysis...</p>
      </section>
    );
  }

  if (mode === "folder") {
    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <h3 className="mb-4 text-xl font-semibold text-slate-900">
          Folder Results
        </h3>
        <FolderResults files={Array.isArray(results) ? results : []} />
      </section>
    );
  }

  if (!results) {
    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <h3 className="mb-4 text-xl font-semibold text-slate-900">
          Analysis Results
        </h3>
        <EmptyState text="Run an analysis to see results." />
      </section>
    );
  }

  if (activeView === "orfs") {
    const items = getItems(results, "orfs");

    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <SectionCard title="ORF Results" count={items.length}>
          <ORFTable items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </section>
    );
  }

  if (activeView === "coding-orfs") {
    const items = Array.isArray(results?.coding_orfs)
      ? results.coding_orfs
      : Array.isArray(results)
      ? results
      : [];

    const best = results?.best_coding_orf ?? null;

    return (
      <section
        className="space-y-6 rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        {best && (
          <SectionCard title="Best Candidate ORF" count={1}>
            <ORFTable items={[best]} onSelectFeature={onSelectFeature} />
          </SectionCard>
        )}

        <SectionCard title="Coding ORF Results" count={items.length}>
          <ORFTable items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </section>
    );
  }

  if (activeView === "promoters") {
    const items = getItems(results, "promoters");

    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <SectionCard title="Promoter Results" count={items.length}>
          <PromoterList items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </section>
    );
  }

  if (activeView === "terminators") {
    const items = getItems(results, "terminators");

    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <SectionCard title="Terminator Results" count={items.length}>
          <TerminatorList
            items={items}
            onSelectFeature={onSelectFeature}
          />
        </SectionCard>
      </section>
    );
  }

  if (activeView === "shine-dalgarno") {
    const items = getItems(results, "shine_dalgarno");

    return (
      <section
        className="rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
        style={{ backgroundImage: `url(${bgImage})` }}
      >
        <SectionCard title="Shine-Dalgarno Results" count={items.length}>
          <ShineDalgarnoList items={items} onSelectFeature={onSelectFeature} />
        </SectionCard>
      </section>
    );
  }

  const summary = {
    orfs: results.orfs?.length ?? 0,
    promoters: results.promoters?.length ?? 0,
    terminators: results.terminators?.length ?? 0,
    shine: results.shine_dalgarno?.length ?? 0,
  };

  return (
    <section
      className="space-y-6 rounded-2xl border border-slate-200 bg-cover bg-center p-6 shadow-sm backdrop-blur-md"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div>
        <h3 className="text-xl font-semibold text-slate-900">
          Analysis Results
        </h3>
        <p className="mt-1 text-sm text-slate-600">
          Clear biological interpretation of detected features.
        </p>
      </div>

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
    </section>
  );
}
