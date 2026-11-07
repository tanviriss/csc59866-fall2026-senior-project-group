# Approximation First Telemetry with Mergeable Quantile Summaries

**Author:** Zihad Patwary  
**Course:** CSC 59866  
**Selected project and option:** NSF project 04, Approximation First Telemetry for Hyperscale Networked Systems (course slot to confirm: A04, A16 or Own Project)  
**Current assignment:** 1  
**Friday commit deadline:** November 6, 2026, at 11:59 p.m. New York time  
**Monday presentation:** November 9, 2026, at 6:30 p.m. New York time  
**Last updated:** November 6, 2026  
**Document status:** Proposed

## Progress note

This first version covers Section 1 only. While writing the worked case I learned that a fleet p99 cannot be rebuilt from per host p99 values, because request counts decide each host's weight. My [earlier proposal](ZihadPatwaryProposal.md) compared five approaches across four experiments, which is too much for this semester, so I narrowed the six week work to one comparison: averaged p99, a uniform sample and merged DDSketch summaries, each judged by relative error against the exact answer. The main open issue is whether public data exists with per request latencies and uneven host loads. No reviewer feedback exists yet, so none is addressed. Next I will write the Section 2 requirements and compare the candidate approaches in Section 3. Evidence so far is the worked case in Figure 1 and the sources in Section 12.

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

**Problem and affected people:** Engineers who run large online services watch one number to judge speed: the fleet p99, the latency that 99 percent of all requests beat. The difficulty is that each host measures its own requests, and the fleet number has to be assembled from many hosts that carry very different loads. If the assembly is wrong, the number is wrong, and people act on it.

| Who | How they use the fleet p99 | What goes wrong |
|---|---|---|
| On call reliability engineer | Decides whether an alert is real and whether to wake someone | An averaged value can invent a slowdown or hide a real one |
| Service owner | Checks the service against a latency target | Reports a number that does not match what users experienced |
| Monitoring platform team | Runs the pipeline that collects and stores measurements | Keeping every request is accurate but costs bandwidth, storage and query time |

**Concrete scenario:** Two hosts serve one hour of traffic. Host A serves 1,000,000 requests and its local p99 is 50 ms. Host B serves 1,000 requests and its local p99 is 900 ms. A dashboard averages the two local values and reports (50 + 900) / 2 = 475 ms. Host B handles only about 0.1 percent of the requests, so the real fleet p99 stays close to Host A's, about 50 ms. The report is roughly 9.5 times too high, and an engineer may chase a slowdown that is not there. The numbers are chosen for illustration and are not measured. The opposite mistake also happens when a busy host hides a small slow one.

![Number line from 0 to 1000 milliseconds. Host A's local p99 is 50 ms and Host B's is 900 ms. The dashboard reports 475 ms, which is 425 ms above the true fleet p99 of about 50 ms. A bar below shows Host A has 99.9 percent of requests and Host B has 0.1 percent.](assets/fleet_p99_gap.png)

**Figure 1.** Averaging gives each host half the weight, but Host B serves only 0.1 percent of the requests, so the reported fleet p99 lands far from the true one.

**Current workflow:** I have not observed a specific company's pipeline. Based on the sources in the Evidence table, there are three common routes from host measurements to a fleet number, and each has a catch. The difficulty occurs at the step where per host results are combined.

1. **Average the local p99 values.** Each host computes its own p99 and a central system averages them. This is cheap, but it is wrong when hosts carry different loads.
2. **Ship every measurement.** One place stores all requests and computes the p99 directly. The answer is exact, but the cost grows with traffic.
3. **Merge fixed bucket histograms.** Hosts report counts per latency bucket, which can be added across hosts. The result is approximate, so the bucket layout matters. I still need to verify how much in Section 3.

Figure 2 shows the three routes for the same two hosts, with a fourth route, merging mergeable sketches, as the part this project adds.

