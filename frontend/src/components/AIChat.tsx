import { useState } from "react";
import { generateSymbol } from "../api/client";
import { useEditor } from "../store/editor";

export function AIChat() {
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
    <aside className="w-72 shrink-0 border-l border-ink/15 p-3 flex flex-col gap-3">
      <h2 className="text-xs uppercase tracking-wider text-ink/60">AI Symbol</h2>
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

      <div className="border-t border-ink/15 pt-3">
        <h2 className="mb-2 text-xs uppercase tracking-wider text-ink/60">Markup edits</h2>
        <p className="text-xs text-ink/60">
          Phase 2: select the draw tool, lasso a region on the map, then describe the change you want.
        </p>
      </div>
    </aside>
  );
}
