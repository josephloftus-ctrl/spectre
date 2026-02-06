# Purchasing & Inventory Analysis Research
## Applied to Spectre/Steady Food Service Platform

---

## Executive Summary

This document synthesizes research on purchasing and inventory analysis methodologies, specifically applied to the **Spectre** (web backend) and **Steady** (iOS mobile) food service inventory management platform. The research covers inventory classification, spend analysis, demand forecasting, variance analysis, and food service-specific practices.

---

## Part 1: Inventory Analysis Methodologies

### 1.1 ABC-XYZ Classification

**What it is:** A dual-axis classification system that categorizes inventory items by value (ABC) and demand predictability (XYZ).

| ABC Axis (Value) | XYZ Axis (Variability) |
|------------------|------------------------|
| **A**: 80% of value, 20% of items | **X**: Stable demand (0-10% variance) |
| **B**: 15% of value, moderate items | **Y**: Fluctuating demand (10-25% variance) |
| **C**: 5% of value, many items | **Z**: Unpredictable demand (25%+ variance) |

**The 9-Box Matrix:**
```
        X (Stable)    Y (Moderate)    Z (Unpredictable)
A (High $)   AX            AY              AZ
B (Med $)    BX            BY              BZ
C (Low $)    CX            CY              CZ
```

**Strategic Actions:**
- **AX items**: Tight control, precise forecasting, automated reordering
- **AY items**: Safety stock buffers, regular review
- **AZ items**: High buffer stock, flexible supply agreements
- **CZ items**: Simplified management, on-demand ordering

#### Application to Spectre/Steady

**Spectre (Backend):**
- Auto-classify items using historical count data and purchase records
- Add ABC-XYZ score to the existing health scoring system
- Surface AX items prominently in dashboards (highest attention)
- Flag AZ items for manual review (high value + unpredictable)
- Use classification to prioritize purchase match validation

**Steady (Mobile):**
- Show ABC classification badges during counts (visual priority)
- Sort count lists by ABC class (A items first)
- Alert users when AZ items show unusual counts
- Canon system items could include default ABC classifications

---

### 1.2 Inventory Turnover Ratio

**Formula:** `Turnover = Cost of Goods Sold (COGS) / Average Inventory`

**Food Service Benchmarks:**
| Rating | Turns/Month | Interpretation |
|--------|-------------|----------------|
| Too Low | < 4 | Overstocking, spoilage risk |
| Optimal | 4-8 | Healthy inventory flow |
| Too High | > 8 | Stockout risk, limited menu |

**Industry average:** 5.9 turns/month for restaurants

#### Application to Spectre/Steady

**Spectre:**
- Calculate turnover per site, per room, per item category
- Add turnover metrics to site health scoring
- Historical trend: "This site's turnover dropped from 6.2 to 4.1 over 8 weeks"
- Benchmark comparison across units: "Site A: 5.8, Site B: 3.2 (needs attention)"
- Alert when turnover deviates significantly from historical norm

**Steady:**
- Show "velocity indicators" during counts (fast/slow movers)
- Flag items that haven't moved since last count
- Weekly summary: "Your turnover this period: 5.4 (healthy)"

---

### 1.3 Days Sales of Inventory (DSI)

**Formula:** `DSI = (Average Inventory / COGS) × Days in Period`

Tells you how many days of inventory you're holding. For perishables, lower is better.

**Benchmarks:**
- Fresh proteins: 2-4 days
- Dairy: 3-7 days
- Dry goods: 14-30 days
- Frozen: 30-60 days

#### Application to Spectre/Steady

**Spectre:**
- Calculate DSI by category/room type
- Flag when DSI exceeds category threshold (walk-in cooler items > 7 days)
- Correlate with spoilage/waste data

**Steady:**
- Zone-aware DSI (walk-in cooler vs. dry storage have different targets)
- Visual warnings when counting items beyond expected DSI

---

## Part 2: Purchasing Analysis

### 2.1 Spend Analysis

**Definition:** The process of collecting, cleaning, classifying, and analyzing procurement data to identify savings opportunities.

**Key Dimensions (Spend Cube):**
1. **Suppliers** - Who are you buying from?
2. **Categories** - What are you buying?
3. **Business Units** - Who is buying?

