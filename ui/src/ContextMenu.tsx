export interface ContextMenuProps {
  /** Viewport coordinates where the menu opens. */
  x: number;
  y: number;
  onCopy?: () => void;
  onCopyMessage?: () => void;
  onPin?: () => void;
  /** The selection contains at least one NOT pinned row (§4 presence;
   *  q1f.1 evaluation lives in pins.ts, passed down by the table). */
  canPin?: boolean;
  onUnpin?: () => void;
  /** The selection contains pinned rows; Unpin is dim while false. */
  canUnpin?: boolean;
  onHighlight?: () => void;
  onRemoveHighlight?: () => void;
  /** The selection contains highlighted rows; Remove highlight is dim while false. */
  canRemoveHighlight?: boolean;
}

/**
 * Row context menu (FUNCTIONAL_SPEC §4; UI_DESIGN study frame "Context menu —
 * right-click on selection"): Copy with the Ctrl-C hint, Copy Message,
 * separator, Unpin/Pin, separator, Highlight/Remove highlight. The menu is a
 * floating overlay over the table; the store wiring (right-click event,
 * clipboard write) belongs to the integrating task, the commands fire the
 * callbacks here.
 *
 * Styles mirror the design's `.cm` rules verbatim (prefixed `lvc-cm` so the
 * class names cannot collide with the global stylesheet). The rules need the
 * --border/--border-strong/--accent-tint tokens, which ui/src/index.css does
 * not carry yet - they are defined here scoped to the menu until the token
 * sheet lands; values come from UI_DESIGN §s4 in both themes.
 */
export function ContextMenu(props: ContextMenuProps) {
  // A command with no wired handler is not applicable (§4: Pin/Unpin and
  // Highlight entries stay disabled until those epics land).
  const dim = !props.canUnpin || !props.onUnpin;
  const rmDim = !props.canRemoveHighlight || !props.onRemoveHighlight;
  const pinDim = !props.canPin || !props.onPin;
  const hlDim = !props.onHighlight;
  return (
    <div
      className="lvc-cm"
      data-menu-root=""
      role="menu"
      style={{ position: "absolute", left: props.x, top: props.y, zIndex: 30 }}
    >
      <style>{CM_STYLE}</style>
      <div data-menu-item="copy" role="menuitem" onClick={props.onCopy}>
        Copy
        <span className="lvc-cm-key">⌃C</span>
      </div>
      <div data-menu-item="copy-message" role="menuitem" onClick={props.onCopyMessage}>
        Copy Message
      </div>
      <div className="lvc-cm-sep" />
      <div
        data-menu-item="unpin"
        role="menuitem"
        aria-disabled={dim || undefined}
        className={dim ? "lvc-cm-dim" : undefined}
        onClick={dim ? undefined : props.onUnpin}
      >
        Unpin
        <span className="lvc-cm-key" />
      </div>
      <div data-menu-item="pin" role="menuitem" aria-disabled={pinDim || undefined}
        className={pinDim ? "lvc-cm-dim" : undefined}
        onClick={pinDim ? undefined : props.onPin}
      >
        Pin
      </div>
      <div className="lvc-cm-sep" />
      <div data-menu-item="highlight" role="menuitem" aria-disabled={hlDim || undefined}
        className={hlDim ? "lvc-cm-dim" : undefined}
        onClick={hlDim ? undefined : props.onHighlight}
      >
        Highlight
      </div>
      <div
        data-menu-item="remove-highlight"
        role="menuitem"
        aria-disabled={rmDim || undefined}
        className={rmDim ? "lvc-cm-dim" : undefined}
        onClick={rmDim ? undefined : props.onRemoveHighlight}
      >
        Remove highlight
      </div>
    </div>
  );
}

/* UI_DESIGN §s3 `.cm`, one token for the class prefix. */
const CM_STYLE = `
.lvc-cm {
  --lvc-border: #dfe4ea;
  --lvc-border-strong: #c4cdd7;
  --lvc-accent-tint: rgba(0, 120, 215, .1);
  display: inline-block; min-width: 190px; padding: 5px;
  border: 1px solid var(--lvc-border-strong); border-radius: 9px; background: var(--surface);
  box-shadow: 0 8px 26px rgba(0, 0, 0, .18);
  font: 400 12.5px/1 system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  .lvc-cm {
    --lvc-border: #243040;
    --lvc-border-strong: #33445a;
    --lvc-accent-tint: rgba(77, 163, 232, .14);
  }
}
.lvc-cm > div {
  padding: 6px 10px 5px; border-radius: 5px; display: flex; justify-content: space-between; gap: 18px; cursor: default;
}
.lvc-cm div:hover { background: var(--lvc-accent-tint); }
.lvc-cm div.lvc-cm-dim { color: var(--dim); }
.lvc-cm .lvc-cm-sep { height: 1px; padding: 0; margin: 4px 2px; background: var(--lvc-border); border-radius: 0; }
.lvc-cm .lvc-cm-key { color: var(--dim); font: 500 11px/1.9 "IBM Plex Mono", monospace; }
`;
