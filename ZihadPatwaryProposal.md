# When Identical Readings Are Not Duplicates

**Recovery and Provenance in a Sensor Processing Pipeline**

**Zihad Patwary**

CSC 59866, Senior Project I

## Overview

**Thesis.** A sensor pipeline that recovers from a checkpoint can commit the same reading three times under unaligned checkpoints. A sensor sink cannot always deduplicate by content, because two identical temperature readings at the same millisecond are legitimate data. I compare recovery rules and test whether a lightweight provenance record can tell a legitimate repeated reading apart from a recovery duplicate.

### Sections

| Section | Core claim |
| --- | --- |
| 1. The problem | Recovery can commit the same sensor reading more than once, and content cannot separate a duplicate from a legitimate repeat |
| 2. Who is affected | Environmental researchers and monitoring teams receive inflated counts or invisible duplicates |
| 3. Evidence | Flink documentation and three open issues establish the failure; no run of my own yet |
| 4. Existing solutions | Aligned checkpoints, unaligned checkpoints, idempotent sinks, and provenance records each leave something open |
| 5. Key unknown | Can a per record provenance token distinguish a legitimate repeat from a recovery duplicate without a unique sensor value |
| 6. Individual scope | One generated sensor stream, one append only sink, one forced restore, two checkpoint modes |
| 7. SIFTER ARA summary | What the published opportunity says, section by section |
| 8. Sources and acronyms | Source addresses and first use definitions |

## 1 The problem

**Main point.** I am investigating why a sensor processing pipeline can record the same reading more than once after it recovers from a checkpoint, and why the usual fix, an idempotent sink, does not work when the data itself contains legitimate identical values.

### 1.1 Define the terms

| Term | Meaning |
| --- | --- |
| Sensor reading | One measurement from one device at one time, such as a temperature of 21.5 degrees at 10:00:00.000 |
| Sink | The final destination that writes readings, such as a file or a time series store |
| Checkpoint | A saved snapshot of processing state and source position, used to restart after a failure |
| Aligned checkpoint | The pipeline pauses at a barrier so every operator snapshots the same point in the stream |
| Unaligned checkpoint | The pipeline does not pause, and records in flight are stored as part of the snapshot |
| Committable | A unit of output that the sink must commit after a checkpoint completes |
| Idempotent | Doing something twice gives the same result as doing it once |

### 1.2 When it happens

The failure considered here has three conditions.

1. The pipeline uses unaligned checkpoints, typically because of backpressure or a slow data path.
2. A boundary committable can shift across runs, so the same output is committed in the first run, committed again on restore, and committed again during normal processing.
3. The sink cannot deduplicate by content, because two readings from the same device at the same time can legitimately be identical.

### 1.3 Worked example, a temperature sensor stream

| Case | What the pipeline does | Result after restore |
| --- | --- | --- |
| Normal | Reads one temperature reading, processes it once, commits once | One row |
| Aligned checkpoint | Commits in run 1 and commits again on restore | Two rows, both from the same reading |
| Unaligned checkpoint | The boundary committable shifts, so run 1 commits, restore commits, and normal processing commits again | Three rows from one reading |

The Flink issue tracker states this directly for unaligned checkpoints: a boundary committable can shift, so it is committed in run 1, re committed on run 2 restore, and committed again in run 2 normal processing, for three times. https://issues.apache.org/jira/browse/FLINK-39954

The hard part is not the count. It is that a real sensor can emit the same value at the same time twice. A temperature reading of 21.5 degrees at 10:00:00.000 from device A is a valid second observation. Deduplicating by content would delete real data. That is why the Flink test cannot make its committer idempotent: the source emits each value twice legitimately, so those committables are byte identical, and there is no unique transaction or committable id to dedupe on. https://issues.apache.org/jira/browse/FLINK-39954

### 1.4 Boundaries

**In scope:** one sensor stream, one append only sink, one forced restore from checkpoint N, aligned versus unaligned checkpoints, and readings that may be identical by value and time.

**Out of scope:** corrupted sensor hardware, malicious data, multi cluster deployment, exactly once sinks that already have a primary key, and network partitions between separate pipelines.

### 1.5 Why it is hard to spot

