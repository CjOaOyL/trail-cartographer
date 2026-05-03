import { useState } from "react";
import { generateSymbol, interpretMarkup } from "../api/client";
import { useEditor } from "../store/editor";

export function AIChat() {
  return (
    <aside className="w-72 shrink-0 border-l border-ink/15 p-3 flex flex-col gap-3 overflow-y-auto">
      <SymbolGenSection />
      <div className="border-t border-ink/15 pt-3">
        <MarkupSection />
      </div>
    </aside>
  );
}

function SymbolGenSection() {
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addCustomSymbol, selectSymbol } = useEditor();

  async function onGenerate() {
    if (!description.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const sym = await generateSymbol(description);
      addCustomSymbol(sym);
      selectSymbol(sym.id);
      setDescription("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2 className="text-xs uppercase tracking-wider text-ink/60">AI symbol</h2>
      <textarea
        className="h-24 w-full resize-none rounded border border-ink/20 bg-white/40 p-2 text-sm"
        placeholder="e.g. blueberry patch with 5 bushes and a small label"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        disabled={busy}
      />
      <button
        className="rounded bg-ink px-3 py-1 text-xs uppercase tracking-wide text-parchment disabled:opacity-50"
        onClick={onGenerate}
        disabled={busy || !description.trim()}
      >
        {busy ? "Generating…" : "Generate symbol"}
      </button>
      {error && <p className="text-xs text-red-700">{error}</p>}
    </>
  );
}

function MarkupSection() {
  const project = useEditor((s) => s.project);
  const pendingMarkup = useEditor((s) => s.pendingMarkup);
  const pendingOps = useEditor((s) => s.pendingOps);
  const setPendingMarkup = useEditor((s) => s.setPendingMarkup);
  const setPendingOps = useEditor((s) => s.setPendingOps);
  const applyOp = useEditor((s) => s.applyOp);

  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit() {
    if (!project || !pendingMarkup || !description.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const polygon = pendingMarkup.points.map((p) => [p.x, p.y] as [number, number]);
      const inRegion = project.symbols.filter((s) =>
        pointInBbox(s.x, s.y, polygon),
      );
      const { ops } = await interpretMarkup({
        project_id: project.id,
        description,
        polygon,
        symbols_in_region: inRegion.map((s) => ({
          instance_id: s.instance_id,
          symbol_id: s.symbol_id,
          x: s.x,
          y: s.y,
        })),
      });
      setPendingOps(ops);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markup failed");
    } finally {
      setBusy(false);
    }
  }

  function applyAll() {
    pendingOps?.forEach(applyOp);
    setPendingOps(null);
    setPendingMarkup(null);
    setDescription("");
  }

  function discard() {
    setPendingOps(null);
    setPendingMarkup(null);
    setDescription("");
  }

  if (!pendingMarkup && !pendingOps) {
    return (
      <>
        <h2 className="text-xs uppercase tracking-wider text-ink/60">Markup edits</h2>
        <p className="text-xs text-ink/60 mt-1">
          Switch to the <strong>draw</strong> tool, drag on the map to lasso a region,
          then describe what should change.
        </p>
      </>
    );
  }

  if (pendingMarkup && !pendingOps) {
    return (
      <>
        <h2 className="text-xs uppercase tracking-wider text-ink/60">Describe edit</h2>
        <p className="text-[11px] text-ink/60 mt-1">
          {pendingMarkup.points.length} points captured.
        </p>
        <textarea
          className="mt-2 h-20 w-full resize-none rounded border border-ink/20 bg-white/40 p-2 text-sm"
          placeholder="e.g. add a fire pit here, or remove the trees in this area"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={busy}
        />
        <div className="mt-2 flex gap-2">
          <button
            className="rounded bg-ink px-3 py-1 text-xs uppercase tracking-wide text-parchment disabled:opacity-50"
            onClick={onSubmit}
            disabled={busy || !description.trim()}
          >
            {busy ? "Thinking…" : "Submit"}
          </button>
          <button
            className="rounded border border-ink/20 px-3 py-1 text-xs uppercase tracking-wide"
            onClick={discard}
            disabled={busy}
          >
            Cancel
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
      </>
    );
  }

  return (
    <>
      <h2 className="text-xs uppercase tracking-wider text-ink/60">Proposed edits</h2>
      <ul className="mt-1 max-h-40 overflow-y-auto text-xs text-ink/80 space-y-1">
        {pendingOps!.map((op, i) => (
          <li key={i} className="rounded border border-ink/15 px-2 py-1">
            <span className="font-mono text-[10px] uppercase">{op.op}</span>{" "}
            {op.name && <span>({op.name})</span>}
            {op.dx != null && <span> Δ{op.dx.toFixed(0)},{op.dy?.toFixed(0)}</span>}
            {op.x != null && <span> @{op.x.toFixed(0)},{op.y?.toFixed(0)}</span>}
          </li>
        ))}
      </ul>
      <div className="mt-2 flex gap-2">
        <button
          className="rounded bg-ink px-3 py-1 text-xs uppercase tracking-wide text-parchment"
          onClick={applyAll}
        >
          Apply all
        </button>
        <button
          className="rounded border border-ink/20 px-3 py-1 text-xs uppercase tracking-wide"
          onClick={discard}
        >
          Discard
        </button>
      </div>
    </>
  );
}

function pointInBbox(x: number, y: number, poly: [number, number][]): boolean {
  if (poly.length === 0) return false;
  const xs = poly.map((p) => p[0]);
  const ys = poly.map((p) => p[1]);
  return x >= Math.min(...xs) && x <= Math.max(...xs) && y >= Math.min(...ys) && y <= Math.max(...ys);
}
