# Week 16 — Buffer + Final Demo

**Phase 5 · Writeup** — ~10 hours (flexible)

## Exit criteria (week done when…)

- [ ] Every exit criterion from weeks 1–15 that is still open is either
      done or explicitly deferred with a reason (in `docs/KNOWN_ISSUES.md`
      or the tracker).
- [ ] The final demo runs start-to-finish **twice** in one sitting without
      a failure (the "demo rehearsal" rule).
- [ ] The repo is in a presentable state: README accurate, results
      regenerated, tests green, `TRACKER.md` complete.
- [ ] (Stretch) One "next step" from the known-issues list is started, or
      the paper pitch is submitted somewhere (workshop CFP, class report).

## Why this week

The plan had a 16-week arc with slack built into every phase; this week is
the explicit overflow tank. Its real job: **make sure the project ends in
a demo, not in a debug session.** If you're on pace, this week is for
polish and one stretch goal; if you're behind, this is where the fallback
list gets executed.

## How to run the buffer week

1. **Audit the tracker (1 h).** Walk every week's exit criteria. Sort the
   open items into: (a) must-fix for the demo, (b) should-fix for the
   writeup, (c) nice-to-have. Do (a) first, (b) second, (c) only if
   something falls over.
2. **Demo rehearsal (2 h, twice).** The demo script, from cold power-on:
   - Power on → telemetry appears → alignment check passes.
   - Run one week-11 cell (smooth tracking) → number on screen.
   - Run the disturbance step → number on screen.
   - Impedance → grab → collision → give-way (the video moment).
   - Power off cleanly.
   Rehearse it twice. The second run must be flawless. **Anything that
   fails in rehearsal fails in the interview — fix it now, not there.**
3. **Repo polish (2 h).** `pytest test/ -q` green; `python -m
   sim.run_experiments` regenerates results; README links all resolve;
   delete scratch files; `git log` tells the project story (commit
   messages readable — consider committing week-by-week work if you
   haven't been). Make sure `results/plots/*.png` are the *final*
   figures.
4. **Stretch goal (3–4 h).** From week 14's list, pick one that fits the
   remaining hours: RLS online adaptation is the strongest resume item
   (it's the obvious next paper and can be demoed live: detune the
   friction model, watch it re-learn); a second spring is the cheapest
   (proves the calibration pipeline transfers); a 2-DOF arm is the
   flashiest but too big for one week — don't start it.
5. **Final review (1 h).** Read `docs/RESULTS.md` and `docs/PAPER_PITCH.md`
   once more, out loud. Update README's headline table if the hardware
   numbers changed anything. Mark the tracker 100% or "deferred with
   reason".

## What "done" looks like

- **The repo** is self-explanatory (someone with the BOM can rebuild the
  project from README + plan).
- **The demo** is 3 minutes and survives a cold start twice.
- **The numbers** are mean ± std, sim + hardware, honest limitations.
- **The story** is 30 seconds: full-stack SEA, MPC beats PID [N]×,
  learned friction enables [150 ms] collision safety.

## If you're behind (fallback execution)

Work the phase fallbacks from `docs/plan/README.md` in this order:
1. Drop the week-14 sensitivity study to a single 0.8×/1.2× run.
2. Collapse the paper pitch into the RESULTS.md limitations paragraph.
3. Cut the stretch goal entirely.
4. **Never cut**: the week-13 collision demo, the week-11 MPC-vs-PID
   table (even at N=3), and the video. Those three are the project.

## The last word

You built something that most robotics courses only gesture at: a
measured, calibrated, identified, model-predictive-controlled,
learned-augmented, human-safe actuator — every layer yours, every number
reproducible. That's the resume story. Go demo it.
