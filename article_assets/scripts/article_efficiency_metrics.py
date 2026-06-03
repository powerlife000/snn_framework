"""Generate reproducible SNN-channel efficiency metrics for the article.

The current matrix-fractal prototype is a conservative step-mode baseline. It
is designed to prove that a period-shift payload can be encoded, summed, and
decoded, not to claim final hardware bandwidth limits.
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


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def required_payload_ticks(cells) -> int:
    """Observation window required by the current direct payload decoder."""

    return max(cell.shift_ticks + cell.period_ticks for cell in cells) + 1


def worst_case_value(base: int, digit_count: int) -> int:
    """Number whose every matrix-radix digit is the largest digit."""

    return sum((base - 1) * (base**index) for index in range(digit_count))


def matrix_fractal_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    configs = [(2, 4), (4, 4), (8, 8), (16, 16)]
    digit_counts = [2, 4, 8, 16, 32, 64]

    for period_levels, shift_levels in configs:
        model = MatrixFractalNumber(
            period_levels=period_levels,
            shift_levels=shift_levels,
            base_period_ticks=max(8, shift_levels),
        )
        for digit_count in digit_counts:
            value = worst_case_value(model.base, digit_count)
            cells = model.encode_cells(value, digit_count=digit_count)
            ticks = required_payload_ticks(cells)
            payload_bits = digit_count * math.log2(model.base)
            max_amplitude = digit_count
            amplitude_resolution_bits = math.log2(max_amplitude + 1)
            stream_ticks = ticks
            raw_id = payload_bits / stream_ticks
            adjusted_id = payload_bits / (stream_ticks * amplitude_resolution_bits)
            rows.append(
                {
                    "method": f"matrix_fractal_{period_levels}x{shift_levels}",
                    "family": "matrix fractal step-mode",
                    "period_levels": period_levels,
                    "shift_levels": shift_levels,
                    "base": model.base,
                    "digit_count": digit_count,
                    "payload_bits": payload_bits,
                    "latency_ticks": ticks,
                    "physical_streams": 1,
                    "stream_ticks": stream_ticks,
                    "max_amplitude": max_amplitude,
                    "amplitude_levels": max_amplitude + 1,
                    "amplitude_resolution_bits": amplitude_resolution_bits,
                    "id_bits_per_stream_tick": raw_id,
                    "adjusted_id": adjusted_id,
                }
            )
    return rows


def baseline_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    payload_bits_values = [8, 16, 32, 64, 128, 256, 512]
    for payload_bits in payload_bits_values:
        for streams in [1, 4, 8, 16]:
            ticks = math.ceil(payload_bits / streams)
            rows.append(
                {
                    "method": f"binary_x{streams}",
                    "family": "binary spike baseline",
                    "period_levels": 0,
                    "shift_levels": 0,
                    "base": 2,
                    "digit_count": payload_bits,
                    "payload_bits": payload_bits,
                    "latency_ticks": ticks,
                    "physical_streams": streams,
                    "stream_ticks": ticks * streams,
                    "max_amplitude": 1,
                    "amplitude_levels": 2,
                    "amplitude_resolution_bits": 1.0,
                    "id_bits_per_stream_tick": payload_bits / (ticks * streams),
                    "adjusted_id": payload_bits / (ticks * streams),
                }
            )
    return rows


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_metrics(rows: list[dict[str, float | int | str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fractal_rows = [row for row in rows if row["family"] == "matrix fractal step-mode"]

    fig, ax = plt.subplots(figsize=(9, 5))
    for method in sorted({row["method"] for row in fractal_rows}):
        group = [row for row in fractal_rows if row["method"] == method]
        group.sort(key=lambda row: row["digit_count"])
        ax.plot(
            [row["digit_count"] for row in group],
            [row["latency_ticks"] for row in group],
            marker="o",
            label=method.replace("matrix_fractal_", ""),
        )
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set_xlabel("Matrix-radix digit count")
    ax.set_ylabel("Required observation window, ticks")
    ax.set_title("Current step-mode payload latency")
    ax.legend(title="period x shift")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_3_efficiency_required_ticks.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    for method in sorted({row["method"] for row in fractal_rows}):
        group = [row for row in fractal_rows if row["method"] == method]
        group.sort(key=lambda row: row["digit_count"])
        ax.plot(
            [row["digit_count"] for row in group],
            [row["id_bits_per_stream_tick"] for row in group],
            marker="o",
            label=method.replace("matrix_fractal_", ""),
        )
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1, label="binary x1")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=10)
    ax.set_xlabel("Matrix-radix digit count")
    ax.set_ylabel("ID, useful bits / stream-tick")
    ax.set_title("Current conservative step-mode information density")
    ax.legend(title="period x shift")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_efficiency_id.png", dpi=180)
    plt.close(fig)


def main() -> None:
    rows = baseline_rows() + matrix_fractal_rows()
    write_csv(rows, OUTPUT_DIR / "article_efficiency_metrics.csv")
    plot_metrics(rows)
    print("Wrote metrics and plots to article_assets/outputs")


if __name__ == "__main__":
    main()
