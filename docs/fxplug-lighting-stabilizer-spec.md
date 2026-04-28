# Final Cut Pro Lighting Drift Stabilizer (FxPlug 4) — Technical Specification v1

## 1) Objective
Build an FxPlug 4 effect for Final Cut Pro that stabilizes **unwanted** exposure and white-balance drift over time while preserving intentional scene changes and natural lighting variation.

## 2) Product Scope
### In scope (v1)
- Temporal analysis of clip lighting metrics.
- Detection of exposure drift and white-balance drift.
- Shot-change aware correction (ignore hard cuts).
- Smoothed correction curves (no frame-by-frame pulsing).
- Editor-facing controls in Final Cut Pro via Motion-published parameters.

### Out of scope (v1)
- Semantic intent prediction using ML.
- Subject segmentation beyond heuristic/optional skin-priority masking.
- Multi-clip global matching across timeline.

## 3) Platform + Stack
- **Plugin framework:** FxPlug 4 effect plugin (Final Cut Pro + Motion path).
- **Image processing:** Core Image and/or Metal kernels.
- **Fast statistics:** MPS histogram/statistical operators where available.
- **Optional later:** Vision/Core ML for subject-aware weighting.

## 4) UX Contract (Final Cut Pro)
### Primary controls
- Analyze Clip (trigger)
- Auto Reference (toggle)
- Reference Mode: First Frame / Manual Frame / Rolling Median
- Manual Reference Frame (frame picker/index)
- Exposure Stabilization (0–100)
- White Balance Stabilization (0–100)
- Flicker Reduction (0–100)
- Highlight Protection (0–100)
- Skin Tone Priority (0–100)
- Scene Change Sensitivity (0–100)
- Sample Rate (every N frames)

### View/debug modes
- Corrected
- Drift Heat Map
- Drift Graph
- Before/After Split

## 5) High-Level Architecture
1. **Analysis Pass**
   - Sample frames at interval N.
   - Compute per-frame metrics.
   - Persist to cache for current clip/parameter signature.
2. **Segmentation Pass**
   - Detect scene boundaries and large discontinuities.
   - Partition timeline into lighting-consistent segments.
3. **Target Curve Builder**
   - Compute robust segment-level baseline.
   - Interpolate/smooth to timeline-wide correction curves.
4. **Render Pass**
   - Apply exposure/WB deltas with guardrails.
   - Preserve highlights and optional skin-priority regions.

## 6) Data Model
```text
FrameMetrics {
  frame_index: Int
  timestamp_sec: Double
  luma_mean: Float
  luma_median: Float
  luma_p10: Float
  luma_p90: Float
  shadow_clip_pct: Float
  highlight_clip_pct: Float
  rgb_mean: float3
  histogram_signature: [Float]   // reduced bins or embedding
  skin_confidence: Float?        // heuristic in v1, optional
}

Segment {
  start_frame: Int
  end_frame: Int
  kind: enum { STABLE, CUT_BOUNDARY, FLICKER_RISK, MAJOR_CHANGE }
}

CorrectionCurve {
  exposure_delta_ev[frame]
  wb_temp_delta[frame]
  wb_tint_delta[frame]
}
```

## 7) Analysis Algorithms
### 7.1 Per-frame metric extraction
For each sampled frame:
- Convert to linear working space.
- Compute luma Y and robust stats (`mean`, `median`, percentiles).
- Compute clipping percentages from tails.
- Compute RGB channel means and chroma bias.
- Build compact histogram signature.

### 7.2 Drift signals
- **Exposure drift signal:**
  - primary: median luma deviation from baseline.
  - secondary: percentile spread changes.
- **WB drift signal:**
  - channel balance drift (`R/G`, `B/G`) or equivalent chroma axes.
- **Localized flicker signal:**
  - frame-to-frame high-frequency residual after low-pass trend removal.

