# Zihad Patwary, CSC 59866 Senior Project I

## Project

Approximation First Telemetry with Mergeable Quantile Summaries. A one student study of how accurately mergeable quantile summaries answer fleet level monitoring questions when data is split across many simulated nodes, skewed and bursty, under a fixed memory budget.

The project is a slice of NSF award 2544434, Approximation First Telemetry for Hyperscale Networked Systems (University of Maryland, College Park), covering only the first two research thrusts: mergeable summaries with error tracking, and a simple query layer.

## Documents

### Final Topic

| Document | What it is |
| --- | --- |
| [Problem Understanding Paper](Final_Topic_Problem_Understanding_Paper.md) | The five questions, my individual scope, and how this topic improves on A15 |
| [Candidate Problem Background](Final_Topic_Candidate_Problem_Background.md) | Problem, evidence, existing solutions, open questions, early risk, readings, and how this topic improves on my earlier topics |
| [Proposal](ZihadPatwaryProposal.md) | The full project proposal |
| [Design document](DESIGN.md) | The weekly design document for the course; its figures and editable sources are in [assets/](assets/) |

### Initial Topics

The topics I worked on before choosing the final topic, kept for the record.

| Document | Date | Topic |
| --- | --- | --- |
| [Candidate Problem Background](Candidate_Problem_Background.md) | Sep 28, 2026 | Recovering interrupted AI document analysis jobs while minimizing repeated work |
| [A15 Problem Understanding Paper](A15_Problem_Understanding_Paper.md) | Oct 19, 2026 | Safe restarts in a dataset enrichment pipeline (USGS earthquake data, Python and Delta Lake) |

## At a glance

- **Problem:** A correct fleet level percentile cannot be built from per host percentiles, and shipping every raw measurement costs too much.
- **Approaches compared:** exact aggregation, uniform sampling, and mergeable sketches (KLL, DDSketch and t digest).
- **Experiments:** show the failure, single node accuracy, a merge study across nodes, and a query layer test.
- **Excluded:** learned compression, the configuration management engine, and any claim of true hyperscale. Scale is simulated.
- **Deliverables:** a simulator, a minimal mergeable sketch of my own, error versus memory results, and a decision guide.
