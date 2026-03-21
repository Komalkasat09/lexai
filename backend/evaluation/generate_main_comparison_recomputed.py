import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def rank_colors(values: np.ndarray, lower_is_better: bool) -> list[str]:
    """Assign green/orange/red by rank for one metric panel."""
    palette = ["#1a9850", "#fdae61", "#d73027"]  # best, middle, worst
    order = np.argsort(values) if lower_is_better else np.argsort(-values)
    colors = [None] * len(values)
    for rank, idx in enumerate(order):
        colors[idx] = palette[min(rank, 2)]
    return colors


def main() -> None:
    results_dir = Path(__file__).resolve().parent / "results"
    figures_dir = results_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    table_csv = results_dir / "paper_table_03_system_comparison.numeric.csv"
    hr_json = Path(__file__).resolve().parent / "results_393_postfix" / "complete_results_20260318_104440.json"

    out_png = figures_dir / "main_comparison_recomputed.png"
    out_prov = figures_dir / "main_comparison_recomputed.png.provenance.json"
    out_caption = figures_dir / "main_comparison_recomputed.caption.tex"

    systems = ["LexAI", "SimpleRAG", "NoRAG"]

    table_df = pd.read_csv(table_csv)
    table_df = table_df.set_index("System").loc[systems].reset_index()

    with open(hr_json, "r", encoding="utf-8") as f:
        all_metrics = json.load(f).get("all_metrics", {})

    hr_structured = {
        system: float(all_metrics[system]["HR"]["HR_overall"])
        for system in systems
    }

    # Build plotting frame from canonical table + structured-only HR override.
    plot_df = pd.DataFrame({
        "System": systems,
        "CAR_overall": [float(table_df.set_index("System").loc[s, "CAR_overall"]) for s in systems],
        "HR_overall": [hr_structured[s] for s in systems],
        "ACS_overall": [float(table_df.set_index("System").loc[s, "ACS_overall"]) for s in systems],
        "OLR_overall": [float(table_df.set_index("System").loc[s, "OLR_overall"]) for s in systems],
    })

    metrics = [
        ("CAR_overall", "CAR (%)", False),
        ("HR_overall", "HR (%)", True),
        ("ACS_overall", "ACS", False),
        ("OLR_overall", "OLR (%)", True),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(18, 6.2))

    for ax, (metric, title, lower_is_better) in zip(axes, metrics):
        vals = plot_df[metric].astype(float).to_numpy()
        x = np.arange(len(systems))
        colors = rank_colors(vals, lower_is_better)

        bars = ax.bar(x, vals, color=colors, alpha=0.92, width=0.62)
        offset = max(vals) * 0.015 + 0.2

        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + offset,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(systems, fontsize=10)
        ax.grid(axis="y", alpha=0.25)
        ax.set_ylim(0, max(vals) * 1.18 + 0.5)
        ax.set_xlabel(
            "lower is better" if lower_is_better else "higher is better",
            fontsize=9,
            style="italic",
        )

    fig.suptitle("System Performance Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    provenance = {
        "figure": "main_comparison_recomputed",
        "output_path": str(out_png),
        "inputs": [
            {
                "source": table_csv.name,
                "path": str(table_csv),
                "fields_used": ["CAR_overall", "ACS_overall", "OLR_overall"],
                "row_count": int(len(table_df)),
            },
            {
                "source": hr_json.name,
                "path": str(hr_json),
                "fields_used": ["all_metrics.*.HR.HR_overall"],
                "note": "HR panel uses structured citation hallucination only.",
            },
        ],
        "metrics_used": [m[0] for m in metrics],
        "values_used": {
            row["System"]: {
                "CAR_overall": float(row["CAR_overall"]),
                "HR_overall": float(row["HR_overall"]),
                "ACS_overall": float(row["ACS_overall"]),
                "OLR_overall": float(row["OLR_overall"]),
            }
            for _, row in plot_df.iterrows()
        },
        "color_policy": "per-metric rank colors (best=green, middle=orange, worst=red)",
    }

    with open(out_prov, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    # Ready-to-paste LaTeX caption note requested by reviewer-style feedback.
    out_caption.write_text(
        "% Caption note for main_comparison_recomputed.png\n"
        "\\caption{System Performance Comparison. Metrics shown are CAR, HR, ACS, and OLR across LexAI, SimpleRAG, and NoRAG. "
        "HR reports structured citation hallucination only (from all\\_metrics.*.HR.HR\\_overall) for consistency with the paper table.}"
        "\n",
        encoding="utf-8",
    )

    print(str(out_png))
    print(str(out_prov))
    print(str(out_caption))


if __name__ == "__main__":
    main()
