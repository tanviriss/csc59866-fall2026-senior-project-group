# Approximation First Telemetry with Mergeable Quantile Summaries

**Author:** Zihad Patwary  
**Course:** CSC 59866  
**Selected project and option:** 04 CAREER: Approximation-First Telemetry for Hyperscale Networked Systems  
**Current assignment:** 2

## Progress note

This version adds the Section 2 specification and a first Section 3 comparison, and revises Section 1. Writing requirements made me fix what I had left vague: the definition of p99, the number of simulated hosts (4 to 256) and the memory per host (512 bytes to 32 KiB). Tanvir's review asked for those numbers and for real data, so Section 1 now uses Alibaba's public 2022 microservices trace, which records each call's response time and serving container. Its description showed that server side times are stored as negative numbers, so the loader must filter them. The main open issue is that at the two smallest budgets DDSketch cannot keep 1 percent accuracy from 1 ms to 10 s, so I must choose coarser accuracy or dropping low values. Next I will select the design and draw the architecture.

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
| Monitoring data can be too large to analyze in full when operators need answers in real time | [National Science Foundation (NSF) award 2544434](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434) | Documented. It shows the research motivation, not that my scenario happens |
| The two host scenario reports 475 ms against a true value near 50 ms | Arithmetic on invented numbers | Assumed |
| Public production data exists with a response time for each call and the identity of the container that served it | [Alibaba 2022 microservices trace description](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2022) | Documented |
| Workloads in a large production deployment follow long tailed distributions | [Winchester et al., 2025](https://arxiv.org/abs/2504.13141) | Documented for load across microservices. Whether the containers of one microservice are uneven is still Assumed and is checked in Section 2 |
| Engineers follow the five steps in Figure 1 | My reading of the sources | Assumed |

![Number line from 0 to 1000 milliseconds. Host A's local p99 is 50 ms and Host B's is 900 ms. The dashboard reports 475 ms, which is 425 ms above the true fleet p99 of about 50 ms. A bar below shows Host A has 99.9 percent of requests and Host B has 0.1 percent.](assets/fleet_p99_gap.png)

**Figure 2.** The scenario on a number line. Averaging gives each host half the weight, but Host B served only 0.1 percent of the requests, so the reported fleet p99 lands far from the true one.

**Six-week contribution:** A Python simulation that splits one stream of request latencies across simulated hosts with uneven traffic, then answers the fleet p99 three ways: averaging each host's p99, merging a uniform random sample from each host, and merging one DDSketch per host. Each answer is compared with the exact p99 computed from all the data. The measure is relative error at p99, meaning the gap between the estimate and the exact value divided by the exact value.

The scale is fixed in advance so results can be compared. I will simulate 4, 16, 64 and 256 hosts. A simulated host is a separate data partition with its own summary inside one Python program on my laptop, not a real server, and it shares nothing with other hosts except the summary it reports. Each host may use 512 bytes, 2 KiB, 8 KiB or 32 KiB for its summary, where 1 KiB is 1,024 bytes. At 8 bytes per stored latency, 32 KiB holds 4,096 values, while keeping every value for 10 million requests takes 80 MB (80 million bytes). Section 2 lists the full settings.

The data comes from two sources. The first is synthetic latencies with heavy tails, where I control the traffic split. The second is real data: one slice of Alibaba's public 2022 microservices trace, which records the response time of each call between services in a production cluster and the container that served it. Each container is treated as a host. One student can do this because it needs one language, an existing open source DDSketch package, and data that is public or generated.

**Semester II scope:** The completed project is a decision guide that says which summary suits which data shape and accuracy target, backed by measurements. It adds the KLL sketch (named for its authors Karnin, Lang and Liberty) and the t digest sketch, one minimal mergeable sketch that I write and validate myself, a simple query layer that answers questions from merged summaries, more hosts with bursty and skewed traffic, and a second dataset.

**Exclusions:** The NSF project has four research thrusts. My work sits inside the first, mergeable summaries that track their own error, and in Semester II part of the second, answering queries from summaries. I exclude the third and fourth thrusts, learned compression for long term storage and the engine that turns accuracy and cost goals into settings. I also exclude real network deployment, security monitoring and failure spread across services. I make no claim of true hyperscale: scale is simulated by splitting data across hosts, and the results will say so.

## 2 Requirements and system specification

The system is a simulator. Its user is me, or anyone repeating the study, acting for the on call engineer in Section 1. It takes a set of request latencies, splits them across simulated hosts, lets each host build a summary of its own requests, combines the summaries into one fleet answer, and scores that answer against the exact one.

**Terms used below.**

- **Exact p99:** sort all N latencies from all hosts and take the value at position ⌈0.99 × N⌉, counting from 1. This is the nearest rank definition, and every estimate is judged against it. Other quantiles q work the same way with ⌈q × N⌉.
- **Relative error:** |estimate − exact| / exact, reported as a percentage.
- **Summary:** what a host reports instead of its raw latencies. The four kinds are its local p99 (for averaging), a uniform random sample with the host's request count, a DDSketch, and the full list of latencies (for the exact reference only).
- **Memory budget:** the bytes one host may use for its summary, counted as 8 bytes per stored latency value and 16 bytes per DDSketch bin, which holds a bin index and a count. Python object overhead is not counted, and results will say so.
- **Traffic skew:** how requests are split across H hosts. Under a skew of s, host i (for i from 1 to H) receives a share of requests proportional to 1 / i^s. A skew of 0 is an even split, and a skew of 2 gives the busiest of 64 hosts about 61 percent of requests.
- **Requirement IDs:** F means a functional requirement, C a correctness rule and Q a quality target, following the course guide. A numbers are assumptions and T numbers are planned tests.
- **α (alpha):** the relative accuracy setting of a summary that promises a relative error bound. α = 0.01 promises that an answer is within 1 percent of the exact value.

### Requirements

| ID | Required behavior and conditions | Acceptance check | Design and test reference |
|---|---|---|---|
| F1 | Given latencies, a host count H and a traffic skew, the simulator assigns every request to exactly one host and reports each host's request count. With Alibaba data, a host is one serving container and the split comes from the data | Synthetic: 1,000,000 latencies, H = 16, skew 1. Host counts must sum to 1,000,000 and each host's share must be within 0.1 percentage points of its target share. Alibaba: host counts must equal the row counts per container after filtering | Partitioner assigns host IDs and counts requests per host. T1: 1,000,000 latencies, 16 hosts, check sum and shares. Planned |
| F2 | Each host builds its summary from its own requests only and stays within the memory budget | Give the summary builder one host's partition and confirm it never receives another host's data. Measure each summary at all four budgets and confirm none exceeds its budget | Host builder gets one host's data and a byte budget. T2: all four summary kinds at all four budgets stay within budget. Planned |
| F3 | The coordinator combines the host summaries and answers a fleet quantile q for q = 0.5, 0.9, 0.99 and 0.999. Every answer lists how many hosts and how many requests it covers | Run the ordinary example below and check the returned estimate, host count and request count | Coordinator merges summaries and adds coverage. T3: two host example returns 50 ms and 2 of 2 hosts. Planned |
| F4 | For every run the simulator computes the exact quantile, the estimate and the relative error, and writes one result row per setting with the dataset, method, host count, skew, budget, quantile and random seed | For one quantile, a grid of 2 host counts × 2 budgets × 3 methods × 2 seeds must produce 24 rows. Running the same settings and seeds again must produce identical rows | Run script writes one result row per setting. T4: a 24 setting grid gives 24 rows, identical on rerun. Planned |
| F5 | The data loader turns raw Alibaba rows into latencies and reports how many rows it dropped and why | On a sample file, the counts of kept rows and dropped rows (negative times, missing container, wrong call type) must add up to the total rows read | Alibaba loader keeps positive times and counts drops by reason. T5: kept plus dropped equals rows read. Planned |
| C1 | Merging the same host summaries in any order or grouping gives the same merged summary. If a method's merge is documented as lossless, the merged summary must also equal one built from all the data at once | Merge 16 host summaries in three shuffled orders, as a chain and as a pairwise tree, and compare their contents exactly. First planned case: DDSketch with no bin limit, comparing bin counts | Merge step adds bin counts. T6: 16 sketches merged in any order give identical bins. Planned |
| C2 | No request is lost or counted twice. The merged request count equals the sum of the counts of the hosts it covers | Compare the merged count with the per host counts. Submit host 3's summary twice and confirm the duplicate host ID is rejected and the count is unchanged | Coordinator rejects a repeated host ID. T7: Host B sent twice is rejected, count stays 1,000 and p99 stays 10 ms. Planned |
| C3 | The simulator never reports a partial fleet answer as complete. If summaries are missing, the answer states the hosts and requests covered. With no summaries, it returns an error and no number | Drop host 3 of 16 and confirm the answer says 15 of 16 hosts and the matching request count. Drop all hosts and confirm an error | Coordinator checks received hosts against the expected list. T8: drop host 3 of 16 and expect "15 of 16 hosts". Planned |
| C4 | When a summary method documents a relative error bound α and its settings keep that bound in force, every fleet answer it gives is within α of the exact value. An answer outside a documented bound is a defect, not an accuracy result | First planned case, DDSketch with α = 0.01 and no bin limit: run the ordinary example and 100 random synthetic streams. Compute the exact value with the rank definition the package uses, which can differ from the nearest rank by one position. Any estimate more than 1 percent from that value fails | Scorer flags answers outside α. T9: DDSketch at α = 0.01 stays within 1 percent on 100 random streams. Planned |
| Q1 | Accuracy, proposed: with 64 hosts, skew 1, 8 KiB per host and 10,000,000 synthetic requests, at least one summary method gives a merged fleet p99 with a relative error of at most 1 percent in each of 5 seeds. The method used in the design is chosen in Assignment 3 | Run the setting with seeds 1 to 5 and record the largest relative error. A run that crashes or gives no answer counts as a miss | Scorer reports p99 relative error. T10: 64 hosts, 8 KiB, 5 seeds. Target only |
| Q2 | Memory, proposed: in the Q1 setting, all host summaries together use at most 1 percent of the bytes needed to store every latency | Add the summary bytes across hosts and divide by 8 × N. By my arithmetic the target needs 64 × 8 KiB = 512 KiB against 80 MB, or about 0.7 percent | Summaries report counted bytes. T11: total bytes at most 1 percent of 80 MB. Target only |
| Q3 | Run time, proposed: the full synthetic grid below finishes within 30 minutes on my laptop | Time one full run of the grid from start to final result file | Run script times the whole grid. T12: all 640 settings under 30 minutes. Target only |
| Q4 | Answer speed, proposed: with 256 hosts at 32 KiB each, the coordinator combines every summary and returns the fleet p99 in under 1 second on my laptop | Time from the arrival of the last summary to the returned answer, 10 times. Every run must finish in under 1 second. Repeat with twice the synthetic traffic to confirm the time does not depend on the number of requests | Coordinator times each merge. T13: 256 hosts at 32 KiB, 10 runs, each under 1 second. Target only |

Why 1 percent: on the 300 ms alert threshold from Section 1, 1 percent is 3 ms, far smaller than the 425 ms error that averaging produced. If baseline runs show the target is too easy or impossible, I will revise it and record why in Section 12.

Why 1 second for Q4: dashboards usually refresh every few seconds to every minute, so a fleet number that takes longer to build than the refresh is already old when the engineer reads it during an outage. The exact answer has to sort every request and slows down as traffic grows, while combining summaries depends only on the number of hosts and their budgets.

### Experiment settings

These settings answer how many hosts I simulate and how much memory I test.

| Setting | Values | Reason |
|---|---|---|
| Simulated hosts | 4, 16, 64, 256 | Shows how error changes as more summaries are merged. 256 hosts still fit in one program on a laptop |
| Memory per host | 512 bytes, 2 KiB, 8 KiB, 32 KiB. That is 64, 256, 1,024 or 4,096 sampled values, or 32, 128, 512 or 2,048 DDSketch bins | Four times apart, so the curve of error against memory has enough points |
| Traffic skew | 0 (even), 1, 2, and a slow small host case: one host with 0.1 percent of traffic and much slower latencies, as in Section 1 | Averaging should do well when traffic is even and badly when it is skewed |
| Synthetic data | 10,000,000 latencies from a lognormal distribution and from a Pareto distribution, which both have long right tails | Two tail shapes, generated with fixed seeds |
| Real data | One 3 minute file of the Alibaba 2022 call graph table, using calls to one busy microservice, with containers as hosts. If its containers carry nearly equal traffic, the same real latencies are also split with the synthetic skews | Real latency values, plus a natural host split if the data has one |
| Quantiles | 0.5, 0.9, 0.99, 0.999 | p99 is the focus. The others show where each method breaks |
| Seeds | 1 to 5 | Sampling and synthetic data are random, so each result is repeated |

The synthetic grid is 4 host counts × 4 budgets × 4 skew cases × 2 distributions × 5 seeds = 640 runs, each scored for every method and quantile.

### Inputs and outputs

**Ordinary example.** This is the Section 1 scenario with exact values, so the expected output can be checked by hand.

| Input | Value |
|---|---|
| Host A | 1,000,000 requests: 985,000 at 20 ms and 15,000 at 50 ms. Its local p99 is position 990,000, which is 50 ms |
| Host B | 1,000 requests: 980 at 100 ms and 20 at 900 ms. Its local p99 is position 990, which is 900 ms |
| Query | Fleet p99. DDSketch with α = 0.01 and no bin limit |

| Output | Expected value |
|---|---|
| Exact fleet p99 | Position ⌈0.99 × 1,001,000⌉ = 990,990 of the pooled sorted list, which falls inside Host A's 50 ms requests, so 50 ms |
| Averaging | (50 + 900) / 2 = 475 ms, a relative error of 850 percent |
| Merged DDSketch | Between 49.5 ms and 50.5 ms, by C4 |
| Coverage | 2 of 2 hosts and 1,001,000 requests |

**Unsuccessful cases.**

| Input | Expected behavior |
|---|---|
| Query q = 1.5 | Rejected with "quantile must be between 0 and 1". No number is returned |
| Every host summary missing | Error "no host summaries received". No number is returned (C3) |
| Host B's summary submitted twice | Rejected as a duplicate host ID. The fleet count stays 1,001,000 (C2) |
| Alibaba row whose response time field (rt) is −7 | Not used as a latency. The trace records server side times as negative numbers, so the loader drops the row and counts it under "negative time" (F5) |

### Assumptions

| ID | Assumption | How I will check it |
|---|---|---|
| A1 | Hosts simulated inside one program are enough for this question, because the question is about what a summary can represent, not about network delay | Code review that each host builder receives only its own partition (F2). Network timing is excluded in Section 1 |
| A2 | One 3 minute Alibaba file has enough calls per container for a p99 to mean something, which I set at 1,000 or more calls per host | Download one file in week 1 and count calls per container for the busiest microservices before relying on it |
| A3 | Whole millisecond times are precise enough at p99. The trace stores times under 1 ms as 0 | Measure the share of zeros and repeated values in the slice. If an exact quantile is below 1 ms, report absolute error for it instead of relative error |
| A4 | The open source DDSketch package behaves as its paper describes, including merging and limiting the number of bins | Run tests T6 and T9 before any experiment |
| A5 | Lognormal and Pareto latencies are a fair stand in for real latencies | Compare their tails with the Alibaba slice and report any large difference |

### Constraints

- Six weeks, one student, one laptop, Python 3 with NumPy and the open source `ddsketch` package.
- Only public or synthetic data. The Alibaba repository has no license file, so I will not copy the trace into my repository. I will commit the download and filtering steps and my derived results, and cite the paper the trace asks users to cite.
- The Alibaba call graph table is about 4 GiB (gibibytes, about 4.3 billion bytes) compressed per hour, and the download script fetches it in 3 minute files. I will use one file and process it in chunks, so the full table never has to fit in memory.
- At most 256 simulated hosts and no real network, as stated in Section 1.

## 3 Alternatives and selected solution

The question for every approach is the same: what should each host send so that the pieces still add up to a correct fleet p99 within the memory budget? Exact pooling is listed only as the reference answer, because it breaks the memory constraint by design.

| Approach and source | Useful behavior | Limitation | Evidence or assumption |
|---|---|---|---|
| Exact pooling: every host sends every latency | Gives the exact answer and serves as ground truth for every test | Memory and transfer grow with traffic: 8 bytes per request, or 80 MB for 10 million requests | Arithmetic |
| Averaging local p99 values (simple baseline, today's cheap practice) | One number per host, trivial to merge in any order | Ignores how many requests each host served, so it is wrong under skew: 475 ms against 50 ms in the ordinary example. Weighting by request count does not fix it in general, because percentiles do not add | [Prometheus documentation](https://prometheus.io/docs/practices/histograms/) states precomputed percentiles generally cannot be combined. Ordinary example in Section 2 |
| Uniform random sample with each host's request count | Simple, works for any range of values, and merges by weighting each sampled value by its host's count divided by the sample size | Only about 1 percent of a sample lies above p99, so 256 values give about 3 tail values per host and a noisy estimate. Results are random, so C1 holds only on average | Judgment, to be measured |
| Fixed bucket histogram: count requests in latency ranges agreed in advance | Merges exactly by adding bucket counts, so C1 and C2 hold | Accuracy depends on where the bucket edges fall, and all hosts must use the same edges, chosen before seeing the data | Prometheus documentation states bucket counts can be added across hosts. Accuracy is my judgment |
| Merged DDSketch: buckets spaced so each one covers a fixed relative width | Fully mergeable by adding bin counts, with a relative error bound α that rank based sketches do not give on skewed data | Covering 1 ms to 10 s at α = 0.01 needs about 461 bins, which is about 7.2 KiB. At 512 bytes or 2 KiB the sketch must either merge its lowest bins or use a coarser α | [Masson, Rim and Lee, 2019](https://arxiv.org/abs/1908.10693) for mergeability and relative error. Bin count is my arithmetic, where ln is the natural logarithm: ln(10,000) / ln(1.01 / 0.99) ≈ 461 |

[Agarwal et al., 2013](https://dimacs.rutgers.edu/~graham/pubs/html/AgarwalCormodeHuangPhillipsWeiYi13.html) give the definition I use to judge every row: a summary is mergeable when two summaries can be combined into a summary of the combined data while keeping the same error and size guarantees. That definition is the source of C1 and C2.

### Comparison against the requirements

Each cell says whether the approach can meet the requirement and what the claim rests on: documented in a source, arithmetic, or my judgment until measured.

| Requirement | Averaging (baseline) | Uniform sample | Fixed bucket histogram | Merged DDSketch |
|---|---|---|---|---|
| F2: summary from own data, within budget | Yes, 8 bytes per host (arithmetic) | Yes, sample size set by the budget (arithmetic) | Yes, number of buckets set by the budget (arithmetic) | Yes, bin limit set by the budget. Library support for a bin limit is assumed (A4) |
| F3: one fleet answer with coverage | Yes, but the answer is not a fleet p99 under skew (documented) | Yes (judgment) | Yes, by finding the bucket that holds position ⌈q × N⌉ (judgment) | Yes (documented) |
| C1: same result in any merge order | Yes, a mean does not depend on order (arithmetic) | Only on average, because merging draws random values (judgment) | Yes, addition does not depend on order (documented) | Yes, addition of bin counts (documented) |
| C2: no request lost or counted twice | Fails unless request counts are sent too (judgment) | Yes, counts are sent with the sample (judgment) | Yes, counts are the summary (documented) | Yes, counts are the summary (documented) |
| Q1: at most 1 percent p99 error at 8 KiB, 64 hosts, skew 1 | Not expected, error is unbounded under skew (ordinary example) | Unlikely, since 1,024 values give about 10 tail values per host (judgment) | Depends on bucket edges (judgment) | Expected, since 512 bins exceed the 461 needed for α = 0.01 (arithmetic from the paper's bound) |
| Q2: total summaries at most 1 percent of exact storage | Yes, far below (arithmetic) | Yes, at the same budget (arithmetic) | Yes, at the same budget (arithmetic) | Yes, at the same budget (arithmetic) |
| Q4: fleet answer in under 1 second at 256 hosts and 32 KiB each | Yes, averaging 256 numbers (arithmetic) | Likely, since sorting up to 1,048,576 sampled values is a small job (judgment, to be measured) | Likely, since it adds bucket counts (judgment, to be measured) | Likely, since it adds up to 524,288 bin counts (judgment, to be measured) |
| Effort in six weeks | Smallest | Small | Small, but the bucket edges are a design choice of their own | Moderate, since the package exists but the bin limit needs care |

A second, smaller choice is how to simulate hosts. Hosts can be objects inside one program, or separate operating system processes that send serialized summaries to a coordinator. Separate processes would measure the real size of a sent summary and make host isolation (F2) automatic, at the cost of setup and slower runs at 256 hosts. Objects in one program are simpler and meet every requirement above if summary sizes are counted as defined in Section 2.

**Choice and reason:** The final choice, with two decision records, comes in Assignment 3. My current direction is that merged DDSketch is the main candidate because it is the only row expected to meet Q1, with averaging and uniform sampling kept as baselines, since showing how they fail is part of the result. Whether to add the fixed bucket histogram, and whether hosts are objects or processes, are the two open decisions. The averaging row already fails C2 and the ordinary example, which is the kind of distinction the RoomReserve restart requirement makes between its options.

### Decision 1

To be completed in Assignment 3: how to fit DDSketch into the two smallest budgets, by merging its lowest bins or by using a coarser α.

### Decision 2

To be completed in Assignment 3: whether simulated hosts are objects in one program or separate processes.

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
| November 14, 2026 | Assignment 2: wrote the Section 2 specification and a first Section 3 comparison. Revised Section 1 to fix the host counts (4 to 256) and memory budgets (512 bytes to 32 KiB) and to name the Alibaba 2022 microservices trace as real data | Tanvir Islam's review asked how many servers I simulate, how much memory I test and for real world data. The Alibaba trace description confirmed a per call response time and serving container. Writing C4 showed that DDSketch at α = 0.01 needs about 461 bins, more than the two smallest budgets allow |
| November 16, 2026 | Added Q4, a proposed target for answer speed, and a matching row in the Section 3 comparison. Rewrote every Design and test reference cell to name the responsible component and its planned test in one or two short sentences | Added after the Assignment 2 presentation so the specification also covers how fast a fleet answer must be ready, not only how accurate and how small it is |

| Open question | Why it matters | Next action |
|---|---|---|
| Does one 3 minute Alibaba file give at least 1,000 calls per container, and is traffic across those containers uneven? | Too few calls make p99 meaningless, and an even split would hide the averaging error | Download one file in week 1 and count calls per container (A2). If traffic is even, split the real latencies with the synthetic skews and label those runs |
| At 512 bytes and 2 KiB per host, should DDSketch merge its lowest bins or use a coarser α? | Merging low bins keeps p99 accurate only if p99 stays above the merged range, while a coarser α loosens the bound everywhere | Decide in Assignment 3 (Decision 1), using a small trial on synthetic data |

**Assistance and reuse:** The document structure comes from the course design document template, and the requirement types and table layouts in Sections 2 and 3 follow Chapters 5 and 6 of the course guide. Figures 1 and 2 were drawn for this document, and their editable sources are listed below. Outside sources are cited where they are used and listed in References.

### References

| Source | Claim it supports | Status |
|---|---|---|
| Prometheus Authors, [Histograms and summaries](https://prometheus.io/docs/practices/histograms/), Prometheus documentation, accessed November 6, 2026 | Histogram bucket counts can be added across hosts, while precomputed percentiles from summaries generally cannot be combined. Supports the averaging and fixed bucket histogram rows of Section 3 | Page read and wording checked |
| Charles Masson, Jee E. Rim and Homin K. Lee, [DDSketch: A Fast and Fully-Mergeable Quantile Sketch with Relative-Error Guarantees](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf), PVLDB 12(12), 2019. Also on [arXiv](https://arxiv.org/abs/1908.10693) | DDSketch is fully mergeable and has a relative error guarantee, while rank error sketches can give large relative errors on skewed data. Supports C1, C4 and the DDSketch row of Section 3 | Abstract read and wording checked. Full paper not yet read, so the bin limit behavior stays an assumption (A4) |
| National Science Foundation, [award 2544434, CAREER: Approximation-First Telemetry for Hyperscale Networked Systems](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434), University of Maryland, College Park, award period June 1, 2026 to May 31, 2031 | The research motivation and its four thrusts, used to bound my scope | Abstract read from the course handout. The award page itself did not load for me |
| Alibaba Group, [cluster trace program](https://github.com/alibaba/clusterdata) and its [2022 microservices trace description](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2022), GitHub repository, accessed November 14, 2026 | The real dataset: the call graph table has a response time and the serving container for each call, server side times are negative, times under 1 ms are stored as 0, and the table is about 4 GiB compressed per hour. Supports F5, A2, A3 and the constraints | Description and download script read. No license file in the repository. No data downloaded yet |
| Shutian Luo, Huanle Xu, Kejiang Ye, Guoyao Xu, Liping Zhang, Guodong Yang and Chengzhong Xu, The Power of Prediction: Microservice Auto Scaling via Workload Learning, ACM Symposium on Cloud Computing, 2022 | The paper the 2022 trace asks users to cite | Citation taken from the trace description. Paper not read |
| Darby Huye, Lan Liu and Raja R. Sambasivan, [Systemizing and Mitigating Topological Inconsistencies in Alibaba's Microservice Call-graph Datasets](https://raja.cs.tufts.edu/assets/pdf/huye2024_paper.pdf), ICPE 2024 | The Alibaba call graph data has data loss and other inconsistencies, at a lower rate in 2022 than in 2021. A reason to filter rows carefully and report what was dropped (F5) | Abstract read |
| Giles Winchester, George Parisis, Guoyao Xu and Luc Berthouze, [Complexity at Scale: A Quantitative Analysis of an Alibaba Microservice Deployment](https://arxiv.org/abs/2504.13141), arXiv 2504.13141, 2025 | Workloads and dependencies in Alibaba's deployment follow long tailed distributions. Partial support for the uneven traffic assumption in Section 1 | Abstract read |
| Pankaj K. Agarwal, Graham Cormode, Zengfeng Huang, Jeff M. Phillips, Zhewei Wei and Ke Yi, [Mergeable Summaries](https://dimacs.rutgers.edu/~graham/pubs/html/AgarwalCormodeHuangPhillipsWeiYi13.html), ACM Transactions on Database Systems 38(4), 2013 | The definition of a mergeable summary used to judge every approach in Section 3, and the basis of C1 and C2 | Abstract read and wording checked |

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
