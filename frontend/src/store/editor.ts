import { create } from "zustand";
import type { PlacedSymbol, Project, Symbol } from "../api/client";

type Tool = "select" | "place" | "draw";

interface EditorState {
  project: Project | null;
  baseSvg: string | null;
  builtinSymbols: Symbol[];
  customSymbols: Symbol[];
  tool: Tool;
  selectedSymbolId: string | null;
  selectedInstanceId: string | null;

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
}

export const useEditor = create<EditorState>((set) => ({
  project: null,
  baseSvg: null,
  builtinSymbols: [],
  customSymbols: [],
  tool: "select",
  selectedSymbolId: null,
  selectedInstanceId: null,

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
}));
