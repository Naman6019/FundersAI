# MarketMind: Project Summary

MarketMind is an AI-orchestrated financial research platform designed specifically for the Indian stock and mutual fund markets. It synthesizes complex quantitative metrics, market news sentiment, and historical trends into actionable, retail-investor-friendly insights through a sophisticated multi-agent pipeline.

## 🚀 Key Features

### 1. AI-Powered Research Assistant
- **Intent Routing**: Automatically routes user queries to specialized pipelines: **Quant** (metrics), **News** (sentiment), **Screener**, or **Comparison**.
- **Context-Aware Chat**: Remembers previous queries and provides synthesized summaries of complex data.
- **Deterministic Tables**: Renders precise financial data in structured tables alongside AI responses.

### 2. Interactive Analysis Canvas
- **Mutual Fund Comparison**: Side-by-side deep dives into funds, featuring NAV charts, historical returns, and risk metrics (Alpha, Beta, Sharpe).
- **Stock Analysis**: Comprehensive view of stock fundamentals (P/E, Market Cap, Ratios) and technical price history charts.
- **Visual Insights**: Dynamic data visualization using Recharts for performance tracking.

### 3. Automated Data Infrastructure
- **Daily EOD Sync**: Automated pipelines for fetching End-of-Day stock prices from NSE (Bhavcopy).
- **Mutual Fund Synchronization**: Daily updates for NAV, Total Expense Ratio (TER), and Assets Under Management (AUM).
- **Corporate Actions**: Automated tracking of dividends, splits, and other corporate events via IndianAPI.

### 4. Robust Backend Architecture
- **Source-Neutral Repository**: A unified data layer that abstracts multiple providers (NSE, IndianAPI, YFinance).
- **Data Quality Assurance**: Logging and monitoring of data quality issues across different providers.

### 5. Premium User Experience
- **Modern Dashboard**: High-fidelity UI with glassmorphism, responsive layouts, and fluid transitions.
- **Landing Page**: A research-first homepage with proof-focused messaging, live Nifty 50 strip, and direct prompt handoff into the dashboard.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: [Next.js 16](https://nextjs.org/) (App Router)
- **Library**: [React 19](https://react.dev/)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/)
- **Animations**: [Framer Motion](https://www.framer.com/motion/) (installed, currently minimal usage)
- **State Management**: [Zustand](https://github.com/pmndrs/zustand)
- **Charts**: [Recharts](https://recharts.org/)
- **Deployment**: [Vercel](https://vercel.com/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Validation**: [Pydantic](https://docs.pydantic.dev/)
- **Data Processing**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Deployment**: [Render](https://render.com/)

### Database & AI
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **AI Engine**: [Groq SDK](https://groq.com/) (Llama 3 / Mixtral models)

### Data Providers
- **Primary Equities**: [NSE India](https://www.nseindia.com/) (via CM-UDiFF Bhavcopy)
- **Financial APIs**: [IndianAPI](https://indianapi.in/) (Fundamentals, Ratios, MF data)
- **Fallbacks**: [YFinance](https://github.com/ranarousay/yfinance)
- **News**: Google News RSS via `feedparser`

### DevOps & Automation
- **CI/CD & Automation**: [GitHub Actions](https://github.com/features/actions) (Scheduled data sync workflows)
- **Version Control**: Git & GitHub
