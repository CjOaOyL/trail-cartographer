import { useEditor } from "../store/editor";
import { useMarkup, type MarkupPath } from "../hooks/useMarkup";

interface Props {
  width: number;
  height: number;
  onSubmit?(path: MarkupPath): void;
}

export function DrawingLayer({ width, height, onSubmit }: Props) {
  const tool = useEditor((s) => s.tool);
  const { drawing, path, start, extend, finish } = useMarkup();

  if (tool !== "draw") return null;

  const onDown = (e: React.PointerEvent<SVGRectElement>) => {
    e.preventDefault();
    start(e.nativeEvent.offsetX, e.nativeEvent.offsetY);
  };
  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    if (!drawing) return;
    extend(e.nativeEvent.offsetX, e.nativeEvent.offsetY);
  };
  const onUp = () => {
    const finished = finish();
    if (finished) onSubmit?.(finished);
  };

  const d = path?.points.map((p, i) => `${i ? "L" : "M"} ${p.x} ${p.y}`).join(" ");

  return (
    <g>
      <rect
        x={0}
        y={0}
        width={width}
        height={height}
        fill="transparent"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        style={{ cursor: "crosshair" }}
      />
      {d && <path d={d} fill="rgba(255,180,0,0.18)" stroke="#e08a2a" strokeWidth={1.5} />}
    </g>
  );
}
