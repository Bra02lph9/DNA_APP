const LINE_WIDTH = 60;

const safeValue = (value, fallback = "N/A") => {
  return value === null || value === undefined || value === "" ? fallback : value;
};

const repeatChar = (char, count) => {
  return Array.from({ length: Math.max(0, count) }, () => char).join("");
};

const getComplement = (sequence = "") => {
  const map = {
    A: "T",
    T: "A",
    G: "C",
    C: "G",
    U: "A",
    N: "N",
  };

  return String(sequence)
    .toUpperCase()
    .split("")
    .map((base) => map[base] || base)
    .join("");
};

const formatDoubleStrandSequence = (sequence, lineWidth = LINE_WIDTH) => {
  const seq = safeValue(sequence, "");
  if (!seq || seq === "N/A") return "N/A\n";

  const cleanSeq = String(seq).replace(/\s+/g, "").toUpperCase();
  const complement = getComplement(cleanSeq);

  let block = "";

  for (let i = 0; i < cleanSeq.length; i += lineWidth) {
    const top = cleanSeq.slice(i, i + lineWidth);
    const bottom = complement.slice(i, i + lineWidth);
    const bonds = repeatChar("|", top.length);

    const start = i + 1;
    const end = i + top.length;

    block += `    5' ${top} 3'   [${start}-${end}]\n`;
    block += `       ${bonds}\n`;
    block += `    3' ${bottom} 5'\n\n`;
  }

  return block;
};

const formatSectionHeader = (title, count) => {
  return `${title} (${count})\n------------------------------\n`;
};

const formatField = (label, value, unit = "") => {
  return `  ${label}: ${safeValue(value)}${unit}\n`;
};

const formatSequenceField = (label, sequence) => {
  let text = `  ${label}:\n`;
  text += formatDoubleStrandSequence(sequence);
  return text;
};

export const formatSingleResultAsText = (singleResults, view = "all") => {
  if (!singleResults) return "No results.";

  let text = "DNA Analysis Results\n";
  text += "====================\n\n";

  if ((view === "orfs" || view === "all") && singleResults.orfs) {
    text += formatSectionHeader("ORFs", singleResults.orfs.length);

    singleResults.orfs.forEach((orf, i) => {
      text += `ORF ${i + 1}\n`;
      text += formatField("Strand", orf.strand);
      text += formatField("Frame", orf.frame);
      text += formatField("Start", orf.start);
      text += formatField("End", orf.end);
      text += formatField("Length", orf.length_nt, " nt");
      text += formatField("Peptide length", orf.peptide_length_aa, " aa");
      text += formatField("Start codon", orf.start_codon);
      text += formatField("Stop codon", orf.stop_codon);
      text += formatSequenceField("Sequence", orf.sequence);
      text += "\n";
    });
  }

  if ((view === "coding-orfs" || view === "all") && singleResults.coding_orfs) {
    text += formatSectionHeader("Coding ORFs", singleResults.coding_orfs.length);

    singleResults.coding_orfs.forEach((orf, i) => {
      text += `Coding ORF ${i + 1}\n`;
      text += formatField("Strand", orf.strand);
      text += formatField("Frame", orf.frame);
      text += formatField("Start", orf.start);
      text += formatField("End", orf.end);
      text += formatField("Length", orf.length_nt, " nt");
      text += formatField("Peptide length", orf.peptide_length_aa, " aa");
      text += formatField("Start codon", orf.start_codon);
      text += formatField("Stop codon", orf.stop_codon);
      text += formatSequenceField("Sequence", orf.sequence);
      text += "\n";
    });

    if (singleResults.best_coding_orf) {
      const best = singleResults.best_coding_orf;

      text += "Best Candidate ORF (l’ORF potentiellement)\n";
      text += "------------------------------\n";
      text += formatField("Strand", best.strand);
      text += formatField("Frame", best.frame);
      text += formatField("Start", best.start);
      text += formatField("End", best.end);
      text += formatField("Length", best.length_nt, " nt");
      text += formatField("Peptide length", best.peptide_length_aa, " aa");
      text += formatField("Start codon", best.start_codon);
      text += formatField("Stop codon", best.stop_codon);
      text += formatSequenceField("Sequence", best.sequence);
      text += "\n";
    }
  }

  if ((view === "promoters" || view === "all") && singleResults.promoters) {
  text += formatSectionHeader("Promoters", singleResults.promoters.length);

  singleResults.promoters.forEach((p, i) => {
    text += `Promoter ${i + 1}\n`;
    text += formatField("Strand", safeValue(p.strand));
    text += formatField(
      "-35 box",
      `${safeValue(p.box35_seq)} (${safeValue(p.box35_start)}-${safeValue(p.box35_end)})`
    );
    text += formatField("-35 mismatches", p.box35_mismatches);
    text += formatField(
      "-10 box",
      `${safeValue(p.box10_seq)} (${safeValue(p.box10_start)}-${safeValue(p.box10_end)})`
    );
    text += formatField("-10 mismatches", p.box10_mismatches);
    text += formatField("Spacing", p.spacing, " nt");
    text += formatField("Spacer sequence", safeValue(p.spacer_seq));
    text += formatField("Spacer AT fraction", p.spacer_at_fraction);
    text += formatField("Score", p.score);
    text += "\n";
  });
}

  if ((view === "terminators" || view === "all") && singleResults.terminators) {
    text += formatSectionHeader("Terminators", singleResults.terminators.length);

    singleResults.terminators.forEach((t, i) => {
      text += `Terminator ${i + 1}\n`;
      text += formatField("Left stem", `${safeValue(t.stem_left_seq)} (${safeValue(t.stem_left_start)}-${safeValue(t.stem_left_end)})`);
      text += formatField("Loop", safeValue(t.loop_seq, "-"));
      text += formatField("Right stem", `${safeValue(t.stem_right_seq)} (${safeValue(t.stem_right_start)}-${safeValue(t.stem_right_end)})`);
      text += formatField("Poly-T", `${safeValue(t.poly_t_seq)} (${safeValue(t.poly_t_start)}-${safeValue(t.poly_t_end)})`);
      text += "\n";
    });
  }

if ((view === "shine-dalgarno" || view === "all") && singleResults.shine_dalgarno) {
  text += formatSectionHeader("Shine-Dalgarno Sites", singleResults.shine_dalgarno.length);

  singleResults.shine_dalgarno.forEach((s, i) => {
    text += `Site ${i + 1}\n`;

    text += formatField("Strand", safeValue(s.strand));
    text += formatField("Sequence", safeValue(s.sequence));
    text += formatField("Position", `${safeValue(s.start)}-${safeValue(s.end)}`);
    text += formatField("Mismatches", safeValue(s.mismatches));

    text += formatField(
      "Linked start codon",
      s.linked_start_codon
        ? `${s.linked_start_codon} (${safeValue(s.linked_start_position)})`
        : "Not found"
    );

    text += formatField(
      "Distance to start",
      safeValue(s.distance_to_start, "Not found"),
      " nt"
    );

    text += formatField("Score", safeValue(s.score));

    text += "\n";
  });
}

  return text.trimEnd();
};

