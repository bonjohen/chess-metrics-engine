# Chess Metrics Engine - Color Coding Improvements

## Overview
Unified color scheme across the web viewer with consistent metric colors and player differentiation using symbols.

## Color Scheme Design

### Metric Colors (Consistent for Both Players)
```
Material (PV):  rgb(59, 130, 246)   - Blue
Mobility (MV):  rgb(34, 197, 94)    - Green
Offense (OV):   rgb(168, 85, 247)   - Purple
Defense (DV):   rgb(249, 115, 22)   - Orange
```

### Player Differentiation

**White:**
- Solid lines (─────)
- Circle markers (●)
- Symbol: ●

**Black:**
- Dashed lines (- - - -)
- Square markers (■)
- Symbol: ■

### Error Colors (Unchanged)
```
Blunders:      #dc3545 (Red)
Mistakes:      #fd7e14 (Orange)
Inaccuracies:  #ffc107 (Yellow)
```

## Changes Made

### 1. Position Metrics Card

**Before:**
```
White                  Black
Material (PV): 25.3    Material (PV): 24.8
Mobility (MV): 15.2    Mobility (MV): 14.9
Offense (OV): 12.1     Offense (OV): 11.8
Defense (DV): 8.5      Defense (DV): 8.2
```

**After:**
```
White ●                Black ■
[Material (PV)]: 25.3  [Material (PV)]: 24.8
[Mobility (MV)]: 15.2  [Mobility (MV)]: 14.9
[Offense (OV)]: 12.1   [Offense (OV)]: 11.8
[Defense (DV)]: 8.5    [Defense (DV)]: 8.2
```

Where `[...]` represents color-coded labels:
- Blue for Material
- Green for Mobility
- Purple for Offense
- Orange for Defense

### 2. Chart Legend

**Enhanced with:**
- Same color for both White and Black per metric type
- Solid lines for White, dashed lines for Black
- Circle markers (●) for White
- Square markers (■) for Black
- Clear visual differentiation

### 3. Chart Header

**Added instructions:**
- "Click legend items to show/hide metrics"
- "White = Solid line ●"
- "Black = Dashed line ■"

### 4. Chart Footer Legend

**Two-column layout:**

**Left column - Metric Colors:**
- [Material (PV)] - Blue badge
- [Mobility (MV)] - Green badge
- [Offense (OV)] - Purple badge
- [Defense (DV)] - Orange badge

**Right column - Error Highlighting:**
- Light red background = Blunder
- Light orange background = Mistake
- Light yellow background = Inaccuracy

## Implementation Details

### Chart Dataset Configuration

Each metric now has:
```javascript
{
    label: 'White PV (Material)',
    borderColor: metricColors.pv,      // Blue
    borderDash: [],                     // Solid line
    pointStyle: 'circle',               // Circle marker
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5
}

{
    label: 'Black PV (Material)',
    borderColor: metricColors.pv,      // Same blue
    borderDash: [5, 5],                 // Dashed line
    pointStyle: 'rect',                 // Square marker
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5
}
```

### CSS Classes

**Metric Labels:**
```css
.metric-pv { background-color: rgb(59, 130, 246); }   /* Blue */
.metric-mv { background-color: rgb(34, 197, 94); }    /* Green */
.metric-ov { background-color: rgb(168, 85, 247); }   /* Purple */
.metric-dv { background-color: rgb(249, 115, 22); }   /* Orange */
```

**Player Symbols:**
```css
.player-symbol {
    font-size: 0.9rem;
    opacity: 0.7;
}
```

**Metric Values:**
```css
.metric-value {
    font-weight: bold;
    font-size: 1.1rem;
}
```

## Benefits

### 1. Visual Consistency
- Same color always means same metric type
- Easy to compare White vs Black for same metric
- Reduces cognitive load

### 2. Clear Differentiation
- Solid vs dashed lines clearly distinguish players
- Different point styles (circle vs square) reinforce distinction
- Symbols (● vs ■) provide additional visual cue

### 3. Professional Appearance
- Color-coded labels look polished
- Consistent design language throughout
- Modern, clean interface

### 4. Better Comprehension
- Instantly identify metric types by color
- Quickly compare same metric across players
- Understand chart at a glance

## Files Modified

1. **src/chess_metrics/web/static/js/game_viewer.js**
   - Updated dataset configuration with unified colors
   - Added borderDash for Black (dashed lines)
   - Added pointStyle differentiation (circle vs rect)
   - Defined metricColors object

2. **src/chess_metrics/web/static/css/style.css**
   - Added .metric-label classes
   - Added .metric-pv, .metric-mv, .metric-ov, .metric-dv
   - Added .metric-value styling
   - Added .player-symbol styling

3. **src/chess_metrics/web/templates/game.html**
   - Updated Position Metrics table with color-coded labels
   - Added player symbols (● for White, ■ for Black)
   - Enhanced chart header with instructions
   - Added two-column legend below chart

## Usage Guide

### Viewing Metrics

1. **Position Metrics Card:**
   - Color-coded labels show metric type
   - Symbols show player (● = White, ■ = Black)
   - Bold values for easy reading

2. **Chart:**
   - Click legend to toggle metrics
   - Solid lines = White
   - Dashed lines = Black
   - Same color = same metric type

3. **Comparing Players:**
   - Look for same color to compare metric
   - Example: Both PV lines are blue
   - White PV = solid blue line with circles
   - Black PV = dashed blue line with squares

## Testing

Server running at: http://localhost:5000

**Test checklist:**
- ✅ Position metrics have color-coded labels
- ✅ Player symbols (● ■) display correctly
- ✅ Chart uses same color for same metric
- ✅ White lines are solid
- ✅ Black lines are dashed
- ✅ White uses circle markers
- ✅ Black uses square markers
- ✅ Legend shows metric colors
- ✅ Error highlighting still works
- ✅ All colors are consistent

