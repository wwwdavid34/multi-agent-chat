/**
 * Discussion Mode Configuration System
 *
 * Defines all available discussion modes with their settings, presets, and UI behavior.
 * This is the single source of truth for mode configuration across the app.
 */

import type { DebateMode, DebateRole } from "../types";

export type DiscussionModeId =
  | "panel"
  | "autonomous"
  | "supervised"
  | "participatory"
  | "business-validation"
  | "decision";

export type ModeCategory = "QUICK" | "STRUCTURED" | "RESEARCH";
export type StanceMode = "free" | "adversarial" | "assigned";

export interface PresetPanelist {
  name: string;
  persona: string;
  /** Optional debate role - if omitted, panelist uses natural persona without stance enforcement */
  role?: DebateRole;
}

export interface DiscussionModeConfig {
  id: DiscussionModeId;
  name: string;
  shortName: string;
  description: string;
  category: ModeCategory;
  icon: string; // SVG path or emoji
  /** Maps to backend debate_mode field (undefined = no debate, just panel responses) */
  debateMode: DebateMode | undefined;
  defaultRounds: number;
  showRoundsConfig: boolean;
  /** If true, mode provides preset panelists that override user's panelists */
  overrideUserPanelists: boolean;
  presetPanelists?: PresetPanelist[];
  /** Stance assignment mode for debates */
  stanceMode?: StanceMode;
  /** Custom moderator prompt for report consolidation */
  moderatorPrompt?: string;
  /** If true, this mode uses the decision assistant endpoint instead of the panel/debate flow */
  isDecisionMode?: boolean;
}

/**
 * All available discussion modes.
 * Order matters - this is the display order in the UI.
 */