A schema check passes because every row is well formed. A row count comparison may look plausible because the extra rows are small in number. Only a reference answer built from one clean pass reveals that one reading became three.

## 2 Who is affected

**Main point.** Monitoring teams and researchers can receive data that looks complete and valid but contains repeated observations, and they cannot tell which rows came from a recovery replay.

### 2.1 Affected parties and consequences

| Affected party | What goes wrong | Tie back to the temperature example |
| --- | --- | --- |
| Environmental researchers | A repeated reading can inflate an average or a count of events | Three rows for one reading raise the daily count |
| Monitoring teams | Duplicate rows consume storage and complicate alerting | A spike threshold may trigger on repeated values |
| Analysts building models | Repeated examples receive extra weight, and legitimate repeats are indistinguishable from duplicates | A model sees three copies of the same reading |
| The pipeline itself | Output no longer matches the number of readings the source emitted | The sink holds three rows for one reading |

### 2.2 Why the consequences matter

Duplicated readings waste storage and computation, and they make a dataset unreliable for trend analysis. The SIFTER announcement describes resilient exploitation in denied, degraded, interrupted, and limited battlespace, where sensors emit under unreliable connectivity and backpressure is common. https://sam.gov/workspace/contract/opp/3312785693294231b7e1832f5f83a4e2/view That is exactly the condition that triggers unaligned checkpoints.

### 2.3 Limits of these claims

These are plausible consequences. I have not measured how often a real sensor stream contains identical values, nor how much a duplicate shifts a specific analysis.

## 3 Evidence

**Main point.** The Flink documentation and three open issues establish that recovery can duplicate output under unaligned checkpoints, and that a sink without a unique identifier cannot always deduplicate it. I have not run my own pipeline yet.

### 3.1 Documented facts

| Claim | Source | What it proves and does not prove |
| --- | --- | --- |
| Under unaligned checkpoints a boundary committable is committed in run 1, again on restore, and again in normal processing, for three times | FLINK-39954 | Proves the triple commit path exists and is contract permitted. Does not prove how often a real sensor pipeline hits it |
| The Committer contract permits repeated commits and states that a commit must be idempotent, because Flink will restart from a previous checkpoint and re attempt to commit all committables | FLINK-39954 quoting the Committer JavaDoc | Proves the system assumes the sink can absorb repeats. Does not prove that a sensor sink can absorb them |
| Under unaligned checkpoints a task may consume data after the barrier before checkpointing, producing duplicated data | FLINK-17568 | Proves the duplication also occurs on the consumption side. Does not prove the exact count in a sensor pipeline |
| A source without state recording how many rows it emitted reads all rows again after restore, so downstream operators process every row twice | FLINK-41217 | Proves a source side replay path exists. Does not prove behavior of a sensor source that does keep state |
| NSF AI Datasets asks for robust data pipelines and says proposals should address dataset security and integrity | NSF 26-512 | Proves funders want reliable pipelines. Does not prove that restart duplicates occur in practice |

Addresses for this section.

* https://issues.apache.org/jira/browse/FLINK-39954
* https://issues.apache.org/jira/browse/FLINK-17568
* https://issues.apache.org/jira/browse/FLINK-41217
* https://www.nsf.gov/funding/opportunities/ai-datasets-unlocking-dataset-value-ai-enabled-scientific-discovery/nsf26-512/solicitation

### 3.2 Reported and observed

**Reported in FLINK-39954:** under aligned checkpoints the pattern is deterministic at two times, and under unaligned checkpoints it becomes three times. The issue is Open, Major, and Unresolved, with a pull request attached. https://issues.apache.org/jira/browse/FLINK-39954

**Observed in the Flink documentation:** unaligned checkpointing stores in flight data in the snapshot, and on restore those records will occur as duplicates if alignment is skipped. https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/

**Observed by me so far:** I have read the Flink documentation and the three issues. I have not yet built the sensor pipeline or run the restore.

### 3.3 Assumptions and missing evidence

**Assumption:** a sensor stream can contain legitimate identical readings at the same device and time. This is true for repeated polling and for sensors that resend a value, and I will state the exact generator rule in my experiment.

**Missing:** a measured duplicate count for a sensor pipeline, a measured cost for a provenance record, and a verified production incident in a sensor deployment.

