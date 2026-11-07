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

* **Done:** Section 1 is drafted from my proposal. It covers who is affected, how the number is produced today, a worked case, the evidence, and the scope.
* **Narrowed:** The proposal compared five approaches across four experiments. For this semester I kept one comparison: three ways to answer a fleet p99 from uneven hosts, judged by relative error against the exact answer.
* **Decided while drafting:** "Error" means relative error at p99, so every method is judged the same way.
* **Still unknown:** Whether I can find public data with real per request latencies and uneven host loads. This is the open question in Section 12.
* **Next:** Write the Section 2 requirements, then compare the candidate approaches in Section 3.

## 1 Problem research and scope

### 1.1 Who has the problem

Engineers who run large online services watch one number to judge speed: the fleet p99, the latency that 99 percent of all requests beat. The people who depend on it are listed below.

| Who | How they use the fleet p99 | What goes wrong |
|---|---|---|
| On call reliability engineer | Decides whether an alert is real and whether to wake someone | An averaged value can invent a slowdown or hide a real one |
| Service owner | Checks the service against a latency target | Reports a number that does not match what users experienced |
| Monitoring platform team | Runs the pipeline that collects and stores measurements | Keeping every request is accurate but costs bandwidth, storage and query time |

### 1.2 How the number is produced today

I have not observed a specific company's pipeline. Based on the sources in 1.4, there are three common routes, and each has a catch.

1. **Average the local p99 values.** Each host computes its own p99 and a central system averages them. This is cheap, but it is wrong when hosts carry different loads.
2. **Ship every measurement.** One place stores all requests and computes the p99 directly. The answer is exact, but the cost grows with traffic.
3. **Merge fixed bucket histograms.** Hosts report counts per latency bucket, which can be added together across hosts. The result is approximate, so the bucket layout matters. I still need to verify how much in Section 3.

### 1.3 A concrete case

Two hosts serve one hour of traffic. Host A serves 1,000,000 requests and its local p99 is 50 ms. Host B serves 1,000 requests and its local p99 is 900 ms. A dashboard averages the two local values and reports (50 + 900) / 2 = 475 ms.

Host B handles only about 0.1 percent of the requests, so the real fleet p99 stays close to Host A's, about 50 ms. The report is roughly 9.5 times too high, and an engineer may chase a slowdown that is not there. The numbers are chosen for illustration and are not measured. The opposite mistake also happens when a busy host hides a small slow one.

![Number line from 0 to 1000 milliseconds. Host A's local p99 is 50 ms and Host B's is 900 ms. The dashboard reports 475 ms, which is 425 ms above the true fleet p99 of about 50 ms. A bar below shows Host A has 99.9 percent of requests and Host B has 0.1 percent.](fleet_p99_gap.png)

**Figure 1.** Averaging gives each host half the weight, but Host B serves only 0.1 percent of the requests, so the reported fleet p99 lands far from the true one.

### 1.4 What I know and what I do not

| Claim | Source | Status |
|---|---|---|
| Percentile values from separate hosts cannot simply be averaged. Prometheus says aggregating a summary's precomputed quantiles rarely makes sense, while histograms can be aggregated | [Prometheus documentation](https://prometheus.io/docs/practices/histograms/) | Documented |
| Rank error guarantees can still allow large relative errors on skewed data. DDSketch is fully mergeable with a relative error guarantee | [Masson et al., 2019](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf) | Documented |
| Telemetry data can be too large to analyze in full when operators need real time answers, which motivates mergeable summaries | [NSF award 2544434](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | Documented. It shows funded interest, not that my case occurs |
| An averaged p99 misleads in the two host case above | Arithmetic on chosen numbers | Illustration. Nothing measured yet |
| Real host loads are uneven enough for the average to mislead | Not yet checked | Assumed |
| Merged sketches stay close to the exact answer at a small memory size | Not yet tested | Assumed |

### 1.5 Scope

**This semester:** I will build a small Python simulation that splits one latency stream across hosts with uneven loads. It compares three ways of answering the fleet p99: the average of per host p99 values, a uniform random sample, and merged DDSketch summaries. Each is measured against the exact p99 from all the data, using relative error at p99, at several memory sizes.

**Semester II:** The goal is a decision guide for which summary suits which data shape. It adds KLL and t digest sketches, one minimal mergeable sketch that I write and validate myself, a simple query layer, a merge study with more nodes and bursty, skewed data, and a second dataset.

**Not included:** Learned compression for long term storage, the configuration management engine, real network deployment, security monitoring, failure propagation across services, and any claim of true hyperscale. Scale is simulated by splitting data across nodes, and I will say so plainly.

## 2 Requirements and system specification

*Not started. Later work, not due this week.*

## 3 Alternatives and selected solution

*Not started. Later work, not due this week.*

## 4 Architectural design

*Not started. Later work, not due this week.*

## 5 Component design and interfaces

*Not started. Later work, not due this week.*

## 6 Data structure design

*Not started. Later work, not due this week.*

## 7 Algorithm design and execution

*Not started. Later work, not due this week.*

## 8 Failures and security

*Not started. Later work, not due this week.*

## 9 Implementation and feasibility

*Not started. Later work, not due this week.*

## 10 Testing and verification

*Not started. Later work, not due this week.*

## 11 Operation maintenance and future work

*Not started. Later work, not due this week.*

## 12 Revision history and references

### Revision history

| Date | Change |
|---|---|
| November 6, 2026 | First version: Section 1, progress note, open question and references. Sections 2 to 11 not started. |

### Open question

| Question | Why it matters | Next action |
|---|---|---|
| Is there public data with per request latencies and uneven host loads? | Invented latencies may not show real skew, so results could look better or worse than reality | Read the Alibaba microservices trace description for response time fields and license terms. If it does not fit, use synthetic skewed streams and label them as synthetic |

### References

| Source | What it supports | Checked |
|---|---|---|
| [Prometheus, Histograms and summaries](https://prometheus.io/docs/practices/histograms/) | The existing approach of merging histograms, and why summary quantiles do not combine | Page opened and wording confirmed |
| [Masson, Rim and Lee, DDSketch, PVLDB 12(12), 2019](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf) | The first sketch I will test | Found in search, not yet read in full |
| [NSF award 2544434, University of Maryland, College Park](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | The funded research source for the project | Link taken from the course abstracts |
| [Alibaba cluster trace program](https://github.com/alibaba/clusterdata) | A possible public source of response time data | Found in search, not yet checked |