**Key Metrics:**
| Metric | Description |
|--------|-------------|
| Spend by Category | Breaking down spend by product type |
| Spend by Supplier | Concentration with top vendors |
| Maverick Spend | Purchases outside approved channels |
| Spend Under Management | % actively managed by procurement |
| Price Variance | Difference from contracted/expected prices |

#### Application to Spectre/Steady

**Spectre:**
- Build spend cube from IPS (Invoice Purchasing Summaries) data
- Dashboard: "Top 10 suppliers by spend" with trend arrows
- Alert: "Maverick spend detected - Site B purchased from non-approved vendor"
- "Price variance alert: Chicken breast up 12% vs. contracted rate"
- Supplier consolidation opportunities: "3 sites use different dairy vendors"

**Steady:**
- Show last purchase price during counts for comparison
- Flag when current inventory suggests off-contract purchasing

---

### 2.2 Vendor/Supplier Scorecards

**Core Metrics (weighted):**
| Metric | Typical Weight | Description |
|--------|----------------|-------------|
| On-Time Delivery | 25-30% | % of orders delivered by promised date |
| Quality/Defect Rate | 25-30% | % of items meeting quality standards |
| Price Competitiveness | 15-20% | Comparison to market rates |
| Responsiveness | 10-15% | Communication and issue resolution |
| Compliance | 10-15% | Meets safety, regulatory requirements |

**Scoring Bands:**
- Green: 95%+ (excellent)
- Yellow: 90-94% (acceptable)
- Red: <90% (needs improvement)

#### Application to Spectre/Steady

**Spectre:**
- Auto-generate vendor scorecards from IPS + inventory data
- Track delivery timing from PO to receipt
- Quality: correlate with inventory flags (damaged items, returns)
- Dashboard: Vendor performance trends over time
- Integration: Feed scores back into purchase match recommendations

**Steady:**
- During receiving, capture delivery timing and quality notes
- "Rate this delivery" quick feedback mechanism

---

### 2.3 SKU Rationalization

**What it is:** Strategic review of product portfolio to eliminate underperforming or redundant items.

**Analysis Framework:**
1. Revenue contribution (Pareto: 80/20 rule)
2. Margin contribution
3. Turnover rate
4. Cost to serve (storage, handling complexity)
5. Strategic importance (menu anchors vs. optional items)

**Red Flags for Elimination:**
- Items ordered < 2x in 6 months
- Items with high waste/spoilage rates
- Duplicate items from different vendors
- Items with declining trend

#### Application to Spectre/Steady

**Spectre:**
- "SKU Rationalization Report" - identifies candidates for elimination
- Cross-site analysis: "Item X only used by 1 of 12 sites"
- Savings calculator: "Eliminating 15 slow-moving SKUs saves $X in carrying costs"
- Integration with Purchase Match: flag items with no recent purchases

**Steady:**
- Surface rationalization candidates during site setup
- "This item hasn't been counted in 3 periods - still needed?"

---

## Part 3: Demand Forecasting & Par Level Optimization

### 3.1 Par Level Management

**Formula:** `Par Level = (Average Daily Usage × Lead Time) + Safety Stock`

**Components:**
| Component | Description |
|-----------|-------------|
| Average Daily Usage | Historical consumption rate |
| Lead Time | Days from order to delivery |
| Safety Stock | Buffer for demand variability |

**Adjustment Factors:**
- Seasonality (holiday menus, summer slowdown)
- Day-of-week patterns (Monday vs. Friday)
- Special events (catering, company meetings)
- Menu changes

#### Application to Spectre/Steady

**Spectre:**
- Auto-calculate suggested par levels from historical data
- Machine learning: adjust for day-of-week, seasonality
- Alert when actual inventory significantly differs from par
- "Par Level Optimizer" - suggests adjustments based on patterns

**Steady:**
- Display par levels during counts (already implemented in Canon)
- Variance indicator: under par / at par / above par (already implemented)
- **Enhancement:** Dynamic par suggestions based on historical counts
- "Last 4 counts averaged 12 units; current par is 8 - suggest increase?"

---

### 3.2 Demand Forecasting Methods

**Quantitative Methods:**
| Method | Best For |
|--------|----------|
| Moving Average | Stable demand (X items) |
| Exponential Smoothing | Trending demand |
| Seasonal Decomposition | Cyclical patterns |
| ML/AI Models | Complex multi-variable prediction |

