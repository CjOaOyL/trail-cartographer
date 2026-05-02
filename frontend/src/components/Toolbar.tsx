import { useRef } from "react";
import { renderProject, svgUrl, uploadGpx } from "../api/client";
import { useEditor } from "../store/editor";

export function Toolbar() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { project, tool, setProject, setBaseSvg, setTool } = useEditor();

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const p = await uploadGpx(file);
    setProject(p);
    await renderProject(p.id);
    const r = await fetch(svgUrl(p.id));
    setBaseSvg(await r.text());
  }

  return (
    <div className="flex items-center gap-3 border-b border-ink/15 px-6 py-2 text-sm">
      <button
        className="rounded border border-ink/30 px-3 py-1 hover:bg-ink/5"
        onClick={() => inputRef.current?.click()}
      >
        Upload GPX
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".gpx,.kml,.geojson"
        className="hidden"
        onChange={onFile}
      />
      <span className="text-ink/60">
        {project ? `Project: ${project.name}` : "No project loaded"}
      </span>

      <div className="ml-auto flex gap-1">
        {(["select", "place", "draw"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTool(t)}
            className={`rounded px-2 py-1 text-xs uppercase tracking-wide ${
              tool === t ? "bg-ink text-parchment" : "border border-ink/20"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}
