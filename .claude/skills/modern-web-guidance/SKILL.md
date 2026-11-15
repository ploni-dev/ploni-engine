---
name: modern-web-guidance
description: Guides for HTML, CSS and browser JavaScript from GoogleChrome/modern-web-guidance, vendored at a pinned commit and read from this folder. Use before writing or reviewing any HTML, CSS or client-side JavaScript in this repository, including HTML that Python code writes. Not for Python, tests, CI or docs.
---

# Modern Web Guidance, as Ploni uses it

209 guides on how to write web pages with what browsers offer today: HTML, CSS, forms, accessibility, performance, security. They sit in `guides/` beside this file, each one identical to the source at one commit (`docs/THIRD_PARTY.md` has the commit and the hash to check).

This file is written for Ploni. It is not the source's own `SKILL.md`. The source's file tells an agent to run `npx -y modern-web-guidance@latest`. **Never run that program here**, and never install it. It is not pinned, it is downloaded on every run, and it reports the search words to Google unless a switch is set. Everything it would return is already in `guides/`.

## 1. Before writing web code

Web code means HTML, CSS and JavaScript that runs in a browser. HTML that a Python function writes counts.

1. **Find the guides.** The file name is the guide's id.
   - Glob `.claude/skills/modern-web-guidance/guides/**/*.md` and pick by name.
   - Grep the folder for the element, property or API in hand: `<dialog`, `popover`, `:user-invalid`, `color-scheme`.
   - One search per thing. "A table that sorts and has a dark mode" is two searches.
2. **Read each guide that fits, in full.** Also read the general guide of its subject: `html/html.md`, `css/css.md`, `css/css-layout.md`, `forms/forms.md`, `accessibility/accessibility.md`, `performance/performance.md`, `security/security.md`, `privacy/privacy.md`, `visual-design/color.md`.
3. **A guide may point to another** with `npx -y modern-web-guidance@latest retrieve "<id>"`. Read `guides/**/<id>.md`. Do not run the command.
4. **No guide fits:** write the code without one, and say so in the PR (section 3).
5. **Before finishing**, check the code against each guide read: the pattern, and the fallback the guide asks for.

## 2. Where Ploni's rules come first

The guides are written for websites on the open internet. Ploni is an offline desktop product that handles sensitive documents. Where a guide and `CLAUDE.md` disagree, `CLAUDE.md` wins.

- **Nothing is loaded from another host.** No CDN, no remote font, image, script or stylesheet. Guides name `unpkg.com`, `esm.sh`, `cdn.jsdelivr.net` and `esm.run`; none of them is used.
- **No package is added because a guide says `npm install`.** Where a guide's fallback is a polyfill, write the small fallback by hand, or leave the enhancement out, and say which in the PR. A new dependency is a PR of its own, pinned, with a row in `docs/THIRD_PARTY.md`.
- **Guides whose job is to send data out do not apply:** analytics, beacons, `fetchLater`, sign-in through another site. The product makes no outbound connection.
- **No experimental feature.** A feature in an Origin Trial, or one that a single browser engine ships, is not used. The source's program refuses to hand out those guides; here nothing refuses, so this line does.
- **Browser support.** A feature a guide marks "Baseline Widely available" is used with no fallback. Anything newer ("Limited availability", "Newly available") gets the fallback the guide gives, or is left out. Which browser shows the Phase 12 screens is not decided yet; when it is, the policy goes into `CLAUDE.md` and this line follows it.
- **Ponytail still holds.** A guide is used for what the task needs. It is not a reason to add a feature nobody asked for.
- **Hebrew and right-to-left.** The guides do not replace the Hebrew axes of the `test-matrix` skill.
- **No document text leaves the page** into a log, a URL or browser storage. `privacy/privacy.md` does not cover that; `CLAUDE.md` does.

## 3. In the PR body

A PR that touches web code carries a section `## Modern Web Guidance`:

- One line per guide that shaped the code: its id, what it changed, and what the guide offered that was left out and why.
- If guides were read and none applied, one sentence: which were read, and why none applied.
- Name only guides read in this session. Never cite one from memory.

## 4. Reviewing web code that already exists

Same steps, on the existing file. The result is a list of findings in the form the `ponytail-review` skill uses: what it is, the problem with a concrete case, the smallest fix, what happens if it is skipped. Each finding names the guide and the line of the guide it rests on. The review changes no code.

## Source and licence

- Source: GitHub `GoogleChrome/modern-web-guidance`, folder `skills/modern-web-guidance/guides/`, unchanged.
- The guides are licensed CC BY 4.0, and the source's software Apache 2.0 (`LICENSE` beside this file), as its `README.md` says under "License". Per that README, parts of the guides are derived from MDN Web Docs by Mozilla Contributors and from W3C, WHATWG and IETF specifications.
- Code copied or adapted from a guide into the product keeps that attribution: add a row to `docs/THIRD_PARTY.md` in the same PR.