export const formatArrayResultsAsText = (arrayResults, view) => {
  if (!Array.isArray(arrayResults) || !arrayResults.length) {
    return "No results.";
  }

  let text = "DNA Folder Analysis Results\n";
  text += "===========================\n\n";

  arrayResults.forEach((fileResult, index) => {
    text += `File ${index + 1}: ${fileResult.file || fileResult.name || "Unknown file"}\n`;
    text += `Length: ${fileResult.length || fileResult.sequence?.length || 0} nt\n`;
    text += "----------------------------------------\n\n";

    if (view === "orfs" && fileResult.orfs) {
      text += formatSectionHeader("ORFs", fileResult.orfs.length);

      fileResult.orfs.forEach((orf, i) => {
        text += `  ORF ${i + 1}\n`;
        text += `    Strand: ${safeValue(orf.strand)}\n`;
        text += `    Frame: ${safeValue(orf.frame)}\n`;
        text += `    Start: ${safeValue(orf.start)}\n`;
        text += `    End: ${safeValue(orf.end)}\n`;
        text += `    Length: ${safeValue(orf.length_nt)} nt\n`;
        text += `    AA: ${safeValue(orf.peptide_length_aa)}\n`;
        text += `    Sequence:\n`;
        text += formatDoubleStrandSequence(orf.sequence)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += "\n";
      });

      text += "\n";
    }

    if (view === "coding-orfs" && fileResult.coding_orfs) {
      text += formatSectionHeader("Coding ORFs", fileResult.coding_orfs.length);

      fileResult.coding_orfs.forEach((orf, i) => {
        text += `  Coding ORF ${i + 1}\n`;
        text += `    Strand: ${safeValue(orf.strand)}\n`;
        text += `    Frame: ${safeValue(orf.frame)}\n`;
        text += `    Start: ${safeValue(orf.start)}\n`;
        text += `    End: ${safeValue(orf.end)}\n`;
        text += `    Length: ${safeValue(orf.length_nt)} nt\n`;
        text += `    AA: ${safeValue(orf.peptide_length_aa)}\n`;
        text += `    Start codon: ${safeValue(orf.start_codon)}\n`;
        text += `    Stop codon: ${safeValue(orf.stop_codon)}\n`;
        text += `    Sequence:\n`;
        text += formatDoubleStrandSequence(orf.sequence)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += "\n";
      });

      text += "\n";
    }

    if (view === "promoters" && fileResult.promoters) {
      text += formatSectionHeader("Promoters", fileResult.promoters.length);

      fileResult.promoters.forEach((p, i) => {
        text += `  Promoter ${i + 1}\n`;
        text += `    -35 box: ${safeValue(p.box35_seq)} (${safeValue(p.box35_start)}-${safeValue(p.box35_end)})\n`;
        text += `    -10 box: ${safeValue(p.box10_seq)} (${safeValue(p.box10_start)}-${safeValue(p.box10_end)})\n`;
        text += `    Spacing: ${safeValue(p.spacing)} nt\n`;
        text += `    -35 sequence:\n`;
        text += formatDoubleStrandSequence(p.box35_seq)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += `    -10 sequence:\n`;
        text += formatDoubleStrandSequence(p.box10_seq)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += "\n";
      });

      text += "\n";
    }

    if (view === "terminators" && fileResult.terminators) {
      text += formatSectionHeader("Terminators", fileResult.terminators.length);

      fileResult.terminators.forEach((t, i) => {
        text += `  Terminator ${i + 1}\n`;
        text += `    Left stem: ${safeValue(t.stem_left_seq)}\n`;
        text += `    Right stem: ${safeValue(t.stem_right_seq)}\n`;
        text += `    Poly-T: ${safeValue(t.poly_t_seq)}\n`;
        text += `    Left stem sequence:\n`;
        text += formatDoubleStrandSequence(t.stem_left_seq)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += `    Right stem sequence:\n`;
        text += formatDoubleStrandSequence(t.stem_right_seq)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += `    Poly-T sequence:\n`;
        text += formatDoubleStrandSequence(t.poly_t_seq)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += "\n";
      });

      text += "\n";
    }

    if (view === "shine-dalgarno" && fileResult.shine_dalgarno) {
      text += formatSectionHeader("Shine-Dalgarno Sites", fileResult.shine_dalgarno.length);

      fileResult.shine_dalgarno.forEach((s, i) => {
        text += `  Site ${i + 1}\n`;
        text += `    Sequence: ${safeValue(s.sequence)}\n`;
        text += `    Position: ${safeValue(s.start)}-${safeValue(s.end)}\n`;
        text += `    Linked ATG: ${safeValue(s.linked_atg_position, "Not found")}\n`;
        text += `    Sequence details:\n`;
        text += formatDoubleStrandSequence(s.sequence)
          .split("\n")
          .map((line) => (line ? `    ${line}` : line))
          .join("\n");
        text += "\n";
      });

      text += "\n";
    }

    if (view === "all") {
      text += `ORFs: ${fileResult.orfs?.length ?? 0}\n`;
      text += `Coding ORFs: ${fileResult.coding_orfs?.length ?? 0}\n`;
      text += `Promoters: ${fileResult.promoters?.length ?? 0}\n`;
      text += `Terminators: ${fileResult.terminators?.length ?? 0}\n`;
      text += `Shine-Dalgarno: ${fileResult.shine_dalgarno?.length ?? 0}\n\n`;
    }

    text += "\n";
  });

  return text.trimEnd();
};

