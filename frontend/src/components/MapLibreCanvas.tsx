import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { Map as MlMap, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEditor } from "../store/editor";
import { useDraggable } from "../hooks/useDraggable";
import { DrawingLayer } from "./DrawingLayer";

type BasemapKind = "cartoon" | "streets" | "satellite";

const STYLES: Record<BasemapKind, StyleSpecification> = {
  cartoon: {
    version: 8,
    sources: {},
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#f3eedd" } },
    ],
  },
  streets: {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }],
  },
  satellite: {
    version: 8,
    sources: {
      sat: {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution:
          'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
      },
    },
    layers: [{ id: "sat", type: "raster", source: "sat" }],
  },
};

const LAYER_IDS = [
  "elevation",
  "nlcd",
  "parcels",
  "water",
  "trees",
  "buildings",
  "peaks",
  "trail",
] as const;

type LayerId = (typeof LAYER_IDS)[number];

const LAYER_LABELS: Record<LayerId, string> = {
  elevation: "Elevation tint",
  nlcd: "Land cover",
  parcels: "Parcels",
  water: "Water",
  trees: "Trees",
  buildings: "Buildings",
  peaks: "Peaks",
  trail: "Trail",
};

export function MapLibreCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const symbolLayerRef = useRef<SVGSVGElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [basemap, setBasemap] = useState<BasemapKind>("cartoon");
  const [overlayOpacity, setOverlayOpacity] = useState(1);
  const [layerVisible, setLayerVisible] = useState<Record<LayerId, boolean>>({
    elevation: true,
    nlcd: true,
    parcels: true,
    water: true,
    trees: true,
    buildings: true,
    peaks: true,
    trail: true,
  });

  const project = useEditor((s) => s.project);
  const baseSvg = useEditor((s) => s.baseSvg);
  const tool = useEditor((s) => s.tool);
  const builtinSymbols = useEditor((s) => s.builtinSymbols);
  const customSymbols = useEditor((s) => s.customSymbols);
  const selectedSymbolId = useEditor((s) => s.selectedSymbolId);
  const placeInstance = useEditor((s) => s.placeInstance);
  const moveInstance = useEditor((s) => s.moveInstance);

  const allSymbols = useMemo(
    () => [...builtinSymbols, ...customSymbols],
    [builtinSymbols, customSymbols],
  );

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const m = new maplibregl.Map({
      container: containerRef.current,
      style: STYLES.cartoon,
      center: [-74, 42],
      zoom: 6,
      attributionControl: { compact: true },
    });
    m.addControl(new maplibregl.NavigationControl({}), "top-right");
    mapRef.current = m;

    const update = () => updateOverlay();
    m.on("move", update);
    m.on("zoom", update);
    m.on("resize", update);

    return () => {
      m.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Style swap
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setStyle(STYLES[basemap]);
  }, [basemap]);

  // Fit to bbox on project change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !project?.geo_bbox) return;
    const [lonMin, latMin, lonMax, latMax] = project.geo_bbox;
    map.fitBounds(
      [
        [lonMin, latMin],
        [lonMax, latMax],
      ],
      { padding: 40, duration: 600 },
    );
  }, [project?.geo_bbox]);

  // Toggle layer visibility on the embedded SVG
  useEffect(() => {
    const root = overlayRef.current?.querySelector("svg");
    if (!root) return;
    for (const id of LAYER_IDS) {
      const g = root.querySelector(`#layer-${id}`) as SVGGElement | null;
      if (g) g.style.display = layerVisible[id] ? "" : "none";
    }
  }, [layerVisible, baseSvg]);

  // Update overlay rect after svg loads or project changes
  useEffect(() => {
    updateOverlay();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseSvg, project?.geo_bbox]);

  function updateOverlay() {
    const map = mapRef.current;
    if (!map || !project?.geo_bbox || !overlayRef.current) return;
    const [lonMin, latMin, lonMax, latMax] = project.geo_bbox;
    const nw = map.project([lonMin, latMax]);
    const se = map.project([lonMax, latMin]);
    const x = Math.min(nw.x, se.x);
    const y = Math.min(nw.y, se.y);
    const w = Math.abs(se.x - nw.x);
    const h = Math.abs(se.y - nw.y);
    const el = overlayRef.current;
    el.style.transform = `translate(${x}px, ${y}px)`;
    el.style.width = `${w}px`;
    el.style.height = `${h}px`;
  }

  // Click-to-place — convert client coords to overlay-local SVG coords
  function onOverlayClick(e: React.MouseEvent<SVGSVGElement>) {
    if (tool !== "place" || !selectedSymbolId || !project) return;
    const svg = symbolLayerRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const local = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    placeInstance({
      instance_id: crypto.randomUUID(),
      symbol_id: selectedSymbolId,
      x: local.x,
      y: local.y,
      rotation: 0,
      scale: 1,
    });
  }

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="absolute inset-0" />

      {/* Cartoon SVG overlay (positioned to match project bbox) */}
      <div
        ref={overlayRef}
        className="absolute top-0 left-0 origin-top-left"
        style={{
          width: 0,
          height: 0,
          pointerEvents: "none",
          opacity: overlayOpacity,
        }}
      >
        {baseSvg && (
          <div
            className="w-full h-full [&>svg]:w-full [&>svg]:h-full [&>svg]:block"
            dangerouslySetInnerHTML={{ __html: baseSvg }}
          />
        )}
        {/* Symbols + drawing share an SVG matching the overlay dimensions */}
        {project && (
          <svg
            ref={symbolLayerRef}
            className="absolute inset-0 w-full h-full"
            viewBox="0 0 1100 860"
            preserveAspectRatio="none"
            style={{ pointerEvents: tool === "select" ? "none" : "auto" }}
            onClick={onOverlayClick}
          >
            {project.symbols.map((p) => {
              const sym = allSymbols.find((s) => s.id === p.symbol_id);
              if (!sym) return null;
              return (
                <DraggableSymbol
                  key={p.instance_id}
                  x={p.x}
                  y={p.y}
                  svg={sym.svg}
                  onMove={(x, y) => moveInstance(p.instance_id, x, y)}
                  getSvg={() => symbolLayerRef.current!}
                />
              );
            })}
            <DrawingLayer width={1100} height={860} />
          </svg>
        )}
      </div>

      <BasemapToggle value={basemap} onChange={setBasemap} />
      <LayerPanel
        visible={layerVisible}
        onToggle={(id) =>
          setLayerVisible((v) => ({ ...v, [id]: !v[id] }))
        }
        opacity={overlayOpacity}
        onOpacityChange={setOverlayOpacity}
      />

      {!baseSvg && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-ink/50 text-sm">
          Upload a GPX to begin.
        </div>
      )}
    </div>
  );
}

