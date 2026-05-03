import { useEffect, useState } from "react";
import { MapLibreCanvas } from "./components/MapLibreCanvas";
import { SymbolPalette } from "./components/SymbolPalette";
import { Toolbar } from "./components/Toolbar";
import { AIChat } from "./components/AIChat";
import { fetchHealth } from "./api/client";

export default function App() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-ink/20 bg-parchment px-6 py-3 flex items-center justify-between">
        <h1 className="font-serif text-xl text-ink">Trail Cartographer</h1>
        <span className="text-xs text-ink/60">
          backend: {healthy === null ? "…" : healthy ? "ok" : "offline"}
        </span>
      </header>

      <Toolbar />

      <div className="flex flex-1 min-h-0">
        <SymbolPalette />
        <main className="flex-1 min-w-0">
          <MapLibreCanvas />
        </main>
        <AIChat />
      </div>
    </div>
  );
}