const isFolderResultsArray = (results) => {
  return (
    Array.isArray(results) &&
    results.length > 0 &&
    typeof results[0] === "object" &&
    (
      "file" in results[0] ||
      "name" in results[0] ||
      "length" in results[0]
    ) &&
    (
      "orfs" in results[0] ||
      "promoters" in results[0] ||
      "terminators" in results[0] ||
      "shine_dalgarno" in results[0] ||
      "coding_orfs" in results[0]
    )
  );
};

export const formatResultsAsText = (currentResults, view) => {
  if (!currentResults) return "No results.";

  if (isFolderResultsArray(currentResults)) {
    return formatArrayResultsAsText(currentResults, view);
  }

  if (Array.isArray(currentResults)) {
    if (view === "orfs") {
      return formatSingleResultAsText({ orfs: currentResults }, "orfs");
    }

    if (view === "coding-orfs") {
      return formatSingleResultAsText({ coding_orfs: currentResults }, "coding-orfs");
    }

    if (view === "promoters") {
      return formatSingleResultAsText({ promoters: currentResults }, "promoters");
    }

    if (view === "terminators") {
      return formatSingleResultAsText({ terminators: currentResults }, "terminators");
    }

    if (view === "shine-dalgarno") {
      return formatSingleResultAsText(
        { shine_dalgarno: currentResults },
        "shine-dalgarno"
      );
    }
  }

  return formatSingleResultAsText(currentResults, view);
};