## 4 Existing solutions

**Main point.** The existing approaches either reduce the number of commits or require the sink to deduplicate. None of them solves the case where content is legitimately identical and the sink has no key.

### 4.1 Comparison of approaches

| Approach | How it works | Handles well | Limits under my conditions |
| --- | --- | --- | --- |
| A. Aligned checkpoints | The pipeline pauses at a barrier, so the replay pattern is deterministic at two times | A known, repeatable duplication count | Still duplicates once, and adds latency under backpressure |
| B. Unaligned checkpoints | The pipeline does not pause, and in flight records are stored in the snapshot | Low latency under backpressure | The commit pattern becomes three times, and the extra commit is contract permitted |
| C. Idempotent sink | The sink deduplicates repeated commits by a key or an identifier | Works when the sink has a unique key | Fails when the reading has no unique id, and content dedupe would delete a legitimate repeat |
| D. Provenance record | Each output row carries a record of which run and checkpoint produced it | Can separate a legitimate repeat from a recovery duplicate | Flink checkpoints do not natively map an output row to a checkpoint |

Sources for this table: Flink documentation and FLINK-39954, addresses listed at the end of the paper.

### 4.2 How the approaches differ

Approach A makes the duplication predictable, which is useful for measurement but does not remove it. Approach B reduces latency but increases the duplication count. Approach C is the documented answer and works only when the sink can deduplicate. Approach D is the only one that addresses the identification problem, but Flink does not provide it, so it would have to be built.

### 4.3 Implications for the comparison

The open question is not whether Flink can duplicate. It can, and the documentation says so. The open question is whether a provenance token can distinguish a legitimate repeat from a recovery duplicate when the reading itself carries no unique value. That is the part the existing solutions leave open.

## 5 Key unknown

**Main point, the central unknown.** Can a lightweight per record provenance token distinguish a legitimate repeated reading from a duplicate produced by recovery, without requiring the sensor reading to carry a unique value?

### 5.1 Why this unknown matters most

The duplicate count alone is not enough. If the pipeline records three rows for one reading, a provenance record that says rows 1 and 2 came from run 1 and run 2 restore, and row 3 came from normal processing, lets an analyst decide which rows are legitimate. Without it, the sink holds three identical rows and no way to choose. The SIFTER emphasis on resilient exploitation in degraded environments makes this a practical question, not only a measurement question. https://sam.gov/workspace/contract/opp/3312785693294231b7e1832f5f83a4e2/view

### 5.2 Experiment to resolve it

1. Generate a sensor stream with one device and a known number of legitimate repeated values. The generator records the true emission count for each value and time.
2. Write to an append only sink with no primary key.
3. Run under aligned checkpoints and under unaligned checkpoints.
4. Force a restore from checkpoint N before the source records that it has finished.
5. Add a provenance token to each row: run id, checkpoint id, and the task that wrote it.
6. Compare four measures: duplicate rows, missing rows, provenance completeness, and whether the token separates a legitimate repeat from a recovery duplicate.

### 5.3 Decision rule

| If the result shows | Then the design |
| --- | --- |
| The provenance token separates legitimate repeats from recovery duplicates in both checkpoint modes | Report the token design and its cost, and recommend it for append only sensor sinks |
| The token separates them under aligned but not unaligned checkpoints | Report the unaligned gap and propose a narrower token that records the committable shift |
| The token cannot separate them without a unique sensor id | Report that the sink cannot be made safe by provenance alone, and that a source side identity is required |

### 5.4 How findings influence design

A failure would show that provenance must be generated closer to the source, not at the sink. A success would show that a small record is enough for an append only sensor sink, which is cheaper than requiring every sensor to emit a unique id.

## 6 Individual scope

**What I will investigate.** I will compare aligned and unaligned checkpoints in a single sensor pipeline, measure duplicate and missing rows after a forced restore, and test whether a per record provenance token separates a legitimate repeated reading from a recovery duplicate.

**What I will exclude.** Multi cluster deployment, cloud object stores, streaming sources other than my generator, schema changes, and sensors that already emit a unique reading id.

**The comparison.** Aligned checkpoints versus unaligned checkpoints, with and without a provenance token, judged on duplicate rows, missing rows, provenance completeness, and recovery time.

