# Chess Metrics Explained

## The Four Metrics (PV, MV, OV, DV)

### 1. PV - Piece Value (Material)
**What it measures:** Total value of all pieces on the board

**Values:**
- Pawn = 1
- Knight = 3
- Bishop = 3
- Rook = 5
- Queen = 9
- King = 0 (not counted)

**Example:**
- Starting position: PV_white = 39, PV_black = 39
- After White loses a pawn: PV_white = 38, PV_black = 39
- Delta: dPV = -1 (White is down material)

**Strategy:** Higher PV = more material = better position (usually)

### 2. MV - Mobility Value
**What it measures:** Number of legal moves available

**Calculation:**
- Count all legal moves for all pieces
- Includes captures, normal moves, castling, en passant
- Does NOT deduplicate (same square attacked by multiple pieces counts multiple times)

**Example:**
- Starting position: MV_white = 20, MV_black = 20
- After e2-e4: MV_white might increase (bishop and queen freed)
- More mobility = more options = better position

**Strategy:** Higher MV = more tactical flexibility

### 3. OV - Offensive Value
**What it measures:** Number of squares attacked in opponent's territory

**Calculation:**
- Count attacks on opponent's half of the board (ranks 5-8 for White, ranks 1-4 for Black)
- Includes all attacked squares, even if occupied by own pieces
- Multiplicity counts (same square attacked multiple times counts multiple times)

**Example:**
- Opening: Low OV (pieces not yet attacking opponent's side)
- Middlegame: High OV (pieces actively attacking)
- Higher OV = more aggressive position

**Strategy:** Higher OV = more pressure on opponent

### 4. DV - Defensive Value
**What it measures:** Defensive coverage of friendly pieces

**Calculation:**
- For each friendly piece, count how many other friendly pieces can defend it
- Uses **square root of piece value** for more realistic scaling
- Piece values: Pawn=1, Knight=3, Bishop=3, Rook=5, Queen=9
- Defense values: Pawn=1.0, Knight=1.73, Bishop=1.73, Rook=2.24, Queen=3.0
- Multiplicity counts (same piece defended by multiple pieces counts multiple times)

**Why square root?**
- Defending a queen is important, but not 9x more important than a pawn
- sqrt(9) = 3.0 means queen defense is 3x more valuable (more realistic)
- Encourages distributed defense across multiple pieces
- Prevents DV from dominating other metrics

**Example:**
- Opening: High DV (pieces protecting each other)
- After castling: DV often increases (king safety)
- Defending 1 queen + 1 pawn: sqrt(9) + sqrt(1) = 4.0 DV
- Defending 2 rooks: sqrt(5) + sqrt(5) = 4.48 DV (valued higher!)

**Strategy:** Higher DV = better defense

## Delta Metrics (dPV, dMV, dOV, dDV)

**Formula:** `delta = White_value - Black_value`

**Interpretation:**
- Positive delta: White has advantage in this metric
- Negative delta: Black has advantage in this metric
- Zero delta: Equal in this metric

**Examples:**
```
dPV = +3  → White is up 3 points of material (e.g., won a knight)
dMV = -5  → Black has 5 more legal moves than White
dOV = +10 → White is attacking 10 more squares in Black's territory
dDV = -2  → Black is defending 2 more squares in their territory
```

## Reading the Metrics Table

### Example Row:
```
#    Move     SAN        dPV   dMV   dOV   dDV |  PVw  MVw  OVw  DVw  PVb  MVb  OVb  DVb
1    e2e4     e4          +0   +10    +0    -4 |   39   30    0   31   39   20    0   35
```

**Interpretation:**
- **Move:** e2e4 (pawn to e4)
- **SAN:** e4 (standard notation)
- **dPV = +0:** No material change (no captures)
- **dMV = +10:** White gains 10 more moves than Black (opened up bishop and queen)
- **dOV = +0:** No change in offensive pressure
- **dDV = -4:** White's defense decreased by 4 (pawn moved forward, less defense)
- **PVw = 39:** White still has all pieces (39 points)
- **MVw = 30:** White now has 30 legal moves
- **OVw = 0:** White not yet attacking Black's territory
- **DVw = 31:** White defending 31 squares in own territory
- **PVb = 39:** Black still has all pieces
- **MVb = 20:** Black has 20 legal moves
- **OVb = 0:** Black not yet attacking White's territory
- **DVb = 35:** Black defending 35 squares in own territory

## Strategic Insights

### Opening Principles
- **MV:** Develop pieces to increase mobility
- **DV:** Maintain good defensive structure
- **OV:** Start building pressure (usually low in opening)
- **PV:** Don't lose material unnecessarily

### Middlegame Principles
- **MV:** Keep pieces active and flexible
- **OV:** Increase attacks on opponent's position
- **DV:** Maintain king safety
- **PV:** Look for tactical opportunities to win material

### Endgame Principles
- **PV:** Material advantage becomes critical
- **MV:** King mobility becomes important
- **OV:** Push passed pawns
- **DV:** Less important (fewer pieces to defend)

## Using Metrics to Choose Moves

### Balanced Play (Default Profile)
Look for moves that:
- Maintain or improve material (dPV ≥ 0)
- Increase mobility (dMV > 0)
- Balance offense and defense

### Aggressive Play (Offense-First Profile)
Prioritize:
- High OV (attacking opponent's territory)
- Sacrificing DV for OV (trading defense for attack)
- Tactical complications (high MV)

### Defensive Play (Defense-First Profile)
Prioritize:
- High DV (solid defensive structure)
- Maintaining material (dPV ≥ 0)
- Reducing opponent's mobility (forcing dMV < 0)

### Materialist Play
Prioritize:
- Maximizing dPV (winning material)
- Avoiding sacrifices
- Trading when ahead in material

## Common Patterns

### Good Moves Often Show:
- dPV ≥ 0 (don't lose material)
- dMV > 0 (increase options)
- Positive change in OV or DV (improve position)

### Bad Moves Often Show:
- dPV < 0 (losing material without compensation)
- dMV < 0 (reducing own options)
- Negative change in both OV and DV (weakening position)

### Sacrifices Show:
- dPV < 0 (giving up material)
- dMV or dOV significantly positive (compensation in activity)

## Limitations

1. **No Checkmate Detection:** Metrics don't directly measure checkmate threats
2. **No Pawn Structure:** Doesn't evaluate doubled pawns, isolated pawns, etc.
3. **No King Safety:** DV is a proxy but not a complete measure
4. **No Piece Coordination:** Doesn't measure how well pieces work together
5. **Multiplicity:** Same square attacked multiple times counts multiple times (by design)

## Tips for Using Metrics

1. **Don't Rely on One Metric:** Look at all four together
2. **Consider Position Type:** Opening vs middlegame vs endgame
3. **Watch Trends:** How metrics change over several moves
4. **Compare to Opponent:** Delta values show relative advantage
5. **Use as Guide:** Metrics help, but chess intuition still matters

## Example: Analyzing a Position

```
Current Metrics: PV=+0 MV=+0 OV=+0 DV=+0

Move Options:
1. e2e4:  dPV=+0, dMV=+10, dOV=+0, dDV=-4  → Good: Increases mobility
2. a2a3:  dPV=+0, dMV=-1,  dOV=+0, dDV=+2  → Weak: Decreases mobility
3. Nc3:   dPV=+0, dMV=+2,  dOV=+0, dDV=+16 → Good: Develops and defends
```

**Analysis:**
- e2e4: Best for mobility, slight defensive cost
- a2a3: Passive, loses tempo
- Nc3: Balanced development, strong defense

**Recommendation:** e2e4 or Nc3 depending on style preference