![Flowchart. Host A (1,000,000 requests, local p99 50 ms) and Host B (1,000 requests, local p99 900 ms) feed four ways to combine them. Route 1, averaging local p99 values, gives 475 ms, about 9.5 times too high. Route 2, shipping every measurement, gives about 50 ms exactly but costs more as traffic grows. Route 3, merging fixed bucket histograms, gives close to 50 ms with error that depends on the bucket layout. Route 4, merging mergeable sketches such as DDSketch, is drawn with a dashed outline as the project's focus, with its result still to be measured.](assets/fleet_p99_workflow.png)

**Figure 2.** Four ways to combine per host measurements into a fleet p99, and what each gives for the Figure 1 example. The dashed boxes mark what this project adds and measures.

**Evidence:** The table separates what the sources document from what I have only illustrated or assumed.

| Claim | Source | Status |
|---|---|---|
| Percentile values from separate hosts cannot simply be averaged. Prometheus says aggregating a summary's precomputed quantiles rarely makes sense, while histograms can be aggregated | [Prometheus documentation](https://prometheus.io/docs/practices/histograms/) | Documented |
| Rank error guarantees can still allow large relative errors on skewed data. DDSketch is fully mergeable with a relative error guarantee | [Masson et al., 2019](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf) | Documented |
| Telemetry data can be too large to analyze in full when operators need real time answers, which motivates mergeable summaries | [NSF award 2544434](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | Documented. It shows funded interest, not that my case occurs |
| An averaged p99 misleads in the two host case above | Arithmetic on chosen numbers | Illustration. Nothing measured yet |
| Real host loads are uneven enough for the average to mislead | Not yet checked | Assumed |
| Merged sketches stay close to the exact answer at a small memory size | Not yet tested | Assumed |

**Six-week contribution:** I will build a small Python simulation that splits one latency stream across hosts with uneven loads. It compares three ways of answering the fleet p99: the average of per host p99 values, a uniform random sample, and merged DDSketch summaries. Each is measured against the exact p99 from all the data, using relative error at p99, at several memory sizes. This is manageable for one person because it needs one language, a public or synthetic latency stream, and an existing DDSketch implementation.

**Semester II scope:** The goal is a decision guide for which summary suits which data shape. It adds KLL and t digest sketches, one minimal mergeable sketch that I write and validate myself, a simple query layer, a merge study with more nodes and bursty, skewed data, and a second dataset.

**Exclusions:** Learned compression for long term storage, the configuration management engine, real network deployment, security monitoring, failure propagation across services, and any claim of true hyperscale. Scale is simulated by splitting data across nodes, and I will say so plainly.

## 2 Requirements and system specification

*Not started. Due in Assignment 2.*

## 3 Alternatives and selected solution

*Not started. Draft due in Assignment 2, completed in Assignment 3.*

## 4 Architectural design

*Not started. Due in Assignment 3.*

## 5 Component design and interfaces

*Not started. Due in Assignment 3.*

## 6 Data structure design

*Not started. Due in Assignment 4.*

## 7 Algorithm design and execution

*Not started. Due in Assignment 4.*

## 8 Failures and security

*Not started. Due in Assignment 4.*

## 9 Implementation and feasibility

*Not started. Begins in Assignment 3.*

## 10 Testing and verification

*Not started. Planned in Assignment 4.*

## 11 Operation maintenance and future work

*Not started. Drafted in Assignment 4.*

## 12 Revision history and references

| Revision date | Change to my design | Reason and evidence |
|---|---|---|
| November 6, 2026 | First version: Section 1, progress note and one open question | Narrowed the earlier [proposal](ZihadPatwaryProposal.md) to one comparison that fits six weeks. Evidence is the worked case in Figure 1 and the sources below |

| Open question | Why it matters | Next action |
|---|---|---|
| Is there public data with per request latencies and uneven host loads? | Invented latencies may not show real skew, so results could look better or worse than reality | Read the Alibaba microservices trace description for response time fields and license terms. If it does not fit, use synthetic skewed streams and label them as synthetic |

**Assistance and reuse:** Figures 1 and 2 were drawn for this document, and their editable sources are in the assets folder. Outside sources are listed below. The course policy on assistance still needs to be checked and stated here before this is final.

### References

| Source | What it supports | Checked |
|---|---|---|
| [Prometheus, Histograms and summaries](https://prometheus.io/docs/practices/histograms/) | The existing approach of merging histograms, and why summary quantiles do not combine | Page opened and wording confirmed |
| [Masson, Rim and Lee, DDSketch, PVLDB 12(12), 2019](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf) | The first sketch I will test | Found in search, not yet read in full |
| [NSF award 2544434, University of Maryland, College Park](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | The funded research source for the project | Link taken from the course abstracts |
| [Alibaba cluster trace program](https://github.com/alibaba/clusterdata) | A possible public source of response time data | Found in search, not yet checked |

### Supporting media and evidence

| Item | Purpose |
|---|---|
| [assets/fleet_p99_gap.png](assets/fleet_p99_gap.png), source [assets/fleet_p99_gap.svg](assets/fleet_p99_gap.svg) | Figure 1, the averaging failure for two hosts |
| [assets/fleet_p99_workflow.png](assets/fleet_p99_workflow.png), source [assets/fleet_p99_workflow.svg](assets/fleet_p99_workflow.svg) | Figure 2, the four ways to combine per host measurements |
