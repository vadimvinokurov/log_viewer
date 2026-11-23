/**
 * Empty state, §2 (UI_DESIGN "Empty state" study): a dashed drop-target box
 * with the primary line and the secondary hint. The table appears once the
 * file is parsed; Reload keeps filters, highlights and levels (§2.1).
 */
export function EmptyState() {
  return (
    <div className="empty-drop">
      <div className="empty-big">Drop a log file here or click Open</div>
      <div className="empty-small">
        The table appears once the file is parsed. Reload keeps filters, highlights and levels.
      </div>
    </div>
  );
}
