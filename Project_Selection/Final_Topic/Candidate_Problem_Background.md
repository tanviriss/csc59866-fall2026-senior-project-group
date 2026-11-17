Zihad Patwary  
Professor Kurt Brown  
CSC 59866  
17 November 2026  

# Candidate Problem Background: Approximation First Telemetry with Mergeable Quantile Summaries

**Status:** Final Topic. This background replaces my initial topic, A15, which is kept in [the V1 A15 paper](../V1_A15_Problem_Understanding_Paper.md). Section 4 explains how this topic differs from it and why it is the better choice.

## 1. Describe the Problem

Online services are judged by how slow their slowest requests are, not by the average. Engineers track the p99, the latency that 99 percent of requests beat, and they want it for the whole fleet of servers at once. A large request often touches many servers, so short slow episodes that do not matter in a small system can dominate performance at scale (Dean and Barroso). The difficulty is that no server sees the fleet. Each host measures only its own requests, and the fleet number has to be built from many separate host reports.

There are two easy ways to build it, and both break. The first is to average each host's own p99. It is cheap, but percentiles do not add, so the result is wrong whenever hosts carry different amounts of traffic. Prometheus, a widely used monitoring tool, warns that precomputed percentiles from separate summaries generally cannot be combined, while histogram bucket counts can (Prometheus Authors). The second is to ship every single measurement to one place and sort it. That is exact, but bandwidth, storage and query time grow with traffic. NSF award 2544434 describes the same tension: telemetry about traffic, resource use and failures can be too large to analyze in full when operators need answers quickly (National Science Foundation).

A small example shows the size of the error. Host A serves 1,000,000 requests in an hour with a local p99 of 50 ms. Host B is overloaded and serves 1,000 requests with a local p99 of 900 ms. Averaging gives 475 ms, which crosses a 300 ms alert and pages an engineer. Pooled, the true fleet p99 is about 50 ms, since Host B served only 0.1 percent of the traffic. The alert was false. If one busy host were slow and many quiet hosts fast, the average would instead hide a real slowdown. These numbers are invented to show the effect.

A middle path exists: each host sends a small summary, called a sketch, that can be merged with the others into a summary of all the data. Whether those merged summaries stay accurate under uneven traffic and tight memory is what this project investigates.

## 2. Evidence

The NSF award, CAREER: Approximation First Telemetry for Hyperscale Networked Systems at the University of Maryland, College Park (June 2026 to May 2031), funds this research area. Its first thrust is mergeable summaries that track their own uncertainty, and its second is answering queries directly from summaries (National Science Foundation). That shows the problem is recognized and funded, though not that it occurs in any particular fleet.

Agarwal et al. define what a mergeable summary must do: two summaries combine into a summary of the combined data while keeping the same error and size guarantees. Masson, Rim and Lee show that DDSketch meets this definition with a relative error guarantee, and that sketches with only a rank error guarantee can give large relative errors on skewed data, which is exactly the shape of latency data.

For real data, Alibaba's public 2022 microservices trace records the response time of each call and the container that served it, so each container can play the role of a host (Alibaba Group). Winchester et al. report that workloads in an Alibaba production deployment follow long tailed distributions, which supports the uneven traffic condition, though I still have to check it for the containers I use.

I have not observed the problem myself yet. My first measurement will be the gap between the averaged p99 and the exact p99 on one slice of the Alibaba trace. My working belief is that the error is driven more by how uneven traffic is than by how many hosts there are, but I have not tested that.

## 3. Existing Solutions

| Approach | How it addresses the problem | Strengths | Limitations or questions |
| --- | --- | --- | --- |
| Averaging local p99 values | Each host sends one number and the dashboard averages them | Smallest possible report, trivial to combine | Wrong under uneven traffic, since percentiles do not add (Prometheus Authors) |
| Exact pooling | Every host sends every latency | Exact answer; the reference for every test | Cost grows with traffic: about 80 MB for 10 million requests at 8 bytes each |
| Fixed bucket histogram | Hosts count requests in latency ranges agreed in advance and the counts are added | Merges exactly (Prometheus Authors) | Accuracy depends on bucket edges chosen before seeing the data |
| KLL sketch | Compacting buffers that keep a rank error bound | Near optimal space and mergeable (Karnin et al.) | Rank error can still mean large relative error in a heavy tail |
| DDSketch | Buckets of fixed relative width, merged by adding counts | Fully mergeable with a relative error bound (Masson et al.) | Covering 1 ms to 10 s at 1 percent accuracy takes about 461 bins, roughly 7.2 KiB, more than small budgets allow |
| t digest | Clusters of values, finer near the extremes | Reported to be very accurate near the tails and used for monitoring at large companies (Dunning and Ertl) | Its accuracy is shown mostly by experiment rather than a worst case merge bound |

DDSketch is the most promising for latency because its guarantee is relative, so a 1 percent bound means 1 percent at p99 no matter how long the tail is. The main question is what happens at budgets below what it needs for the full latency range, where it must either loosen its accuracy or merge its lowest buckets, and whether that still holds when hundreds of uneven host summaries are merged.

## 4. Relating the Problem to My Senior Project

The subject of this project is the distributed system itself: how separate machines that share information only by messages can produce one correct fleet answer. No host sees every request, each must send something far smaller than its raw data, reports arrive in any order, and some never arrive. The project is a one student slice of the NSF award, covering the first thrust and, in Semester II, part of the second.

Adaptive design, reusing an existing solution for a different need (Driscoll et al., ch. 1), describes the approach. I am not inventing a new sketch from scratch. I take published, open source summaries and measure them under conditions the papers do not report for my setting: many simulated hosts, uneven traffic, and a fixed small budget per host, on a real production trace. The result is a decision guide for which summary to use for which data shape.

