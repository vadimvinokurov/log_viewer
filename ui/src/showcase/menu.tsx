import { useLayoutEffect, useRef, useState } from "react";
import { ContextMenu, type ContextMenuProps } from "../ContextMenu.tsx";

/**
 * Showcase entries for the context menu (?show=menu) for the visual harness.
 * The menu is an absolutely positioned overlay, so each variant renders it
 * inside a frame that measures the rendered menu and shrinks to its box -
 * the design oracle screenshots the variant and compares it against the
 * design mock's exact `.cm` element.
 */
function MenuFrame(props: ContextMenuProps) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);
  useLayoutEffect(() => {
    const root = frameRef.current?.querySelector<HTMLElement>("[data-menu-root]");
    if (root) {
      const rect = root.getBoundingClientRect();
      setBox({ w: rect.width, h: rect.height });
    }
  }, []);
  return (
    <div
      ref={frameRef}
      style={{ position: "relative", width: box?.w, height: box?.h }}
    >
      <ContextMenu {...props} />
    </div>
  );
}

// Static gallery: commands are no-ops here, toggling behavior is covered by
// unit tests on the component.
const noop = (): void => {};

const commandHandlers = (): ContextMenuProps => ({
  x: 0,
  y: 0,
  onCopy: noop,
  onCopyMessage: noop,
  onPin: noop,
  onUnpin: noop,
  onHighlight: noop,
  onRemoveHighlight: noop,
});

export const menuShowcase: Record<string, React.ReactNode> = {
  // The study frame itself (UI_DESIGN §s3 .cm): nothing pinned or highlighted
  // yet, so Unpin and Remove highlight are dimmed - the design oracle pair.
  default: <MenuFrame {...commandHandlers()} />,
  // Selection on rows that carry pins and highlights: every command enabled.
  "on-rows": (
    <MenuFrame {...commandHandlers()} canUnpin canRemoveHighlight />
  ),
};
