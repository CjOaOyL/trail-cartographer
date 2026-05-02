import { useEffect } from "react";
import { listBuiltinSymbols } from "../api/client";
import { useEditor } from "../store/editor";

export function SymbolPalette() {
  const { builtinSymbols, customSymbols, selectedSymbolId, setBuiltinSymbols, selectSymbol } =
    useEditor();

  useEffect(() => {
    listBuiltinSymbols().then(setBuiltinSymbols).catch(() => {});
  }, [setBuiltinSymbols]);

  const all = [...builtinSymbols, ...customSymbols];

  return (
    <aside className="w-48 shrink-0 border-r border-ink/15 overflow-y-auto p-3">
      <h2 className="mb-2 text-xs uppercase tracking-wider text-ink/60">Symbols</h2>
      <div className="grid grid-cols-2 gap-2">
        {all.map((s) => (
          <button
            key={s.id}
            onClick={() => selectSymbol(s.id)}
            className={`flex flex-col items-center gap-1 rounded border p-2 hover:bg-ink/5 ${
              selectedSymbolId === s.id ? "border-ink" : "border-ink/20"
            }`}
            title={s.name}
          >
            <svg viewBox="-16 -16 32 32" className="h-10 w-10" dangerouslySetInnerHTML={{ __html: s.svg }} />
            <span className="text-[10px] text-ink/70 truncate w-full text-center">{s.name}</span>
          </button>
        ))}
      </div>
      {all.length === 0 && <p className="text-xs text-ink/50">Loading…</p>}
    </aside>
  );
}
