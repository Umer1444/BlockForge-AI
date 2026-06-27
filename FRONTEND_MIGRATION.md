# Frontend Migration Guide - Minimal UI Changes

## Summary

The frontend requires **minimal UI changes** to support the 15 production-grade upgrades while maintaining the existing Minecraft-themed design system.

## New UI Components (Optional/Additive)

### 1. Detection Mode Selector
**Location**: Before mask drawing
**Component**: Dropdown/Radio group
**Options**: 
- Manual Brush (existing)
- Auto Detect (new)
- Hybrid (new)

```typescript
// Pseudo-code
<DetectionModeSelector
  value="manual" | "auto" | "hybrid"
  onChange={(mode) => setDetectionMode(mode)}
/>
```

**Styling**: Use existing `mc-btn` styles, maintain Minecraft aesthetic

### 2. Confidence Threshold Sliders (Auto Mode Only)
**Location**: Below detection mode selector
**Visible only when mode = "auto"**
**Components**:
- Text Confidence Slider (0.1 - 1.0, default 0.5)
- Logo Confidence Slider (0.1 - 1.0, default 0.4)

```typescript
<ConfidenceThresholds
  textConfidence={0.5}
  logoConfidence={0.4}
  onTextChange={(val) => setTextConfidence(val)}
  onLogoChange={(val) => setLogoConfidence(val)}
/>
```

### 3. Preview-Before-Process Button (Auto Mode Only)
**Location**: Below threshold sliders
**Action**: Calls `/api/preview-auto-detect/{job_id}`
**Response**: Shows preview image with detected watermarks highlighted

```typescript
<PreviewDetectionButton
  jobId={jobId}
  onPreviewLoad={(preview) => setDetectionPreview(preview)}
/>
```

**UI**: Full-screen preview modal with detection highlights, confidence scores visible

### 4. Quality Preset Selector
**Location**: Export/Download section
**Default**: "standard"
**Options**: original, highest, high, standard, balanced, web

```typescript
<QualityPresetSelector
  value="standard"
  onChange={(preset) => setQualityPreset(preset)}
/>
```

**Help text**: Show file size estimate for each preset

### 5. Bitrate Preservation Toggle
**Location**: Next to quality preset
**Default**: ON
**Label**: "Preserve Original Bitrate"

```typescript
<PreserveBitrateToggle
  checked={true}
  onChange={(checked) => setPreserveBitrate(checked)}
/>
```

## Updated Request Payload

### Current (Existing)
```typescript
const uploadPayload = {
  job_id: jobId,
  mask_base64: maskData,
  use_enhancement: false,
  crf: 18,
};
```

### Updated (New Fields Optional)
```typescript
const uploadPayload = {
  job_id: jobId,
  mode: "manual" | "auto" | "hybrid",  // NEW
  mask_base64: maskData,  // Optional if auto/hybrid
  text_confidence: 0.5,   // NEW
  logo_confidence: 0.4,   // NEW
  quality_preset: "standard",  // NEW
  preserve_bitrate: true,  // NEW
  use_enhancement: false,
  crf: undefined,  // Auto-calculated from quality_preset
};
```

## UI Flow Updates

### Manual Mode (Existing - No Change)
```
1. Upload Video
2. Draw Mask
3. Click Process
4. Download Result
```

### Auto Mode (New)
```
1. Upload Video
2. Select "Auto Detect" mode
3. Adjust confidence sliders (optional)
4. Click "Preview Detection"
5. Review detected watermarks
6. Click "Process with Detected"
7. Select quality preset
8. Download Result
```

### Hybrid Mode (New)
```
1. Upload Video
2. Select "Hybrid" mode
3. Adjust confidence sliders (optional)
4. Click "Preview Detection"
5. Manually refine (add/remove detections)
6. Click "Process with Refinements"
7. Select quality preset
8. Download Result
```

## No-Change Areas

✅ **Existing functionality preserved**:
- Minecraft theme (colors, fonts, pixel aesthetics)
- Navigation bar and header
- XP progress bar
- Before/after video preview
- History cards
- WebSocket real-time updates
- Responsive grid layout

✅ **Design system unchanged**:
- `mc-btn` button styles
- `mc-panel` panel styling
- Color variables (grass, diamond, gold, etc.)
- Pixel font
- Glowing text effects

## Minimal CSS Classes

Add these optional classes to `globals.css`:

```css
/* Confidence sliders - use existing color scheme */
.slider-container {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}

.slider-label {
  font-family: var(--font-pixel);
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.slider {
  flex: 1;
  accent-color: var(--mc-emerald);
}

/* Detection preview modal */
.detection-preview-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.detection-preview-image {
  max-width: 90vw;
  max-height: 90vh;
  border: 3px solid var(--mc-emerald);
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
}

.detection-confidence-badge {
  position: absolute;
  background: var(--mc-diamond);
  color: white;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 2px;
  font-family: var(--font-pixel);
}
```

