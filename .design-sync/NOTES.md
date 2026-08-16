# design-sync notes — FundersAI UI

## Source shape
`frontend/components/ui/` is not a standalone package — no `dist/`, no `package.json` of its own, no Storybook. Converter runs in **package shape, synth-entry mode**:
- `--entry ./frontend/components/ui/__entry__.tsx` — a path that does **not** exist. This is intentional: passing a real entry file makes `resolveDistEntry` treat it as an authoritative pre-built dist entry (bypassing synthesis). Passing a non-existent path under `components/ui/` makes the PKG_DIR-walk (in `package-build.mjs`) find `frontend/package.json` (name `marketmind`) while `resolveDistEntry`'s `soft: true` path correctly falls through to synthesizing an entry from `cfg.srcDir` (`components/ui`). Don't "fix" this by pointing `--entry` at a real file.
- `cfg.pkg` = `"marketmind"` (frontend's real package.json name), `cfg.globalName` = `"FundersAIUI"` (marketmind would derive an awkward namespace).
- `cfg.srcDir` = `"components/ui"` (relative to PKG_DIR = `frontend/`).
- `cfg.tsconfig` = `"tsconfig.json"` (also relative to PKG_DIR = `frontend/`) — resolves the `@/*` path alias esbuild needs for synth-entry mode.

## Styling
No prebuilt CSS exists either (Tailwind v4, config lives inline in `app/globals.css` via `@theme`, no `tailwind.config.js`). Compiled a real stylesheet via the Tailwind v4 standalone CLI:
```
cd frontend && npm install --no-save @tailwindcss/cli   # not saved to package.json/lockfile
frontend/node_modules/.bin/tailwindcss -i app/globals.css -o .ds-compiled/tailwind.css
```
`cfg.cssEntry` = `.ds-compiled/tailwind.css` (relative to PKG_DIR = `frontend/`; must stay inside `frontend/` — `cssEntry` is bounded to PKG_DIR, not the workspace root). This compile step scans the whole `frontend/` tree for used classes — **must be re-run before every rebuild** if `globals.css` or any component's Tailwind classes changed, or the shipped CSS goes stale. `--color-terminal-emerald` and similar tokens are correctly absent from the compiled output — they're defined in `@theme` but genuinely unused anywhere in the app right now (verified via grep), not a compile bug.

## Two forks in `.design-sync/overrides/` (both declared in `cfg.libOverrides`)
1. **`common.mjs`** — adds `'excludeSrcFiles'` to `CONFIG_KEYS` (needed so `source-kit.mjs`'s fork can read the new config field without failing strict validation).
2. **`source-kit.mjs`** — two fixes:
   - **`cfg.excludeSrcFiles`** (new field, array of package-relative substrings) drops matching files from `srcFiles` before entry synthesis AND discovery. Used to exclude `components/ui/info-card.tsx` and `components/ui/animated-feature-carousel.tsx` — both import `next/image`, whose compiled module references `process.env.*` unconditionally at module-load time. In a standalone esbuild bundle (no `process` global, no webpack DefinePlugin), that's a `ReferenceError` that fires the instant the shared bundle loads — since the synthesized entry does `export *` from every file in one bundle, ONE bad top-level import crashed **all 70** components, not just the 2 files' own exports. Excluding those 2 files drops `InfoCard`/`InfoCardTitle`/`InfoCardDescription`/`InfoCardContent`/`InfoCardMedia`/`InfoCardFooter`/`InfoCardDismiss`/`InfoCardAction`/`FeatureCarousel` (9 exports) from the synced design system. **This is a real, permanent gap** — `next/image` is fundamentally coupled to the Next.js server/webpack runtime and can't run in Claude Design's plain-React preview environment. If FundersAI's engineers want `InfoCardMedia` synced, it would need a plain-`<img>` variant.
   - **Default-export re-export fix**: `export * from "<path>"` never re-exports a file's `default` export (ES module semantics). Two components — `FundSearchSelect` (`FundSearchSelect.tsx`) and `Magnetic` (`Magnetic.tsx`) — are `export default function Name()`. `deriveComponentsFromSrc` already recovers `default`-exported names correctly for the catalog, but the *entry* synthesis only did `export *`, so both were silently `[BUNDLE_EXPORT]`-missing from `window.FundersAIUI` even though they showed up in the component list. Fixed by detecting each file's default-export name (same ts-morph recovery logic) and adding `export { default as <Name> } from "<path>";` alongside the star re-export.
   - Both fixes only touch `resolvePackage` in `source-kit.mjs` — no change to `lib/bundle.mjs` or `lib/emit.mjs` (per skill instructions, those stay unforked).
   - `.design-sync/node_modules` is a **junction/symlink** to `../.ds-sync/node_modules` (created via `ln -sfn`) so the fork's bare `ts-morph` import resolves. Gitignored — recreate on a fresh clone if `.design-sync/overrides/` forks ever need bare imports again.

## Component count
61 components synced (from 27 source files under `components/ui/` minus the 2 excluded above — 25 files feed the bundle). Many shadcn files export several sub-components (Card family: 5, Sidebar family: ~20), each becomes its own synced "component" with `group: "general"` (no dir-based grouping since all 25 files sit flat in one directory — `componentSrcMap`/group refinement would need per-file `group` overrides if the flat "general" bucket turns out to be a real usability problem in the DS pane; not addressed yet).

## Preview scope (user's choice)
User chose **rich authored previews for all 61 components** (not just the ~9 core primitives) — decorative/marketing components (sparkles, border-beam, etc.) get real previews too, not floor cards. Budget accordingly on re-syncs.

## Known render warns (pre-authoring baseline)
At the first clean build (0 previews authored), 42/61 rendered clean, 19 flagged `[RENDER_BLANK]` — all children-requiring wrapper/leaf components with no content when mounted standalone (Card family, Sidebar sub-parts, MagicCard, Magnetic, NumberTicker, Panel, Sheet sub-parts). Expected to clear once real previews are authored per §4.2 (compose leaves inside their realistic parent).

## Component API gotchas found while authoring previews
- `MagicCard` and `Sparkles` (both `components/ui/`) accept `className` but silently drop a `style` prop passed by a consumer — no spread/merge onto the root element. Most other components here (`Panel`, `ShimmerButton`) forward `style` normally. Size these two via a wrapping `<div>`/`className` instead of inline `style={{width,height}}`.
- `VerticalCutReveal`'s per-segment `transition.delay` is **additive** with `staggerIndex * staggerDuration`, not overridden by it — a preview that wants every segment visible immediately needs BOTH `staggerDuration={0}` AND `transition={{duration:0, delay:0}}`; zeroing only one still leaves later segments invisible in a static capture.
- `Sparkles`' particle field (framer-motion keyframe arrays, random per-particle delay 0–5s / duration 10–20s) has no prop to force a mid-animation frame — every particle literally starts at opacity 0. A static screenshot of the container/copy is correct and expected to show no visible particles; this is graded "good" as an honest limitation, not fixed.
- `HeroWave`'s `minHeight: calc(100dvh - 68px)` is relative to the actual capture viewport, not the wrapping div — undersized preview containers clip its content; give it a tall wrapper (≥640px) or override via `cfg.overrides`.
- Base-UI's dialog/tooltip primitives (`Sheet`, `Tooltip`, both on `@base-ui/react`) use `defaultOpen` (not Radix's `open`) to statically force an overlay open. `SheetClose`/`SheetTrigger` compose via the `render={<Button .../>}` prop pattern, not `<Button>` as a child.
- `Input` wraps `@base-ui/react/input`, not a plain `<input>`, but forwards standard HTML input props transparently — no special preview handling needed.

## Re-sync risks
- The Tailwind compile step (`.ds-compiled/tailwind.css`) is NOT regenerated automatically by `package-build.mjs` — it's a manual pre-step. A re-sync that forgets to re-run the Tailwind CLI ships **stale** CSS (works today, silently wrong after any future Tailwind-class change in the app).
- `cfg.excludeSrcFiles` is a hand-picked list, not auto-detected — if a future component starts importing `next/image` (or any other browser-hostile Node/webpack-coupled API), it will reproduce the exact same "process is not defined, 0/N components render" failure and need the same triage (check `.render-check.json` firstErr, grep the bundle for bare `process.*`).
- `--entry` deliberately points at a non-existent file — a future skill update that makes `resolveDistEntry` treat a non-existent `--entry` differently would silently break the build shape here.

## Un-anchored on purpose (2026-08-17 session) — what the next sync needs to do
This run's `package-build.mjs` step (the one that reads all 25 `components/ui/*.tsx` files via ts-morph to synthesize the entry — the exact code the `source-kit.mjs` fork touches) started hanging with near-zero CPU usage partway through — not a crash, not an OOM, not disk/OneDrive I/O (all individually ruled out: plain file reads were fast, machine CPU was ~10%, moving `--out` outside the OneDrive-synced tree didn't help). Root cause undiagnosed; suspect a pathological ts-morph/TypeScript-checker resolution blowup (possibly triggered by the second `Project` instance the fork's default-export-detection code creates — see the `source-kit.mjs` fork entry above), but this is a guess, not confirmed.

**What this means practically:**
- All 61 components ARE correctly live in the project (every batch was pushed and `list_files`-verified as it was graded — see the conversation history for the per-batch pushes). The remote project is complete and correct.
- **`_ds_sync.json` was never uploaded** — the project has no verification anchor. This is the intended safe fallback for an aborted run (per the base skill): the next sync will simply re-verify every component from scratch (no `unchanged` fast-path), which costs more time but is correct.
- **`conventions.md` was authored and `readmeHeader` is wired in `config.json`, but the README on the live project does NOT yet carry it** — baking it in requires one clean full `package-build.mjs` run, which this session couldn't complete. First thing the next sync should do: retry the full build (try a normal `git pull`/fresh clone first — this environment had been through dozens of rapid rebuild/delete cycles in one session, which may itself have been a contributing factor) and, once it completes cleanly, do the close-out (full writes + reconciliation deletes + `_ds_sync.json` last) as normal.
- No components need re-authoring — this is purely a local-tooling/environment issue, not a content or config problem.
