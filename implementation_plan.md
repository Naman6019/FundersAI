# Dashboard-First UI & Navigation Redesign

The objective is to redesign the app flow so that users land on a structured dashboard rather than directly dropping them into the AI research chat. We will create a command center for mutual fund research with dedicated pages for comparing funds, portfolio review, AI research, and more.

## User Review Required

> [!WARNING]
> **Major Routing Shift**
> Currently, the entire app operates within `DashboardLayout.tsx` acting as a single-page app (SPA) with tabs. The new design shifts to standard Next.js App Router folders (`app/dashboard`, `app/dashboard/compare`, `app/dashboard/research`, etc.). This means state that isn't stored in global stores (like `useChatStore` or `useCanvasStore`) won't persist across navigation. Are you okay with moving to route-based navigation?

## Proposed Changes

### 1. Route Re-Architecture

We will split the monolithic `DashboardLayout` into a true Next.js layout (`app/dashboard/layout.tsx`) and individual page components.

#### [NEW] `frontend/app/dashboard/layout.tsx`
- Extracts the sidebar and top navigation from `DashboardLayout.tsx`.
- Maps to the new navigation items: Dashboard, Compare, AI Research, Portfolio, Reports, Watchlist, Learn.
- Adds responsive sidebar behavior for mobile.

#### [NEW] `frontend/app/dashboard/page.tsx`
- **Dashboard Landing:** Replaces the current `renderOverview` with the new design.
- **Top Header:** Search bar, logo, and primary CTAs (Compare Funds, Ask AI, Upload Portfolio).
- **Main Action Cards:** Compare Funds, AI Fund Research, Portfolio Review.
- **Quick Compare Widget:** Select up to 3 funds and route to the Compare page.
- **Market Snapshot:** Popular categories (Large Cap, Flexi Cap, etc.).
- **Beginner Tools Placeholder.**
- **Recent Activity & Disclaimer.**

### 2. Dedicated Pages

#### [NEW] `frontend/app/dashboard/compare/page.tsx`
- **Compare Funds UI:**
  - Fund selection area (min 2, max 3).
  - Tabs: Overview, Returns, Risk, Fees, Portfolio, Holdings, Charts.
  - Factual comparison tables with simple visual indicators.
  - Integration with existing backend data structures.
  - Bottom actions: Save, PDF, Watchlist, **Explain with AI** (routes to `/dashboard/research` with context).

#### [MODIFY] `frontend/app/dashboard/research/page.tsx`
- **AI Research:**
  - Wraps the existing `ChatWindow` and Canvas UI.
  - Adjusts header to "AI Fund Research".
  - Adds example prompts and pre-loads context if arriving from the Compare page.

#### [NEW] `frontend/app/dashboard/portfolio/page.tsx`
- **Portfolio Review Placeholder:**
  - Upload portfolio section.
  - Factual portfolio health metrics layout.
  - Optional AI explanation button.

#### [NEW] `frontend/app/dashboard/reports/page.tsx`
- **Reports & Saved Results Placeholder:**
  - Grid of saved comparisons, AI reports, and portfolio reviews.

#### [NEW] `frontend/app/dashboard/watchlist/page.tsx`
- **Watchlist UI:**
  - Display saved funds with key metrics (NAV, Returns, ER).
  - Ability to select items and push them to the Compare page.

#### [NEW] `frontend/app/dashboard/learn/page.tsx`
- **Learn & Tools Placeholder:**
  - Educational sections on mutual funds.
  - Links to tools (SIP calculators, risk profiles).

### 3. State Management & Integration

#### [MODIFY] `frontend/store/useChatStore.ts` & `frontend/store/useCanvasStore.ts`
- Ensure the stores can handle context-passing (e.g., when clicking "Explain with AI" from the Compare page, we need to populate the chat context with the compared funds and navigate).

## Open Questions

> [!IMPORTANT]
> **Component Library**
> The current layout uses custom Lucide icons and inline Tailwind. Should I create reusable UI components (e.g., `Card`, `Button`, `Tabs`) in `components/ui/` or continue using inline Tailwind for speed during this prototype phase?

> [!NOTE]
> **Chart Implementation**
> The Compare Funds page requires charts (Returns over time, Rolling returns, Risk vs Return scatter, Asset allocation pie chart). Are you currently using a specific charting library (e.g., Recharts, Chart.js), or should I introduce `recharts` / `react-chartjs-2`?

## Verification Plan

### Manual Verification
1. **Routing:** Start the app and ensure the default page after login is the new Dashboard.
2. **Navigation:** Click through the sidebar to verify all new route placeholders load without errors.
3. **Quick Compare:** Use the widget on the Dashboard to select 2 funds and verify it redirects to the Compare page with the funds pre-loaded.
4. **Compare UI:** Verify tabs in the Compare page switch correctly and display the mocked/fetched factual data.
5. **AI Handoff:** Click "Explain with AI" on the Compare page and verify it transitions to the AI Research page with context.
6. **Mobile Layout:** Verify sidebar collapses into a hamburger menu and tables become horizontally scrollable on small screens.