**How this differs from and improves on my initial topic.** My initial topic was [A15](../V1_A15_Problem_Understanding_Paper.md), a resilient pipeline for dataset enrichment. It studied how a restart duplicates or loses records when a worker crashes between saving a batch of rows and recording that the batch is done, using USGS earthquake data, Python and Delta Lake. After my presentation, my professor said A15 had to be narrowed to a slice of work another group is funded for, or replaced with another project. This topic answers that directly. It is a clearly bounded slice of an active NSF award, approved by my professor, while A15 only cited the NSF AI Datasets call as broad motivation. It also has stronger evidence. A15 had no verified production incident, and its own assumptions admitted that I could not show how many pipelines separate output and progress writes. Here, the Prometheus documentation states the averaging failure outright, and a public Alibaba production trace lets me measure it on real data instead of synthetic records. The research question is also more open. A15 narrowed to whether one existing fix, Delta transaction identifiers, was as safe as another, MERGE, which my dry run had already shown passing. This topic asks how merged error changes with memory, host count and skew, so the result is a set of measurements and a decision guide rather than a single pass or fail. It still runs on one laptop with public data. It also carries forward what I learned in A15, since the rule that no record may be counted twice or silently dropped when summaries are merged is the same duplicate and loss problem in a new setting. Finally, it suits my goal of working between data science and data engineering, because it combines distributions and error analysis with distributed aggregation.

## 5. What I Still Do Not Know

| Question | How I might investigate it |
| --- | --- |
| Does a merged DDSketch keep the fleet p99 within 1 percent as hosts grow from 4 to 256 and traffic becomes more uneven? | Simulate hosts with controlled skew, merge their sketches and compare with the exact p99 over 5 seeds |
| At 512 bytes and 2 KiB per host, is it better to loosen DDSketch's accuracy or merge its lowest buckets? | A small trial on synthetic data before the main runs, checking whether p99 stays above the merged range |
| Is traffic across Alibaba containers uneven enough, with at least 1,000 calls per container, for the averaging error to show? | Download one 3 minute file in week 1 and count calls per container for the busiest microservices |
| How much better is a sketch than a simple sample at the same memory? | Run uniform sampling at the same budgets and compare error at p99 and p99.9 |

## 6. One Early Risk

The main risk is that the project reads as a demonstration of existing libraries with no finding of its own. If DDSketch simply works everywhere, there is little to report. To manage this, the first experiment must show the averaging failure on real data, and the contribution is the measured behavior at small budgets and high skew, where the documented guarantee no longer applies, plus the decision guide. A smaller technical risk is the dataset: the Alibaba trace has no license file and some known inconsistencies, so I will not copy it into my repository, I will commit only the download and filtering steps, and I will count every row I drop.

## 7. Connecting the Readings

The idea of adaptive design changed how I framed the project. I first thought I needed a new mechanism, as in A15, but mergeable sketches already exist, so my work is to adapt and evaluate them for a setting they are not documented for (Driscoll et al., ch. 1). The reading also says to study existing solutions before deciding whether to modify one or build something new (Driscoll et al., ch. 2), which is why Section 3 compares six approaches before choosing DDSketch as the main candidate and keeping averaging and sampling as baselines. The risk management process (Driscoll et al., ch. 3) shaped Section 6, separating the project risk of having no finding from the technical risk of the dataset.

## Works Cited

Agarwal, Pankaj K., et al. "Mergeable Summaries." *ACM Transactions on Database Systems*, vol. 38, no. 4, 2013, dimacs.rutgers.edu/~graham/pubs/html/AgarwalCormodeHuangPhillipsWeiYi13.html.

Alibaba Group. "Cluster Trace Microservices v2022." *GitHub*, github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2022. Accessed 14 Nov. 2026.

Dean, Jeffrey, and Luiz André Barroso. "The Tail at Scale." *Communications of the ACM*, vol. 56, no. 2, 2013, pages 74 to 80, research.google/pubs/pub40801/.

Driscoll, Mark, et al. *Engineering Capstone Design: Project Planning, Organizing, and Executing*. Wiley, 2024.

Dunning, Ted, and Otmar Ertl. "Computing Extremely Accurate Quantiles Using t-Digests." *arXiv*, 2019, arxiv.org/abs/1902.04023.

Karnin, Zohar, Kevin Lang, and Edo Liberty. "Optimal Quantile Approximation in Streams." *Proceedings of the 57th IEEE Symposium on Foundations of Computer Science*, 2016, pages 71 to 78, arxiv.org/abs/1603.05346.

Masson, Charles, Jee E. Rim, and Homin K. Lee. "DDSketch: A Fast and Fully-Mergeable Quantile Sketch with Relative-Error Guarantees." *Proceedings of the VLDB Endowment*, vol. 12, no. 12, 2019, www.vldb.org/pvldb/vol12/p2195-masson.pdf.

National Science Foundation. "Award 2544434: CAREER: Approximation-First Telemetry for Hyperscale Networked Systems." University of Maryland, College Park, www.nsf.gov/awardsearch/show-award?AWD_ID=2544434.

Prometheus Authors. "Histograms and Summaries." *Prometheus Documentation*, prometheus.io/docs/practices/histograms/. Accessed 6 Nov. 2026.

Winchester, Giles, et al. "Complexity at Scale: A Quantitative Analysis of an Alibaba Microservice Deployment." *arXiv*, 2025, arxiv.org/abs/2504.13141.
