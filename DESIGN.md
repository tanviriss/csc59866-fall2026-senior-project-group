# Approximation First Telemetry with Mergeable Quantile Summaries

**Author:** Zihad Patwary  
**Course:** CSC 59866  
**Selected project and option:** 04 CAREER: Approximation-First Telemetry for Hyperscale Networked Systems  
**Current assignment:** 1

## Progress note

This is the first version of the document. I started from the course template and wrote Section 1. Working through the example showed me the core difficulty: a fleet p99 cannot be rebuilt from each host's own p99, because the number of requests a host served decides how much it should count. My earlier proposal compared five approaches in four experiments, which is too much for six weeks, so this semester I will compare three ways of answering the fleet p99 against the exact answer. The main open issue is data, since I do not yet know of a public trace with per request latencies and uneven host traffic. There is no reviewer feedback yet. Next I will write the Section 2 requirements and draft the Section 3 comparison of approaches.

## Contents

- [1 Problem research and scope](#1-problem-research-and-scope)
- [2 Requirements and system specification](#2-requirements-and-system-specification)
- [3 Alternatives and selected solution](#3-alternatives-and-selected-solution)
- [4 Architectural design](#4-architectural-design)
- [5 Component design and interfaces](#5-component-design-and-interfaces)
- [6 Data structure design](#6-data-structure-design)
- [7 Algorithm design and execution](#7-algorithm-design-and-execution)
- [8 Failures and security](#8-failures-and-security)
- [9 Implementation and feasibility](#9-implementation-and-feasibility)
- [10 Testing and verification](#10-testing-and-verification)
- [11 Operation maintenance and future work](#11-operation-maintenance-and-future-work)
- [12 Revision history and references](#12-revision-history-and-references)

## 1 Problem research and scope

**Problem and affected people:** Teams that run large online services judge speed with a number called the fleet p99. A p99 is the 99th percentile latency: 99 percent of requests finish faster than it. "Fleet" means all requests from all servers, called hosts, taken together. Each host only sees its own requests, so the fleet number has to be assembled from many hosts, and hosts rarely carry equal traffic. When the assembly is done the cheap way, the number can be badly wrong, and people make decisions on it.

| Who | What they need from the fleet p99 | What a wrong number costs them |
|---|---|---|
| On call engineer | To know whether users are really getting slow responses right now | A false alarm wakes someone for nothing, and a hidden slowdown goes unfixed |
| Service owner | To check the service against its promised latency target | Reports that do not match what users experienced |
| Monitoring platform team | A correct fleet number without storing every request | Exact answers cost bandwidth, storage and query time that grow with traffic |

**Concrete scenario:** In one hour, Host A serves 1,000,000 requests with a local p99 of 50 milliseconds (ms). Host B serves 1,000 requests with a local p99 of 900 ms, perhaps because it is overloaded. The dashboard averages the two local values and shows (50 + 900) / 2 = 475 ms. That crosses a 300 ms alert threshold, so the on call engineer is paged. But Host B served only about 0.1 percent of all requests. If every request is pooled, the true fleet p99 is about 50 ms, so almost no users were slow and the alert was false. The reverse also happens: when one busy host is slow and several small hosts are fast, the average comes out low and hides a slowdown that most users feel. These numbers, including the threshold, are invented to show the effect and are not measurements. Figure 2 below draws the gap.

In one sentence: for an on call engineer reading a fleet dashboard, uneven traffic across hosts makes an averaged fleet p99 wrong, which causes false alarms or missed slowdowns. My project will investigate whether merged quantile sketches, small summaries that hosts can send instead of raw measurements, give a fleet p99 close to the exact answer while using far less memory.

**Current workflow:** Figure 1 shows the steps from measurement to decision as I understand them from the sources in Section 12. I have not watched a real team do this, so the steps are an assumption to confirm.

1. **Record.** Each host times every request it serves.
2. **Report.** Each host sends a report to the monitoring system on a fixed schedule.
3. **Combine.** The monitoring system turns the host reports into one fleet p99. This is where the difficulty occurs.
4. **Display.** The dashboard shows the number and raises an alert if it crosses the target.
5. **Decide.** The engineer investigates, pages a teammate or waits.

![Flowchart of five steps from left to right: Record, Report, Combine, Display and Decide. Step 3, Combine, is outlined in red and labeled as where the workflow fails. An arrow from step 3 leads to a panel listing four ways to combine host reports for the example in Section 1: averaging local p99 values gives 475 ms, a false alarm; shipping every measurement gives about 50 ms exactly but at a cost that grows with traffic; adding up fixed bucket histograms gives near 50 ms with error that depends on the buckets; merging quantile sketches, drawn with a dashed outline as this project, has its error still to be measured.](assets/workflow.png)

**Figure 1.** The current workflow. Whatever step 3 produces is the only number the engineer sees in steps 4 and 5, so an error there passes straight into the decision. The dashed row is the option this project measures.

The sources describe three common ways to do step 3. Averaging each host's p99 is cheap but wrong under uneven traffic. Sending every measurement to one place is exact but costly. Adding up histograms of fixed latency buckets is approximate, and its error depends on where the bucket edges fall. A fourth way, merging quantile sketches, is what this project studies.

This is a distributed systems problem because the hosts are separate machines that share information only by sending messages. No single machine sees every request unless every request is shipped, which is the costly option. Each host must therefore send something smaller, and the design question is what that something should be so the pieces still add up to a correct fleet answer. A host's report can also arrive late or not at all while the others arrive. A fleet number built from only some hosts should say which hosts it covers, and I will return to that case in Section 8.

**Evidence:** The table uses the handbook's labels. Documented means a source states it, and Assumed means I rely on it but have not established it. Nothing is labeled Observed yet, because that starts once the simulation runs.

| Claim | Source | Label |
|---|---|---|
| Precomputed percentiles from separate summaries generally cannot be combined meaningfully, while histogram bucket counts can be added across hosts | [Prometheus documentation](https://prometheus.io/docs/practices/histograms/) | Documented |
| DDSketch can be merged and keeps a relative error guarantee, which sketches with only a rank error guarantee do not give on skewed data | [Masson, Rim and Lee, 2019](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf) | Documented |
| Monitoring data can be too large to analyze in full when operators need answers in real time | [NSF award 2544434](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | Documented. It shows the research motivation, not that my scenario happens |
| The two host scenario reports 475 ms against a true value near 50 ms | Arithmetic on invented numbers | Assumed |
| Real host traffic is uneven enough for averaging to mislead | Not checked yet | Assumed |
| Engineers follow the five steps in Figure 1 | My reading of the sources | Assumed |

![Number line from 0 to 1000 milliseconds. Host A's local p99 is 50 ms and Host B's is 900 ms. The dashboard reports 475 ms, which is 425 ms above the true fleet p99 of about 50 ms. A bar below shows Host A has 99.9 percent of requests and Host B has 0.1 percent.](assets/fleet_p99_gap.png)

**Figure 2.** The scenario on a number line. Averaging gives each host half the weight, but Host B served only 0.1 percent of the requests, so the reported fleet p99 lands far from the true one.

**Six-week contribution:** A Python simulation that splits one stream of request latencies across several hosts with uneven traffic, then answers the fleet p99 three ways: averaging each host's p99, taking a uniform random sample, and merging one DDSketch per host. Each answer is compared with the exact p99 computed from all the data. The measure is relative error at p99, meaning the gap between the estimate and the exact value divided by the exact value, at several memory sizes. One student can do this because it needs one language, an existing open source DDSketch implementation, and public or synthetic data.

**Semester II scope:** The completed project is a decision guide that says which summary suits which data shape and accuracy target, backed by measurements. It adds the KLL and t digest sketches, one minimal mergeable sketch that I write and validate myself, a simple query layer that answers questions from merged summaries, more hosts with bursty and skewed traffic, and a second dataset.

**Exclusions:** The NSF project has four research thrusts. My work sits inside the first, mergeable summaries that track their own error, and in Semester II part of the second, answering queries from summaries. I exclude the third and fourth thrusts, learned compression for long term storage and the engine that turns accuracy and cost goals into settings. I also exclude real network deployment, security monitoring and failure spread across services. I make no claim of true hyperscale: scale is simulated by splitting data across hosts, and the results will say so.

## 2 Requirements and system specification

*Not due yet. To be completed in Assignment 2.*

## 3 Alternatives and selected solution

*Not due yet. Drafted in Assignment 2 and completed in Assignment 3.*

## 4 Architectural design

*Not due yet. To be completed in Assignment 3.*

## 5 Component design and interfaces

*Not due yet. To be completed in Assignment 3.*

## 6 Data structure design

*Not due yet. To be completed in Assignment 4.*

## 7 Algorithm design and execution

*Not due yet. To be completed in Assignment 4.*

## 8 Failures and security

*Not due yet. To be completed in Assignment 4.*

## 9 Implementation and feasibility

*Not due yet. Started in Assignment 3 and refined through Assignment 6.*

## 10 Testing and verification

*Not due yet. Planned in Assignment 4, with results in Assignments 5 and 6.*

## 11 Operation maintenance and future work

*Not due yet. Drafted in Assignment 4 and completed in Assignment 6.*

## 12 Revision history and references

| Revision date | Change to my design | Reason and evidence |
|---|---|---|
| November 6, 2026 | First version from the course template: Section 1, progress note and one open question | My earlier [proposal](ZihadPatwaryProposal.md) was too large for six weeks, so I narrowed it to one comparison. Evidence is the scenario in Figures 1 and 2 and the sources below |

| Open question | Why it matters | Next action |
|---|---|---|
| Is there public data with per request latencies and uneven traffic across hosts? | Invented latencies may not show real skew, so results could look better or worse than reality | Read the Alibaba microservices trace description for response time fields and license terms. If it does not fit, generate synthetic skewed streams and label every result that uses them as synthetic |

**Assistance and reuse:** The document structure comes from the course design document template. Figures 1 and 2 were drawn for this document, and their editable sources are listed below. Outside sources are cited where they are used and listed in References.

### References

| Source | Claim it supports | Status |
|---|---|---|
| Prometheus Authors, [Histograms and summaries](https://prometheus.io/docs/practices/histograms/), Prometheus documentation, accessed November 6, 2026 | Histogram bucket counts can be added across hosts, while precomputed percentiles from summaries generally cannot be combined | Page read and wording checked |
| Charles Masson, Jee E. Rim and Homin K. Lee, [DDSketch: A Fast and Fully-Mergeable Quantile Sketch with Relative-Error Guarantees](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf), PVLDB 12(12), 2019 | DDSketch merges and keeps a relative error guarantee. It is the first sketch I will test | Found in search, full paper not yet read |
| National Science Foundation, [award 2544434, CAREER: Approximation-First Telemetry for Hyperscale Networked Systems](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434), University of Maryland, College Park, award period June 1, 2026 to May 31, 2031 | The research motivation and its four thrusts, used to bound my scope | Abstract read from the course handout. The award page itself did not load for me |
| Alibaba Group, [cluster trace program](https://github.com/alibaba/clusterdata), GitHub repository | A possible public source of response time data | Found, not yet checked for fields or license |

### Supporting media and evidence

| Item | Purpose |
|---|---|
| [assets/workflow.png](assets/workflow.png), with editable sources [assets/workflow.svg](assets/workflow.svg) and [assets/workflow.mmd](assets/workflow.mmd) | Figure 1, the current workflow and where it fails |
| [assets/fleet_p99_gap.png](assets/fleet_p99_gap.png), with editable source [assets/fleet_p99_gap.svg](assets/fleet_p99_gap.svg) | Figure 2, the averaging error for two hosts |

There is no evidence directory yet because nothing has been measured. Simulation output will go in `evidence/` starting in Assignment 5.

### Final document check

- [ ] Terms and examples make the project understandable to a beginner.
- [ ] All twelve sections contain project specific content.
- [ ] Requirements connect to design and tests.
- [ ] Architecture, components, data, and algorithms agree.
- [ ] Targets and plans are separate from observations.
- [ ] Tables, images, pseudocode, references, and evidence links render correctly.
- [ ] Images have alternative text, captions, and readable labels.
- [ ] Run instructions and evidence support reproduction.
- [ ] I am prepared to present my work and orally review the same selected group mate.
- [ ] Remaining work and maintenance needs are explicit.
- [ ] Instructional placeholders are removed from the final submission.
