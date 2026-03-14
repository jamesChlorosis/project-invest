from __future__ import annotations


def render_dashboard(app_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{app_name}</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f4efe5;
        --panel: rgba(255, 252, 245, 0.86);
        --ink: #1f2c1f;
        --muted: #61715f;
        --accent: #0b6b47;
        --accent-soft: #dff3e9;
        --border: rgba(17, 37, 25, 0.12);
        --warning: #8a5a13;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background:
          radial-gradient(circle at top left, rgba(11, 107, 71, 0.16), transparent 35%),
          linear-gradient(180deg, #f6f0e7 0%, #efe6d8 100%);
        color: var(--ink);
        min-height: 100vh;
      }}

      .shell {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}

      .hero {{
        display: grid;
        gap: 18px;
        padding: 28px;
        background: linear-gradient(135deg, rgba(255, 252, 245, 0.9), rgba(224, 244, 234, 0.88));
        border: 1px solid var(--border);
        border-radius: 28px;
        box-shadow: 0 16px 48px rgba(60, 46, 28, 0.08);
      }}

      .hero h1 {{
        margin: 0;
        font-size: clamp(2rem, 4vw, 3.6rem);
        line-height: 0.95;
        letter-spacing: -0.04em;
      }}

      .hero p {{
        margin: 0;
        color: var(--muted);
        max-width: 760px;
        font-size: 1rem;
      }}

      .hero-actions {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }}

      button {{
        border: none;
        border-radius: 999px;
        padding: 12px 18px;
        font-size: 0.95rem;
        font-weight: 700;
        cursor: pointer;
        transition: transform 120ms ease, opacity 120ms ease;
      }}

      button:hover {{
        transform: translateY(-1px);
      }}

      .primary {{
        background: var(--accent);
        color: white;
      }}

      .secondary {{
        background: var(--panel);
        color: var(--ink);
        border: 1px solid var(--border);
      }}

      .grid {{
        display: grid;
        gap: 18px;
        margin-top: 22px;
        grid-template-columns: repeat(12, minmax(0, 1fr));
      }}

      .card {{
        grid-column: span 12;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 20px;
        box-shadow: 0 12px 32px rgba(60, 46, 28, 0.05);
      }}

      .wide {{
        grid-column: span 8;
      }}

      .side {{
        grid-column: span 4;
      }}

      .card h2 {{
        margin: 0 0 10px;
        font-size: 1.05rem;
      }}

      .kpis {{
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      }}

      .kpi {{
        padding: 14px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid var(--border);
      }}

      .label {{
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}

      .value {{
        margin-top: 6px;
        font-size: 1.35rem;
        font-weight: 700;
      }}

      ul {{
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 10px;
      }}

      li {{
        padding: 12px 14px;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.54);
      }}

      .meta {{
        color: var(--muted);
        font-size: 0.9rem;
      }}

      .note {{
        color: var(--warning);
      }}

      pre {{
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 0.88rem;
        color: var(--muted);
      }}

      @media (max-width: 900px) {{
        .wide,
        .side {{
          grid-column: span 12;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <h1>Project Invest</h1>
        <p>
          A private quant research operating system with execution-mode switching, evolving strategies,
          realistic paper fills, and a clean seam for future live broker adapters.
        </p>
        <div class="hero-actions">
          <button class="primary" id="run-cycle">Run Research Cycle</button>
          <button class="secondary" id="refresh">Refresh Dashboard</button>
        </div>
      </section>

      <section class="grid">
        <article class="card wide">
          <h2>System Summary</h2>
          <div class="kpis" id="summary"></div>
        </article>
        <article class="card side">
          <h2>Health</h2>
          <pre id="health">Loading...</pre>
        </article>
        <article class="card wide">
          <h2>Top Strategies</h2>
          <ul id="strategies"></ul>
        </article>
        <article class="card side">
          <h2>Allocation Plan</h2>
          <ul id="allocations"></ul>
        </article>
        <article class="card wide">
          <h2>Open Positions</h2>
          <ul id="positions"></ul>
        </article>
        <article class="card side">
          <h2>Recent Orders</h2>
          <ul id="orders"></ul>
        </article>
      </section>
    </main>

    <script>
      const summaryNode = document.getElementById("summary");
      const healthNode = document.getElementById("health");
      const strategiesNode = document.getElementById("strategies");
      const allocationsNode = document.getElementById("allocations");
      const positionsNode = document.getElementById("positions");
      const ordersNode = document.getElementById("orders");

      const currency = new Intl.NumberFormat("en-IN", {{
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
      }});

      function renderKpi(label, value) {{
        return `<div class="kpi"><div class="label">${{label}}</div><div class="value">${{value}}</div></div>`;
      }}

      function li(content) {{
        return `<li>${{content}}</li>`;
      }}

      async function loadDashboard() {{
        const [healthRes, portfolioRes, analyticsRes] = await Promise.all([
          fetch("/health"),
          fetch("/api/portfolio"),
          fetch("/api/analytics/summary")
        ]);

        const health = await healthRes.json();
        const portfolio = await portfolioRes.json();
        const analytics = await analyticsRes.json();

        healthNode.textContent = JSON.stringify(health, null, 2);

        summaryNode.innerHTML = [
          renderKpi("Mode", analytics.mode || health.execution_mode || "paper"),
          renderKpi("Portfolio", analytics.portfolio_value != null ? currency.format(analytics.portfolio_value) : "N/A"),
          renderKpi("Cash", analytics.cash != null ? currency.format(analytics.cash) : "N/A"),
          renderKpi("Positions", analytics.open_positions ?? 0),
          renderKpi("PnL", currency.format(analytics.realized_pnl || 0)),
          renderKpi("Last Run", analytics.last_run ? new Date(analytics.last_run).toLocaleString() : "No runs yet")
        ].join("");

        strategiesNode.innerHTML = analytics.top_strategies.length
          ? analytics.top_strategies.map((item) =>
              li(`<strong>${{item.symbol}}</strong><div class="meta">score=${{item.score}} sharpe=${{item.sharpe_ratio}} signal=${{item.signal}}</div>`)
            ).join("")
          : li(`<span class="note">No research results yet.</span>`);

        allocationsNode.innerHTML = Object.keys(analytics.allocation_plan).length
          ? Object.entries(analytics.allocation_plan).map(([symbol, weight]) =>
              li(`<strong>${{symbol}}</strong><div class="meta">${{(weight * 100).toFixed(1)}}% suggested capital</div>`)
            ).join("")
          : li(`<span class="note">Run research to generate allocations.</span>`);

        const positions = Object.values(portfolio.positions || {{}});
        positionsNode.innerHTML = positions.length
          ? positions.map((position) =>
              li(`<strong>${{position.symbol}}</strong><div class="meta">${{position.quantity}} units at ${{
                currency.format(position.average_price)
              }}</div>`)
            ).join("")
          : li(`<span class="note">No open positions.</span>`);

        ordersNode.innerHTML = analytics.recent_orders.length
          ? analytics.recent_orders.map((order) =>
              li(`<strong>${{order.symbol}}</strong><div class="meta">${{order.action}} ${{order.status}} in ${{
                order.mode
              }} mode</div>`)
            ).join("")
          : li(`<span class="note">No orders recorded yet.</span>`);
      }}

      async function runCycle() {{
        const button = document.getElementById("run-cycle");
        button.disabled = true;
        button.textContent = "Running...";
        try {{
          await fetch("/api/research/run", {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: "{{}}" }});
          await loadDashboard();
        }} finally {{
          button.disabled = false;
          button.textContent = "Run Research Cycle";
        }}
      }}

      document.getElementById("run-cycle").addEventListener("click", runCycle);
      document.getElementById("refresh").addEventListener("click", loadDashboard);
      loadDashboard();
    </script>
  </body>
</html>
"""
