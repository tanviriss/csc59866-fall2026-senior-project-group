# Zihad Patwary, CSC 59866 Senior Project I

## Project

Approximation First Telemetry with Mergeable Quantile Summaries. A one student study of how accurately mergeable quantile summaries answer fleet level monitoring questions when data is split across many simulated nodes, skewed and bursty, under a fixed memory budget.

The project is a slice of NSF award 2544434, Approximation First Telemetry for Hyperscale Networked Systems (University of Maryland, College Park), covering only the first two research thrusts: mergeable summaries with error tracking, and a simple query layer.

## Design document

The weekly design document for the course is [DESIGN.md](DESIGN.md). Its figures and editable sources are in [assets/](assets/).

## Proposal

Read the full proposal: [ZihadPatwaryProposal.md](ZihadPatwaryProposal.md)

## At a glance

- **Problem:** A correct fleet level percentile cannot be built from per host percentiles, and shipping every raw measurement costs too much.
- **Approaches compared:** exact aggregation, uniform sampling, and mergeable sketches (KLL, DDSketch and t digest).
- **Experiments:** show the failure, single node accuracy, a merge study across nodes, and a query layer test.
- **Excluded:** learned compression, the configuration management engine, and any claim of true hyperscale. Scale is simulated.
- **Deliverables:** a simulator, a minimal mergeable sketch of my own, error versus memory results, and a decision guide.

