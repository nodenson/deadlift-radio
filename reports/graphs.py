import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from db.schema import DB_PATH
from db.queries import (
    get_bench_sets_all_time, get_all_sets_all_time,
    get_all_sets_with_exercise_all_time, estimate_e1rm,
)
from classification.movements import classify_exercise_movement
from utils.spinner import run_with_grimdark_spinner

BG      = "#0d0d0d"
PANEL   = "#141414"
ACCENT  = "#c8a96e"
ACCENT2 = "#7a3f3f"
GRIDLINE = "#222222"
TEXT    = "#cccccc"
SUBTEXT = "#666666"
SPINE   = "#333333"

EXERCISE_COLORS = [
    "#c8a96e", "#7a3f3f", "#4a7a6a", "#5a5a9a",
    "#8a6a3a", "#6a3a6a", "#3a6a4a", "#9a5a2a",
]


def _apply_dark_style(ax, fig):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(ACCENT)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.5, linestyle="--")
    ax.set_axisbelow(True)


def _save(fig, filename: str) -> Path:
    path = Path(f"exports/{filename}")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    return path


def graph_e1rm_progression(conn) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = get_all_sets_with_exercise_all_time(conn)
    if not rows:
        return []

    by_exercise = {}
    for session_date, exercise_name, load, reps in rows:
        e1rm = estimate_e1rm(load, reps)
        if exercise_name not in by_exercise:
            by_exercise[exercise_name] = {}
        prev = by_exercise[exercise_name].get(session_date, 0.0)
        by_exercise[exercise_name][session_date] = max(prev, e1rm)

    plottable = {name: data for name, data in by_exercise.items() if len(data) >= 3}
    if not plottable:
        return []

    saved = []

    fig, ax = plt.subplots(figsize=(12, 6))
    _apply_dark_style(ax, fig)

    for i, (name, date_map) in enumerate(sorted(plottable.items())):
        dates = sorted(date_map.keys())
        values = [date_map[d] for d in dates]
        color = EXERCISE_COLORS[i % len(EXERCISE_COLORS)]
        ax.plot(dates, values, marker="o", markersize=4, linewidth=1.8,
                color=color, label=name, alpha=0.9)
        ax.annotate(
            f"{int(values[-1])}",
            xy=(dates[-1], values[-1]),
            xytext=(4, 4), textcoords="offset points",
            fontsize=7, color=color, alpha=0.85,
        )

    ax.set_title("ESTIMATED 1RM PROGRESSION", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=9)
    ax.set_ylabel("Est. 1RM (lbs)", fontsize=9)
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=SPINE, labelcolor=TEXT,
              loc="upper left", framealpha=0.9)
    plt.xticks(rotation=40, ha="right", fontsize=7)
    plt.tight_layout()
    saved.append(_save(fig, "e1rm_progression.png"))
    plt.close(fig)

    for name, date_map in sorted(plottable.items()):
        dates = sorted(date_map.keys())
        values = [date_map[d] for d in dates]

        fig, ax = plt.subplots(figsize=(10, 5))
        _apply_dark_style(ax, fig)
        ax.fill_between(dates, values, alpha=0.12, color=ACCENT)
        ax.plot(dates, values, marker="o", markersize=5, linewidth=2,
                color=ACCENT, zorder=3)

        peak_val = max(values)
        peak_idx = values.index(peak_val)
        ax.scatter([dates[peak_idx]], [peak_val], color=ACCENT2,
                   s=80, zorder=5, label=f"Peak: {int(peak_val)} lbs")

        if len(values) >= 4:
            import numpy as np
            x_idx = list(range(len(values)))
            z = np.polyfit(x_idx, values, 1)
            p = np.poly1d(z)
            trend = [p(xi) for xi in x_idx]
            ax.plot(dates, trend, linestyle="--", linewidth=1,
                    color=SUBTEXT, alpha=0.6, label="Trend")

        safe_name = name.replace(" ", "_").lower()
        ax.set_title(f"{name.upper()} — EST. 1RM", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Date", fontsize=9)
        ax.set_ylabel("Est. 1RM (lbs)", fontsize=9)
        ax.legend(fontsize=8, facecolor=PANEL, edgecolor=SPINE,
                  labelcolor=TEXT, framealpha=0.9)
        plt.xticks(rotation=40, ha="right", fontsize=7)
        plt.tight_layout()
        saved.append(_save(fig, f"e1rm_{safe_name}.png"))
        plt.close(fig)

    return saved


def graph_weekly_tonnage(conn) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = get_all_sets_with_exercise_all_time(conn)
    if not rows:
        return []

    weekly = {}
    all_weeks = set()

    for session_date, exercise_name, load, reps in rows:
        dt = datetime.strptime(session_date, "%Y-%m-%d").date()
        week = str(dt - timedelta(days=dt.weekday()))
        all_weeks.add(week)
        if exercise_name not in weekly:
            weekly[exercise_name] = {}
        weekly[exercise_name][week] = weekly[exercise_name].get(week, 0.0) + load * reps

    weeks = sorted(all_weeks)
    exercises = sorted(weekly.keys())
    x = list(range(len(weeks)))

    fig, ax = plt.subplots(figsize=(12, 6))
    _apply_dark_style(ax, fig)

    bottoms = [0.0] * len(weeks)
    for i, ex in enumerate(exercises):
        values = [weekly[ex].get(w, 0.0) for w in weeks]
        color = EXERCISE_COLORS[i % len(EXERCISE_COLORS)]
        ax.bar(x, values, bottom=bottoms, color=color, label=ex, alpha=0.85, width=0.7)
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for xi, total in enumerate(bottoms):
        if total > 0:
            ax.text(xi, total + max(bottoms) * 0.01, f"{int(total):,}",
                    ha="center", va="bottom", fontsize=6.5, color=SUBTEXT)

    ax.set_title("WEEKLY TONNAGE BY EXERCISE", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Week Starting", fontsize=9)
    ax.set_ylabel("Tonnage (lbs)", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(weeks, rotation=40, ha="right", fontsize=7)
    ax.legend(fontsize=7, facecolor=PANEL, edgecolor=SPINE,
              labelcolor=TEXT, loc="upper left", framealpha=0.9)
    plt.tight_layout()
    saved = [_save(fig, "weekly_tonnage.png")]
    plt.close(fig)
    return saved


def graph_push_pull_balance(conn) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = get_all_sets_with_exercise_all_time(conn)
    if not rows:
        return []

    weekly_push = {}
    weekly_pull = {}

    for session_date, exercise_name, load, reps in rows:
        dt = datetime.strptime(session_date, "%Y-%m-%d").date()
        week = str(dt - timedelta(days=dt.weekday()))
        movement = classify_exercise_movement(exercise_name)
        weekly_push.setdefault(week, 0)
        weekly_pull.setdefault(week, 0)
        if movement in {"horizontal_press", "incline_press", "elbow_extension", "lateral_raise"}:
            weekly_push[week] += 1
        if movement in {"row", "rear_delt", "elbow_flexion"}:
            weekly_pull[week] += 1

    weeks = sorted(set(weekly_push) | set(weekly_pull))
    if not weeks:
        return []

    push_vals = [weekly_push.get(w, 0) for w in weeks]
    pull_vals  = [weekly_pull.get(w, 0) for w in weeks]
    x = list(range(len(weeks)))
    width = 0.38

    fig, ax = plt.subplots(figsize=(12, 5))
    _apply_dark_style(ax, fig)
    ax.bar([xi - width / 2 for xi in x], push_vals, width=width,
           color=ACCENT, label="Push", alpha=0.85)
    ax.bar([xi + width / 2 for xi in x], pull_vals, width=width,
           color=ACCENT2, label="Pull", alpha=0.85)

    ratios = [p / u if u > 0 else None for p, u in zip(push_vals, pull_vals)]
    ax2 = ax.twinx()
    ax2.set_facecolor(PANEL)
    valid_x = [xi for xi, r in zip(x, ratios) if r is not None]
    valid_r = [r for r in ratios if r is not None]
    if valid_r:
        ax2.plot(valid_x, valid_r, color="#ffffff", linewidth=1.2,
                 linestyle=":", alpha=0.4, label="Push:Pull ratio")
        ax2.axhline(1.0, color=SUBTEXT, linewidth=0.8, linestyle="--", alpha=0.4)
        ax2.set_ylabel("Push:Pull Ratio", color=SUBTEXT, fontsize=8)
        ax2.tick_params(colors=SUBTEXT, labelsize=7)
        for spine in ax2.spines.values():
            spine.set_edgecolor(SPINE)

    ax.set_title("WEEKLY PUSH vs PULL SET COUNT", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Week Starting", fontsize=9)
    ax.set_ylabel("Set Count", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(weeks, rotation=40, ha="right", fontsize=7)
    ax.legend(fontsize=8, facecolor=PANEL, edgecolor=SPINE,
              labelcolor=TEXT, loc="upper left", framealpha=0.9)
    plt.tight_layout()
    saved = [_save(fig, "push_pull_balance.png")]
    plt.close(fig)
    return saved


def graph_session_heatmap(conn) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np

    rows = get_all_sets_all_time(conn)
    if not rows:
        return []

    daily = {}
    for session_date, load, reps in rows:
        daily[session_date] = daily.get(session_date, 0.0) + load * reps

    if not daily:
        return []

    dates = sorted(daily.keys())
    start = datetime.strptime(dates[0], "%Y-%m-%d").date()
    end   = datetime.strptime(dates[-1], "%Y-%m-%d").date()

    weeks = []
    current = start - timedelta(days=start.weekday())
    while current <= end:
        week_row = []
        for d in range(7):
            day = current + timedelta(days=d)
            key = day.strftime("%Y-%m-%d")
            week_row.append(daily.get(key, 0.0) if start <= day <= end else None)
        weeks.append(week_row)
        current += timedelta(weeks=1)

    data = np.array([[v if v is not None else np.nan for v in w] for w in weeks])

    fig, ax = plt.subplots(figsize=(max(8, len(weeks) * 0.35), 4))
    _apply_dark_style(ax, fig)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "dlr", [PANEL, "#3a2a0a", ACCENT], N=256
    )
    cmap.set_bad(color=BG)
    im = ax.imshow(data.T, aspect="auto", cmap=cmap, interpolation="nearest")

    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                       fontsize=8, color=TEXT)

    month_ticks = []
    month_labels = []
    seen_months = set()
    for i, w in enumerate(weeks):
        day = start - timedelta(days=start.weekday()) + timedelta(weeks=i)
        m = day.strftime("%b %Y")
        if m not in seen_months:
            month_ticks.append(i)
            month_labels.append(m)
            seen_months.add(m)

    ax.set_xticks(month_ticks)
    ax.set_xticklabels(month_labels, rotation=30, ha="right", fontsize=7, color=TEXT)

    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.ax.tick_params(colors=SUBTEXT, labelsize=7)
    cbar.set_label("Tonnage (lbs)", color=SUBTEXT, fontsize=8)
    cbar.outline.set_edgecolor(SPINE)

    ax.set_title("TRAINING VOLUME HEATMAP", fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    saved = [_save(fig, "session_heatmap.png")]
    plt.close(fig)
    return saved


def _generate_training_graphs_inner() -> None:
    Path("exports").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    saved = []
    saved += graph_e1rm_progression(conn)
    saved += graph_weekly_tonnage(conn)
    saved += graph_push_pull_balance(conn)
    saved += graph_session_heatmap(conn)

    conn.close()

    print("\n+++ TRAINING GRAPHS GENERATED +++")
    if saved:
        for p in saved:
            print(f"- {p}")
    else:
        print("No data found to graph. Log some sessions first.")


def generate_training_graphs() -> None:
    run_with_grimdark_spinner("FORGING IRON RECORDS", _generate_training_graphs_inner)