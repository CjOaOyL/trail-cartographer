import { useState } from "react";
import { useEditor, type MarkupPath } from "../store/editor";

interface Props {
  width: number;
  height: number;
}

export function DrawingLayer({ width, height }: Props) {
  const tool = useEditor((s) => s.tool);
  const setPendingMarkup = useEditor((s) => s.setPendingMarkup);
  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<{ x: number; y: number }[]>([]);

  if (tool !== "draw") return null;

  function svgPoint(target: SVGGraphicsElement, clientX: number, clientY: number) {
    const svg = target.ownerSVGElement!;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const m = target.getScreenCTM();
    return m ? pt.matrixTransform(m.inverse()) : pt;
  }

  const onDown = (e: React.PointerEvent<SVGRectElement>) => {
    e.stopPropagation();
    const p = svgPoint(e.currentTarget, e.clientX, e.clientY);
    setDrawing(true);
    setPoints([{ x: p.x, y: p.y }]);
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    if (!drawing) return;
    const p = svgPoint(e.currentTarget, e.clientX, e.clientY);
    setPoints((prev) => [...prev, { x: p.x, y: p.y }]);
  };
  const onUp = (e: React.PointerEvent<SVGRectElement>) => {
    if (!drawing) return;
    e.currentTarget.releasePointerCapture(e.pointerId);
    setDrawing(false);
    if (points.length >= 3) {
      const path: MarkupPath = { points };
      setPendingMarkup(path);
    }
    setPoints([]);
  };

  const d = points.map((p, i) => `${i ? "L" : "M"} ${p.x.toFixed(0)} ${p.y.toFixed(0)}`).join(" ");

  return (
    <g style={{ pointerEvents: "all" }}>
      <rect
        x={0}
        y={0}
        width={width}
        height={height}
        fill="transparent"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        style={{ cursor: "crosshair" }}
      />
      {d && (
        <path
          d={d}
          fill="rgba(255,180,0,0.18)"
          stroke="#e08a2a"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          pointerEvents="none"
        />
      )}
    </g>
  );
}
