# Project Selection: Problem Understanding Paper

## Approximation First Telemetry with Mergeable Quantile Summaries

**Zihad Patwary**  
Senior Project I (CSC 59866)  
November 2026  
**Status:** Final Topic. My initial topic, A15, is kept in [my A15 paper](A15_Problem_Understanding_Paper.md).

### What problem are you investigating?

Teams that run large online services judge speed by tail latency, not by the average. The usual number is the p99: the latency that 99 percent of requests beat. Operators want it for the whole fleet, meaning every request served by every server (host) taken together. No single host sees the whole fleet. Each host only sees its own requests, so the fleet p99 has to be assembled from many separate reports, and hosts rarely carry equal traffic.

The problem is that the two common ways to assemble it each fail. The cheap way, averaging each host's own p99, gives a wrong number because percentiles do not add. The exact way, sending every measurement to one place and sorting it, is correct but costs bandwidth, storage and query time that grow with traffic. The NSF award this project is drawn from states the general version of this: data about traffic, resource use and failures can be too large to analyze in full when operators need answers in real time (National Science Foundation, n.d.).

**Example.** In one hour, Host A serves 1,000,000 requests with a local p99 of 50 milliseconds (ms). Host B serves 1,000 requests with a local p99 of 900 ms because it is overloaded. A dashboard that averages the two shows (50 + 900) / 2 = 475 ms. That crosses a 300 ms alert threshold and pages the on call engineer. But Host B served only about 0.1 percent of the requests. Pooled together, the true fleet p99 is about 50 ms, so the alert was false. The reverse also happens: when one busy host is slow and several quiet hosts are fast, the average comes out low and hides a slowdown most users feel. These numbers are invented to show the effect and are not measurements.

**Conditions.** The error appears when traffic is uneven across hosts, latencies have long tails, and each host can only afford a small report. With even traffic or small data, averaging or exact pooling both work well enough.

**Boundaries.** I investigate how host reports are combined into one fleet quantile answer. I do not study network delay, anomaly detection, long term storage compression or tuning services to be faster.

This is a distributed systems problem because hosts share information only by sending messages. Each host must send something much smaller than its raw data, and the pieces still have to add up to a correct fleet answer, in any arrival order, even when some reports arrive late or never.

### Who or what is affected by it?

**On call engineers** are affected first. A wrong fleet p99 either wakes someone for a slowdown that is not happening or hides one that is. Dean and Barroso (2013) explain why the tail matters at scale: short slow episodes that are unimportant in a small system can dominate overall performance when a request touches many servers.

**Service owners** check their service against a promised latency target. If the reported fleet number does not match what users experienced, their reports and decisions are wrong.

**Monitoring platform teams** pay for the pipeline. Exact answers cost network, storage and compute that grow with traffic, which the monitored system could use for real work. The NSF abstract names lower compute, storage and energy cost as goals of the funded project (National Science Foundation, n.d.).

**End users** feel the slowdowns that a wrong number hides.

### What evidence do you currently have that it is a real problem?

**Published opportunity (Documented).** NSF award 2544434, CAREER: Approximation First Telemetry for Hyperscale Networked Systems (University of Maryland, College Park, June 2026 to May 2031) funds this research area. Its first thrust is mergeable summaries that track their own uncertainty and its second is answering queries directly from summaries (National Science Foundation, n.d.). This shows the problem is recognized and active, not that my scenario happens in a particular fleet.

**Technical documentation (Documented).** The Prometheus documentation states that precomputed percentiles from separate summaries generally cannot be combined meaningfully, while histogram bucket counts can be added across instances (Prometheus Authors, n.d.). That is the averaging failure, stated by a widely used monitoring tool.

**Research (Documented).** Agarwal et al. (2013) define a mergeable summary: two summaries combine into a summary of the combined data with the same error and size guarantees. Masson, Rim and Lee (2019) show that DDSketch is fully mergeable with a relative error guarantee and that sketches with only a rank error guarantee can give large relative errors on skewed data. Winchester et al. (2025) report that workloads in an Alibaba production deployment follow long tailed distributions.