export const DISCUSSION_MODES: DiscussionModeConfig[] = [
  // QUICK - Single-round, fast responses
  {
    id: "panel",
    name: "Panel Discussion",
    shortName: "Panel",
    description: "Single round of responses from all panelists",
    category: "QUICK",
    icon: "lightning",
    debateMode: undefined,
    defaultRounds: 1,
    showRoundsConfig: false,
    overrideUserPanelists: false,
  },

  // STRUCTURED - Multi-round debates with different control levels
  {
    id: "autonomous",
    name: "Autonomous Debate",
    shortName: "Auto",
    description: "Runs until consensus or max rounds",
    category: "STRUCTURED",
    icon: "robot",
    debateMode: "autonomous",
    defaultRounds: 3,
    showRoundsConfig: true,
    overrideUserPanelists: false,
    stanceMode: "adversarial",
  },
  {
    id: "supervised",
    name: "Supervised Debate",
    shortName: "Supervised",
    description: "Pause after each round for review",
    category: "STRUCTURED",
    icon: "eye",
    debateMode: "supervised",
    defaultRounds: 3,
    showRoundsConfig: true,
    overrideUserPanelists: false,
    stanceMode: "adversarial",
  },
  {
    id: "participatory",
    name: "Participatory Debate",
    shortName: "Participatory",
    description: "Add your input each round",
    category: "STRUCTURED",
    icon: "hand",
    debateMode: "participatory",
    defaultRounds: 5,
    showRoundsConfig: true,
    overrideUserPanelists: false,
    stanceMode: "adversarial",
  },

  // RESEARCH - Specialized preset panels for specific use cases
  {
    id: "business-validation",
    name: "Business Validation",
    shortName: "Validate",
    description: "Expert panel researches and validates your business idea",
    category: "RESEARCH",
    icon: "briefcase",
    debateMode: undefined, // No debate - independent research then consolidation
    defaultRounds: 1,
    showRoundsConfig: false,
    overrideUserPanelists: true,
    stanceMode: "free",
    moderatorPrompt: `You are a Senior Business Analyst consolidating expert research into a formal validation report.

Respond in the same language the user used.

Review all expert analyses and produce a FORMAL CONSOLIDATED REPORT:

# Business Validation Report

## Executive Summary
[2-3 sentences: Is this viable? Key finding?]

## Financial Analysis

### Cost Structure
| Category | Startup | Monthly | Annual |
|----------|---------|---------|--------|
| [from Cost Analyst findings] |

### Revenue Potential
| Timeframe | Revenue | Customers | Assumptions |
|-----------|---------|-----------|-------------|
| [from Revenue Analyst findings] |

### Unit Economics
| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| CAC | $ | $ | ✓/✗ |
| LTV | $ | $ | ✓/✗ |
| LTV:CAC | X:1 | >3:1 | ✓/✗ |
| Gross Margin | % | >50% | ✓/✗ |
| Break-even | X months | <18mo | ✓/✗ |

## Market Analysis
- **TAM**: $X (realistic)
- **Competition**: [summary]
- **Timing**: [early/right/late]

## Risk Assessment

| Risk Category | Severity | Likelihood | Mitigation |
|---------------|----------|------------|------------|
| [Top 5 risks from all experts] |

## Verdict

| Criteria | Score (1-5) |
|----------|-------------|
| Financial Viability | |
| Market Opportunity | |
| Competitive Position | |
| Execution Feasibility | |
| **OVERALL** | **/5** |

**Recommendation**: [GO / CONDITIONAL GO / NO-GO]

**Critical Next Steps**:
1. [most important action]
2. [second action]
3. [third action]`,
    presetPanelists: [
      {
        name: "Financial_Researcher",
        persona: `You are a Financial Analyst. Research and report on COSTS and REVENUE.
Respond in the user's language.

Produce a research report with these sections:

## Cost Analysis

### Startup Costs (One-time)
| Item | Estimated Cost | Notes |
|------|---------------|-------|
| [itemize all startup costs] |
| **TOTAL** | $X | |

### Operating Costs (Monthly)
| Item | Cost | Notes |
|------|------|-------|
| [itemize: rent, staff, marketing, tech, etc.] |
| **TOTAL MONTHLY BURN** | $X | |

## Revenue Analysis

### Revenue Model
[Describe how this business makes money]

### Pricing
- Proposed price: $X
- Comparable market prices: $X-Y
- Recommended price: $X

### Projections
| Period | Customers | Revenue/Mo | Cumulative |
|--------|-----------|------------|------------|
| Month 1-3 | | | |
| Month 4-6 | | | |
| Month 7-12 | | | |
| Year 2 | | | |

## Break-even Analysis
- Monthly revenue needed: $X
- Customers needed at $Y price: N
- Estimated months to break-even: X

## Financial Risks
1. [risk + impact]
2. [risk + impact]
3. [risk + impact]

Be specific with numbers. Research comparable businesses for benchmarks.`,
      },
      {
        name: "Market_Researcher",
        persona: `You are a Market Research Analyst. Research MARKET SIZE and COMPETITION.
Respond in the user's language.

Produce a research report with these sections:

## Market Size Analysis

### TAM/SAM/SOM
| Metric | Value | Calculation |
|--------|-------|-------------|
| TAM (Total Addressable) | $X | [how calculated] |
| SAM (Serviceable) | $X | [how calculated] |
| SOM (3-year realistic) | $X | [how calculated] |

### Market Trends
- Growth rate: X% annually
- Key drivers: [list]
- Headwinds: [list]

## Competitive Landscape

### Direct Competitors
| Competitor | Revenue/Size | Strengths | Weaknesses |
|------------|--------------|-----------|------------|
| | | | |

### Indirect Alternatives
[What do customers use today instead?]

### Competitive Positioning
- Differentiation: [how is this different?]
- Moat strength: [NONE / WEAK / MODERATE / STRONG]
- Defensibility: [why can't competitors copy this?]

## Market Timing
- Current stage: [emerging / growing / mature / declining]
- Timing assessment: [too early / right time / too late]
- Why: [explanation]

## Market Risks
1. [risk + impact]
2. [risk + impact]
3. [risk + impact]

Research real competitors and market data. Be specific.`,
      },
      {
        name: "Model_Analyst",
        persona: `You are a Business Model Analyst. Evaluate MODEL VIABILITY and UNIT ECONOMICS.
Respond in the user's language.

Produce a research report with these sections:

## Business Model Classification
- Type: [subscription / marketplace / retail / SaaS / etc.]
- Revenue mechanism: [how money flows]
- Value proposition: [what customer pays for]

## Unit Economics

### Customer Economics
| Metric | Estimate | Healthy Benchmark | Assessment |
|--------|----------|-------------------|------------|
| CAC (acquisition cost) | $X | varies | |
| LTV (lifetime value) | $X | >3x CAC | |
| LTV:CAC Ratio | X:1 | >3:1 | |
| Payback Period | X months | <12 months | |

### Transaction Economics
| Metric | Value |
|--------|-------|
| Gross Margin | X% |
| Contribution Margin | X% |
| Net Margin (target) | X% |

## Model Stress Test

### Weaknesses
1. [fundamental flaw]
2. [fundamental flaw]
3. [fundamental flaw]

### Failure Modes
[How could this business model fail?]

### Comparable Failures
| Company | Similar Model | Why Failed |
|---------|---------------|------------|
| | | |

## Model Verdict
- Viability: [WEAK / MODERATE / STRONG]
- Biggest concern: [one sentence]
- Required fix: [what must change for this to work]`,
      },
      {
        name: "Operations_Researcher",
        persona: `You are an Operations Analyst. Research EXECUTION REQUIREMENTS and RISKS.
Respond in the user's language.

Produce a research report with these sections:

## Staffing Requirements

### Team Needed
| Role | Count | Annual Cost | When Needed |
|------|-------|-------------|-------------|
| | | | |
| **TOTAL** | X people | $X/year | |

### Hiring Challenges
[What roles will be hard to fill? Why?]

## Operational Requirements

### Infrastructure
| Need | Cost | Complexity |
|------|------|------------|
| | | |

### Key Processes
[What operational processes must be built?]

### Dependencies
[External dependencies: suppliers, partners, APIs, etc.]

## Timeline Reality

### Milestones
| Milestone | Founder Estimate | Realistic Estimate | Why Longer |
|-----------|------------------|-------------------|------------|
| MVP | | | |
| First customer | | | |
| Break-even | | | |

## Execution Risks

### Risk Matrix
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| | H/M/L | H/M/L | |

### Top 3 Execution Risks
1. [most likely to kill the business]
2. [second most likely]
3. [third most likely]

## Execution Verdict
- Difficulty: [HIGH / MEDIUM / LOW]
- Founder readiness: [assessment]
- Critical gap: [what's missing]`,
      },
    ],
  },

  // STRUCTURED - Decision Assistant (uses separate decision endpoint)
  {
    id: "decision",
    name: "Decision Assistant",
    shortName: "Decision",
    description: "Multi-expert analysis with conflict detection and structured recommendations",
    category: "STRUCTURED",
    icon: "scale",
    debateMode: undefined, // Not a debate — uses /decision-stream endpoint
    defaultRounds: 1,
    showRoundsConfig: false,
    overrideUserPanelists: false,
    isDecisionMode: true,
  },
];

