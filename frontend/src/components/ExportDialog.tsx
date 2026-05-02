import { useState } from "react";
import { useEditor } from "../store/editor";

export function ExportDialog({ open, onClose }: { open: boolean; onClose(): void }) {
  const project = useEditor((s) => s.project);
  const baseSvg = useEditor((s) => s.baseSvg);
  const [format, setFormat] = useState<"svg" | "png">("svg");

  if (!open || !project || !baseSvg) return null;

  function download() {
    const blob = new Blob([baseSvg!], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${project!.name}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="fixed inset-0 grid place-items-center bg-black/40">
      <div className="w-80 rounded bg-parchment p-4 shadow-xl">
        <h3 className="mb-3 text-sm font-semibold">Export map</h3>
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as "svg" | "png")}
          className="mb-3 w-full rounded border border-ink/20 bg-white/40 p-1"
        >
          <option value="svg">SVG (vector)</option>
          <option value="png">PNG (TODO)</option>
        </select>
        <div className="flex justify-end gap-2 text-sm">
          <button onClick={onClose} className="rounded border border-ink/20 px-3 py-1">
            Cancel
          </button>
          <button onClick={download} className="rounded bg-ink px-3 py-1 text-parchment">
            Download
          </button>
        </div>
      </div>
    </div>
  );
}
