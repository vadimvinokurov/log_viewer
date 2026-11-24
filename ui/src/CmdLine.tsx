//! CmdLine (bead 7rf.1, §13/§11.1): the flat command input in the bottom
//! bar. Markup, classes and tokens are copied verbatim from
//! docs/UI_DESIGN.html (bbar mock + "Command line" component study). The
//! component wires the store slice to markup: Enter submits, Esc clears and
//! returns the focus to the table (blur), ↑/↓ walk the in-session history;
//! the GLOBAL ':' keydown lives in App (document-level, like Ctrl+F/Ctrl+B).

import { useEffect, useRef, type KeyboardEvent, type ReactElement } from "react";
import type { CmdlineState } from "./cmdline";

export interface CmdLineProps {
  command: CmdlineState;
  /** A keystroke changed the field text. */
  onText(text: string): void;
  /** Enter: submit the current field text. */
  onSubmit(): void;
  /** Esc: clear the field (App/console keep the state; the component blurs
   *  to return the focus to the table — the table has no focusable node). */
  onClear(): void;
  /** ↑/↓ in the field: dir −1 = older, +1 = newer (§13.2). */
  onRecall(dir: -1 | 1): void;
}

export function CmdLine(props: CmdLineProps): ReactElement {
  const { command } = props;
  const inputRef = useRef<HTMLInputElement | null>(null);
  const focusTick = command.focusTick;

  // §13 activation: the ':' keydown over the table pre-fills the field with
  // ':' and must place the caret right after it. focusTick is the bump.
  useEffect(() => {
    if (focusTick === 0) {
      return;
    }
    const input = inputRef.current;
    if (input) {
      input.focus();
      input.setSelectionRange(1, 1);
    }
  }, [focusTick]);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "Enter") {
      e.preventDefault();
      props.onSubmit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      props.onClear();
      inputRef.current?.blur();
    } else if (e.key === "ArrowUp") {
      // §13.2: text fields keep caret navigation only for left/right;
      // the arrows belong to the history recall while the field is focused.
      e.preventDefault();
      props.onRecall(-1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      props.onRecall(1);
    }
  };

  return (
    <span className="cmd" data-testid="cmdline">
      <span className="dot">:</span>
      <input
        ref={inputRef}
        value={command.value}
        placeholder=":type command..."
        aria-label="Command line"
        spellCheck={false}
        onChange={(e) => props.onText(e.target.value)}
        onKeyDown={onKeyDown}
      />
    </span>
  );
}
