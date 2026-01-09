# Chart Markers Update - W and B Text Markers

## Overview
Updated the chart markers to display "W" and "B" text instead of geometric shapes (circles and squares) for better clarity.

## Changes Made

### 1. Custom Text Marker Function

Created `createTextMarker()` function in `game_viewer.js`:

```javascript
function createTextMarker(text, color, size = 20) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    // Draw background circle
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(size/2, size/2, size/2 - 1, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw border
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Draw text
    ctx.fillStyle = color;
    ctx.font = `bold ${size * 0.6}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, size/2, size/2);
    
    const img = new Image();
    img.src = canvas.toDataURL();
    return img;
}
```

**Features:**
- Creates custom image markers with text
- White background circle
- Colored border matching metric color
- Bold text in center
- Returns Image object for Chart.js

### 2. Marker Generation

Created markers for each metric and player:

```javascript
// Create custom markers
const whiteMarkers = {
    pv: createTextMarker('W', metricColors.pv),
    mv: createTextMarker('W', metricColors.mv),
    ov: createTextMarker('W', metricColors.ov),
    dv: createTextMarker('W', metricColors.dv)
};

const blackMarkers = {
    pv: createTextMarker('B', metricColors.pv),
    mv: createTextMarker('B', metricColors.mv),
    ov: createTextMarker('B', metricColors.ov),
    dv: createTextMarker('B', metricColors.dv)
};
```

**Result:**
- 8 unique markers (4 for White, 4 for Black)
- Each marker color-coded to its metric
- Clear W/B text differentiation

### 3. Updated Dataset Configuration

Changed from geometric shapes to custom markers:

**Before:**
```javascript
pointStyle: 'circle',     // Circle for White
pointRadius: 3,
```

**After:**
```javascript
pointStyle: whiteMarkers.pv,  // W marker
pointRadius: 8,
```

**Changes:**
- White metrics use `whiteMarkers.*` (W text)
- Black metrics use `blackMarkers.*` (B text)
- Increased `pointRadius` from 3 to 8 for better visibility
- Increased `pointHoverRadius` from 5 to 10

### 4. Updated UI Text

**Chart Header:**
```
Before: "White = Solid line ●" | "Black = Dashed line ■"
After:  "White = Solid line with W markers" | "Black = Dashed line with B markers"
```

**Position Metrics:**
```
Before: White ● | Black ■
After:  White [W] | Black [B]
```

Where `[W]` and `[B]` are styled circular badges.

### 5. Player Badges CSS

Added new CSS classes for player badges:

```css
.player-badge {
    display: inline-block;
    width: 24px;
    height: 24px;
    line-height: 24px;
    text-align: center;
    border-radius: 50%;
    font-weight: bold;
    font-size: 0.85rem;
    margin-left: 5px;
    border: 2px solid;
}

.player-badge-white {
    background-color: white;
    color: #333;
    border-color: #333;
}

.player-badge-black {
    background-color: #333;
    color: white;
    border-color: #333;
}
```

## Visual Comparison

### Before (Geometric Shapes)
```
Chart markers:
White PV: ● (blue circle)
Black PV: ■ (blue square)
```

### After (Text Markers)
```
Chart markers:
White PV: (W) in blue circle
Black PV: (B) in blue circle
```

## Benefits

1. **Clearer Identification**
   - "W" and "B" are immediately recognizable
   - No need to remember circle = White, square = Black
   - Text is universal and intuitive

2. **Better Visibility**
   - Larger markers (radius 8 vs 3)
   - Bold text stands out
   - White background provides contrast

3. **Consistent Design**
   - Matches player badges in Position Metrics section
   - Same W/B convention throughout interface
   - Professional appearance

4. **Accessibility**
   - Text is easier to read than shapes
   - Works better for colorblind users
   - Clear even at small sizes

## Files Modified

1. ✅ `src/chess_metrics/web/static/js/game_viewer.js`
   - Added `createTextMarker()` function
   - Created `whiteMarkers` and `blackMarkers` objects
   - Updated all 8 datasets to use custom markers
   - Increased point radius for better visibility

2. ✅ `src/chess_metrics/web/templates/game.html`
   - Updated chart header instructions
   - Changed player symbols from ● ■ to W B badges
   - Updated Position Metrics section

3. ✅ `src/chess_metrics/web/static/css/style.css`
   - Removed `.player-symbol` class
   - Added `.player-badge` classes
   - Added `.player-badge-white` and `.player-badge-black`

## Technical Details

### Canvas-Based Marker Generation

The markers are created using HTML5 Canvas API:
1. Create 20x20 pixel canvas
2. Draw white circle background
3. Draw colored border (metric color)
4. Draw bold text ("W" or "B") in center
5. Convert to data URL
6. Create Image object

### Chart.js Integration

Chart.js accepts Image objects as `pointStyle`:
- Custom images replace default shapes
- Scales with `pointRadius` setting
- Works with hover effects
- Displays in legend

## Testing

**Server running at:** http://localhost:5000

**Test checklist:**
- ✅ Chart shows W markers for White metrics
- ✅ Chart shows B markers for Black metrics
- ✅ Markers are color-coded by metric type
- ✅ Markers are visible and clear
- ✅ Hover effect works (markers enlarge)
- ✅ Legend shows custom markers
- ✅ Position Metrics shows W/B badges
- ✅ All text is consistent

## Summary

**Before:** Circle (●) for White, Square (■) for Black

**After:** "W" text marker for White, "B" text marker for Black

**Result:** Clearer, more intuitive chart markers that are immediately recognizable! 🎯

