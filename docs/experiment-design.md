# Prospective experiment protocol — no test has been run

## Selection and hypothesis

The pipeline selects the largest proportional dropoff among ordered funnel transitions with at least 100 eligible sessions. This is exploratory prioritization, subject to instrumentation review, uncertainty, expected value, and engineering feasibility—not proof that the largest dropoff is an avoidable defect.

The generated report selects one proposal:

| Observed bottleneck | Candidate change | Learning goal |
|---|---|---|
| Product view → cart | Clarify availability and the add-to-cart action | Does clearer product-page action increase progression? |
| Cart → checkout | Clarify checkout entry and delivery-cost expectations | Does reducing ambiguity increase checkout entry? |
| Checkout → purchase | Improve form guidance and validation messages | Does guidance help users complete checkout? |

Until real data execution, no bottleneck or numerical baseline is asserted.

## Protocol

* **Business hypothesis:** the selected change increases next-stage progression among eligible users without harming downstream purchasing or customer experience.
* **Randomization:** persistent user-level, equally allocated treatment/control; use a stable first-party ID in production when permitted. The dataset's pseudo ID is the available baseline proxy.
* **Control:** current experience. **Treatment:** only the selected product change.
* **Eligibility:** first qualifying exposure during enrollment; exclude internal/test/bot traffic only with validated rules available in the actual implementation. Do not exclude users based on post-assignment behavior.
* **Exposure:** pre-treatment logging of the relevant product/cart/checkout surface; assignment before rendering the change. Audit assigned versus exposed counts by arm. GA4 stage events are a historical exposure proxy, not an existing experiment log.
* **Primary metric:** binary next-stage event strictly after eligibility, during that first eligible session. Analyze one record per randomized user. Keep future repeated sessions out of this primary endpoint.
* **Expected direction:** increase in progression. Use two-sided inference to detect harm too.
* **Guardrails:** user purchase probability and revenue/user on a prespecified mature window; errors, latency, accessibility failures, and refunds require new instrumentation or validated coverage. These are proposed guardrails, not metrics claimed to be observed in this source.
* **Assignment analysis:** intention-to-treat over eligible assigned users, including assigned users with missing exposure telemetry. Resolve missingness through instrumentation QA, not post-treatment filtering.

## Power and enrollment

The baseline uses the first eligible session per user **for the selected transition**, not the ordered-session rate. Historical eligibility uses any occurrence of the immediately preceding event; it does not condition on all earlier funnel stages. The report discloses that distinction.

Calculate a two-sided normal-approximation two-proportion sample size with Cohen's arcsine effect size, 5% alpha, 50/50 allocation, and 80% / 90% power. The default relative MDE is an explicit 10% planning assumption, not expected lift. Reject a baseline of zero/one or an impossible target. Duration divides total users by observed eligible users per calendar day, rounds up to full weeks, and imposes a two-week minimum. Exclude the final source day from baseline collection to reduce endpoint censoring. Holiday traffic, obfuscation, finite-window de-duplication, returning-user saturation, and seasonality mean this is a rough enrollment projection, not a launch-date promise. Long durations should trigger feasibility review.

## Analysis and operations

1. Verify assignment, exposure order, transaction deduplication, and event parity in an A/A or instrumentation test. This source provides no such experiment.
2. Check sample-ratio mismatch against 50/50 with a prespecified chi-square threshold and inspect missing assignments; investigate SRM before interpreting efficacy.
3. Freeze the primary metric, hypothesis, sample target, eligibility, duration and exclusions before launch. Use a fixed horizon; no optional stopping from daily p-value checks. Safety monitoring needs its own prespecified rules.
4. Treat secondary metrics as exploratory; apply a multiplicity procedure if making multiple confirmatory claims. Do not select a winning metric after seeing treatment data.
5. Cover complete weekly cycles and examine prespecified time interactions for novelty. Do not discard an initial week post hoc because it looks inconvenient.
6. Report absolute and relative effect, uncertainty, guardrail evidence, data exclusions, and practical significance together. A null result can justify keeping the current experience.

CUPED is omitted: this dataset does not provide a randomized experiment with a verified pre-treatment covariate. This project does not duplicate attribution or uplift modeling.
