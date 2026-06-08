# -*- coding: utf-8 -*-

import json
import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio

# =========================
# CONFIG
# =========================
CUT_OFF = datetime.datetime(2026, 6, 8, 0, 0, 0, tzinfo=datetime.timezone.utc)
pio.templates.default = "plotly_dark"

# =========================
# LOAD DATA
# =========================
with open("challenge-data.json", encoding="utf-8") as f:
    data = json.load(f)

# =========================
# MAPS
# =========================
account_team = {}
team_members_count = {}
id_to_name = {}

for m in data.get("members", []):
    id_to_name[m["id"]] = m["full_name"]

for team in data.get("teams", []):
    name = team["name"].strip()
    team_members_count[name] = len(team["team_members"])
    
    for m in team["team_members"]:
        account_team[m["account_id"]] = name

# =========================
# DATAFRAME
# =========================
rows = []

for c in data.get("check_ins", []):
    if c.get("points") is None:
        continue

    occurred = datetime.datetime.fromisoformat(
        c["occurred_at"].replace("Z", "+00:00")
    )

    if occurred >= CUT_OFF:
        continue

    team = account_team.get(c["account_id"])

    if team:
        year, week, _ = occurred.isocalendar()

        rows.append({
            "team": team,
            "points": c["points"],
            "date": occurred.date(),
            "week": f"{year}-W{week}",
            "account_id": c["account_id"]
        })

df = pd.DataFrame(rows)

# =========================
# TIMES
# =========================
team_points = df.groupby("team")["points"].sum().reset_index()
team_avg = (df.groupby("team")["points"].sum() / pd.Series(team_members_count)).reset_index()
engagement = (df.groupby("team")["account_id"].nunique() / pd.Series(team_members_count)).reset_index()

team_avg.columns = ["team", "points"]
engagement.columns = ["team", "engagement"]

# =========================
# PARTICIPANTES (✅ NOME + TIME)
# =========================
player_points = df.groupby("account_id")["points"].sum().reset_index()
player_points["name"] = player_points["account_id"].map(id_to_name).fillna("Sem nome")
player_points["team"] = player_points["account_id"].map(account_team)

player_points["name"] = player_points["name"] + " - " + player_points["team"]

player_points = player_points.sort_values("points", ascending=False)
mvp = player_points.iloc[0]

# =========================
# SEMANAL TIMES
# =========================
weekly = df.groupby(["week", "team"])["points"].sum().reset_index()

weekly_pivot = weekly.pivot(index="week", columns="team", values="points").fillna(0)
weekly_cumsum = weekly_pivot.cumsum().reset_index()

# =========================
# RANKING SEMANAL PARTICIPANTES (✅ NOME + TIME)
# =========================
weekly_players = df.groupby(["week", "account_id"])["points"].sum().reset_index()

weekly_players["name"] = weekly_players["account_id"].map(id_to_name).fillna("Sem nome")
weekly_players["team"] = weekly_players["account_id"].map(account_team)

weekly_players["name"] = weekly_players["name"] + " - " + weekly_players["team"]

weekly_players = weekly_players.sort_values(["week", "points"], ascending=[True, False])

weekly_players["rank"] = weekly_players.groupby("week")["points"] \
    .rank(method="first", ascending=False)

# =========================
# MVP POR SEMANA (✅ CORRIGIDO)
# =========================
weekly_mvp = (
    weekly_players
    .sort_values(["week", "points"], ascending=[True, False])
    .groupby("week")
    .head(1)
)

mvp_semanal_html = ""

for _, row in weekly_mvp.iterrows():
    team = account_team.get(row["account_id"], "")
    nome_base = id_to_name.get(row["account_id"], "Sem nome")

    mvp_semanal_html += f"<p>{row['week']} → {nome_base} - {team} ({round(row['points'],2)} pts)</p>"

# =========================
# TOP 20 SEMANAL
# =========================
weekly_top = weekly_players.groupby("week").head(20)

# =========================
# DIÁRIO
# =========================
daily = df.groupby(["date", "team"])["points"].sum().reset_index()

daily_avg = daily.copy()
daily_avg["avg_points"] = daily_avg.apply(
    lambda row: row["points"] / team_members_count[row["team"]],
    axis=1
)

# =========================
# GRÁFICOS
# =========================
fig_total = px.bar(team_points, x="team", y="points", title="🏆 Ranking Times")

fig_avg = px.bar(team_avg, x="team", y="points", title="⚡ Eficiência")

fig_eng = px.bar(engagement, x="team", y="engagement", title="👥 Engajamento")

fig_weekly = px.line(
    weekly, x="week", y="points", color="team",
    markers=True, title="📈 Evolução Semanal"
)

fig_cumsum = px.line(
    weekly_cumsum, x="week", y=weekly_cumsum.columns[1:],
    markers=True, title="🚀 Acumulado"
)

fig_daily = px.line(
    daily, x="date", y="points", color="team",
    markers=True, title="📅 Evolução Diária"
)

fig_daily_avg = px.line(
    daily_avg, x="date", y="avg_points", color="team",
    markers=True, title="⚡ Média Diária"
)

# Ranking geral
top50 = player_points.head(50)

fig_players = px.bar(
    top50.sort_values("points"),
    x="points",
    y="name",
    orientation="h",
    title="🏆 Ranking Geral Participantes"
)

fig_players.update_layout(
    height=30 * len(top50),
    yaxis=dict(tickfont=dict(size=14))
)

# Ranking semanal
fig_weekly_players = px.bar(
    weekly_top,
    x="points",
    y="name",
    color="week",
    facet_col="week",
    facet_col_wrap=2,
    title="📅 Ranking Semanal (Top 20)"
)

fig_weekly_players.update_layout(height=1200)

# =========================
# HTML
# =========================
html = f"""
<html>
<head>
<title>Dashboard Copa GET</title>
<style>
body {{
    background:#0f1117;
    color:white;
    font-family:Arial;
    margin:40px;
}}
h1 {{text-align:center;}}
h2 {{margin-top:60px;}}
</style>
</head>
<body>

<h1>🏆 Copa GET Dashboard</h1>

<h2>📊 Times</h2>
{fig_total.to_html(False)}
{fig_avg.to_html(False)}
{fig_eng.to_html(False)}

<h2>📈 Evolução</h2>
{fig_weekly.to_html(False)}
{fig_cumsum.to_html(False)}

<h2>📅 Evolução Diária</h2>
{fig_daily.to_html(False)}
{fig_daily_avg.to_html(False)}

<h2>🏆 Ranking Geral Participantes</h2>
{fig_players.to_html(False)}

<h2>📅 Ranking Semanal</h2>
{fig_weekly_players.to_html(False)}

<h2>👑 MVP Geral</h2>
<p>{mvp['name']} ({round(mvp['points'],2)} pts)</p>

<h2>👑 MVP por Semana</h2>
{mvp_semanal_html}

</body>
</html>
"""

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Dashboard gerado: dashboard.html")
print(f"🏆 MVP Geral: {mvp['name']} ({round(mvp['points'],2)} pts)")

