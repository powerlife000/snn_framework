# SNN Framework

Experimental research prototype for matrix-fractal numbers, period-shift payloads, and self-synchronizing SNN packets.

The project explores a mathematical layer for representing large numeric payloads as hierarchical event-time structures. A value is converted into matrix-radix digits; each digit selects a period-shift cell; selected cells generate channel signals; channels are summed into one amplitude stream; the decoder restores the value through residual peeling.

Repository: https://github.com/powerlife000/snn_framework

## Current Scope

This is a research prototype, not a production SNN simulator.

Implemented:

- `snn_framework/matrix_fractal_number.py` - matrix-radix fractal number, period-shift cells, step-signal generation, and residual peeling decoder.
- `snn_framework/fractal_packet.py` - self-synchronizing packet envelope around matrix-fractal payloads.
- `snn_framework/fractal_number.py` - functional generator model `F(n, i)`.
- `snn_framework/frequency_phase_digit.py` - frequency-phase digit matrix.
- `snn_framework/o1_decoder.py` - direct tick extraction research for base/global-shift channels.
- `tests/` - regression tests for the mathematical core.
- `experiments/` - notebooks and scripts for article figures and metrics.

The prototype currently verifies representation and roundtrip decoding. It does not yet prove final hardware bandwidth superiority. High-density physical modes require further research into correlation decoders, spike-mode encodings, analog phase receivers, and learned SNN/population decoders.

## Core Pipeline

```text
decimal value
  -> matrix-radix digits
  -> selected period-shift cells
  -> generator parameter table
  -> channel functions C_k(t)
  -> summed amplitude signal A(t)
  -> residual peeling decoder
```

The ordering invariant is:

```text
digit_index = 0 -> least significant digit -> shortest period -> highest frequency
larger digit_index -> more significant digit -> larger period -> lower frequency
```

## Matrix-Fractal Number

`MatrixFractalNumber` treats a period-shift matrix as a numeral alphabet:

```text
base = period_levels * shift_levels
digit = period_index * shift_levels + shift_index
```

Example:

```python
from snn_framework import MatrixFractalNumber

number = MatrixFractalNumber(period_levels=4, shift_levels=8)
cells = number.encode_cells(123456789)
restored = number.decode_cells(cells)
assert restored == 123456789
```

For signal generation, each selected cell emits a half-period step signal:

```text
phase_position_i(t) = (t - shift_ticks_i) mod period_ticks_i
active_i(t) = phase_position_i(t) >= active_width_ticks_i
output_signal(t) = sum_i channel_i_signal(t)
```

The primary summed-signal decoder peels channels from highest frequency to lowest frequency.

## Fractal SNN Packet

`FractalSNNPacketCodec` adds a service envelope:

```text
PREAMBLE
START_DELIMITER
SIGN
PAYLOAD_START_GUARD
FRACTAL_PAYLOAD
END_GUARD
END_DELIMITER
CHECK
```

Example:

```python
from snn_framework import FractalSNNPacketCodec, MatrixFractalNumber

number = MatrixFractalNumber(period_levels=2, shift_levels=4)
codec = FractalSNNPacketCodec(number)

encoded = codec.encode(-2026, digit_count=4)
decoded = codec.decode(encoded.samples)
assert decoded.value == -2026
assert decoded.check_ok
```

## Reproduce Tests

From the repository root:

```powershell
python -m pytest
```

Current expected result:

```text
32 passed
```

## Reproduce Article Assets

Generate signal and residual-peeling figures:

```powershell
python article_assets/scripts/generate_article_figures.py
```

Outputs:

```text
article_assets/outputs/figure_1_signal_2748.png
article_assets/outputs/figure_2_residual_peeling_2748.png
```

Generate efficiency metrics and plots:

```powershell
python article_assets/scripts/article_efficiency_metrics.py
```

Outputs:

```text
article_assets/outputs/article_efficiency_metrics.csv
article_assets/outputs/figure_3_efficiency_required_ticks.png
article_assets/outputs/figure_4_efficiency_id.png
```

See `article_assets/README.md` for descriptions of every generated figure and metric file.

## Efficiency Interpretation

The current conservative step-mode implementation uses non-overlapping period bands and half-period step signals. This makes the decoder simple and deterministic, but it increases the required observation window.

For the current prototype, payload latency is estimated as:

```text
required_payload_ticks = max(cell.shift_ticks + cell.period_ticks for cell in cells) + 1
```

This is intentionally stricter than simply counting matrix-radix digits. Therefore, current metrics should be interpreted as a baseline for correct representation and decoding, not as the final limit of fractal SNN-channel bandwidth.

Future high-density research directions:

- correlation decoding without waiting for the full maximum period;
- nearest-cell decoding with confidence;
- partially overlapping period bands;
- sparse spike-mode payloads;
- analog phase/period receivers;
- learned SNN or population decoders.

## Notebooks

Available exploratory notebooks:

- `experiments/fractal_number_compression_demo.ipynb`
- `experiments/fractal_packet_demo.ipynb`
- `experiments/fractal_number_robustness_experiment.ipynb`
- `experiments/fractal_number_compression_experiment.ipynb`

The scripts in `experiments/*.py` are preferred for reproducible article artifacts.

## Roadmap

- Add explicit distance/similarity metrics between fractal numbers.
- Add arithmetic operations: addition, subtraction, multiplication, scaling.
- Add signed, fixed-point, and float-like modes.
- Add noise/jitter experiments with confidence estimates.
- Add SNN-channel efficiency experiments against rate coding, TTFS, population coding, and binary spike-channel baselines.
- Add differentiable neuron-facing operations and surrogate-gradient experiments.

## License

Apache-2.0.
