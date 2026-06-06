"""Generate dynamic-alphabet sweep metrics for the article."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snn_framework import MatrixFractalNumber
try:
    from .dynamic_alphabet_helpers import (
        capacity_bits,
        custom_rule_examples,
        required_payload_ticks,
        worst_case_value,
    )
except ImportError:
    from dynamic_alphabet_helpers import (
        capacity_bits,
        custom_rule_examples,
        required_payload_ticks,
        worst_case_value,
    )


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def sweep_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    configs = custom_rule_examples()

    for method, label, model in configs:
        for digit_count in range(2, 33, 2):
            if method == "article_348_alphabet" and digit_count > 2:
                continue
            value = worst_case_value(model, digit_count)
            cells = model.encode_cells(value, digit_count=digit_count)
            latency_ticks = required_payload_ticks(cells)
            payload_bits = capacity_bits(model, digit_count)
            rows.append(
                {
                    "method": method,
                    "label": label,
                    "digit_count": digit_count,
                    "max_period_ticks": max(cell.period_ticks for cell in cells),
                    "payload_bits": payload_bits,
                    "latency_ticks": latency_ticks,
                    "id_bits_per_tick": payload_bits / latency_ticks,
                }
            )
    return rows


def write_csv(rows: list[dict[str, float | int | str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "matrix_alphabet_sweep_metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_sweep(rows: list[dict[str, float | int | str]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for method in sorted({row["method"] for row in rows}):
        group = [row for row in rows if row["method"] == method]
        group.sort(key=lambda row: row["digit_count"])
        label = str(group[0]["label"])
        axes[0].plot(
            [row["payload_bits"] for row in group],
            [row["latency_ticks"] for row in group],
            marker="o",
            label=label,
        )
        axes[1].plot(
            [row["payload_bits"] for row in group],
            [row["id_bits_per_tick"] for row in group],
            marker="s",
            label=label,
        )

    axes[0].set_xscale("log", base=2)
    axes[0].set_yscale("log", base=10)
    axes[0].set_xlabel("Payload capacity, bits")
    axes[0].set_ylabel("Latency, ticks")
    axes[0].set_title("Matrix-channel alphabet latency sweep")
    axes[0].grid(True, which="both", alpha=0.3)

    axes[1].set_xscale("log", base=2)
    axes[1].set_yscale("log", base=10)
    axes[1].set_xlabel("Payload capacity, bits")
    axes[1].set_ylabel("ID, bits / tick")
    axes[1].set_title("Matrix-channel alphabet information density")
    axes[1].grid(True, which="both", alpha=0.3)
    axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_7_matrix_alphabet_sweep.png", dpi=180)
    plt.close(fig)


def main() -> None:
    rows = sweep_rows()
    write_csv(rows)
    plot_sweep(rows)
    print("Wrote matrix alphabet sweep metrics to article_assets/outputs")


if __name__ == "__main__":
    main()
