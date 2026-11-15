---
name: modern-web-guidance
description: Guides for HTML, CSS and browser JavaScript from GoogleChrome/modern-web-guidance, vendored at a pinned commit and read from this folder. Use before writing or reviewing any HTML, CSS or client-side JavaScript in this repository, including HTML that Python code writes. Not for Python, tests, CI or docs.
---

# Modern Web Guidance, as Ploni uses it

209 guides on how to write web pages with what browsers offer today: HTML, CSS, forms, accessibility, performance, security. They sit in `guides/` beside this file, each one identical to the source at one commit (`docs/THIRD_PARTY.md` has the commit and the hash to check).

This file is written for Ploni. It is not the source's own `SKILL.md`. The source's file tells an agent to run `npx -y modern-web-guidance@latest`. **Never run that program here**, and never install it. It is not pinned: npm is asked for the newest version on every run. The pinned commit does not cover it, because it is built from another repository. And it reports the search words to Google unless a switch is set. Every guide it would return is already in `guides/`.

## 1. Before writing web code

Web code means HTML, CSS and JavaScript that runs in a browser. HTML that a Python function writes counts.

1. **Find the guides.** The file name is the guide's id, and no two guides share a name.
   - The guides are in 17 folders: `accessibility`, `built-in-ai`, `css`, `forms`, `html`, `js`, `performance`, `privacy`, `pwa`, `security`, `ui-atoms`, `ui-behaviors`, `ui-components`, `user-experience`, `visual-design`, `wasm`, `webmcp`.
   - Glob one folder at a time: `.claude/skills/modern-web-guidance/guides/<folder>/*.md`. A Glob over all folders at once is cut off at 100 files of the 209.
   - Grep `guides/` for the element, property or API in hand: `<dialog`, `popover`, `:user-invalid`, `color-scheme`.
   - One search per thing. "A table that sorts and has a dark mode" is two searches.
2. **Read each guide that fits, in full.** Then read the general guides, chosen by what the code holds:
   - any HTML: `html/html.md` and `accessibility/accessibility.md`
   - any CSS: `css/css.md`; a layout: also `css/css-layout.md`; a colour: also `visual-design/color.md`
   - a form: `forms/forms.md`
   - a page that a server sends, which every Phase 12 screen is: `security/security.md`, `privacy/privacy.md`, `performance/performance.md`. A page opened from disk with no script needs none of the three.
3. **A guide may point to another** with `npx -y modern-web-guidance@latest retrieve "<id>"`. Read `guides/<folder>/<id>.md`. Do not run the command.
4. **No guide fits:** write the code without one, and say so in the PR (section 3).
5. **Before finishing**, check the code against each guide read: the pattern, and the fallback the guide asks for.

## 2. Where Ploni's rules come first

The guides are written for websites on the open internet. Ploni is an offline desktop product that handles sensitive documents. Where a guide and `CLAUDE.md` disagree, `CLAUDE.md` wins.

- **Nothing is loaded from another host.** No CDN, no remote font, image, video, script or stylesheet. Guides name `unpkg.com`, `esm.sh`, `cdn.jsdelivr.net`, `esm.run`, `img.youtube.com` and `www.youtube-nocookie.com`; none of them is used.
- **No package is added because a guide says `npm install`.** Where a guide's fallback is a polyfill, write the small fallback by hand, or leave the enhancement out, and say which in the PR. A new dependency is a PR of its own, pinned, with a row in `docs/THIRD_PARTY.md`.
- **Guides whose job is to send data out do not apply:** analytics, beacons, `fetchLater`, sign-in through another site. The product makes no outbound connection.
- **Which features may be used.** Read the status line of the feature in the guide ("Baseline status for ..." or "Browser support for ...") and the "Supported by" line under it. Chrome and Edge are one engine; Firefox is a second; Safari is a third.
  - *Widely available:* use it, with no fallback.
  - *Newly available, or Limited availability with two engines or more:* use it with the fallback the guide gives, or leave it out.
  - *One engine only (for example Chrome and Edge and nothing else), or an Origin Trial:* not used.
  - The last line is stricter than the source, which lets an agent use such a feature with a fallback. It is strict because the browser that shows the Phase 12 screens is not decided. When Achia decides it, the policy goes into `CLAUDE.md` and this list follows it.
- **Ponytail still holds.** A guide is used for what the task needs. It is not a reason to add a feature nobody asked for.
- **Hebrew and right-to-left.** No guide covers text that mixes right-to-left and left-to-right. The Hebrew axes of the `test-matrix` skill do.
- **No document text leaves the page.** `CLAUDE.md` bans document text in logs and temp files. In a page that also means: not in a URL, and not in browser storage. `privacy/privacy.md` does not cover this.
- **The browser's own features can send page text out,** for example an offer to translate a Hebrew page. Before the first Phase 12 screen is written, list which such features the chosen browser has and switch each off in the page (`translate="no"` on `<html>` is the usual switch for translation). This has not been tested here yet.

## 3. In the PR body

A PR that touches web code carries a section `## Modern Web Guidance`:

- One line per guide that shaped the code: the guide's file and line, what it changed, and what the guide offered that was left out and why.
- If guides were read and none applied, one sentence: which were read, and why none applied.
- Name only guides read in this session. Never cite one from memory.

The Ponytail reviewer of that PR invokes this skill too. It finds the guides itself and does not work from the writer's list. What it finds goes into its review.

## 4. Reviewing web code that already exists

Same steps, on the existing file. The review changes no code. Its report has:

- Findings, numbered, in three groups: must fix, should fix, nice to have. Each finding says what the thing is, the problem with a concrete case (who opens the page and what goes wrong for them), the smallest fix as exact HTML or CSS, and what happens if it is skipped. Each names the guide's file and line.
- No concrete case for this page and its real use: no finding.
- One closing line, "Read and not applied": the guide advice that does not matter here, with the reason.

The report goes to Achia.

## Source and licence

- Source: GitHub `GoogleChrome/modern-web-guidance`, folder `skills/modern-web-guidance/guides/`, at tag `v1.0.0`, unchanged.
- The guides are licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), and the source's software Apache 2.0 (`LICENSE` beside this file), as its `README.md` says under "License". Per that README, parts of the guides are derived from MDN Web Docs by Mozilla Contributors and from W3C, WHATWG and IETF specifications.
- Code copied or adapted from a guide into the product keeps that attribution: add a row to `docs/THIRD_PARTY.md` in the same PR.
