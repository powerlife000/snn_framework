"""Generate storage-efficiency metrics for matrix-fractal article assets.

The storage comparison separates exact numeric storage from unfolded SNN state
storage. A matrix-fractal value is stored as selected period-shift cells, while
the unfolded forms explicitly store either the summed amplitude signal A(t) or
the dense channel-state table C_k(t).
"""

from __future__ import annotations

import csv
import math
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


def bits_for_levels(levels: int) -> int:
    """Minimum integer bit width needed to index ``levels`` states."""

    if levels <= 1:
        return 1
    return math.ceil(math.log2(levels))


def storage_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    configs = custom_rule_examples()
    digit_counts = [2, 4, 8, 16, 32]

    for method, label, model in configs:
        for digit_count in digit_counts:
            if method == "article_348_alphabet" and digit_count > 2:
                continue
            value = worst_case_value(model, digit_count)
            cells = model.encode_cells(value, digit_count=digit_count)
            latency_ticks = required_payload_ticks(cells)
            payload_bits = capacity_bits(model, digit_count)

            fractal_value_bits = payload_bits
            binary_integer_bits = payload_bits
            amplitude_resolution_bits = bits_for_levels(digit_count + 1)
            unfolded_amplitude_signal_bits = latency_ticks * amplitude_resolution_bits
            unfolded_channel_table_bits = latency_ticks * digit_count

            rows.append(
                {
                    "method": method,
                    "label": label,
                    "period_levels": "",
                    "shift_levels": "P_max per channel",
                    "digit_count": digit_count,
                    "payload_bits": payload_bits,
                    "latency_ticks": latency_ticks,
                    "fractal_value_bits": fractal_value_bits,
                    "binary_integer_bits": binary_integer_bits,
                    "unfolded_amplitude_signal_bits": unfolded_amplitude_signal_bits,
                    "unfolded_channel_table_bits": unfolded_channel_table_bits,
                    "number_storage_gain_vs_binary": binary_integer_bits
                    / fractal_value_bits,
                    "signal_storage_gain_vs_unfolded": unfolded_amplitude_signal_bits
                    / fractal_value_bits,
                    "state_table_storage_gain_vs_unfolded": unfolded_channel_table_bits
                    / fractal_value_bits,
                }
            )
    return rows


def write_csv(rows: list[dict[str, float | int | str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "storage_efficiency_metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_number_vs_unfolded_signal(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    for method in sorted({row["method"] for row in rows}):
        group = [row for row in rows if row["method"] == method]
        group.sort(key=lambda row: row["payload_bits"])
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["signal_storage_gain_vs_unfolded"] for row in group],
            marker="o",
            label=str(group[0]["label"]),
        )

    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload capacity, bits")
    ax.set_ylabel("Storage gain vs unfolded A(t)")
    ax.set_title("Fractal value parameters vs unfolded amplitude signal")
    ax.legend(title="channel alphabet")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_5_storage_number_vs_signal.png", dpi=180)
    plt.close(fig)


def plot_state_table_compression(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    for method in sorted({row["method"] for row in rows}):
        group = [row for row in rows if row["method"] == method]
        group.sort(key=lambda row: row["payload_bits"])
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["state_table_storage_gain_vs_unfolded"] for row in group],
            marker="s",
            label=str(group[0]["label"]),
        )

    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload capacity, bits")
    ax.set_ylabel("Storage gain vs dense C_k(t) table")
    ax.set_title("Fractal generator parameters vs dense state table")
    ax.legend(title="channel alphabet")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_6_storage_state_table.png", dpi=180)
    plt.close(fig)


def main() -> None:
    rows = storage_rows()
    write_csv(rows)
    plot_number_vs_unfolded_signal(rows)
    plot_state_table_compression(rows)
    print("Wrote storage metrics to article_assets/outputs")


if __name__ == "__main__":
    main()
