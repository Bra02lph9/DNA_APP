import { jsPDF } from "jspdf";

export function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url);
}

export function downloadPdfFile(content, filename = "dna_analysis_results.pdf") {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const marginLeft = 10;
  const marginTop = 10;
  const marginBottom = 10;
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxLineWidth = 190;
  const lineHeight = 5;

  let y = marginTop;

  doc.setFont("courier", "normal");
  doc.setFontSize(10);

  const rawLines = String(content).split("\n");

  rawLines.forEach((rawLine) => {
    const wrappedLines = doc.splitTextToSize(rawLine, maxLineWidth);

    if (!wrappedLines.length) {
      if (y + lineHeight > pageHeight - marginBottom) {
        doc.addPage();
        y = marginTop;
      }
      y += lineHeight;
      return;
    }

    wrappedLines.forEach((line) => {
      if (y + lineHeight > pageHeight - marginBottom) {
        doc.addPage();
        y = marginTop;
      }

      doc.text(line, marginLeft, y);
      y += lineHeight;
    });
  });

  doc.save(filename.endsWith(".pdf") ? filename : `${filename}.pdf`);
}
