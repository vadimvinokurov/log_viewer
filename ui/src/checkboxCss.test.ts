//! CSS-contract unit test for the category checkbox (2026-11-25 paint
//! bug): the checkbox must be custom-drawn (appearance:none) because native
//! checkboxes paint grey-until-hover in WKWebView's scrolled content, and a
//! checked box must paint the accent fill by CSS, never native painting.
//!
//! Gate: parses src/index.css (the single CSS source), asserts the rules.

/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

/** The single CSS source; vitest gates run from ui/ (project rule), so the
 *  cwd-relative path is pinned to the test file location instead: */
const css = readFileSync(join(process.cwd(), "src", "index.css"), "utf8");

/** Body of one CSS rule — the text between the opening brace following the
 *  selector and its closing brace; throws when the selector is missing. */
function ruleFor(selector: string): string {
  const at = css.indexOf(selector);
  if (at === -1) {
    throw new Error(`missing CSS rule: ${selector}`);
  }
  const open = css.indexOf("{", at);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

describe("category checkbox CSS contract (paint bug 2026-11-25)", () => {
  test("custom-drawn, never native painting (grey-until-hover bug)", () => {
    const rule = ruleFor(".tree .row input.cb");
    expect(rule).toContain("appearance: none");
  });

  test("checked/indeterminate paint the accent fill", () => {
    const checked = ruleFor(".tree .row input.cb:checked");
    expect(checked).toContain("background: var(--accent)");
    expect(checked).toContain("border-color: var(--accent)");
    const indet = ruleFor(".tree .row input.cb:indeterminate");
    expect(indet).toContain("background: var(--accent)");
  });
});
