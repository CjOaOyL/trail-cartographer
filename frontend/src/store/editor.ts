import { create } from "zustand";
import type { EditOp, PlacedSymbol, Project, Symbol } from "../api/client";

type Tool = "select" | "place" | "draw";
export type LoadStage =
  | "idle"
  | "uploading"
  | "rendering"
  | "loading-svg"
  | "ready"
  | "error";

export interface MarkupPath {
  points: { x: number; y: number }[];
}

interface EditorState {
  project: Project | null;
  baseSvg: string | null;
  builtinSymbols: Symbol[];
  customSymbols: Symbol[];
  tool: Tool;
  selectedSymbolId: string | null;
  selectedInstanceId: string | null;
  pendingMarkup: MarkupPath | null;
  pendingOps: EditOp[] | null;
  loadStage: LoadStage;
  loadError: string | null;

  setProject(p: Project | null): void;
  setBaseSvg(svg: string | null): void;
  setBuiltinSymbols(s: Symbol[]): void;
  addCustomSymbol(s: Symbol): void;
  setTool(t: Tool): void;
  selectSymbol(id: string | null): void;
  selectInstance(id: string | null): void;
  placeInstance(p: PlacedSymbol): void;
  moveInstance(instanceId: string, x: number, y: number): void;
  removeInstance(instanceId: string): void;
  setPendingMarkup(p: MarkupPath | null): void;
  setPendingOps(ops: EditOp[] | null): void;
  applyOp(op: EditOp): void;
  setLoadStage(stage: LoadStage, error?: string | null): void;
}

export const useEditor = create<EditorState>((set) => ({
  project: null,
  baseSvg: null,
  builtinSymbols: [],
  customSymbols: [],
  tool: "select",
  selectedSymbolId: null,
  selectedInstanceId: null,
  pendingMarkup: null,
  pendingOps: null,
  loadStage: "idle",
  loadError: null,

  setProject: (project) => set({ project }),
  setBaseSvg: (baseSvg) => set({ baseSvg }),
  setBuiltinSymbols: (builtinSymbols) => set({ builtinSymbols }),
  addCustomSymbol: (s) =>
    set((state) => ({ customSymbols: [...state.customSymbols, s] })),
  setTool: (tool) => set({ tool }),
  selectSymbol: (selectedSymbolId) => set({ selectedSymbolId, tool: "place" }),
  selectInstance: (selectedInstanceId) => set({ selectedInstanceId }),
  placeInstance: (p) =>
    set((state) =>
      state.project
        ? { project: { ...state.project, symbols: [...state.project.symbols, p] } }
        : {},
    ),
  moveInstance: (instanceId, x, y) =>
    set((state) =>
      state.project
        ? {
            project: {
              ...state.project,
              symbols: state.project.symbols.map((s) =>
                s.instance_id === instanceId ? { ...s, x, y } : s,
              ),
            },
          }
        : {},
    ),
  removeInstance: (instanceId) =>
    set((state) =>
      state.project
        ? {
            project: {
              ...state.project,
              symbols: state.project.symbols.filter((s) => s.instance_id !== instanceId),
            },
          }
        : {},
    ),
  setPendingMarkup: (pendingMarkup) => set({ pendingMarkup }),
  setPendingOps: (pendingOps) => set({ pendingOps }),
  setLoadStage: (loadStage, loadError = null) => set({ loadStage, loadError }),
  applyOp: (op) =>
    set((state) => {
      if (!state.project) return {};
      const symbols = state.project.symbols;
      switch (op.op) {
        case "add": {
          if (op.x == null || op.y == null || !op.svg) return {};
          const newSym: Symbol = {
            id: `gen_${Date.now()}`,
            name: op.name ?? "Custom",
            svg: op.svg,
            generated: true,
          };
          return {
            customSymbols: [...state.customSymbols, newSym],
            project: {
              ...state.project,
              symbols: [
                ...symbols,
                {
                  instance_id: crypto.randomUUID(),
                  symbol_id: newSym.id,
                  x: op.x,
                  y: op.y,
                  rotation: 0,
                  scale: 1,
                },
              ],
            },
          };
        }
        case "move": {
          if (!op.instance_id || op.dx == null || op.dy == null) return {};
          return {
            project: {
              ...state.project,
              symbols: symbols.map((s) =>
                s.instance_id === op.instance_id
                  ? { ...s, x: s.x + op.dx!, y: s.y + op.dy! }
                  : s,
              ),
            },
          };
        }
        case "remove": {
          if (!op.instance_id) return {};
          return {
            project: {
              ...state.project,
              symbols: symbols.filter((s) => s.instance_id !== op.instance_id),
            },
          };
        }
        default:
          return {};
      }
    }),
}));