### 6.1 Tools and data

| Tool or data | Role |
| --- | --- |
| Apache Flink | Stream processing and checkpointing |
| A Python sensor generator | Produces readings, including legitimate repeats, with a known true count |
| An append only file sink | Writes rows without a primary key |
| A local fault trigger | Forces a restore from checkpoint N |
| pytest | Unit tests for the generator and the token |

**Possible solution direction, not proven.** A per record provenance token that carries run id, checkpoint id, and writer task id. The token is provisional until it is tested in both checkpoint modes.

**Why one student can do it.** It needs one laptop and a local Flink cluster, the sensor stream is generated, and the check is a comparison against the generator true count. The pipeline is small and the measures are simple.

## 7 SIFTER ARA summary

**Published opportunity, SIFTER, ARA FA8750-24-S-7007.** The Air Force Research Laboratory calls for research in resilient signal exploitation and reporting, including Technology Area 4 on resilient exploitation in denied, degraded, interrupted, and limited battlespace. https://sam.gov/workspace/contract/opp/3312785693294231b7e1832f5f83a4e2/view

### 7.1 Key facts

| Item | Detail |
| --- | --- |
| Title | Signals Intelligence Focused Technologies for Exploitation and Reporting (SIFTER) |
| Number | ARA FA8750-24-S-7007 |
| Type | Open, two step advanced research announcement |
| Initial submission | White papers only, formal proposals by invitation |
| Open until | 28 September 2029 |
| Suggested dates | FY27 by 25 September 2026, FY28 by 25 September 2027, FY29 by 25 September 2028 |
| Technology Area 4 | Resilient exploitation in denied, degraded, interrupted, and limited battlespace |

### 7.2 Section by section

| Section | What it says | What it means for B20 |
| --- | --- | --- |
| Technology Requirements | Seeks algorithms and techniques for signal processing, exploitation, dissemination, and analytics | The sensor pipeline is a small slice of this area |
| Technology Area 4 | Resilient exploitation in DDIL environments | Recovery under unreliable connectivity is directly relevant |
| Award Information | Multiple awards anticipated, normally one million to five million dollars | Award size does not establish student fit |
| Eligibility | Open to qualified offerors, closed to foreign participation | This is a contracting opportunity, not a student grant |
| Review Criteria | Scientific merit, related experience, maturity, and cost realism | My project is a bounded study, not a white paper submission |

### 7.3 Connection to the paper

SIFTER motivates resilient sensor processing under degraded conditions. It does not establish a specific duplicate commit incident. The proposed comparison is a bounded student study within that broader area.

## 8 Sources and acronyms

### 8.1 Sources

| Role | Source | Full web address, supports, and status |
| --- | --- | --- |
| Published opportunity | SIFTER ARA FA8750-24-S-7007 | https://sam.gov/workspace/contract/opp/3312785693294231b7e1832f5f83a4e2/view Supports motivation and DDIL context. Official announcement, checked October 26, 2026 |
| Technical documentation | Flink stateful stream processing | https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/ Supports checkpoints, unaligned behavior, duplicates on restore. Primary documentation |
| Active fault | FLINK-39954 | https://issues.apache.org/jira/browse/FLINK-39954 Supports triple commit under unaligned checkpoints and no unique id to dedupe. Open, Major, Unresolved |
| Supporting fault | FLINK-17568 | https://issues.apache.org/jira/browse/FLINK-17568 Supports consumption side duplication under unaligned checkpoints. Open |
| Supporting fault | FLINK-41217 | https://issues.apache.org/jira/browse/FLINK-41217 Supports source replay after restore. Open |
| Secondary motivation | NSF 26-512 AI Datasets | https://www.nsf.gov/funding/opportunities/ai-datasets-unlocking-dataset-value-ai-enabled-scientific-discovery/nsf26-512/solicitation Supports robust pipelines and dataset integrity. Active solicitation |

### 8.2 Acronyms

| Acronym | Meaning |
| --- | --- |
| ARA | Advanced Research Announcement |
| DDIL | Denied, Degraded, Interrupted, and Limited |
| Flink | Apache Flink |
| NSF | National Science Foundation |
| SIFTER | Signals Intelligence Focused Technologies for Exploitation and Reporting |
