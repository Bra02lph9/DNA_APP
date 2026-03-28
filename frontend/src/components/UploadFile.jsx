import { useEffect, useRef, useState } from "react";

const FASTA_EXTENSIONS = [".fasta", ".fa", ".fna", ".fas", ".txt"];
const LARGE_SEQUENCE_WARNING_LENGTH = 50000;
const HUGE_SEQUENCE_LENGTH = 500000;
const PREVIEW_LENGTH = 5000;
const MAX_FOLDER_FILES_TO_PROCESS_AT_ONCE = 200;

function isFastaFile(filename = "") {
  const lower = filename.toLowerCase();
  return FASTA_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function extractSequenceFromFasta(text = "") {
  const lines = text.split(/\r?\n/);
  const sequenceParts = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith(">")) continue;
    sequenceParts.push(trimmed);
  }

  return sequenceParts.join("").replace(/\s+/g, "").toUpperCase().trim();
}

function isValidDNASequence(sequence = "") {
  return /^[ACGTN]*$/i.test(sequence);
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (event) => {
      resolve(event.target?.result || "");
    };

    reader.onerror = () => {
      reject(new Error(`Failed to read ${file.name}`));
    };

    reader.readAsText(file);
  });
}

function buildSequenceMeta(sequence, fileName) {
  return {
    fileName,
    length: sequence.length,
    isLarge: sequence.length >= LARGE_SEQUENCE_WARNING_LENGTH,
    isHuge: sequence.length >= HUGE_SEQUENCE_LENGTH,
    previewLength: Math.min(sequence.length, PREVIEW_LENGTH),
  };
}

function getPreviewSequence(sequence) {
  return sequence.slice(0, PREVIEW_LENGTH);
}

