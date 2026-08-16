# FundersAI UI conventions

FundersAI is an Indian stocks + mutual-funds research app. This library is `frontend/components/ui/` — shadcn primitives (`base-ui/react` under the hood) plus a set of decorative/marketing effects. There is **no root provider or ThemeProvider to wrap with** — none of these components read from React context for theming. Just import and use them directly.

## Important: this library does NOT auto-render dark

Despite FundersAI's product having a dark "Terminal Modernism" look in practice, the shadcn primitives here (`Button`, `Card`, `Input`, `Sheet`, `Tooltip`, `Separator`, `Skeleton`) use standard light-mode tokens (`bg-background`, `bg-card`, `text-foreground`, etc.) by default — the app never applies a `.dark` class. If you compose a screen that mixes these primitives with FundersAI's dark surfaces, give the container an explicit dark background (see the `Sidebar` family below, which IS built dark-first with hardcoded hex values, not the light token system) rather than assuming the primitives switch automatically.

## Styling idiom: Tailwind utility classes + two token systems

Style with Tailwind utility classes — never invent CSS. Two coexisting token vocabularies, both real (verified against the compiled stylesheet):

**shadcn semantic tokens** (light-mode by default, used by primitives — `Button`, `Card`, `Input`, `Sheet`, `Tooltip`):
- `bg-primary` / `text-primary-foreground` — primary actions
- `bg-secondary` / `text-secondary-foreground` — secondary actions
- `bg-card` / `text-card-foreground` — card surfaces
- `bg-background` — page/input background
- `border-input` — form control borders
- `text-muted-foreground` — secondary/caption text
- `bg-destructive` / `text-destructive` — destructive actions
- `rounded-lg`, `rounded-xl` — the standard corner radii here (not `rounded-md`)

**Terminal Modernism tokens** (dark, hand-built — used by `Sidebar`/`SidebarInset` and anything meant to sit on FundersAI's actual dark shell):
- `bg-terminal-bg` — the near-black app background (`#07080c`)
- `border-terminal-border` — subtle hairline borders on dark surfaces
- Sidebar-specific: the `Sidebar` component itself uses raw hex (`#050505` bg, emerald `#00FF9D` active state) rather than the terminal-* utility classes — copy its pattern (see `.design-sync/previews/Sidebar.tsx`) rather than inventing new dark utilities.

Don't mix the two systems in one surface — a `Card` (light tokens) dropped directly onto `bg-terminal-bg` (dark) will look like a mistake, not a design choice, unless that contrast is clearly intentional (e.g. a light modal over a dark shell).

## Typography

Headings render in a serif display face (`Playfair Display`, loaded remotely — see `[FONT_REMOTE]` in the build log, nothing to configure), body/UI text in a sans face (`Inter`). Numeric/financial figures (NAV, CAGR) commonly use a monospace face — see `NumberTicker`'s preview for the pattern.

## Where the truth lives

- `styles.css` (imports `_ds_bundle.css`) — the full compiled stylesheet; grep it for any class before inventing one.
- Each component's own `<Name>.prompt.md` and `<Name>.d.ts` — the authoritative prop API.
- `.design-sync/previews/*.tsx` — real, graded compositions. `Sidebar.tsx`, `Card.tsx`, `Sheet.tsx` are good starting references for how FundersAI actually composes these primitives with realistic content (real fund names, CAGR/NAV figures, Indian tickers).

## Realistic content

This is a mutual-fund/stock research tool — use real-feeling sample data: fund names like "Axis Bluechip Fund", "HDFC Flexi Cap", "Parag Parikh Flexi Cap"; category labels like "Large Cap", "Mid Cap"; metrics like CAGR, NAV (₹), expense ratio, Sharpe ratio; Indian tickers like RELIANCE, TCS, HDFCBANK.

## Example: a realistic composed card

```tsx
import { Card, CardHeader, CardContent, Button } from 'marketmind';

function FundCard() {
  return (
    <Card style={{ maxWidth: 360 }}>
      <CardHeader>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          Axis Bluechip Fund
        </h3>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
          Large Cap · Direct Growth
        </p>
      </CardHeader>
      <CardContent>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          3Y CAGR: <strong>14.2%</strong> · Expense ratio: 0.58%
        </p>
        <Button variant="default" size="sm">View details</Button>
      </CardContent>
    </Card>
  );
}
```

Note: the package name to import from is `marketmind` (the frontend app's internal package name — not published, just the identifier this sync uses).
