import { useState } from "react";

export interface MarkupPath {
  points: { x: number; y: number }[];
  description?: string;
}

export function useMarkup() {
  const [drawing, setDrawing] = useState(false);
  const [path, setPath] = useState<MarkupPath | null>(null);
  const [history, setHistory] = useState<MarkupPath[]>([]);

  function start(x: number, y: number) {
    setDrawing(true);
    setPath({ points: [{ x, y }] });
  }
  function extend(x: number, y: number) {
    if (!drawing || !path) return;
    setPath({ ...path, points: [...path.points, { x, y }] });
  }
  function finish(description?: string) {
    if (!path) return;
    const finished = { ...path, description };
    setHistory((h) => [...h, finished]);
    setPath(null);
    setDrawing(false);
    return finished;
  }
  function clear() {
    setPath(null);
    setDrawing(false);
  }

  return { drawing, path, history, start, extend, finish, clear };
}
