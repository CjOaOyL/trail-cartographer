import { useRef } from "react";
import { useEditor } from "../store/editor";
import { useDraggable } from "../hooks/useDraggable";
import { DrawingLayer } from "./DrawingLayer";

export function MapCanvas() {
  const svgRef = useRef<SVGSVGElement>(null);
  const { project, baseSvg, builtinSymbols, customSymbols, tool, selectedSymbolId, placeInstance, moveInstance } =
    useEditor();

  const allSymbols = [...builtinSymbols, ...customSymbols];

  const onClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (tool !== "place" || !selectedSymbolId || !project) return;
    const pt = svgPoint(svgRef.current!, e.clientX, e.clientY);
    placeInstance({
      instance_id: crypto.randomUUID(),
      symbol_id: selectedSymbolId,
      x: pt.x,
      y: pt.y,
      rotation: 0,
      scale: 1,
    });
  };

  return (
    <div className="h-full w-full overflow-auto p-4">
      {!baseSvg && (
        <div className="grid h-full place-items-center text-ink/50">
          Upload a GPX to begin.
        </div>
      )}
      {baseSvg && (
        <svg
          ref={svgRef}
          viewBox="0 0 1100 860"
          className="mx-auto block w-full max-w-5xl bg-parchment shadow"
          onClick={onClick}
        >
          <g dangerouslySetInnerHTML={{ __html: stripSvgWrapper(baseSvg) }} />
          {project?.symbols.map((p) => {
            const sym = allSymbols.find((s) => s.id === p.symbol_id);
            if (!sym) return null;
            return (
              <DraggableSymbol
                key={p.instance_id}
                instanceId={p.instance_id}
                x={p.x}
                y={p.y}
                svg={sym.svg}
                onMove={(x, y) => moveInstance(p.instance_id, x, y)}
                getSvg={() => svgRef.current!}
              />
            );
          })}
          <DrawingLayer width={1100} height={860} />
        </svg>
      )}
    </div>
  );
}

interface DraggableProps {
  instanceId: string;
  x: number;
  y: number;
  svg: string;
  onMove(x: number, y: number): void;
  getSvg(): SVGSVGElement;
}

function DraggableSymbol({ x, y, svg, onMove, getSvg }: DraggableProps) {
  const ref = useRef<SVGGElement>(null);
  useDraggable(ref, (clientX, clientY) => {
    const pt = svgPoint(getSvg(), clientX, clientY);
    onMove(pt.x, pt.y);
  });
  return (
    <g
      ref={ref}
      transform={`translate(${x} ${y})`}
      style={{ cursor: "grab" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

function svgPoint(svg: SVGSVGElement, clientX: number, clientY: number): DOMPoint {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  return pt.matrixTransform(svg.getScreenCTM()!.inverse());
}

function stripSvgWrapper(svg: string): string {
  return svg.replace(/<\?xml[\s\S]*?\?>/, "").replace(/<svg[^>]*>|<\/svg>/g, "");
}
