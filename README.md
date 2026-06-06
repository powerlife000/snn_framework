# SNN Framework

Experimental research prototype for diagonal matrix-channel fractal numbers, period/shift payloads, and self-synchronizing SNN packets.

The project explores a mathematical layer for representing numeric payloads as hierarchical event-time structures. A value is converted into mixed-radix digits; each digit selects a cell in a user-defined channel matrix `(period_index, P_i, S_i)`; selected cells generate delayed step signals; channels are summed into one amplitude stream; the decoder restores the value through residual peeling.

Repository: https://github.com/powerlife000/snn_framework

## Current Scope

This is a research prototype, not a production SNN simulator.

Implemented:

- `snn_framework/matrix_fractal_number.py` - diagonal matrix-channel fractal number, user-defined `ChannelAlphabet`, step-signal generation, and residual peeling decoder.
- `snn_framework/fractal_packet.py` - self-synchronizing packet envelope around matrix-fractal payloads.
- `snn_framework/fractal_number.py` - functional generator model `F(n, i)`.
- `snn_framework/frequency_phase_digit.py` - frequency-phase digit matrix.
- `snn_framework/o1_decoder.py` - direct tick extraction research for base/global-shift channels.
- `tests/` - regression tests for the mathematical core.
- `experiments/` - exploratory notebooks.
- `article_assets/` - reproducible article scripts, generated figures, and CSV metrics.

The prototype currently verifies representation and roundtrip decoding. It does not yet prove final hardware bandwidth superiority. High-density physical modes require further research into correlation decoders, spike-mode encodings, analog phase receivers, and learned SNN/population decoders.

## Core Pipeline

```text
decimal value
  -> mixed-radix digits V_i
  -> matrix cells (period_index, P_i, S_i)
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

## Matrix-Channel Fractal Number

`MatrixFractalNumber` treats each channel as a user-defined diagonal period/shift matrix. Periods must be contiguous with step `1`; each period row `P` has exactly `P` legal shifts `S in [0, P - 1]`.

```text
periods_i = user_defined_periods(i)
Base_i = sum(P for P in periods_i)
V_i = sum(previous periods) + S_i
```

Example:

```python
from snn_framework import ChannelAlphabet, MatrixFractalNumber

number = MatrixFractalNumber(channel_alphabets=[
    ChannelAlphabet(periods=range(2, 7)),
    ChannelAlphabet(periods=range(7, 11)),
])

digits = number.encode_digits(348, digit_count=2)
cells = number.encode_cells(348, digit_count=2)

assert [number.radix(0), number.radix(1)] == [20, 34]
assert digits == [8, 17]
assert [(cell.period_ticks, cell.shift_ticks) for cell in cells] == [(4, 3), (9, 2)]
assert number.decode_cells(cells) == 348
```

For signal generation, shift `S_i` is a start delay, not cyclic phase rotation:

```text
C_i(t) = 0, if t < S_i
C_i(t) = 1[((t - S_i) mod P_i) >= floor(P_i / 2)], if t >= S_i
A(t) = sum_i C_i(t)
```

Helper factories are available for experiments, but they are not the mathematics itself:

```python
MatrixFractalNumber.article_348_alphabet()
MatrixFractalNumber.from_contiguous_bands(start=2, widths=[5, 4, 4])
MatrixFractalNumber.from_rule(lambda i: ChannelAlphabet(...))
```

The primary summed-signal decoder peels channels from highest frequency to lowest frequency.

## Fractal SNN Packet

`FractalSNNPacketCodec` adds a service envelope:

```text
PREAMBLE
START_DELIMITER
SIGN
DIGIT_COUNT
PAYLOAD_START_GUARD
FRACTAL_PAYLOAD
END_GUARD
END_DELIMITER
CHECK
```

Example:

```python
from snn_framework import FractalSNNPacketCodec, MatrixFractalNumber

number = MatrixFractalNumber.article_348_alphabet()
codec = FractalSNNPacketCodec(number)

encoded = codec.encode(-348, digit_count=2)
decoded = codec.decode(encoded.samples)
assert decoded.value == -348
assert decoded.check_ok
```

## Reproduce Tests

From the repository root:

```powershell
python -m pytest
```

Current expected result:

```text
31 passed
```

## Reproduce Article Assets

Generate signal and residual-peeling figures:

```powershell
python article_assets/scripts/generate_article_figures.py
```

Outputs:

```text
article_assets/outputs/figure_1_signal_matrix_348.png
article_assets/outputs/figure_2_residual_peeling_matrix_348.png
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

Generate multistream comparative metrics against an idealized binary serial reference:

```powershell
python article_assets/scripts/generate_snn_comparative_metrics.py
```

Outputs:

```text
article_assets/outputs/snn_comparative_metrics.csv
article_assets/outputs/figure_3_comparative_latency.png
article_assets/outputs/figure_4_comparative_id.png
```

The multistream comparison splits the same payload across equal numbers of physical streams for both methods. For `MatrixFractalNumber`, each stream restarts its period hierarchy from the fastest digit channel; for `Binary Serial`, each stream carries one bit per tick under an ideal external clock.

Generate matrix-alphabet sweep metrics:

```powershell
python article_assets/scripts/generate_alphabet_sweep_metrics.py
```

Outputs:

```text
article_assets/outputs/matrix_alphabet_sweep_metrics.csv
article_assets/outputs/figure_7_matrix_alphabet_sweep.png
```

See `article_assets/README.md` for descriptions of every generated figure and metric file.

## Efficiency Interpretation

The current step-mode implementation uses half-period step signals over diagonal matrix-channel alphabets. This makes the decoder simple and deterministic enough for a research prototype, while keeping the mathematical table form explicit.

For the current prototype, payload latency is estimated as:

```text
required_payload_ticks = max(cell.shift_ticks + 3 * cell.period_ticks for cell in cells) + 1
```

This is intentionally stricter than simply counting mixed-radix digits. Therefore, current metrics should be interpreted as a baseline for correct representation and decoding, not as the final limit of fractal SNN-channel bandwidth. The idealized binary serial line in the comparative plots is a synchronized lower-bound reference, not an SNN-native value code.

Future high-density research directions:

- correlation decoding without waiting for the full maximum period;
- nearest-cell decoding with confidence;
- partially overlapping period bands;
- sparse spike-mode payloads;
- analog phase/period receivers;
- learned SNN or population decoders.

## Notebooks

Available exploratory notebooks:

- `experiments/fractal_alphabet_demo.ipynb`
- `experiments/multistream_fractal_vs_binary.ipynb`
- `experiments/fractal_number_compression_demo.ipynb`
- `experiments/fractal_packet_demo.ipynb`
- `experiments/fractal_number_robustness_experiment.ipynb`
- `experiments/fractal_number_efficiency_experiment.ipynb`

The scripts in `article_assets/scripts/*.py` are preferred for reproducible article artifacts.

## Roadmap

- Add explicit distance/similarity metrics between fractal numbers.
- Add arithmetic operations: addition, subtraction, multiplication, scaling.
- Add signed, fixed-point, and float-like modes.
- Add noise/jitter experiments with confidence estimates.
- Add SNN-channel efficiency experiments against rate coding, TTFS, population coding, and binary spike-channel baselines.
- Add differentiable neuron-facing operations and surrogate-gradient experiments.

## License

Apache-2.0.
