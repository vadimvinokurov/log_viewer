# Report data — mistake catalog from session mining (2026-11-25)

resolution: superseded by docs/report-02-agent-mistakes.html

Input corpus: 15 session transcripts (2026-11-22 -> 2026-11-25, ~70 MB), 249 owner text
messages extracted, 16 persistent `bd` memories, CLAUDE.md rules 1-9, `docs/PIPELINE.md`
sections 5-7, `docs/notes/agent-brief.md`, `docs/token-usage-report.html`.

Legend: **[EXISTS]** = prevention already encoded in CLAUDE.md/PIPELINE/agent-brief;
**[NEW]** = not yet encoded, recommendation is new.

---

## P1. Token-budget blindness until the 429 kills the run

**What happened.** 16 occurrences of `Request rejected (429) ... reached your session/weekly
usage limit` across three sessions (9785223c: 10, 3de36a6d: 5, 405193b3: 1). Two sub-agents
(qt7.2, rhl.2) died mid-task on 2026-11-23 21:36/22:04 with `< 20k` partial spend each.
On 2026-11-25 08:06 a weekly limit froze the whole session; the owner poked the dead session
six times with "prodolzhi" (08:11-08:13) before work resumed. Nothing distinguishes
"working" from "dead by 429", so the owner reads silence as a hang ("chet vstal agent
pokhodu" 11-24 05:55, "chet vislo vse" 11-24 20:12).

**Cost.** Two partial agent runs lost; repeated owner pokes during dead air; checkpoints
made restarts cheap, but the kill itself was invisible.

**Cause.** Owner-side: token report was generated only after the first budget crash.
Agent-side: no "checkpoint BEFORE the expensive step" discipline — checkpoints were taken
at milestones, not before long gates/benchmarks, so 429s landed in the least-recoverable
places.

**Prevention.**
- [EXISTS] Rule 7 (short turns, milestone commits, checkpoint agents).
- [NEW] Kit rule/hook: before every long gate (`cargo test --workspace`, full e2e,
  benchmark run) the agent posts a `bd update --notes` checkpoint + announces
  "entering a ~X-minute gate".
- [NEW] Rule: when a turn ends without visible output (limit kill), the next session
  must tell the owner how to resume; the owner should never guess hang/limit/finished.

## P2. Late verification — CI catching what local gates missed

**What happened.** v0.2.0, 2026-11-25 07:16: agent pushed main + tag; CI's `tsc -b` caught
two type errors vitest cannot see (esbuild strips types) — settings-seam optional-method
call in a closure + missing type. The gates WERE run, but with a stale incremental
`tsbuildinfo` cache and no fresh `tsc -b`, so the decisive check proved nothing (PIPELINE
6a records this verbatim). Previously v0.1.0 (2026-11-24 22:08-22:09) was already re-tagged
twice: a `filters-live-mixed` golden was rebased mid-push due to anti-aliasing
nondeterminism, and the ubuntu CI gate panicked on missing GTK/webkit dev libs.

**Cost.** Three re-tagged releases across two tags; ~19 min per CI cycle; rules
retrofitted only after the failures.

**Cause.** Agent-side: treated green vitest as type coverage; ran an approximate subset of
gates. Owner-side: the norm did not exist until the owner set it after the v0.2.0 failure
("pered pushem reliza nado lokalno te same prygony", 11-25 07:28).

**Prevention.**
- [EXISTS] Rule 9 + PIPELINE 6a (exact gate list, cache wipe, gates on the tagged commit).
- [NEW] `scripts/release_gates.sh` running the exact CI sequence (wiping tsbuildinfo
  BEFORE `tsc -b`) as the only sanctioned way to cut a tag; hook on `git push` of a `v*`
  tag checking the script's last green run is newer than the tag commit. Rule text alone
  already failed once.

## P3. Trusting completion claims without a visible artifact

**What happened.** Agents reported "all gates green" while milestone live checks failed in
the real window: e1/e3/e6 viewport-anchor FAILs repeated across the baseline run, a second
run, and the walk-fix build (11-24 20:36-21:10 monitor events); offline goldens never
covered real-window anchor settling, later traced to the per-probe counts walk (beads vdr
+ ddp, in persistent memories). Also the spec's "6.4M lines" estimate was accepted in docs
until a real benchmark run found 1,294,246 lines.

**Cost.** Two full live-check rounds wasted; a 100%-idle-CPU perf bug sat at HEAD until the
live check caught it.

**Cause.** Agent-side: green tests treated as completion. Owner-side: initially accepted
verbal status (live-check-at-milestone norm appeared after owner feedback 11-23 21:05).

**Prevention.**
- [EXISTS] Rule 4 (snapshots AND rendered output before task close), rule 5, bd acceptance
  as commands.
- [NEW] Spawn-prompt template field: every "done" claim carries gate OUTPUTS (command,
  counts, exit codes); a bare "all green" is treated as not-reporting.

## P4. Debugging by narration instead of measurement

**What happened.** The e2e suite hung 10+ minutes; the agent's first answer to "pochemu oni
takoe dolgie?" was a justification ("eto ne visit, a medlenno rabotaet: ~37 states,
full reload each"). Only "Che za bred, eto tochno ne doljna zanimat po 10 minut"
(11-24 22:02) made it measure golden timestamps — the old suite took **14 seconds**, and
state 33 (`installUpdate()`) blocked on a never-resolving `downloadAndInstall` promise
inside `page.evaluate`. One measurement, instant root cause. Same shape: the e1/e3/e6
anchor plateau was narrated as UI scroll behavior before the backend per-probe walk
was proven the cause.

**Cost.** ~10 minutes of a stuck run before any measurement; one owner escalation;
misdirected anchor investigation.

**Cause.** Agent-side entirely: theory-before-evidence, presented confidently.

**Prevention.**
- [EXISTS] `superpowers:systematic-debugging` in the kit.
- [NEW] Hard clause: when a run exceeds its expected duration 2x, the FIRST action is a
  timed observation (timestamps/progress markers), never an explanation; no cost claim
  ("it's just slow") without the number. Rule 7's "numbers instead of screenshots"
  extended to durations.

## P5. Debugging by shell-escaping into files

**What happened.** The `driver.rs` escaping fight (token report): 5-6 consecutive
python-heredoc attempts with mangled quoting, each costing a full read+edit cycle; the
Write tool solved it on the first try. Even after rule 7 (11-24), the habit resurfaced:
a broken macOS `sed: 1: ",+10p ": invalid command code ,` plus a wrong-cwd ugrep miss
(c07fb80d, 11-25 08:45).

**Cost.** "Tens of thousands of tokens" (token report estimate); rule text did not
mechanically stop the pattern.

**Cause.** Agent-side.

**Prevention.**
- [EXISTS] Rule 7 bullet + agent-brief "Known traps".
- [NEW] PostToolUse hook counting Bash-based file mutations (`sed -i`, heredoc
  redirections, `perl -pi`, `tee file`) and blocking the THIRD with "use Edit/Write";
  prose has failed twice, so this needs a hook.

## P6. Agent prompt bloat — decoding the spec per agent

**What happened.** Early agent prompts restated spec semantics inline and pointed agents at
4-6 files; the same section decode was "paid 9+ times across agents" (token report);
prompts were ~1k tokens vs the 30-line brief.

**Cost.** Tens of thousands of duplicate tokens; duplicated RISK — each agent re-decided
conventions, which produced the case-insensitive import bug class.

**Cause.** Agent-side prompt authoring; the shared-brief pattern was owner-suggested only
in the 11-24 04:55 feedback.

**Prevention.**
- [EXISTS] Rule 7 + `docs/notes/agent-brief.md` (live, good).
- [NEW] Kit skill: "shared per-project agent brief" with a template (where truth lives /
  hard constraints / conventions / spawn contract / traps); a spawn prompt longer than
  ~15 lines is a smell — write missing context into the brief/bead.

## P7. Runaway agents — no cap in practice, despite the rule

**What happened.** AFTER the token-saving rules were written (11-24 morning), UI agents
grew 4-8x: "Side panel and categories tab UI" 628k tokens, "Highlights tab and row
rendering" 578k, "Command line UI and registry" 385k, "Search panel UI and navigation"
361k, "Pins UI" 327k — versus 44-85k agents on 11-23. The cmdline agent posted six
"waiting on its own background work" notifications while sitting on ~378k tokens for 21+
minutes, monitoring live runs. Roughly **2.65M sub-agent tokens** were spent on
11-24 05:00-20:00 alone — 5x the 528k total that triggered the token report.

**Cost.** The biggest billable bucket in the project (numbers above).

**Cause.** Agent-side: spawn prompts did not limit scope (live-run monitoring parked
inside a UI agent; a UI build absorbed live-check debugging rounds 1-4). Owner-side: none
— this is exactly what rule 7 targets, but the rule is prose adopted asynchronously.

**Prevention.**
- [EXISTS] Rule 7 ("cap and checkpoint agents", "two small agents over one fat one").
- [NEW] Mechanical: (a) explicit token cap IN the prompt + instruction "at the cap,
  checkpoint + stop + report status"; (b) monitoring background jobs is the coordinator's
  job (or a Monitor), never a long-lived agent — an agent polling a benchmark for 20
  minutes pays its whole context every round for zero output.

## P8. Dead air — silent stops, owner poking, empty replies

**What happened.** Six "prodolzhi" messages after the 429 kill (11-25 08:11-08:13);
"chet vstal agent pokhodu" and "chet vislo vse"; "ty prodolzhay rabotu, ne
ostanavlivaysya poka ne zakonchish" (11-24 06:33, agent had stopped early); two literal
"No response requested." turns (08:12) answering the owner's poke with nothing.

**Cost.** Owner attention per poke; full replay paid for two empty turns.

**Cause.** Agent-side: stops without a status line (limit kills, background waits).

**Prevention.**
- [EXISTS] Nothing — CLAUDE.md covers verification, not status-on-stop.
- [NEW] Kit rule: every turn ends with a one-line status (done / waiting on X, background
  id / resumable at bead Y); a stop with no user-visible text is a bug class the
  coordinator re-opens immediately.

## P9. Requirement churn: taste changes and unvalidated features built then cut

**What happened.** (a) Design churn 11-25 morning: >20 screenshot-driven
micro-corrections in ~1.5 h (f3da036d 05:01-05:50), including two reverts within a minute
("dobav otstup pered C" -> "ne, verni kak bylo", 05:37) and "dizain vkladok verni kak
byl" (07:51). Mock approval raced the agent: app-side porting had started before sign-off
("Stoy, escho rano. Ya escho ne soglasoval maket", 07:42). (b) The per-category counters:
built per spec section 10, then cut by the owner ("ubierem schetchik logov... ne nuzhno
schytat i tratit perf", 08:40) — and the same counts walk was ALSO the idle-CPU spin
(bead vdr) and the live-check plateau (bead ddp): one unvalidated feature cost a build, a
perf bug, two debugging beads, and an end-to-end rollback (commit 0d880c8). (c) The first
spec carried Qt-specific wording before any stack decision ("a prichem tut QT poisk?
uberi QT spetsifiku... stek my escho ne opredelili", 11-23 17:36, resurfacing 20:47).
(d) The v2-features section survived until "to chto napisali to i vhodit... ni kakoy
versii vtoroy ne budet" (11-23 17:52).

**Cost.** Dozens of full-replay screenshot turns; one feature built and removed
end-to-end; two perf debugging beads.

**Cause.** Owner-side: iterating design via verbal descriptions, approving in hindsight,
spec written in one pass. Agent-side: no approval gate between mock and app port; never
challenged a per-probe-cost feature with a cost estimate; stack words in an
uncommitted-stack spec.

**Prevention.**
- [EXISTS] `superpowers:brainstorming` used for the release pipeline; spec-as-truth rules.
- [NEW] UI skill: batch taste changes on the mock ONLY, require explicit mock approval
  before any app-side port, never re-edit a reverted change without a fresh ask. Spec
  skill: any criterion whose cost scales per-row/per-probe gets flagged to the owner with
  a perf estimate before implementing; no implementation stack may appear in a spec
  before STACK.md decides it.

## P10. Environment/cwd traps — silent wrong-context runs

**What happened.** (a) JS gates run from the repo root silently test the wrong environment
(rule 7 bullet: "forced a paid rerun"). (b) Tauri 2 runs beforeDevCommand with cwd =
frontend dir, so `--prefix ui` broke the scaffold (task n4y.1, persistent memory).
(c) Live failures: ugrep/sed missing `ui/src/headless.ts` from a drifted cwd (0203913a
21:34) and `docs/PIPELINE.md` not found from `ui/` (c07fb80d 08:45).

**Cost.** Reruns of gate commands; several wasted tool calls per incident.

**Cause.** Agent-side (cwd drift in long sessions).

**Prevention.**
- [EXISTS] Rule 7 bullet + agent-brief trap + bd memory.
- [NEW] Hook: on Bash failing with "No such file or directory" for a project-internal
  path, echo `pwd` and the resolution path — makes the class self-diagnosing.

## P11. Silent-hazard class: toolchain differs from the agent's belief

**What happened.** Two incidents of one shape: (a) macOS case-insensitive FS resolving
`./FiltersTab` to `filtersTab.ts` -> undefined component (bd memory + agent-brief trap;
plus an import-shape slip in 405193b3 08:02); (b) vitest proving nothing about TS types
because esbuild strips them (v0.2.0 CI failure). Both were caught only after a shipped
failure; both became memories AFTER the cost was paid. No canary test exists for either.

**Cause.** Agent-side: no upfront sensitivity to platform/build gaps.

**Prevention.**
- [EXISTS] Both traps documented.
- [NEW] Kit rule of the general shape: for every load-bearing "X works" assumption
  (module resolution, type stripping, cache freshness), add a 1-line canary gate on day
  one — before code relies on it.

## P12. Skill/plugin non-triggering — the owner had to ask twice

**What happened.** 11-23: owner asked twice in one session whether the mandated skills
were used: "A ty polzovalsya /vvv-claude-kit:building-testable-apps?" (20:28), "pochemu ty
ne polzuyeshsya blagami..." (20:57), "Pochemu ty ne delaesh tak kak tam napisano?"
(21:24). The owner then hand-distilled skill rules into CLAUDE.md (21:03).

**Cost.** One evening where PNG-golden visual acceptance was not applied until the owner
intervened; design debt had to be redone.

**Cause.** Agent-side: skill descriptions did not fire for UI work; rule 3 is again prose.

**Prevention.**
- [EXISTS] Rule 3.
- [NEW] Mechanical trigger: replica the `bd prime` SessionStart hook pattern for the
  vvv-claude-kit skills — inject a 3-line reminder whenever the task touches `ui/` or a
  new feature bead. Owner-asked-twice is the signal that description text will not
  trigger.

## P13. Delegation/harness-specific failures

**What happened.** (a) Review agents spawned with a nonexistent model override
`claude-fable-5-1` -> 404 `model_not_found`, 9 occurrences (b3c8e200: 3, c07fb80d: 6);
a whole-branch review attempt was wasted before a re-spawn (07:04) succeeded. (b) The
first CI gate failed on a runner difference (ubuntu lacks GTK/webkit dev libs; v0.1.0
22:09) — CI environment assumptions never pre-flighted. (c) Sub-agent reports drifted by
language (Chinese interim reports from the "Optimize visibility recompute" agent) — rule 6
never reached spawn prompts.

**Cost.** One lost review run; one extra re-tag; noise.

**Cause.** Agent-side; (b) partly environmental.

**Prevention.**
- [NEW] Delegation rule: pin models to verified-available names only; one-line
  owner-language clause in every spawn prompt ("final owner-facing report in Russian");
  first-run any new CI workflow on a throwaway branch/tag before a release tag rides on it.

## Owner-side behaviors worth keeping (counter-evidence)

Not every correction was a mistake: the owner self-revised agent guidance promptly ("Ne
sleduy pryam tem pravilam chto ya opisal. Reshi sam", 11-24 04:59), set language rules,
the beads workflow, and the release-gates rule with clear motivation; good habits (bd
memories, agent-brief, PIPELINE rulings) show the feedback loop works. Recurring
owner-side gaps: (1) approving in hindsight instead of confirming before the port (P9);
(2) no live visibility of burn rate, so corrections arrive only after the bill (P1, P7).

## Priority of new mechanisms (what the kit should build)

1. **Spawn contract template + per-agent cap + status-on-stop** (P7, P8, P3, P13) —
   largest bucket (~2.7M sub-agent tokens measured).
2. **Bash-based-edit blocker hook** (P5) — cheapest mechanical win, recurring cost.
3. **Skill-trigger injection hook** (P12) — the original P0; owner asked twice.
4. **Release-gates script + tag-push precheck** (P2) — turns rule 9 into a command.
5. **Checkpoint-before-long-gate** (P1) — makes 429s recoverable by design.
6. **Measurement-before-explanation + duration watch** (P4).
7. **Mock-approval gate + spec cost-flags** (P9).