interface DraggableProps {
  x: number;
  y: number;
  svg: string;
  onMove(x: number, y: number): void;
  getSvg(): SVGSVGElement;
}

function DraggableSymbol({ x, y, svg, onMove, getSvg }: DraggableProps) {
  const ref = useRef<SVGGElement>(null);
  useDraggable(ref, (clientX, clientY) => {
    const s = getSvg();
    const pt = s.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const local = pt.matrixTransform(s.getScreenCTM()!.inverse());
    onMove(local.x, local.y);
  });
  return (
    <g
      ref={ref}
      transform={`translate(${x} ${y})`}
      style={{ cursor: "grab", pointerEvents: "all" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

function BasemapToggle({
  value,
  onChange,
}: {
  value: BasemapKind;
  onChange(v: BasemapKind): void;
}) {
  return (
    <div className="absolute top-3 left-3 z-10 rounded bg-white/90 shadow border border-ink/15 p-1 flex gap-1 text-xs">
      {(["cartoon", "streets", "satellite"] as const).map((k) => (
        <button
          key={k}
          onClick={() => onChange(k)}
          className={`rounded px-2 py-1 capitalize ${
            value === k ? "bg-ink text-parchment" : "hover:bg-ink/5"
          }`}
        >
          {k}
        </button>
      ))}
    </div>
  );
}

function LayerPanel({
  visible,
  onToggle,
  opacity,
  onOpacityChange,
}: {
  visible: Record<LayerId, boolean>;
  onToggle(id: LayerId): void;
  opacity: number;
  onOpacityChange(o: number): void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded bg-white/90 shadow border border-ink/15 px-3 py-1 text-xs"
      >
        Layers {open ? "▴" : "▾"}
      </button>
      {open && (
        <div className="mt-1 rounded bg-white/95 shadow border border-ink/15 p-3 text-xs space-y-1 w-56">
          <div className="flex items-center gap-2 pb-2 border-b border-ink/10">
            <span className="text-ink/60">Cartoon opacity</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
              className="flex-1"
            />
          </div>
          {LAYER_IDS.map((id) => (
            <label key={id} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={visible[id]}
                onChange={() => onToggle(id)}
              />
              <span>{LAYER_LABELS[id]}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
