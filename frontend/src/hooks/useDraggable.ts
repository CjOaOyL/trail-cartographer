import { RefObject, useEffect } from "react";

export function useDraggable(
  ref: RefObject<SVGGElement>,
  onMove: (clientX: number, clientY: number) => void,
) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let dragging = false;

    const onDown = (e: PointerEvent) => {
      e.stopPropagation();
      dragging = true;
      el.setPointerCapture(e.pointerId);
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!dragging) return;
      onMove(e.clientX, e.clientY);
    };
    const onUp = (e: PointerEvent) => {
      dragging = false;
      el.releasePointerCapture(e.pointerId);
    };

    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
    return () => {
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
    };
  }, [ref, onMove]);
}
