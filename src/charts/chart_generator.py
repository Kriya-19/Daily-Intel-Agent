import matplotlib
matplotlib.use("Agg")  # non-interactive backend — required for GitHub Actions (no display)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

def generate_market_chart(market_data, output_path="chart.png"):
    """
    Generates a horizontal bar chart of % change for all tickers.
    Green bars = positive, red bars = negative.
    Saves to output_path and returns the path.
    """
    if not market_data:
        print("[Chart] No market data — skipping chart generation")

        return None

    labels = []
    changes = []
    colors = []

    for item in market_data:
        pct = item["change_pct"]
        # Format: "NIFTY 50  24,150" — label includes current price
        label = f"{item['label']}  {item['currency']}{item['price']:,.2f}"
        labels.append(label)
        changes.append(pct)
        colors.append("#2ecc71" if pct >= 0 else "#e74c3c")  # green / red

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.6)))
    
    # Dark background — looks cleaner in Telegram dark mode
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    bars = ax.barh(labels, changes, color=colors, height=0.6, edgecolor="none")

    # Add % change text at end of each bar
    for bar, pct in zip(bars, changes):
        x_pos = bar.get_width()
        sign = "+" if pct >= 0 else ""
        ax.text(
            x_pos + (0.05 if pct >= 0 else -0.05),
            bar.get_y() + bar.get_height() / 2,
            f"{sign}{pct:.2f}%",
            va="center",
            ha="left" if pct >= 0 else "right",
            color="white",
            fontsize=10,
            fontweight="bold",
        )

    # Vertical line at 0
    ax.axvline(0, color="#888888", linewidth=0.8, linestyle="--")

    ax.set_xlabel("% Change", color="white", fontsize=10)
    ax.tick_params(colors="white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    
    # Title with today's date
    from datetime import datetime
    today = datetime.now().strftime("%a, %d %b %Y")
    ax.set_title(f"Markets · {today}", color="white", fontsize=13, pad=15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()

    print(f"[Chart] Saved to {output_path}")
    return output_path