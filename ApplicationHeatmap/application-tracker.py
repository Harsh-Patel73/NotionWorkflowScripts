import requests
import datetime
import os
from dotenv import load_dotenv
import plotly.graph_objects as go

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if NOTION_TOKEN is None or DATABASE_ID is None:
    raise ValueError("NOTION_TOKEN or DATABASE_ID not set.")

NOTION_API_URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# -----------------------------
# Fetch applications from Notion
# -----------------------------
def get_applications():
    all_results = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        res = requests.post(NOTION_API_URL, headers=HEADERS, json=payload)
        res.raise_for_status()
        data = res.json()
        all_results.extend(data["results"])
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    return all_results

# -----------------------------
# Count applications per day
# -----------------------------
def count_per_day(applications):
    counts = {}
    for app in applications:
        props = app["properties"]
        date_field = props.get("Date Applied", {}).get("date")
        if not date_field:
            continue
        date_str = date_field["start"]
        counts[date_str] = counts.get(date_str, 0) + 1
    return counts

# -----------------------------
# Draw interactive GitHub-style grid
# -----------------------------
def draw_interactive_grid(counts, output_path="interactive_grid.html"):
    today = datetime.date.today()
    start_date = today - datetime.timedelta(weeks=10)
    dates = [start_date + datetime.timedelta(days=i) for i in range((today - start_date).days + 1)]
    total_weeks = (len(dates) + 6) // 7  # ceiling division

    # Prepare z-values (numeric) and hover text
    z = [[0 for _ in range(total_weeks)] for _ in range(7)]
    hover_text = [[None for _ in range(total_weeks)] for _ in range(7)]

    for i, d in enumerate(dates):
        week_idx = i // 7
        day_idx = d.weekday()  # Monday=0
        if d > today:
            val = 0  # future day = 0
            hover_text[day_idx][week_idx] = f"{d}: 0 applications"
        else:
            val = counts.get(d.isoformat(), 0)
            hover_text[day_idx][week_idx] = f"{d}: {val} application{'s' if val != 1 else ''}"
        z[day_idx][week_idx] = val

    # Define discrete colorscale for GitHub-style
    # Map: 0=future gray, 1-9=red, 10-24=yellow, 25+=green
    def discrete_colorscale(val):
        if val == 0:
            return 0
        elif val < 10:
            return 1
        elif val < 25:
            return 2
        else:
            return 3

    z_colors = [[discrete_colorscale(z[y][x]) for x in range(total_weeks)] for y in range(7)]

    colorscale = [
        [0, '#ebedf0'],   # gray for 0 (future or no apps)
        [0.25, '#e74c3c'], # red <10
        [0.5, '#f1c40f'],  # yellow 10-24
        [1, '#2ecc71']     # green 25+
    ]

    fig = go.Figure(go.Heatmap(
        z=z_colors,
        text=hover_text,
        hoverinfo='text',
        x=list(range(total_weeks)),
        y=list(range(7)),
        colorscale=colorscale,
        showscale=False,
        xgap=2,
        ygap=2,
        zmin=0,
        zmax=3
    ))

    fig.update_yaxes(autorange="reversed", showgrid=False, zeroline=False, visible=False)
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y")
    fig.update_layout(
        width=total_weeks*20,
        height=7*20,
        margin=dict(l=10,r=10,t=10,b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )


    fig.write_html(output_path)
    print(f"Interactive grid saved to {output_path}")

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    applications = get_applications()
    daily_counts = count_per_day(applications)
    draw_interactive_grid(daily_counts, output_path="ApplicationHeatmap/interactive_grid.html")
