import { useRef } from "react";
import { renderProject, svgUrl, uploadGpx } from "../api/client";
import { useEditor } from "../store/editor";

const STAGE_LABEL: Record<string, string> = {
  idle: "",
  uploading: "Uploading…",
  rendering: "Rendering map (first load fetches elevation, land cover, OSM, parcels — can take a minute)…",
  "loading-svg": "Loading map…",
  ready: "",
  error: "Error",
};

export function Toolbar() {
  const inputRef = useRef<HTMLInputElement>(null);
  const project = useEditor((s) => s.project);
  const tool = useEditor((s) => s.tool);
  const loadStage = useEditor((s) => s.loadStage);
  const loadError = useEditor((s) => s.loadError);
  const setProject = useEditor((s) => s.setProject);
  const setBaseSvg = useEditor((s) => s.setBaseSvg);
  const setTool = useEditor((s) => s.setTool);
  const setLoadStage = useEditor((s) => s.setLoadStage);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";  // allow re-upload of same file
    try {
      setLoadStage("uploading");
      const p = await uploadGpx(file);
      setProject(p);
      setLoadStage("rendering");
      await renderProject(p.id);
      setLoadStage("loading-svg");
      const r = await fetch(svgUrl(p.id));
      setBaseSvg(await r.text());
      setLoadStage("ready");
    } catch (err) {
      setLoadStage("error", err instanceof Error ? err.message : "Upload failed");
    }
  }

  const busy = loadStage !== "idle" && loadStage !== "ready" && loadStage !== "error";

  return (
    <div className="border-b border-ink/15">
      <div className="flex items-center gap-3 px-6 py-2 text-sm">
        <button
          className="rounded border border-ink/30 px-3 py-1 hover:bg-ink/5 disabled:opacity-50"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
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
        <span className="text-ink/60 truncate">
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

      {(busy || loadStage === "error") && (
        <div className="px-6 pb-2">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-1 bg-ink/10 overflow-hidden rounded">
              {busy && (
                <div className="h-full bg-ink/60 animate-[load_1.4s_ease-in-out_infinite]" style={{
                  width: "40%",
                  animation: "loadbar 1.4s ease-in-out infinite",
                }} />
              )}
              {loadStage === "error" && <div className="h-full bg-red-700 w-full" />}
            </div>
            <span className="text-xs text-ink/70 whitespace-nowrap">
              {loadStage === "error" ? loadError : STAGE_LABEL[loadStage]}
            </span>
          </div>
        </div>
      )}

      <style>{`
        @keyframes loadbar {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(150%); }
          100% { transform: translateX(250%); }
        }
      `}</style>
    </div>
  );
}