**Real data (Documented).** Alibaba's public 2022 microservices trace records the response time of each call and the container that served it, which lets me treat containers as hosts (Alibaba Group, n.d.).

**Observed.** None yet. My first observation will be the gap between averaged and exact p99 on the Alibaba slice.

**Assumptions.**

- Traffic across the containers of one busy microservice is uneven enough to expose the averaging error.
- Hosts simulated inside one program are a fair stand in for real hosts, because the question is what a summary can represent, not network timing.
- Lognormal and Pareto latencies are a fair stand in for real latencies.

**Missing evidence.** Telemetry from a real hyperscale fleet, the accuracy targets operators actually use, and real transfer costs, which I will only count in bytes.

### What solutions already exist?

| Approach | How it works | Strength | Limitation under my conditions |
| --- | --- | --- | --- |
| Exact pooling | Every host sends every latency; sort and read the percentile | Exact; the reference for all error | Cost grows with traffic: 8 bytes per request, 80 MB for 10 million requests |
| Averaging local p99 | Each host sends one number | Tiny and simple | Wrong under skew (475 ms against 50 ms above); percentiles do not add |
| Uniform sample | Each host sends a random sample and its request count | Simple and mergeable | Only about 1 percent of samples lie above p99, so 256 values give about 3 tail values per host |
| Fixed bucket histogram | Hosts count requests in agreed latency ranges | Merges exactly by adding counts (Prometheus Authors, n.d.) | Accuracy depends on bucket edges chosen before seeing the data |
| KLL sketch | Compacting buffers with a rank error bound | Near optimal space for rank error and mergeable (Karnin et al., 2016) | Rank error can mean large relative error far out in a heavy tail |
| DDSketch | Buckets of fixed relative width | Fully mergeable with a relative error bound (Masson et al., 2019) | Covering 1 ms to 10 s at 1 percent accuracy needs about 461 bins (about 7.2 KiB), more than small budgets allow |
| t digest | Clusters of centroids, finer near the extremes | Reported to be very accurate near the tails and used in production monitoring (Dunning & Ertl, 2019) | Accuracy is shown by experiment more than by a worst case merge bound |

The libraries exist, so the gap is not a missing algorithm. The open part is how merged error behaves when many host summaries are combined under uneven traffic at a small fixed memory budget per host, and therefore which summary an operator should choose for a given data shape.

### What is the most important thing you still do not know?

The main unknown is whether a merged fleet p99 built from small per host summaries stays within 1 percent of the exact value as the number of hosts grows and traffic becomes more uneven, at budgets from 512 bytes to 32 KiB per host.

**Experiment.** Split one stream of latencies across 4, 16, 64 and 256 simulated hosts with traffic skews from even to heavily uneven, plus a slow small host case like the example. Answer the fleet p99 three ways: averaging local p99 values, merging uniform samples, and merging one DDSketch per host. Score every answer against the exact p99 computed from all the data, over 5 random seeds.

**Measurements.** Relative error at p50, p90, p99 and p99.9; summary bytes per host; total bytes against exact storage; time to merge.

**How the result would influence the design.**

- DDSketch stays within 1 percent at 8 KiB and above but not below: the design must choose, at small budgets, between a coarser accuracy setting and merging the lowest bins.
- Merged error grows with host count or skew for a method with a merge guarantee: that is a defect in my code or my use of the package, and it must be fixed before any result counts.
- Sampling matches DDSketch at the same memory: the recommendation shifts toward the simpler method for those data shapes.

### Your Individual Scope

In six weeks I will build a Python simulation that partitions request latencies across simulated hosts, builds one summary per host within a memory budget, merges the summaries and scores the fleet answer against the exact one. I compare averaging, uniform sampling and DDSketch on synthetic heavy tailed data and on one slice of the Alibaba 2022 trace. In Semester II I add KLL and t digest, a minimal mergeable sketch I write myself, a simple query layer and a decision guide for which summary fits which data shape.