### 7.3 Shot/change detection
Mark boundary if one or more exceed threshold:
- histogram distance jump,
- large luma discontinuity,
- large chroma discontinuity.

## 8) Correction Strategy
### 8.1 Target baseline
Within each segment, compute robust targets:
- `target_luma = rolling_median(luma_median)`
- `target_wb = rolling_median(channel_bias)`

### 8.2 Delta generation
Per frame:
- `raw_exp_delta = f(target_luma - frame_luma)`
- `raw_wb_delta  = g(target_wb - frame_wb)`

### 8.3 Guardrails
- Clamp max per-frame delta.
- Clamp cumulative range per segment.
- Suppress correction near scene cuts.
- Attenuate correction when highlight clipping risk increases.
- Preserve saturation/skin tones via weighted masks.

### 8.4 Temporal smoothing
Use robust smoothing (e.g., bilateral-in-time or Savitzky–Golay-like trend + residual clamp):
- low-frequency trend correction,
- reject outlier spikes,
- avoid oscillation/pumping.

## 9) Caching + Invalidations
### Cache keys
- Clip identity + source modification timestamp.
- Frame size / color configuration.
- Sample rate.
- Reference mode + relevant parameters.

### Invalidate when
- Source clip changes.
- Any analysis-affecting parameter changes.
- Manual reference frame changes.

## 10) Performance Targets
- Analysis pass: asynchronous/background where host API allows.
- Render pass: near real-time playback on common Apple Silicon systems.
- Degrade gracefully:
  - larger sample interval,
  - fewer histogram bins,
  - reduced debug overlays.

## 11) Module Breakdown
- `FrameSampler`
  - pulls frames at sample interval.
- `MetricExtractor`
  - computes luma/chroma/histogram metrics.
- `SceneBoundaryDetector`
  - emits segment boundaries.
- `TargetCurveBuilder`
  - computes robust baseline and temporal curves.
- `CorrectionRenderer`
  - applies EV + WB correction with protection controls.
- `CacheStore`
  - stores metrics, segments, curves.
- `DebugOverlayRenderer`
  - heat map/graph/split output.

## 12) Pseudocode (v1)
```pseudo
metrics = analyze_frames(clip, sample_rate)
segments = detect_boundaries(metrics, scene_sensitivity)
curves = build_curves(metrics, segments, reference_mode)
curves = smooth_and_clamp(curves, strength, flicker_reduction, protections)

for frame in clip.frames:
    seg = segments.for(frame)
    delta = curves.at(frame)
    corrected = apply_exposure_wb(frame, delta)
    corrected = protect_highlights(corrected, highlight_protection)
    corrected = protect_skin_tones(corrected, skin_priority)
    output(corrected)
```

## 13) Acceptance Criteria
- On static-light shots: visible reduction in slow exposure and WB drift.
- On hard cuts: no cross-cut pumping or baseline contamination.
- On intentional lighting changes: partial/no correction according to sensitivity.
- No visible frame-to-frame pulsing at default settings.
- Graph/debug mode reflects underlying drift trend and applied correction.

## 14) Delivery Plan
### Phase 1: External prototype (macOS app)
- Build analyzer + correction math off-host.
- Emit CSV/JSON metrics and preview corrected exports.

### Phase 2: FxPlug integration
- Wrap correction engine in FxPlug 4 effect.
- Publish controls through Motion for Final Cut Pro use.

### Phase 3: Caching and optimization
- Add persistent cache and minimal invalidation graph.
- Tune GPU kernels and sampling strategy.

### Phase 4: Subject-aware extension (optional)
- Add Vision/Core ML face/subject weighting.
- Add “protect practical lights/window regions” heuristics.

## 15) Risks and Mitigations
- **Over-correction risk:** default conservative strength and hard clamps.
- **False positives on intent:** scene sensitivity + user override + debug graph.
- **Playback performance:** async analysis, cache reuse, scalable quality modes.
- **Color pipeline mismatch:** define and enforce a single internal working space.
