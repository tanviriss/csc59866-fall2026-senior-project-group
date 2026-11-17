# V1: Candidate Problem Background

> **V1, initial candidate problem.** This is my first Candidate Problem Background, written September 28, 2026, before I moved to A15 and then to my final topic. It is kept as written for the record and is no longer active. My final topic papers are [Final_Topic_Problem_Understanding_Paper.md](Final_Topic_Problem_Understanding_Paper.md) and [Final_Topic_Candidate_Problem_Background.md](Final_Topic_Candidate_Problem_Background.md).

[Zihad Patwary] · Senior Project I  
**Candidate Problem Background**

## Recovering Interrupted AI Document-Analysis Jobs While Minimizing Repeated Work

### Part 1: Describe the Problem

Developers and student researchers increasingly run multi-step AI jobs over collections of documents. A representative task extracts specified facts and supporting passages from each document, then combines the results into a traceable report. Their goal is a complete, verifiable set of results for every document.

This work is commonly implemented either as a plain script that loops over the documents and calls a model API, often skipping any document whose output file already exists, or through workflow frameworks that add retries, saved intermediate results, and checkpoints. I still need to determine which approach the intended users actually employ.

The difficulty arises when execution stops after some work has succeeded but before the job finishes: a worker process stops, a request times out, or a model or storage service becomes temporarily unavailable. The operator must then determine which results remain usable, which tasks are unfinished, and which outcomes are uncertain because a request may have completed without a confirmed response. Restarting too much repeats expensive analysis; assuming too much has finished omits required work.

The problem matters because repeated model requests may increase token usage, cost, and completion time, and because a report that silently omits documents is not trustworthy. The size of these effects depends on when the interruption occurs and how the existing recovery path behaves, so they must be measured rather than assumed.

### Part 2: Provide Evidence

**Documented:** A missing response can leave a caller unable to tell whether a remote operation succeeded, which makes naive retries unsafe [1]. This establishes the uncertainty mechanism, but not how often it occurs in document-analysis workloads.

**Documented:** Recovery tools already exist. LangGraph checkpoints workflow state and, when one node fails, keeps the writes of nodes that completed in the same step so they are not re-run [2]. Prefect supports task retries and reuse of persisted results [3, 4]. Recovery itself is therefore not a new idea.

**Documented:** Prompt caching reduces repeated input processing but does not eliminate output generation [5]. Reusing a saved analysis result and getting a cache hit are different operations.

**Reported:** LangGraph developers have reported recovery edge cases, including a crash before the first checkpoint leaving no record that a run was accepted [6] and a completed error handler re-executing on resume [7]. These show that recovery boundaries are subtle even in a mature tool; they do not show how often my proposed users encounter them.

**Hypothesized:** The intended users experience meaningful avoidable repetition, and a narrowly scoped adaptation could reduce repeated model work compared with a correctly configured existing tool while preserving completeness.

**Observed:** None yet. I have not collected measurements or first-hand incident reports.

### Part 3: Investigate Existing Solutions

The comparison table below covers a common manual method, two workflow frameworks, and a durable-execution platform. Configuration matters: LangGraph offers three durability modes, and only "sync" persists state before the next step begins [2]. Prefect caching requires result persistence, which is off by default, and its default cache key includes the flow-run ID [4]. A fair comparison must specify these settings, because a feature I have not configured is not a missing feature. If a properly configured tool already meets the requirements, my contribution should shift toward evaluation or a different problem.

| Approach | How It Addresses the Problem | Strengths | Limitations / Questions |
| --- | --- | --- | --- |
| Skip-if-output-exists script (common practice; hypothesized) | On restart, reruns the job and skips documents whose output file already exists. | Simple and transparent; no framework to learn. | Cannot detect partial or invalid outputs or requests with uncertain outcomes; tracks completion only per file. |
| LangGraph checkpointing [2] | Saves graph state at each step and resumes from the last checkpoint, keeping completed nodes' writes. | Built for AI workflows; several persistence backends; configurable durability. | Protection depends on the durability mode and node boundaries; developers have reported edge cases [6, 7]. |
| Prefect retries and result caching [3, 4] | Retries failed tasks and reuses persisted results when the cache key matches. | General-purpose; retry and cache policies set per task. | Persistence is off by default; the default key includes the flow-run ID, so a new run may not reuse earlier results. |
| Temporal durable execution [8, 9] | Records an event history so a workflow resumes from its last recorded event after a failure; activities are retried automatically. | Mature platform designed for long-running jobs that survive process failure. | Retried activities (such as model calls) should be idempotent, so a call may still repeat; requires running a Temporal service and has a learning curve. |

