# Senior Project Proposal: Approximation First Telemetry with Mergeable Quantile Summaries

**Zihad Patwary**

CSC 59866, Senior Project I. November 4, 2026.

## Summary

This project will measure how accurately mergeable quantile summaries answer fleet level monitoring questions when data is split across many nodes, skewed and bursty, under a fixed memory budget. It is a one student slice of NSF award 2544434, Approximation First Telemetry for Hyperscale Networked Systems (University of Maryland, College Park), covering only the first two research thrusts.

I will partition public telemetry data across simulated nodes, summarize locally, merge the summaries, and compare three approaches against exact answers: exact aggregation, uniform sampling and mergeable sketches (KLL, DDSketch and t digest). The deliverables are an error versus memory study, a minimal sketch I implement myself, and a decision guide for which summary fits which data shape.

## Problem

A correct fleet level percentile cannot be built from per host percentiles, and shipping every raw measurement to one place costs too much. The NSF abstract states the general issue: data about traffic, resource use and failures can be too large to analyze in full, especially when operators need answers in real time.

Normal behavior: an operator watches request latency across thousands of servers and asks for the fleet p99, the latency that 99 percent of requests beat. Each host can compute its own p99, but averaging those numbers gives a wrong fleet p99, because hosts serve different request counts with different traffic shapes.

What goes wrong depends on the workaround:

1. Exact aggregation: send and store every measurement. Bandwidth, storage and query cost grow with the data volume.
2. Uniform sampling: keep a random fraction. Rare slow requests are barely sampled, so the tail estimate is noisiest exactly where operators look.
3. Summaries without merge guarantees: combine local summaries that were not designed to merge, or whose error is not tracked. The answer arrives with no stated accuracy.

## Who Is Affected

Operators and reliability engineers feel it first, followed by the teams that pay for the monitoring pipeline and the users of the monitored services. In the latency example, a wrong fleet p99 can hide a service level breach or send an engineer chasing a problem that does not exist.

The cost side matters too. Raw telemetry consumes network, storage and compute that the monitored system could use for real work, and the NSF abstract names lower compute, storage and energy as goals of the funded project. Slow or inaccurate answers also delay detection of anomalies, bottlenecks, failures and attacks, which the abstract lists as the operator benefits.

## Evidence and Open Questions

The funded topic alone does not prove my specific failure case, so the first experiment has to demonstrate it on real data. Here is what I have, separated by how solid it is:

- **Documented:** The NSF abstract states the telemetry volume problem. It names mergeable summaries that track uncertainty as thrust one, and fast queries answered directly from summaries as thrust two. Published sketch papers document mergeability and error guarantees, and I must read and verify them (see Sources).
- **My observation:** None yet. Experiment 1 produces it: the gap between averaged per host p99 values and the true fleet p99 on real data.
- **Assumptions:** Public traces resemble production telemetry in skew and burstiness. Splitting a dataset across simulated nodes is a fair stand in for hosts. Merge behavior at hundreds of simulated nodes says something about larger fleets.
- **Missing evidence:** Production telemetry from a real hyperscale fleet, how operators actually set accuracy targets, and real network transfer costs, which I will only count as bytes.

## Existing Approaches

Exact aggregation is the baseline, sampling is the cheap alternative, and three families of mergeable sketch are the serious candidates. Each trades memory for accuracy in a different way, which is what my experiments will measure.

| Approach | How it works | Strength | Limitation under my conditions |
| --- | --- | --- | --- |
| Exact aggregation | Collect every measurement, sort, read the percentile | Exact answer, the reference for all error | Cost grows with data volume; slow for real time answers |
| Uniform sampling | Keep a random fraction of measurements | Simple and easy to merge | Rare slow events are rarely kept, so tail estimates are noisy |
| KLL sketch | Compacting buffers with a rank error bound | Provable rank error; mergeable; in Apache DataSketches | Rank error may mean large relative error far out in a heavy tail |
| DDSketch | Log scaled buckets with a relative error bound | Relative error guarantee suits latency tails; mergeable | Memory depends on the value range; bucket limits trade accuracy for size |
| t digest | Clusters of centroids, finer near the extremes | Accurate at extreme quantiles in practice; mergeable | Accuracy is shown mostly by experiment, not a worst case bound |

These entries are my current reading of the sources and must be checked against the papers before submission.

## Research Question and Hypotheses

The central question is how the error of a merged quantile summary behaves when data is spread across many nodes, skewed and bursty, at a fixed memory budget per node. This is the most important thing I do not yet know, and the answer decides which sketch I would recommend.

I will test three hypotheses, each of which can fail:

1. **H1:** On heavy tailed latency data, a relative error sketch keeps tail quantile error lower than a rank error sketch at the same memory.
2. **H2:** Error after merging many node summaries stays close to the error of one summary built on all the data, for sketches with a stated merge guarantee, but drifts for sketches without one.
3. **H3:** Uneven partition sizes and bursts raise merged error more than the number of nodes does.

Evidence that would change my design: a sketch that breaks down on a data shape I did not expect, or merged error that grows with node count. Either result would redirect the recommendation and the choice of what to implement myself.

