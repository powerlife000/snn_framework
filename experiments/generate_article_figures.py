"""Generate article figures for the matrix-fractal number paper."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snn_framework import MatrixFractalNumber


OUTPUT_DIR = Path(__file__).resolve().parent / "article_outputs"


def make_demo_signal(value: int = 2748, digit_count: int = 3, ticks: int = 120):
    model = MatrixFractalNumber(period_levels=4, shift_levels=4, base_period_ticks=8)
    cells = model.encode_cells(value, digit_count=digit_count)
    samples = model.signal(value, digit_count=digit_count, ticks=ticks)
    channel_series = [
        [sample.channel_amplitudes[channel] for sample in samples]
        for channel in range(digit_count)
    ]
    summed = [sample.total_amplitude for sample in samples]
    return model, cells, channel_series, summed


def plot_signal() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _, cells, channels, summed = make_demo_signal()
    ticks = list(range(len(summed)))

    fig, axes = plt.subplots(len(channels) + 1, 1, figsize=(11, 7), sharex=True)
    for index, channel in enumerate(channels):
        cell = cells[index]
        axes[index].step(ticks, channel, where="post")
        axes[index].set_ylim(-0.15, 1.25)
        axes[index].set_ylabel(f"C{index}")
        axes[index].set_title(
            f"channel {index}: digit={cell.digit_value}, P={cell.period_ticks}, S={cell.shift_ticks}"
        )
        axes[index].grid(True, alpha=0.25)

    axes[-1].step(ticks, summed, where="post", color="black")
    axes[-1].set_ylabel("A(t)")
    axes[-1].set_xlabel("tick")
    axes[-1].set_title("Summed amplitude stream A(t)")
    axes[-1].grid(True, alpha=0.25)
    fig.suptitle("Figure 1. Matrix-fractal signal for value 2748", y=0.995)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_1_signal_2748.png", dpi=180)
    plt.close(fig)


def plot_residual_peeling() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model, cells, _, summed = make_demo_signal()
    ticks = list(range(len(summed)))
    residual = [float(value) for value in summed]

    rows: list[tuple[str, list[float]]] = [("A(t)", residual.copy())]
    for cell in cells:
        channel = [
            1.0 if model.cell_schedule(cell).is_active(tick) else 0.0
            for tick in ticks
        ]
        rows.append((f"C{cell.digit_index}(t), digit={cell.digit_value}", channel))
        residual = [value - channel_value for value, channel_value in zip(residual, channel)]
        rows.append((f"residual after C{cell.digit_index}", residual.copy()))

    fig, axes = plt.subplots(len(rows), 1, figsize=(11, 11), sharex=True)
    for ax, (label, values) in zip(axes, rows):
        ax.step(ticks, values, where="post")
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("tick")
    fig.suptitle("Figure 2. Residual peeling for value 2748", y=0.995)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "figure_2_residual_peeling_2748.png", dpi=180)
    plt.close(fig)


def main() -> None:
    plot_signal()
    plot_residual_peeling()
    print("Wrote article figures to experiments/article_outputs")


if __name__ == "__main__":
    main()
