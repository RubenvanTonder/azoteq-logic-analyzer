# 🔬 Logic Analyzer Test & Validation Report

**Device Name:** DSLogic U3Pro (Sigrok Compatible)
**Model / Variant:** 16 Digital + 2 Analog Channels
**Firmware / Software Version:** FW v3.x / PulseView 0.4.2
**Date Tested:** 2026-05-06
**Engineer:** Ruben van Tonder

---

# ⏱️ Sampling & Frequency Tests

## Maximum Sampling Rate (Buffer)
- **Test Setup:**
  - Signal Source: Rigol DG4162
  - Frequency Tested: 10MHz → 100MHz
  - Channels Used: 16
  - Sample Rate: 500MS/s

- **Observed Results:**
  - Clean waveform up to ~80MHz
  - Aliasing above ~100MHz

- **Validation Outcome:** ✅ Pass

---

## Minimum Detectable Pulse Width
- **Observed Results:**
  - Reliable ≥ 5ns
  - Intermittent below 4ns

- **Validation Outcome:** ⚠️ Partial Pass

---

# ⏱️ Timing Accuracy & Jitter

## Timing Accuracy (Edge-to-Edge Measurement)
- **Test Setup:**
  - Signal Source: Precision clock generator (10MHz reference)
  - Channel Count: 1
  - Sample Rate: 500MS/s

- **Procedure:**
  - Measured period and frequency using PulseView timing cursors
  - Compared against known reference signal

- **Expected Behavior:**
  - Measured period deviation within ±1 sample clock interval

- **Observed Results:**
  - Expected period: 100ns
  - Measured period: 99.8ns – 100.3ns
  - Maximum error: ~±0.3ns

- **Validation Outcome:** ✅ Pass
- **Notes:**
  - Accuracy limited by sampling resolution (2ns at 500MS/s)

---

## Jitter Measurement (Cycle-to-Cycle Variation)
- **Test Setup:**
  - Signal: Stable 10MHz clock source (low phase-noise generator)
  - Sample Rate: 500MS/s

- **Procedure:**
  - Captured 10,000+ edges
  - Measured variation in period across cycles

- **Expected Behavior:**
  - Minimal variation for clean clock source
  - Variance primarily due to sampling uncertainty

- **Observed Results:**
  - Peak-to-peak jitter: ~2.5ns
  - RMS jitter: ~0.6ns

- **Validation Outcome:** ✅ Pass
- **Notes:**
  - Jitter dominated by sampling granularity, not signal source

---

## Inter-Channel Timing Skew
- **Test Setup:**
  - Signal: Same clock fed to multiple channels
  - Channels Tested: CH0–CH7

- **Procedure:**
  - Measured edge alignment between channels

- **Expected Behavior:**
  - Minimal skew between channels

- **Observed Results:**
  - Max skew observed: ~1.5ns

- **Validation Outcome:** ✅ Pass
- **Notes:**
  - Acceptable for parallel bus analysis

---

# 💾 Storage & Data Mode Tests

## Hardware Storage Depth
- **Observed Capture Duration:**
  - ~1.2 seconds (expected ≈1.25s)

- **Validation Outcome:** ✅ Pass

---

## Stream Mode (Computer Memory)
- **Observed Results:**
  - Stable streaming
  - No dropped samples
  - RAM usage ~5GB

- **Validation Outcome:** ✅ Pass

---

# ⚡ Electrical & Signal Integrity

## Input Impedance
- **Observed Results:**
  - Minimal voltage drop (<5%)

- **Validation Outcome:** ✅ Pass

---

## Adjustable Threshold
- **Observed Results:**
  - Works as expected across voltage levels

- **Validation Outcome:** ✅ Pass

---

# 📈 Analog Channel Tests

## Analog Sampling Accuracy
- **Observed Results:**
  - 1kHz: Clean waveform
  - 100kHz: Slight rounding
  - 1MHz: Attenuation visible

- **Validation Outcome:** ⚠️ Partial Pass

---

## Analog Voltage Accuracy
- **Observed Results:**
  - Within ~2–3% error

- **Validation Outcome:** ✅ Pass

---

## Analog-Digital Correlation
- **Observed Results:**
  - Strong edge alignment between analog and digital

- **Validation Outcome:** ✅ Pass

---

# 🔍 Protocol & Triggering

## Trigger Accuracy
- **Observed Results:**
  - Trigger offset < 100ns

- **Validation Outcome:** ✅ Pass

---

## Protocol Decoding
- **Observed Results:**
  - Reliable decoding up to:
    - UART: 1Mbps
    - I2C: 1MHz
    - SPI: ~20MHz

- **Validation Outcome:** ✅ Pass

---

# 📊 Summary

| Category                  | Result       |
|--------------------------|--------------|
| Sampling & Frequency     | ✅ Pass      |
| Timing & Jitter          | ✅ Pass      |
| Storage & Data Modes     | ✅ Pass      |
| Electrical Characteristics | ✅ Pass    |
| Analog Performance       | ⚠️ Partial   |
| Triggering & Protocol    | ✅ Pass      |

**Overall Verdict:** ✅ PASS (with expected analog and sampling limitations)

---

# 📎 Additional Notes & Observations
- Timing accuracy is strongly tied to sample rate (no interpolation)
- Jitter measurements reflect quantization error, not true signal jitter
- Suitable for digital timing analysis but **not a replacement for high-end T&M equipment**

---

# 📁 Attachments
- Waveform Screenshots: `/captures/jitter_test.png`
- Logs: `/logs/timing_analysis.log`
- Raw Capture Files: `/data/timing_test.sr`