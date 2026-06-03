"""Generate SNN-channel comparative metrics for the article.

This script compares a conservative matrix-fractal step-mode payload against
single-channel value-resolution temporal/rate coding and an idealized binary
serial baseline. The matrix-fractal latency is computed through the public
``MatrixFractalNumber`` implementation, not through a hand-written surrogate
formula.
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


def fractal_latency_ticks(
    payload_bits: int,
    *,
    period_levels: int = 4,
    shift_levels: int = 4,
) -> tuple[int, int, int]:
    """Return ``(latency_ticks, digit_count, payload_capacity_bits)``.

    ``payload_bits`` may not be divisible by ``log2(base)``. In that case the
    matrix-fractal payload allocates one extra digit; ``payload_capacity_bits``
    records the representable payload size for the selected digit count.
    """

    model = MatrixFractalNumber(
        period_levels=period_levels,
        shift_levels=shift_levels,
        base_period_ticks=max(8, shift_levels),
    )
    bits_per_digit = math.log2(model.base)
    digit_count = math.ceil(payload_bits / bits_per_digit)
    payload_capacity_bits = int(digit_count * bits_per_digit)
    value = worst_case_value(model.base, digit_count)
    cells = model.encode_cells(value, digit_count=digit_count)
    return required_payload_ticks(cells), digit_count, payload_capacity_bits


def comparative_rows() -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    payload_sizes = list(range(2, 25, 2))

    for payload_bits in payload_sizes:
        baselines = [
            (
                "rate_ttfs_value_code_2powB_levels",
                "Rate / TTFS value code (2^B levels)",
                2**payload_bits,
                1,
                payload_bits,
            ),
            (
                "binary_serial",
                "Binary serial baseline",
                payload_bits,
                1,
                payload_bits,
            ),
        ]
        for method, label, latency_ticks, physical_streams, capacity_bits in baselines:
            stream_ticks = latency_ticks * physical_streams
            rows.append(
                {
                    "method": method,
                    "label": label,
                    "payload_bits": payload_bits,
                    "payload_capacity_bits": capacity_bits,
                    "digit_count": "",
                    "latency_ticks": latency_ticks,
                    "physical_streams": physical_streams,
                    "stream_ticks": stream_ticks,
                    "id_bits_per_stream_tick": payload_bits / stream_ticks,
                }
            )

        latency_ticks, digit_count, capacity_bits = fractal_latency_ticks(payload_bits)
        rows.append(
            {
                "method": "matrix_fractal_4x4_step_mode",
                "label": "Matrix-fractal 4x4 step-mode",
                "payload_bits": payload_bits,
                "payload_capacity_bits": capacity_bits,
                "digit_count": digit_count,
                "latency_ticks": latency_ticks,
                "physical_streams": 1,
                "stream_ticks": latency_ticks,
                "id_bits_per_stream_tick": payload_bits / latency_ticks,
            }
        )
    return rows


def write_csv(rows: list[dict[str, float | int | str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "snn_comparative_metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_latency(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    styles = {
        "rate_ttfs_value_code_2powB_levels": ("o", "red"),
        "matrix_fractal_4x4_step_mode": ("s", "blue"),
        "binary_serial": ("^", "green"),
    }
    for method in styles:
        group = [row for row in rows if row["method"] == method]
        marker, color = styles[method]
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["latency_ticks"] for row in group],
            label=str(group[0]["label"]),
            marker=marker,
            color=color,
        )

    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload size, bits")
    ax.set_ylabel("Latency, ticks")
    ax.set_title("SNN-channel payload transmission: latency")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_3_comparative_latency.png", dpi=180)
    plt.close(fig)


def plot_information_density(rows: list[dict[str, float | int | str]]) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    styles = {
        "rate_ttfs_value_code_2powB_levels": ("o", "red"),
        "matrix_fractal_4x4_step_mode": ("s", "blue"),
        "binary_serial": ("^", "green"),
    }
    for method in styles:
        group = [row for row in rows if row["method"] == method]
        marker, color = styles[method]
        ax.plot(
            [row["payload_bits"] for row in group],
            [row["id_bits_per_stream_tick"] for row in group],
            label=str(group[0]["label"]),
            marker=marker,
            color=color,
        )

    ax.set_yscale("log", base=10)
    ax.set_xlabel("Payload size, bits")
    ax.set_ylabel("Information density, bits / stream-tick")
    ax.set_title("SNN-channel payload transmission: information density")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_4_comparative_id.png", dpi=180)
    plt.close(fig)


def main() -> None:
    rows = comparative_rows()
    write_csv(rows)
    plot_latency(rows)
    plot_information_density(rows)
    print("Wrote comparative SNN-channel metrics to article_assets/outputs")


if __name__ == "__main__":
    main()