/**
 * Group modes by category for UI display
 */
export const MODES_BY_CATEGORY: Record<ModeCategory, DiscussionModeConfig[]> = {
  QUICK: DISCUSSION_MODES.filter((m) => m.category === "QUICK"),
  STRUCTURED: DISCUSSION_MODES.filter((m) => m.category === "STRUCTURED"),
  RESEARCH: DISCUSSION_MODES.filter((m) => m.category === "RESEARCH"),
};

/**
 * Category display labels
 */
export const CATEGORY_LABELS: Record<ModeCategory, string> = {
  QUICK: "Quick",
  STRUCTURED: "Structured",
  RESEARCH: "Research",
};

/**
 * Get mode config by ID
 */
export function getModeConfig(
  modeId: DiscussionModeId | undefined
): DiscussionModeConfig | undefined {
  if (!modeId) return undefined;
  return DISCUSSION_MODES.find((m) => m.id === modeId);
}

/**
 * Get default mode config
 */
export function getDefaultMode(): DiscussionModeConfig {
  return DISCUSSION_MODES[0]; // Panel mode
}

/**
 * Check if a mode has preset panelists
 */
export function hasPresetPanelists(modeId: DiscussionModeId): boolean {
  const mode = getModeConfig(modeId);
  return Boolean(mode?.overrideUserPanelists && mode?.presetPanelists?.length);
}

/**
 * Get icon path for mode
 * Returns SVG path data for common icons
 */
export function getModeIconPath(icon: string): string {
  const icons: Record<string, string> = {
    // Lightning bolt - quick/instant
    lightning: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    // Robot - autonomous
    robot: "M12 2a2 2 0 0 1 2 2v2h4a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4V4a2 2 0 0 1 2-2z M9 12a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z M15 12a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z",
    // Eye - supervision
    eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    // Raised hand - participation
    hand: "M18 10v-4c0-1.1-.9-2-2-2s-2 .9-2 2v4h-2V5c0-1.1-.9-2-2-2s-2 .9-2 2v9l-2.3-2.3c-.4-.4-.9-.6-1.5-.6-1.1 0-2 .9-2 2 0 .5.2 1 .6 1.4l4.2 4.2c1.5 1.5 3.5 2.3 5.5 2.3H14c2.8 0 5-2.2 5-5v-5c0-1.1-.9-2-2-2s-2 .9-2 2z M14 10V4c0-1.1-.9-2-2-2s-2 .9-2 2v10",
    // Briefcase - business
    briefcase:
      "M20 7h-4V5c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2z M10 5h4v2h-4V5z",
    // Scale - decision/balance
    scale:
      "M12 3v18M3 7l9-4 9 4M3 7v4a9 9 0 0 0 9 0 9 9 0 0 0 9 0V7",
    // Fallback - chat bubble
    default:
      "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  };
  return icons[icon] || icons.default;
}