I exclude the NSF project's third and fourth thrusts (learned compression and the engine that turns goals into settings), real network deployment, security monitoring and any claim of true hyperscale. Scale is simulated and the results will say so. One student can do this because it needs one language, an open source DDSketch package, public or generated data and one laptop, and every result has an exact answer to check against.

### How this topic differs from and improves on my initial topic

My initial topic was [A15](A15_Problem_Understanding_Paper.md): how a dataset enrichment pipeline duplicates or loses records when a worker crashes between saving its rows and marking its batch done, tested on USGS earthquake data with Python and Delta Lake. After I presented it, my professor said A15 had to be narrowed to a slice of work another group is funded for, or replaced. This topic does that. It is a defined slice (thrusts one and two) of an active NSF award, so the scope comes from funded research, while A15 only used the NSF AI Datasets call as general motivation. The evidence is also stronger. A15 had no verified production incident and rested on the assumption that enough pipelines separate output and progress writes, while here a widely used monitoring tool documents the averaging failure itself, and I can test on a public production trace instead of synthetic records. The question is also richer. A15 came down to a pass or fail comparison of two existing fixes, MERGE and Delta transaction identifiers, and my dry run had already shown MERGE passing. Here the open part is how error changes with memory, host count and skew, which produces a measured result and a decision guide rather than one verdict. It still runs on one laptop with public data, and it keeps the core lesson from A15: no record may be counted twice or silently left out, now applied to merging summaries from many hosts. Finally, it fits my goal of working between data science and data engineering, since it combines distributions and error analysis with distributed aggregation.

### References

Agarwal, P. K., Cormode, G., Huang, Z., Phillips, J. M., Wei, Z., & Yi, K. (2013). Mergeable summaries. *ACM Transactions on Database Systems, 38*(4). [https://dimacs.rutgers.edu/~graham/pubs/html/AgarwalCormodeHuangPhillipsWeiYi13.html](https://dimacs.rutgers.edu/~graham/pubs/html/AgarwalCormodeHuangPhillipsWeiYi13.html)

Alibaba Group. (n.d.). *Cluster trace microservices v2022* [Data set description]. GitHub. Retrieved November 14, 2026, from [https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2022](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2022)

Dean, J., & Barroso, L. A. (2013). The tail at scale. *Communications of the ACM, 56*(2), pages 74 to 80. [https://research.google/pubs/pub40801/](https://research.google/pubs/pub40801/)

Dunning, T., & Ertl, O. (2019). *Computing extremely accurate quantiles using t-digests* (arXiv:1902.04023). arXiv. [https://arxiv.org/abs/1902.04023](https://arxiv.org/abs/1902.04023)

Karnin, Z., Lang, K., & Liberty, E. (2016). Optimal quantile approximation in streams. In *Proceedings of the 57th IEEE Symposium on Foundations of Computer Science (FOCS)* (pages 71 to 78). IEEE. [https://arxiv.org/abs/1603.05346](https://arxiv.org/abs/1603.05346)

Masson, C., Rim, J. E., & Lee, H. K. (2019). DDSketch: A fast and fully-mergeable quantile sketch with relative-error guarantees. *Proceedings of the VLDB Endowment, 12*(12), pages 2195 to 2205. [https://www.vldb.org/pvldb/vol12/p2195-masson.pdf](https://www.vldb.org/pvldb/vol12/p2195-masson.pdf)

National Science Foundation. (n.d.). *Award 2544434: CAREER: Approximation-First Telemetry for Hyperscale Networked Systems*. University of Maryland, College Park. [https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434](https://www.nsf.gov/awardsearch/show-award?AWD_ID=2544434)

Prometheus Authors. (n.d.). *Histograms and summaries*. Prometheus documentation. Retrieved November 6, 2026, from [https://prometheus.io/docs/practices/histograms/](https://prometheus.io/docs/practices/histograms/)

Winchester, G., Parisis, G., Xu, G., & Berthouze, L. (2025). *Complexity at scale: A quantitative analysis of an Alibaba microservice deployment* (arXiv:2504.13141). arXiv. [https://arxiv.org/abs/2504.13141](https://arxiv.org/abs/2504.13141)