export default function UploadFile({
  setSequence,
  setLoadedFileName,
  setFolderFiles,
  setMode,
  setResults,
  setFullSequenceRef,   // nouvelle prop recommandée
  setSequenceMeta,      // nouvelle prop recommandée
}) {
  const folderInputRef = useRef(null);
  const singleFileInputRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
    }
  }, []);

  const resetInputs = () => {
    if (singleFileInputRef.current) {
      singleFileInputRef.current.value = "";
    }
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  };

  const resetAnalysisState = () => {
    setResults(null);
  };

  const warnIfLargeSequence = (seqLength) => {
    if (seqLength >= HUGE_SEQUENCE_LENGTH) {
      alert(
        `Huge sequence detected (${seqLength.toLocaleString()} nt).\n\n` +
          `Only a preview will be sent to the visible viewer to keep the frontend responsive.`
      );
      return;
    }

    if (seqLength >= LARGE_SEQUENCE_WARNING_LENGTH) {
      alert(
        `Large sequence detected (${seqLength.toLocaleString()} nt).\n\n` +
          `The frontend may become slower if the full sequence is rendered.`
      );
    }
  };

  const applyLoadedSingleSequence = (seq, fileName) => {
    const meta = buildSequenceMeta(seq, fileName);

    warnIfLargeSequence(seq.length);

    setMode("single");

    if (typeof setFullSequenceRef === "function") {
      setFullSequenceRef(seq);
    }

    if (typeof setSequenceMeta === "function") {
      setSequenceMeta(meta);
    }

    if (meta.isHuge) {
      setSequence(getPreviewSequence(seq));
    } else {
      setSequence(seq);
    }

    setLoadedFileName(fileName);
    setFolderFiles([]);
    resetAnalysisState();
  };

  const handleSingleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!isFastaFile(file.name)) {
      alert("Please select a valid FASTA file.");
      resetInputs();
      return;
    }

    setIsLoading(true);

    try {
      const text = await readFileAsText(file);
      const seq = extractSequenceFromFasta(text);

      if (!seq) {
        alert("No DNA sequence found in the selected FASTA file.");
        resetInputs();
        return;
      }

      if (!isValidDNASequence(seq)) {
        alert(
          "The selected file contains invalid characters. Only A, C, G, T and N are allowed."
        );
        resetInputs();
        return;
      }

      applyLoadedSingleSequence(seq, file.name);
    } catch (error) {
      console.error(error);
      alert("Failed to parse the selected file.");
    } finally {
      setIsLoading(false);
      resetInputs();
    }
  };

  const readSingleFastaFile = async (file) => {
    const text = await readFileAsText(file);
    const sequence = extractSequenceFromFasta(text);

    return {
      name: file.webkitRelativePath || file.name,
      sequence,
      meta: buildSequenceMeta(sequence, file.webkitRelativePath || file.name),
    };
  };

  const handleFolder = async (e) => {
    const files = Array.from(e.target.files || []);

    if (!files.length) {
      alert("No files detected.");
      resetInputs();
      return;
    }

    const fastaFiles = files.filter((file) => isFastaFile(file.name));

    if (!fastaFiles.length) {
      alert("No FASTA files found in the selected folder.");
      resetInputs();
      return;
    }

    if (fastaFiles.length > MAX_FOLDER_FILES_TO_PROCESS_AT_ONCE) {
      alert(
        `Too many FASTA files selected (${fastaFiles.length}). ` +
          `Please load fewer than ${MAX_FOLDER_FILES_TO_PROCESS_AT_ONCE} files at once.`
      );
      resetInputs();
      return;
    }

    setIsLoading(true);

    try {
      const validFiles = [];

      for (const file of fastaFiles) {
        const parsed = await readSingleFastaFile(file);

        if (!parsed.sequence || parsed.sequence.length === 0) {
          continue;
        }

        if (!isValidDNASequence(parsed.sequence)) {
          console.warn(`Skipping invalid DNA file: ${parsed.name}`);
          continue;
        }

        validFiles.push(parsed);
      }

      if (!validFiles.length) {
        alert("No valid DNA sequence found in the selected folder.");
        resetInputs();
        return;
      }

      const first = validFiles[0];
      warnIfLargeSequence(first.sequence.length);

      setMode("folder");
      setFolderFiles(validFiles);

      if (typeof setFullSequenceRef === "function") {
        setFullSequenceRef(first.sequence);
      }

      if (typeof setSequenceMeta === "function") {
        setSequenceMeta(first.meta);
      }

      if (first.meta.isHuge) {
        setSequence(getPreviewSequence(first.sequence));
      } else {
        setSequence(first.sequence);
      }

      setLoadedFileName(`${validFiles.length} FASTA file(s) loaded`);
      resetAnalysisState();
    } catch (error) {
      console.error(error);
      alert("Failed to load folder.");
    } finally {
      setIsLoading(false);
      resetInputs();
    }
  };

  return (
    <div className="flex flex-wrap gap-3">
      <label
        className={`cursor-pointer rounded-xl border px-4 py-2 text-sm font-medium transition ${
          isLoading
            ? "border-slate-300 bg-slate-300 text-slate-500"
            : "border-slate-200 bg-slate-900 text-white hover:bg-slate-800"
        }`}
      >
        {isLoading ? "Loading..." : "Import FASTA file"}
        <input
          ref={singleFileInputRef}
          type="file"
          accept=".fasta,.fa,.fna,.fas,.txt"
          onChange={handleSingleFile}
          className="hidden"
          disabled={isLoading}
        />
      </label>

      <label
        className={`cursor-pointer rounded-xl border px-4 py-2 text-sm font-medium transition ${
          isLoading
            ? "border-slate-300 bg-slate-300 text-slate-500"
            : "border-slate-700 bg-slate-100 text-slate-900 hover:bg-slate-300"
        }`}
      >
        {isLoading ? "Loading..." : "Import FASTA folder"}
        <input
          ref={folderInputRef}
          type="file"
          multiple
          onChange={handleFolder}
          className="hidden"
          disabled={isLoading}
        />
      </label>
    </div>
  );
}