## Scope

I will cover mergeable summaries with error tracking and a simple query layer, which map to thrusts one and two of the NSF project, and nothing beyond them. The work is manageable for one student because it is simulation on public data, uses mature open libraries for comparison, and has an exact answer to check every result against.

**Included**

- Quantile summaries built per simulated node, merged, and queried for p50, p90, p99 and p99.9.
- A comparison of exact aggregation, uniform sampling, KLL, DDSketch and t digest on error, memory, merge cost and bytes moved.
- One minimal mergeable relative error sketch implemented by me, validated against a reference library.

**Excluded**

- Learned compression for long term storage (thrust three) and the configuration management engine (thrust four).
- Any claim of true hyperscale. Scale is simulated by partitioning data across nodes, and I will say so plainly.
- Real network deployment, security monitoring and failure propagation across services.

Tentative solution direction: a decision guide that says which summary to use for which data shape and accuracy target, backed by measured results.

Open item: confirm with my professor which course list slot this registers under (A04, A16 or Own Project).

## Method and Experiments

Four experiments move from demonstrating the failure to measuring merged error. Every result is compared with the exact answer computed on the full data.

| Experiment | Question | Setup | Output |
| --- | --- | --- | --- |
| 1. Show the failure | How wrong is an averaged per host p99, and how noisy is sampling in the tail? | Split data across simulated nodes; compare averaged p99, sampled p99 and true p99 | Error table that proves the failure case |
| 2. Single node accuracy | How does error fall as memory grows? | Each sketch at several memory sizes on one data stream | Error versus memory curves per quantile |
| 3. Merge study | Does merged error stay close to single sketch error? | Vary node count, partition skew and burstiness; merge all summaries | Merged error versus node count and skew (tests H2, H3) |
| 4. Query layer | How fast and how big are answers from summaries? | Answer fleet queries from merged summaries versus scanning raw data | Query time and bytes moved |

**Data.** Candidates are a public cluster trace (such as the Google or Alibaba cluster data) and, if my professor approves it, market tick data as a second event stream. Availability and licenses must be checked before I commit. I will add synthetic heavy tailed and bursty streams to stress the sketches.

**Tools.** Python, with libraries for the sketches (Apache DataSketches for KLL, plus DDSketch and t digest packages, to be verified), and a Jupyter notebook for analysis.

**Metrics.** Rank error and relative error at p50, p90, p99 and p99.9, memory in bytes, merge time, and bytes sent compared with raw data.

## Timeline and Deliverables

The design document starts only after the paper is graded and revised, and no experiment is built before it. Graduation is expected in May 2027, so Senior Project II has to finish inside that window. The order below is what matters. Dates follow the course calendar and are not entered yet.

**Senior Project I, this semester**

1. Understanding Paper: five sections plus scope.
2. Graded and revised: required revisions made.
3. Design document: data, sketches and experiments.

**Senior Project II, next semester**

4. Build: simulator and my own sketch.
5. Run experiments: error, memory, merge and query.
6. Final report and demo: decision guide and repo.

**Deliverables**

- Problem Understanding Paper: 1,500 to 2,000 words, five sections plus Your Individual Scope.
- Design document with the chosen dataset, sketches and experiment plan.
- Simulator and a minimal mergeable sketch of my own, in a public repo.
- Results for Experiments 1 to 4, with error versus memory curves.
- Final report with the decision guide.

## Risks and Mitigations

The biggest risk is that the project reads as a rerun of existing libraries, so the contribution has to be the measured merge and skew study. The table lists that risk and the others.

| Risk | Mitigation |
| --- | --- |
| Result looks like a library demo with no failure case | Experiment 1 proves the failure on real data; the contribution is the merge and skew study plus a decision guide |
| Public trace is unavailable, too large or restricted by license | Check licenses first; use a sampled slice; fall back to synthetic streams with documented shapes |
| Simulated nodes do not reflect real fleets | State the limit plainly; test several partition and burst patterns; make no hyperscale claim |
| Scope creep into learned compression or the management engine | Excluded in writing; revisit only after the main results exist |
| Library behavior differs from the papers | Validate my own sketch against the reference library and read the papers directly |
| Registration slot is unconfirmed | Ask my professor to confirm A04, A16 or Own Project before the paper is submitted |

## Sources

Only the first two entries came from my course materials. The rest are leads from memory that I have not opened, so I must verify authors, years, titles and claims before citing any of them.

- [NSF award 2544434, Approximation First Telemetry for Hyperscale Networked Systems](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434), University of Maryland, College Park. Award period June 1, 2026 to May 31, 2031.
- Project repository named in the abstract: frootlab.cs.umd.edu/projectasap
- Agarwal et al., "Mergeable Summaries" (lead).
- Karnin, Lang and Liberty, on optimal quantile approximation in streams, the KLL sketch (lead).
- Masson, Rim and Lee, the DDSketch paper on relative error quantile sketches (lead).
- Dunning and Ertl, on computing accurate quantiles with t digests (lead).
- Apache DataSketches documentation (lead).
