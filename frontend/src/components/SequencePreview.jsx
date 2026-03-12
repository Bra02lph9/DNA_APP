import { getHighlightClass } from "../utils/sequenceHighlight";

export default function SequencePreview({ preview, highlights }) {

  if (!preview) {
    return (
      <div className="font-mono text-xs leading-6 text-slate-500">
        No sequence loaded.
      </div>
    );
  }
  const displaySequence = preview.slice(0, 2000);

  return (
    <div className="max-h-80 overflow-y-auto overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs leading-6">

      {displaySequence.split("").map((char, index) => {

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