**Qualitative Inputs:**
- Menu changes
- Marketing promotions
- Local events
- Weather forecasts

**B&I-Specific Challenges:**
- Hybrid work unpredictability (53% of workers now hybrid)
- Day-to-day attendance variance
- Seasonal corporate patterns (Q4 busy, summer slow)

#### Application to Spectre/Steady

**Spectre:**
- Time-series analysis on inventory snapshots
- Detect seasonal patterns automatically
- "Forecast Dashboard" - predicted demand for next period
- Integration with external signals (if available): corporate calendar, weather

**Steady:**
- Pre-order integration (if B&I clients use meal ordering)
- Historical pattern display: "Mondays typically use 20% less"

---

## Part 4: Variance Analysis

### 4.1 Actual vs. Theoretical (AvT) Food Cost

**Formula:** `Variance = Actual Food Cost % - Theoretical Food Cost %`

**Theoretical Food Cost:** What costs *should* be based on:
- Recipe costs × items sold
- Perfect portions
- No waste/theft/spoilage

**Actual Food Cost:** What you actually spent based on inventory movement.

**Benchmark:** Variance should be < 2%. Each 1% variance = significant profit loss.

**Common Variance Causes:**
| Cause | Detection Method |
|-------|------------------|
| Overportioning | Compare actual vs. recipe yields |
| Theft | Unexplained shrinkage patterns |
| Spoilage | Waste logs, expiration tracking |
| Receiving errors | PO vs. actual received |
| Price variance | Contract vs. invoice prices |
| Recipe non-compliance | Audit checks |

#### Application to Spectre/Steady

**Spectre:**
- Calculate theoretical cost from recipes + sales data (requires POS integration)
- AvT report by site, by category, by item
- Drill-down: "Chicken variance is 4.2% - investigate"
- Root cause suggestions based on patterns
- Trend tracking: "Variance increasing over 4 weeks"

**Steady:**
- Waste logging during/after counts
- "Flag" system for noting issues (already exists - damaged, expired, etc.)
- Enhancement: Structured waste capture for analysis

---

### 4.2 Inventory Count Variance

**Formula:** `Count Variance = System Quantity - Physical Count`

**Causes:**
- Receiving errors (wrong quantity delivered)
- Unrecorded usage
- Theft/shrinkage
- Counting errors
- Data entry mistakes

**Accuracy Target:** 97%+ item/location accuracy

#### Application to Spectre/Steady

**Spectre:**
- Track count-to-count variance trends
- Flag sites with high variance for investigation
- Pattern detection: "Proteins consistently under-counted at Site C"
- Already partially implemented via "drift detection" and health scoring

**Steady:**
- Show previous count during entry (already implemented)
- Require confirmation for large variances
- Enhancement: Photo capture for unusual variances

---

## Part 5: Food Service-Specific Practices

### 5.1 FIFO (First-In, First-Out)

**Principle:** Use oldest inventory first to minimize spoilage.

**Implementation:**
- Date labeling on all items
- Storage organization (new items behind old)
- Staff training on rotation

**Impact:** Proper FIFO can reduce waste by 15-25%

#### Application to Spectre/Steady

**Spectre:**
- Track item age based on receiving dates
- Flag items approaching expiration
- "FIFO compliance score" based on usage patterns

**Steady:**
- Zone organization guidance (Canon system can suggest shelf arrangement)
- Date checking prompts during counts
- "Expiration alert" for items past expected shelf life

---

### 5.2 Waste Tracking Categories

**Standard Waste Categories:**
| Category | Description |
|----------|-------------|
| Spoilage | Expired, rotted items |
| Overproduction | Made too much, couldn't sell |
| Plate Waste | Customer leftovers |
| Prep Waste | Trimmings, unusable portions |
| Spillage | Accidents, drops |
| Theft | Unexplained disappearance |

**Tracking Frequency:** Daily waste logs recommended

#### Application to Spectre/Steady

**Spectre:**
- Waste tracking module with categorization
- Waste trends by site, category, day-of-week
- Cost impact calculation: "This week's waste = $X"
- Correlation with inventory variance

