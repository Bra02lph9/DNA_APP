import { useEffect, useRef } from "react";

const FASTA_EXTENSIONS = [".fasta", ".fa", ".fna", ".fas", ".txt"];

function isFastaFile(filename = "") {
  const lower = filename.toLowerCase();
  return FASTA_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function extractSequenceFromFasta(text = "") {
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim() && !line.startsWith(">"))
    .join("")
    .replace(/\s+/g, "")
    .toUpperCase()
    .trim();
}

function isValidDNASequence(sequence = "") {
  return /^[ACGTN]*$/i.test(sequence);
}

export default function UploadFile({
  setSequence,
  setLoadedFileName,
  setFolderFiles,
  setMode,
  setResults,
}) {
  const folderInputRef = useRef(null);
  const singleFileInputRef = useRef(null);

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

  const handleSingleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!isFastaFile(file.name)) {
      alert("Please select a valid FASTA file.");
      resetInputs();
      return;
    }

    const reader = new FileReader();

    reader.onload = (event) => {
      try {
        const text = event.target?.result || "";
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

        setMode("single");
        setSequence(seq);
        setLoadedFileName(file.name);
        setFolderFiles([]);
        resetAnalysisState();
      } catch (error) {
        console.error(error);
        alert("Failed to parse the selected file.");
      } finally {
        resetInputs();
      }
    };

    reader.onerror = () => {
      alert("Failed to read the file.");
      resetInputs();
    };

    reader.readAsText(file);
  };

  const readSingleFastaFile = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        try {
          const text = event.target?.result || "";
          const sequence = extractSequenceFromFasta(text);

          resolve({
            name: file.webkitRelativePath || file.name,
            sequence,
          });
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => {
        reject(new Error(`Failed to read ${file.name}`));
      };

      reader.readAsText(file);
    });

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

    try {
      const parsedFiles = await Promise.all(fastaFiles.map(readSingleFastaFile));

      const validFiles = parsedFiles.filter(
        (file) =>
          file.sequence &&
          file.sequence.length > 0 &&
          isValidDNASequence(file.sequence)
      );

      if (!validFiles.length) {
        alert("No valid DNA sequence found in the selected folder.");
        resetInputs();
        return;
      }

      setMode("folder");
      setFolderFiles(validFiles);
      setSequence(validFiles[0].sequence);
      setLoadedFileName(`${validFiles.length} FASTA file(s) loaded`);
      resetAnalysisState();
    } catch (error) {
      console.error(error);
      alert("Failed to load folder.");
    } finally {
      resetInputs();
    }
  };

  return (
    <div className="flex flex-wrap gap-3">
      <label className="cursor-pointer border border-slate-200 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800">
        Import FASTA file
        <input
          ref={singleFileInputRef}
          type="file"
          accept=".fasta,.fa,.fna,.fas,.txt"
          onChange={handleSingleFile}
          className="hidden"
        />
      </label>

      <label className="cursor-pointer rounded-xl border border-slate-700 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-300">
        Import FASTA folder
        <input
          ref={folderInputRef}
          type="file"
          multiple
          onChange={handleFolder}
          className="hidden"
        />
      </label>
    </div>
  );
}