## Implementation Order

### Phase 1 (Day 1) - API Integration
- ✅ Update POST /api/process to accept new fields
- ✅ Add optional `mode` parameter (default: "manual")
- ✅ Add optional `quality_preset` parameter (default: "standard")

### Phase 2 (Day 2) - Manual UI Controls
- Add detection mode selector (3 radio buttons)
- Add confidence sliders (visible only in auto/hybrid mode)
- Add quality preset selector
- Update request payload builder

### Phase 3 (Day 3) - Preview Feature
- Add "Preview Detection" button
- Implement preview modal
- Display detection highlights
- Show confidence scores

### Phase 4 (Day 4) - Polish
- Add help tooltips
- File size estimator for quality presets
- Real-time feedback
- Error handling

## Code Structure

```typescript
// components/ProcessPanel.tsx - Main component
export function ProcessPanel() {
  const [detectionMode, setDetectionMode] = useState('manual');
  const [textConfidence, setTextConfidence] = useState(0.5);
  const [logoConfidence, setLogoConfidence] = useState(0.4);
  const [qualityPreset, setQualityPreset] = useState('standard');
  const [preserveBitrate, setPreserveBitrate] = useState(true);
  const [detectionPreview, setDetectionPreview] = useState(null);

  // Existing mask drawing logic...
  
  // New: handle mode selection
  const handleModeChange = (mode) => {
    setDetectionMode(mode);
    if (mode !== 'manual') {
      // Clear manual mask if switching to auto/hybrid
      setMaskData(null);
    }
  };

  // New: generate preview
  const handlePreviewDetection = async () => {
    const response = await fetch(`/api/preview-auto-detect/${jobId}`, {
      method: 'POST',
      body: JSON.stringify({
        text_confidence: textConfidence,
        logo_confidence: logoConfidence,
      }),
    });
    const data = await response.json();
    setDetectionPreview(data);
  };

  // Updated: build process request
  const buildProcessRequest = () => {
    const request = {
      job_id: jobId,
      mode: detectionMode,
      quality_preset: qualityPreset,
      preserve_bitrate: preserveBitrate,
      text_confidence: textConfidence,
      logo_confidence: logoConfidence,
    };

    if (detectionMode === 'manual' && maskData) {
      request.mask_base64 = maskData;
    } else if (detectionMode === 'hybrid' && refinements) {
      request.refinements = refinements;
    }

    return request;
  };

  return (
    <div className="process-panel">
      {/* Detection Mode Selector */}
      <DetectionModeSelector
        value={detectionMode}
        onChange={handleModeChange}
      />

      {/* Show confidence sliders only for auto/hybrid */}
      {detectionMode !== 'manual' && (
        <>
          <ConfidenceSliders
            textConfidence={textConfidence}
            logoConfidence={logoConfidence}
            onTextChange={setTextConfidence}
            onLogoChange={setLogoConfidence}
          />
          <button onClick={handlePreviewDetection}>
            🔍 Preview Detection
          </button>
        </>
      )}

      {/* Existing mask drawing for manual/hybrid */}
      {(detectionMode === 'manual' || detectionMode === 'hybrid') && (
        <MaskCanvas jobId={jobId} onMaskChange={setMaskData} />
      )}

      {/* Quality Settings */}
      <QualityPresetSelector
        value={qualityPreset}
        onChange={setQualityPreset}
      />
      <PreserveBitrateToggle
        checked={preserveBitrate}
        onChange={setPreserveBitrate}
      />

      {/* Existing process button */}
      <button onClick={handleProcess}>
        ⚔️ START FORGING
      </button>

      {/* Detection preview modal (if available) */}
      {detectionPreview && (
        <DetectionPreviewModal
          preview={detectionPreview}
          onClose={() => setDetectionPreview(null)}
        />
      )}
    </div>
  );
}
```

## No New Dependencies

✅ All new UI can use existing libraries:
- React hooks (useState, useEffect)
- Fetch API (already used)
- CSS (add to globals.css)
- No new npm packages needed

## Testing Checklist

- [ ] Detection mode dropdown works
- [ ] Confidence sliders visible in auto/hybrid only
- [ ] Preview button calls API endpoint
- [ ] Detection preview displays correctly
- [ ] Quality preset selector works
- [ ] Bitrate toggle works
- [ ] Process request includes all new fields
- [ ] Existing manual mode still works
- [ ] Design matches Minecraft aesthetic
- [ ] Responsive on mobile/tablet

## Backward Compatibility

✅ **Fully backward compatible**:
- Existing `/api/process` calls still work (defaults to manual mode)
- Old frontend can ignore new response fields
- New frontend works with old backend (though without new features)

---

## Summary

**Total UI changes**: ~5 new optional components
**Breaking changes**: None
**Design impact**: Minimal (1-2 additional control rows)
**Estimated implementation time**: 4-6 hours
**User learning curve**: Low (intuitive controls)