**Steady:**
- Quick waste logging during counts
- Enhancement: "Log waste" action with category selection
- Photo capture for waste documentation

---

### 5.3 Cycle Counting Best Practices

**Frequency by Category:**
| Item Type | Count Frequency |
|-----------|-----------------|
| A items (high value) | Weekly |
| B items (moderate) | Bi-weekly |
| C items (low value) | Monthly |
| Perishables | More frequent regardless of value |

**Food Service Recommended Approach:**
- Daily spot checks on high-value proteins
- Weekly zone-based counts (Steady's model)
- Monthly full inventory audit
- Quarterly comprehensive review

#### Application to Spectre/Steady

**Spectre:**
- Count scheduling recommendations based on ABC classification
- Track count frequency compliance by site
- "Counting health" score in site dashboard

**Steady:**
- Count scheduling reminders
- ABC-based count prioritization in zone lists
- "You haven't counted proteins in 8 days" alerts

---

## Part 6: Multi-Unit Benchmarking

### 6.1 Cross-Site Comparison Metrics

**Key Benchmarks:**
| Metric | Target Range |
|--------|--------------|
| Food Cost % | 25-35% of revenue |
| Prime Cost % | < 55-60% |
| Inventory Turnover | 4-8x/month |
| Count Accuracy | 97%+ |
| AvT Variance | < 2% |
| Waste % | < 4-6% of COGS |

**Comparison Approaches:**
- Rank sites by each metric
- Identify outliers (top and bottom performers)
- Share best practices from top performers
- Target bottom quartile for intervention

#### Application to Spectre/Steady

**Spectre:**
- Multi-unit dashboard with side-by-side comparison
- "Leaderboard" view ranking sites by key metrics
- "Peer comparison" - similar sites benchmarked together
- Outlier detection: "Site F is 2 standard deviations above average waste"
- Best practice identification: "Site A has lowest variance - review their process"

**Steady:**
- Site comparison in session completion summary
- "Your site vs. fleet average" context

---

## Part 7: Feature Recommendations

### 7.1 High-Priority Enhancements for Spectre

1. **ABC-XYZ Classification Engine**
   - Auto-classify items based on value + variability
   - Integrate into health scoring
   - Drive count prioritization

2. **Spend Analysis Dashboard**
   - Spend cube visualization (supplier × category × site)
   - Maverick spend detection
   - Price variance alerts

3. **Vendor Scorecard Module**
   - Auto-generate from IPS data
   - On-time delivery tracking
   - Quality correlation with inventory flags

4. **AvT Variance Calculator**
   - Theoretical cost from recipes (requires recipe data)
   - Comparison with actual (from inventory movement)
   - Root cause drill-down

5. **Par Level Optimizer**
   - ML-based par suggestions
   - Seasonal adjustment
   - Lead time factoring

6. **Multi-Unit Benchmarking Dashboard**
   - Site ranking by key metrics
   - Outlier detection
   - Best practice identification

### 7.2 High-Priority Enhancements for Steady

1. **ABC Classification Badges**
   - Visual indicators during counts
   - Priority sorting in zone item lists

2. **Dynamic Par Suggestions**
   - Based on historical count patterns
   - "Suggest par adjustment" prompts

3. **Structured Waste Logging**
   - Category selection (spoilage, overproduction, etc.)
   - Photo capture
   - Feeds into Spectre analysis

4. **Variance Confirmation Flow**
   - Require explanation for large variances
   - Photo capture option
   - Root cause selection

5. **Count Scheduling Intelligence**
   - ABC-based reminders
   - "Proteins need counting" alerts
   - Compliance tracking

### 7.3 Integration Opportunities

1. **POS Integration** (for AvT calculation)
   - Sales data for theoretical cost
   - Recipe depletion tracking

2. **Receiving Module**
   - Capture delivery timing for vendor scoring
   - PO vs. actual comparison
   - Quality notes

3. **Pre-Order Integration** (B&I specific)
   - Demand signal from employee orders
   - Same-day production planning

---

## Part 8: Research Sources

### Inventory Analysis
- [ABC Analysis - NetSuite](https://www.netsuite.com/portal/resource/articles/inventory-management/abc-inventory-analysis.shtml)
- [ABC-XYZ Analysis for Restaurants - Syrve](https://www.syrve.com/en-gb/blog/restaurant-abc-xyz-analysis-syrve)
- [ABC-XYZ Complete Guide - AbcSupplyChain](https://abcsupplychain.com/abc-xyz-analysis/)
- [9-Box Model Classification - Intelichain](https://inteli-chain.com/the-9-box-model-abc-xyz-classification-in-demand-planning/)

### Inventory Turnover
- [Restaurant Inventory Turnover - Toast](https://pos.toasttab.com/blog/how-to-calculate-inventory-turnover-ratio-in-your-restaurant)
- [Average Turnover Ratio - Sculpture Hospitality](https://www.sculpturehospitality.com/blog/average-inventory-turnover-ratio-for-restaurant-food)
- [Inventory Metrics - Apicbase](https://get.apicbase.com/restaurant-inventory-metrics/)

### Spend Analysis & Procurement
- [Spend Analysis 101 - Sievo](https://sievo.com/en/resources/spend-analysis-101)
- [Spend Analysis Guide - SAP](https://www.sap.com/resources/guide-to-spend-analysis)
- [Procurement KPIs - NetSuite](https://www.netsuite.com/portal/resource/articles/erp/procurement-kpis.shtml)

### Vendor Scorecards
- [Supplier Scorecard Guide - Ramp](https://ramp.com/blog/supplier-scorecard-metrics)
- [Vendor Scorecard Best Practices - Ivalua](https://www.ivalua.com/blog/vendor-scorecard/)
- [Vendor Management KPIs - Gatekeeper](https://www.gatekeeperhq.com/blog/how-to-track-the-performance-of-your-key-vendors)

### Par Levels & Forecasting
- [Par Level Inventory - 5-Out](https://www.5out.io/post/what-is-par-level-inventory-in-restaurants)
- [Par Level Guide - WISK](https://www.wisk.ai/blog/a-wisks-guide-what-are-par-level-inventory)
- [Demand Forecasting - Balloonone](https://balloonone.com/blog/the-complete-guide-to-demand-forecasting-in-the-food-industry/)

### Food Cost Variance
- [AvT Food Cost Variance - Crunchtime](https://www.crunchtime.com/blog/blog/explaining-actual-vs-theoretical-food-cost-variance)
- [Food Cost Variance Control - Toast](https://pos.toasttab.com/blog/on-the-line/food-cost-variance)
- [Variance Management - MarketMan](https://www.marketman.com/blog/how-to-control-food-cost-variance-to-improve-operations-and-increase-revenue)

### Waste & FIFO
- [FIFO Guide - FoodDocs](https://www.fooddocs.com/post/fifo-food)
- [Food Waste Reduction - DiningAlliance](https://diningalliance.com/blog/smart-inventory-management-a-key-to-reducing-food-waste-and-controlling-costs/)
- [Inventory Best Practices - Altametrics](https://altametrics.com/blog/5-best-practices-for-food-inventory-management-to-reduce-waste/)

### Multi-Unit Benchmarking
- [Restaurant Benchmarks - NetSuite](https://www.netsuite.com/portal/resource/articles/erp/restaurant-benchmarks.shtml)
- [Multi-Location Comparison - Restaurant365](https://www.restaurant365.com/blog/how-to-compare-performance-across-multiple-restaurant-locations/)
- [COGS Benchmarks - Fortesg](https://fortesg.com/blog/restaurant-cogs-benchmarks-and-how-to-improve-them)

### B&I/Institutional Food Service
- [B&I Challenges - Foodservice Equipment & Supplies](https://fesmag.com/topics/trends/4915-bi-bouncing-back)
- [Corporate Dining Crisis - Jitjatjo](https://news.jitjatjo.com/post/the-corporate-cafeteria-crisis-how-flex-staffing-can-save-b-i-foodservice)

### Cycle Counting
- [Cycle Counting 101 - NetSuite](https://www.netsuite.com/portal/resource/articles/inventory-management/using-inventory-control-software-for-cycle-counting.shtml)
- [F&B Cycle Counting - Zastro](https://zastro.com/maximizing-efficiency-and-accuracy-in-food-beverage-manufacturing-best-practices-for-cycle-inventory-counting/)

---

*Document generated: January 2026*
*For: Spectre/Steady Food Service Platform*