### Part 4: Relate the Problem to My Senior Project

**Project option:** Option 1 (Distributed Systems Tool) fits best, because the focus is recovery behavior in AI-processing infrastructure rather than one organization's application. Option 2 would fit better if a verified domain need became central.

**Type of design:** Mainly adaptive and selection design: adapting existing recovery mechanisms to a bounded workflow and selecting suitable components. Redesign would apply only if testing revealed a limitation in an existing component. I am not claiming original design.

**Distributed-systems relevance:** A worker, a model service, and a storage service communicate over a network and can fail independently. A service may finish an operation while the worker never receives confirmation, so progress records and actual outcomes can disagree. If multiple workers share a job, coordination becomes important: a task held by a crashed worker must be completed once, not lost or duplicated. Partial failure, reliability, and coordination apply; large scale and geographic distribution are not central.

### Part 5: What I Still Do Not Know

| Question | How I Might Investigate It |
| --- | --- |
| Who experiences consequential repeated work, and how often? | Interview developers or student researchers about a specific interrupted job, and search framework issue trackers and forums for incident reports. |
| Does a correctly configured existing tool already satisfy the recovery requirements? | Review documentation and source code, then later run controlled interruptions at defined points with recorded settings. |
| Does reducing repetition produce a net benefit without reducing completeness? | Compare equivalent jobs with and without failures, counting model requests, token categories, cost, time, and output correctness. |

### Part 6: Early Risk

The main risk is technical complexity. Distinguishing saved results from uncertain remote outcomes, and evaluating recovery fairly, may be difficult for a beginner within two semesters. A second risk is that existing tools already meet the requirements, leaving too little room for a meaningful contribution.

### Part 7: Connect the Readings

**Types of Engineering Design:** The adaptive-design category changed my expected contribution. Rather than inventing checkpointing, I should apply existing recovery mechanisms to a specific requirement and justify that adaptation [10].

**Research and Analysis of Existing Solutions:** Studying alternatives before designing means I must test existing tools as an informed user would configure them before claiming a gap [11].

**Communications:** Keeping a design notebook means logging each claim with its label (documented, reported, observed, or hypothesized) so that changes to the problem statement remain traceable [12].

### References

Online sources accessed September 28, 2026.

1. M. Featonby, "Making retries safe with idempotent APIs," Amazon Builders' Library, Amazon Web Services. [https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
2. LangChain, "Checkpointers," LangGraph documentation. [https://docs.langchain.com/oss/python/langgraph/checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers)
3. Prefect, "How to automatically rerun your workflow when it fails," Prefect documentation. [https://docs.prefect.io/v3/how-to-guides/workflows/retries](https://docs.prefect.io/v3/how-to-guides/workflows/retries)
4. Prefect, "Caching," Prefect documentation. [https://docs.prefect.io/v3/concepts/caching](https://docs.prefect.io/v3/concepts/caching)
5. Anthropic, "Prompt caching," Claude Platform documentation. [https://platform.claude.com/docs/en/build-with-claude/prompt-caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
6. LangGraph GitHub issue #8764, "Crash before first durable checkpoint can silently drop an accepted run with no durable failure record." [https://github.com/langchain-ai/langgraph/issues/8764](https://github.com/langchain-ai/langgraph/issues/8764)
7. LangGraph GitHub issue #9002, "error_handler is executed again on resume even if it already ran and commited its write." [https://github.com/langchain-ai/langgraph/issues/9002](https://github.com/langchain-ai/langgraph/issues/9002)
8. Temporal, "Temporal Workflow Execution overview," Temporal documentation. [https://docs.temporal.io/workflow-execution](https://docs.temporal.io/workflow-execution)
9. Temporal, "What is a Temporal Activity?," Temporal documentation. [https://docs.temporal.io/activities](https://docs.temporal.io/activities)
10. *Engineering Capstone Design: Project Planning, Organizing, and Executing*, "01-Types of Engineering Design," course-provided reading, pp. 3–5.
11. *Engineering Capstone Design: Project Planning, Organizing, and Executing*, "02-Research and Analysis of Existing Solutions," course-provided reading, pp. 1–2.
12. *Engineering Capstone Design: Project Planning, Organizing, and Executing*, "03-Communications," course-provided reading, pp. 1–2.
