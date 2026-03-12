export function getHighlightClass(pos, highlights) {
  const hit = highlights.find((h) => pos >= h.start && pos <= h.end);

  if (!hit) return "text-slate-800";

  const base = "text-black rounded px-[1px]";

  switch (hit.type) {
    case "promoter35":
      return `bg-yellow-300 ${base}`;

    case "promoter10":
      return `bg-orange-300 ${base}`;

    case "shineDalgarno":
      return `bg-pink-200 ${base}`;
    case "startCodon":
         return `bg-red-300 ${base}`;

    case "terminatorLeft":
      return `bg-purple-300 ${base}`;

    case "terminatorRight":
      return `bg-fuchsia-300 ${base}`;

    case "polyT":
      return `bg-red-300 ${base}`;

    case "orf":
      return `bg-cyan-300 ${base}`;

    default:
      return `bg-lime-300 ${base}`;
  }
}
