# Fair Scheduling for Shared AI Computing
 
**Author:** Tanvir Islam  
**Course:** CSC 59866  
**Selected project and option:** A02 Fair scheduling for shared AI computing; Option 1  
**Current assignment:** 3  
**Friday commit deadline:** November 22, 2026, at 11:59 p.m. New York time  
**Monday presentation:** November 23, 2026, at 6:30 p.m. New York time  
**Last updated:** November 22, 2026  
**Document status:** Revised
 
## Progress note
 
This week I selected fair-share scheduling, designed the simulator's six parts, and ran a first feasibility experiment with a small SimPy prototype. Following the grading feedback, I made the burst workload repeatable (Chen's jobs are now listed), stated the strict-order, no-backfilling, no-pausing assumptions, wrote out the priority normalization, and replaced the C2 count check with a job-ID check. The experiment changed my design: in the burst workload, fair-share cut Ana's wait from 59.9 to 5.9 hours with no change in total completion time, but the "longest wait" target failed because Ben's last job waits behind his own batch. I now judge fairness by slowdown for users within their share and report the heavy user's cost separately. Fair-share passed this target in 11 of 11 uneven runs but only 2 of 10 balanced runs. Next I will define data records and test whether gap filling changes these results.
 
## 1 Problem research and scope
 
**Problem and affected people:** Students and researchers share a cluster of GPUs, which are the processors used to train artificial intelligence (AI) models. A scheduler decides which waiting job should run next. If one user submits a large batch of jobs, smaller jobs from other users can end up waiting much longer than they actually take to run. The scheduler has to balance giving users fair access while also keeping the GPUs busy.
 
| Stakeholder | Need | Problem today |
|---|---|---|
| User with small jobs | Quick results | Has to wait behind another user's large batch |
| User with large batches | Finish many long jobs | Fairness rules may limit how many GPUs they can use |
| Cluster administrator | A fair policy that still keeps GPUs busy | Has to choose a policy without fully knowing the trade-offs |
 
**Current workflow:** First, a user submits a job and says how many GPUs it needs and roughly how long it will run. The scheduler then puts the job into a queue. When enough GPUs become available, the next job starts running. After it finishes, the results are returned to the user. The main problem happens when deciding which job should run next. Slurm, a widely used scheduler, uses first-in, first-out (FIFO) ordering by default ([SchedMD, 2019](https://slurm.schedmd.com/SLUG19/Priority_and_Fair_Trees.pdf)), which means jobs are mainly started based on when they were submitted.
 
**Scenario:** An 8-GPU cluster is shared by Ana, Ben, and Chen with equal shares. The scheduler uses strict FIFO: the oldest job must start first, no later job may jump into leftover GPUs (no backfilling), and running jobs are never paused (no preemption). The exact workload is:
 
| User | Jobs | GPUs per job | Run time per job | Submitted at |
|---|---|---|---|---|
| Ben | 20 | 4 | 6 hours | 9:00 a.m. (t = 0) |
| Ana | 1 | 1 | 30 minutes | 9:05 a.m. (t = 5 minutes) |
| Chen | 2 | 2 | 3 hours | 10:00 a.m. (t = 1 hour) |
 
Ben's jobs fill all 8 GPUs, two at a time, for 60 hours. Under strict FIFO, Ana waits 59 hours 55 minutes and Chen waits 59 hours. GPU utilization is high (97.7%), so the cluster looks efficient, but Ana and Chen are treated poorly. The problem is unfair waiting, not idle GPUs.
 
![Three users submit jobs into a first-in, first-out queue. Ben's 4-GPU jobs use all 8 GPUs while Ana's 1-GPU job waits in the queue.](workflow.png)
 
**Figure 1.** The current workflow in this example. Since Ben's batch arrived first and uses all the GPUs, Ana's 30-minute job waits about 2.5 days. This waiting problem is what my project focuses on.
 
**Evidence:**
 
- *Documented:* The National Science Foundation (NSF) AI Infrastructure Hubs program is expanding access to shared AI computing ([NSF 26-513](https://www.nsf.gov/funding/opportunities/us-national-science-foundation-state-regional-artificial)). This shows a growing need, but not that any policy is unfair.
- *Documented:* A study of Microsoft's shared GPU cluster found jobs delayed while waiting for their fair share and for enough GPUs to free up ([Jeon et al., 2019](https://www.usenix.org/conference/atc19/presentation/jeon)).
- *Observed (simulation):* The prototype in Section 9 reproduces the 59 hour 55 minute FIFO wait and measures fair-share's effect.
- *Assumed:* Job run times are known at submission, and the three workloads in this section resemble real student use.
### How I define fair GPU use
 
Fair use in this project means **each user who currently has work gets an equal share of the GPUs over time, and users who stay within their share do not wait far longer than their job sizes justify.** The scheduler distributes GPUs using these rules:
 
| Rule | What it means | Why |
|---|---|---|
| 1. Active users | A user is active at time t if they have at least one job waiting or running. Only active users are counted. | GPUs should not be reserved for a user who is away. |
| 2. Equal share | Each active user's share is S = 1 / (number of active users). With three active users, S = 1/3. | Users are in the same department and no one has a reason for higher priority. Slurm's fair-share also starts from assigned shares ([SchedMD, classic fair-share](https://slurm.schedmd.com/classic_fair_share.html)). |
| 3. Usage in GPU-hours | Usage = GPUs used × hours, including jobs still running. A 4-GPU, 6-hour job counts as 24 GPU-hours. | Counting jobs instead would treat a tiny job and a huge job as equal. |
| 4. Older usage counts less | Usage is cut in half every 24 simulated hours (a "half-life"). | A user who ran a lot last week should not be punished forever. Slurm uses the same idea through its decay half-life setting. |
| 5. Normalized usage | U = the user's decayed GPU-hours ÷ the total decayed GPU-hours of all active users. If the total is 0, every U is 0. | Puts usage and share on the same 0-to-1 scale. |
| 6. Priority | F = 2^(−U / S), Slurm's fair-share formula. The waiting job of the user with the highest F goes next; ties go to the earlier submission, then the lower job ID. | Users below their share move ahead. |
| 7. Strict order | If the chosen job does not fit in the free GPUs, it waits and no other job starts (no backfilling). FIFO follows the same rule. | Keeps the comparison fair: any difference comes from the order rule, not from gap filling. |
| 8. No pausing | A running job always finishes. | Pausing a long training job can lose its work, and pausing is outside my scope. |
 
*Worked priority example.* At t = 6 hours in the burst workload, Ben's first two jobs finish. Active users: Ana, Ben, Chen, so S = 1/3. Ben's decayed usage is 44.07 GPU-hours and the others have 0, so U(Ben) = 44.07 / 44.07 = 1 and U(Ana) = U(Chen) = 0. Priorities: F(Ana) = F(Chen) = 2^0 = 1 and F(Ben) = 2^(−1 / (1/3)) = 2^(−3) = 0.125. Ana goes first (earlier submission), then both of Chen's jobs.
 
**How I will measure whether the result is fair:**
 
- **Light and heavy users.** A user is *light* if their total GPU-hour demand in the workload is at most 1/(number of users) of the total; otherwise they are *heavy*. In the burst workload, Ben is heavy (97% of demand) and Ana and Chen are light. Users with no jobs are excluded from all fairness measures, under both policies.
- **Slowdown per job = (wait + run time) / run time.** This judges each wait against job size. Under FIFO, Ana's slowdown is 120.83.
- **Main fairness measure:** the worst slowdown among light users.
- **Heavy users' cost:** the worst slowdown among heavy users, reported but not limited. Fair-share is expected to make heavy users wait longer.
- **Jain's fairness index (secondary):** J = (x₁ + … + xₙ)² / (n × (x₁² + … + xₙ²)) over each user's average slowdown ([Jain, Chiu, and Hawe, 1984](https://arxiv.org/abs/cs/9809099)). J = 1 when all users have equal slowdown. Worked FIFO burst example: x = (120.83, 5.50, 20.67), so J = 146.99² / (3 × 15,058.4) = 0.478. Under fair-share, x = (12.83, 5.76, 2.67) and J = 0.735. The experiment showed J can be high when everyone waits equally long, so it is reported but does not decide success.
- **Cost measures:** total completion time (first submission to last finish), GPU utilization (busy GPU-hours ÷ 8 × total completion time), and each user's longest wait.
**Success target (proposed design target):** fair-share is better than FIFO if it cuts the **worst light-user slowdown by at least 50%** while increasing **total completion time by no more than 10%**.
 
**Six-week contribution:** A Python simulation, built with the SimPy event library, of one 8-GPU cluster shared by three users with equal shares. The same jobs and seeds run under strict FIFO and fair-share. Three workloads are used:
 
| Workload | Definition |
|---|---|
| Burst | The fixed table above |
| Balanced | Each user submits 10 jobs at random times between 0 and 24 hours |
| One heavy user | Ben submits 30 jobs between 0 and 2 hours; Ana and Chen submit 5 each between 0 and 24 hours |
 
In the random workloads, each job's GPU count is chosen from {1, 2, 4} and its run time from {0.5, 1, 2, 4, 6} hours. Each random workload runs with seeds 1 to 10.
 
**Semester II scope:** Keep the same question, workloads, seeds, metrics, and success target, and add one policy: fair-share with a limit on how many GPUs one user can hold at once. If the public trace fits, add it as a fourth workload.
 
**Exclusions:** This project does not include real hardware, making individual jobs run faster, scheduling across multiple clusters, billing, security, or pausing jobs that are already running.
 
## 2 Requirements and system specification
 
| ID | Required behavior and conditions | Acceptance check | Design and test reference |
|---|---|---|---|
| F1 | Load a job list with user, submit time, GPUs, and run time; reject invalid jobs with a clear message | Burst workload gives 23 accepted jobs; a job asking for 10 GPUs and a job with a negative run time are rejected | Section 5, job loader; Section 9 experiment (passed) |
| F2 | Run the same job list and seed under FIFO and fair-share | Both runs finish the same 23 burst jobs | Section 5, scheduler; Section 9 (passed) |
| F3 | Record each job's start, finish, and wait, and each user's longest wait and slowdown | Under FIFO, Ana's wait is 59 h 55 min and her slowdown is 120.83 | Section 5, results recorder; Section 9 (passed) |
| F4 | Report total completion time, GPU utilization, light and heavy users' worst slowdown, and Jain's index for each run | Burst FIFO: 63.00 h, 97.7%, Jain 0.478 | Section 5, results recorder; Section 9 (passed) |
| F5 | Give identical results for the same input, policy, and seed | Two runs produce identical results | Section 9 (passed for both policies) |
| C1 | GPUs in use never exceed 8, and a job never starts with fewer GPUs than it asked for | Jobs 2 and 3 (4 GPUs each) become ready at the same moment with 4 GPUs free; only one may start | Section 5, operation "start next jobs"; Section 9 (passed) |
| C2 | The set of finished job IDs equals the set of accepted job IDs, every accepted ID starts and finishes exactly once, and no job starts before it was submitted | With accepted IDs {A, B, C}, finishes {A, B, B} must fail, because C is missing and B repeats | Section 5, results recorder; Section 9 (passed) |
| Q1 | Fair-share cuts the worst light-user slowdown by at least 50% versus FIFO, with total completion time no more than 10% higher, on the burst and one-heavy-user workloads | Compare both runs' results on the same jobs and seeds | Proposed target; first measurement in Section 9 |
 
**Inputs and outputs:**
 
*Ordinary example (simulator output, Section 9):*
 
| Policy | Ana's wait | Chen's wait | Ben's longest wait | Worst light-user slowdown | Total completion time | GPU utilization |
|---|---|---|---|---|---|---|
| FIFO | 59.92 h | 59.00 h | 54.00 h | 120.83 | 63.00 h | 97.7% |
| Fair-share | 5.92 h | 5.00 h | 57.00 h | 12.83 | 63.00 h | 97.7% |
 
*Unsuccessful example.* Input: a job asking for 10 GPUs, or with a negative run time. Output: the job is rejected before the simulation starts, with the message "asks for 10 GPUs; cluster has 8" or "run time must be positive," and no results are produced for it.
 
**Assumptions:**
 
- Run times are known when the job is submitted. In real clusters they are estimates; I will check this later by adding random error to run times.
- All 8 GPUs are identical and on one machine, so placement does not matter.
- Both policies use strict order with no backfilling and no pausing.
- Users have equal shares, do not change behavior to game the scheduler, and jobs never fail.
- A public trace is used only if it has arrival time, duration, GPU count, and user identity for each job.
**Constraints:** Six weeks, Python with SimPy on a laptop, no real cluster, and generated job data unless a usable public trace is found.
 
## 3 Alternatives and selected solution
 
| Approach and source | Useful behavior | Limitation | Evidence or assumption |
|---|---|---|---|
| Strict FIFO, simple baseline ([SchedMD, 2019](https://slurm.schedmd.com/SLUG19/Priority_and_Fair_Trees.pdf)) | Simple, predictable, keeps GPUs busy | Light users wait behind a heavy user's batch: Ana's slowdown is 120.83 | Measured in Section 9 |
| Fair-share priority ([SchedMD, classic fair-share](https://slurm.schedmd.com/classic_fair_share.html)) | Moves users below their share ahead | Cannot help until a running job finishes, because there is no pausing; makes heavy users wait longer; no benefit when demand is balanced | Measured in Section 9 |
| Fair-share plus per-user GPU cap (Semester II) | Could keep GPUs free so small jobs start immediately | With a cap of 6 and 4-GPU jobs, Ben can use only 4 of 8 GPUs when alone | Assumed; not built |
| Finish-time fairness, Themis ([Mahajan et al., 2020](https://www.usenix.org/conference/nsdi20/presentation/mahajan)) | Designed for AI jobs; improved fairness by more than 2.25 times on a production trace | Auction design is complex and built for large clusters | Documented; reference only |
 
**Requirement-by-policy comparison** (same jobs, seeds, and checks for every policy):
 
| Requirement | Strict FIFO | Fair-share | Fair-share plus cap | Themis |
|---|---|---|---|---|
| F1 rejects invalid jobs | Pass (shared loader) | Pass (shared loader) | Not built | Not built |
| F5 same seed, same result | Pass | Pass | Not built | Not built |
| C1 never over 8 GPUs | Pass (fixture, burst, 20 random runs) | Pass (fixture, burst, 20 random runs) | Not built | Not built |
| C2 every job ID exactly once | Pass (burst, 20 random runs) | Pass (burst, 20 random runs) | Not built | Not built |
| Q1 burst workload | Baseline: worst light slowdown 120.83 | Pass: 12.83 (−89%), completion +0.0% | Not built | Not built |
| Q1 one-heavy-user workload | Baseline | Pass in 10 of 10 seeds (−65% to −96%; completion −7.3% to +7.9%) | Not built | Not built |
| Balanced workload (not the target problem) | Baseline | Pass in 2 of 10 seeds; sometimes worse | Not built | Not built |
| Heavy user's cost | Baseline | Higher: Ben's worst slowdown rose from 10.0 to 10.5 (burst) and, in one-heavy-user seed 1, from 59 to 90 | Not built | Not built |
 
**Choice and reason:** I select **fair-share priority**, compared against strict FIFO. It meets every correctness requirement and passed Q1 in all 11 uneven-demand runs, which is the problem this project targets, without exceeding the completion-time limit. Its costs are explicit: heavy users wait longer, and it gives no clear benefit when demand is balanced.
 
### Decision 1
 
**Context and requirement:** Q1 needs a policy that protects users who stay within their share, without breaking C1 and C2 or adding more than 10% to total completion time.  
**Options:** strict FIFO only; fair-share priority; fair-share plus a per-user GPU cap; Themis finish-time fairness.  
**Decision and reason:** Fair-share priority. In the experiment it cut the worst light-user slowdown by 65% to 96% in every uneven run, with completion-time changes between −7.3% and +7.9%. Its formula is documented and used by Slurm. The cap is deferred to Semester II, and Themis is too complex for six weeks.  
**Consequences:** Light users are protected; the heavy user's worst slowdown rises (for example, from 59 to 90 in one-heavy-user seed 1). Fair-share cannot help until a running job finishes. Balanced workloads gain little.  
**Status and revisit condition:** Accepted. Revisit if, with gap filling or the public trace, fair-share fails Q1 in more than 2 of 10 uneven runs, or adds more than 10% to completion time.
 
### Decision 2
 
**Context and requirement:** Q1 needs a fairness measure that tells unfair waiting apart from a user waiting behind their own jobs.  
**Options:** each user's longest wait (the earlier measure); Jain's index over all users; worst slowdown among light users, with the heavy user's cost reported separately.  
**Decision and reason:** Worst light-user slowdown. In the burst experiment, the longest-wait measure barely moved (59.92 to 57.00 hours, a 5% cut) because Ben's last job waits behind his own batch, even though Ana's wait fell from 59.92 to 5.92 hours. Jain's index over all users scored FIFO 0.935 and fair-share 0.514 in one-heavy-user seed 1, rewarding everyone waiting equally long.  
**Consequences:** The measure matches the problem, but it needs a light/heavy rule (demand at most 1/n of the total). The heavy user's cost must always be reported beside it so it is not hidden.  
**Status and revisit condition:** Accepted. Revisit if the light/heavy split changes for small changes in the workload, or if reviewers want a cost limit on heavy users.
 
## 4 Architectural design
 
![Architecture: a user supplies a policy, seed, and workload. Inside one Python process, the job loader passes accepted jobs to the SimPy event engine, which notifies the scheduler of each arrival or finish. The scheduler reads usage from the usage tracker, takes GPUs from the simulated 8-GPU cluster, and reports start times to the results recorder, which writes result files.](architecture.png)
 
**Figure 2.** The simulator's architecture: six parts running in one Python process, with the scheduler at the center deciding which jobs take GPUs.
 
**Boundary and outside participants:** The system is the simulator. Outside it are the person running it (who chooses the policy, seed, and workload) and the workload source (a CSV file, the seeded generator, or later the public trace). Nothing else connects to it.
 
**Main parts and messages:**
 
1. **Job loader** reads the job list, rejects invalid jobs (F1), and passes accepted jobs to the event engine.
2. **Event engine** (SimPy) keeps the simulated clock and fires an *arrival* event at each job's submit time and a *finish* event at start time + run time. After all events at the same instant are processed, it asks the scheduler for one decision.
3. **Scheduler** holds the waiting queue, applies the policy (FIFO or fair-share), and runs the critical operation *start next jobs* (Section 5).
4. **Usage tracker** keeps each user's decayed GPU-hours and the number of GPUs each user is running; it updates on every start and finish.
5. **Simulated cluster** keeps the free GPU count (0 to 8). Starting a job takes GPUs; a finish event returns them.
6. **Results recorder** stores each job's start and finish time, checks C1 and C2, and computes the measures in Section 1.
**Saved state:** During a run, the queue, free GPU count, usage, and job times live only in memory. The workload file and the result files are the only saved data. If a run crashes, nothing is recovered; it is rerun from the same workload and seed, which gives identical results (F5).
 
**Where parts run:** All six parts run in one Python process on my laptop. There is no network and no shared machine. The cluster's GPUs are modeled, not real.
 
**What I build, reuse, or simulate:**
 
| Build | Reuse | Simulate |
|---|---|---|
| Job loader, scheduler with both policies, usage tracker, results recorder, workload generator | SimPy event engine ([SimPy documentation](https://simpy.readthedocs.io/)); Slurm's fair-share formula | The 8 GPUs, time, job running, and the three users |
 
## 5 Component design and interfaces
 
| Component | Responsibility | Input | Output or state change |
|---|---|---|---|
| Job loader | Check and accept jobs (F1) | Rows of user, submit time, GPUs, run time | Accepted jobs; rejected jobs with a reason |
| Event engine | Keep simulated time; fire arrival and finish events | Accepted jobs; finished jobs | One scheduler call after each instant's events |
| Scheduler | Hold the queue; choose and start jobs (C1, Q1) | Event at time t; queue; free GPUs; usage | Jobs started; queue and free GPUs updated |
| Usage tracker | Keep decayed GPU-hours per user | Start or finish of a job at time t | Updated usage per user |
| Simulated cluster | Keep the free GPU count | GPUs taken or returned | Free count between 0 and 8 |
| Results recorder | Record times; check C1 and C2; compute measures (F3, F4) | Start and finish times | Results tables and files |
 
**Critical operation: start next jobs.** It decides which waiting jobs start at time t. It is linked to **C1** (never over 8 GPUs), **C2** (each job starts once, not before submission), and **Q1** (its ordering rule is what changes fairness).
 
**Input:**
 
| Field | Type and allowed values | Example |
|---|---|---|
| Caller | The event engine only, once per instant after all events at that instant | Called at t = 6.0 h |
| t | Simulated time in hours, ≥ 0 | 6.0 |
| policy | "fifo" or "fair" | "fair" |
| queue | Waiting jobs: id (integer), user (text), submit (hours ≥ 0), gpus (1 to 8), run (hours > 0) | Ana #21 (1 GPU), Chen #22 and #23 (2 GPUs each), Ben #3 to #20 (4 GPUs each) |
| free | Integer 0 to 8 | 8 |
| usage | Decayed GPU-hours per user, ≥ 0 | Ben 44.07; Ana 0; Chen 0 |
 
**Output:** a list of (job id, start time) for jobs started at t, possibly empty. Example: [(#21, 6.0), (#22, 6.0), (#23, 6.0)].
 
**State changes for each started job:** the job leaves the queue; free GPUs drop by its GPU count; the usage tracker adds its GPUs to that user's running count; a finish event is scheduled at t + run; the recorder stores the start time.
 
**Steps:** repeat while the queue is not empty: choose the job with the highest priority (FIFO: earliest submission; fair-share: highest F, then earlier submission, then lower ID). If its GPUs exceed the free count, stop. Otherwise, start it.
 
**Successful example:** At t = 6.0 h in the burst workload, free = 8, F(Ana) = F(Chen) = 1, F(Ben) = 0.125. Ana #21 starts (free 7), Chen #22 starts (free 5), Chen #23 starts (free 3). Ben #3 needs 4 GPUs but only 3 are free, so the operation stops.
 
**Unsuccessful example (job must wait):** At that same moment, Ben #3 does not start, and no other job may jump ahead of it. It starts at t = 6.5 h, when Ana's job finishes and 4 GPUs are free.
 
**Errors:**
 
| Condition | Behavior | Caller action |
|---|---|---|
| Chosen job needs more GPUs than are free | Not an error: the job waits; nothing else starts | None; the next finish event calls again |
| Queue is empty | Returns an empty list | None |
| Free count would go below 0 | Run stops with "C1 violated" | This is a program bug; fix the code and rerun |
| Unknown policy name | Run refuses to start | Use "fifo" or "fair" |
| Invalid job (for example, 10 GPUs) | Never reaches this operation; rejected by the loader | Correct the workload file |
 
**Repeated or overlapping calls:** When several events happen at the same instant (for example, two of Ben's jobs finishing at t = 6 h), the engine waits until all of them are processed and then calls the operation once, so it sees all 8 free GPUs. A job is removed from the queue before it starts, so it cannot start twice (C2).
 
**Still being worked out:** the exact CSV file format, the result file layout, and behavior when a job fails partway.
 
## 6 Data structure design
 
*Work to come in Assignment 4.*
 
## 7 Algorithm design and execution
 
*Work to come in Assignment 4.*
 
## 8 Failures and security
 
*Work to come in Assignment 4.*
 
## 9 Implementation and feasibility
 
**Minimal path:** Load the burst workload → run strict FIFO → print Ana's wait. Then run the same jobs under fair-share and print both results side by side. This is the smallest run that shows the problem and the effect of the chosen policy.
 
**Feasibility experiment 1:**
 
- **Question:** Without pausing jobs or gap filling, does fair-share meet Q1 on the same jobs as strict FIFO, and do C1 and C2 hold?
- **Procedure:** I built a prototype ([gpu_sched.py](gpu_sched.py)) with the six parts from Section 4. I ran (1) the F1 invalid-job check, (2) the C1 fixture, (3) the burst workload under both policies, (4) the balanced and one-heavy-user workloads with seeds 1 to 10 under both policies, and (5) repeat runs for F5. [summary.py](summary.py) splits users into light and heavy.
- **Evidence:** raw output in [experiment1_results.txt](experiment1_results.txt) and [experiment1_light_vs_heavy.txt](experiment1_light_vs_heavy.txt).
| Workload | Worst light-user slowdown (FIFO → fair-share) | Total completion time change | Q1 |
|---|---|---|---|
| Burst | 120.83 → 12.83 (−89%) | +0.0% (63.00 h both) | Pass |
| One heavy user, 10 seeds | cut by 65% to 96% | −7.3% to +7.9% | Pass in 10 of 10 |
| Balanced, 10 seeds | from −102% (worse) to +62% | −3.8% to +6.5% | Pass in 2 of 10 |
 
C1 and C2 passed in every run, and repeat runs gave identical results for both policies.
 
- **Finding:** Fair-share is feasible and works for the target problem (uneven demand) without pausing or gap filling. Two things I did not expect: the longest-wait measure failed in the burst workload because Ben's last job waited 57 hours behind his own jobs, and fair-share gave no clear benefit when demand was balanced.
- **Resulting decision:** Select fair-share (Decision 1) and judge fairness by worst light-user slowdown, with the heavy user's cost reported (Decision 2). Limit the Q1 claim to uneven-demand workloads.
**Current implementation:**
 
| Part | Status |
|---|---|
| Job loader (generated workloads; CSV reading) | Generated workloads implemented; CSV reading deferred |
| Event engine | Reused (SimPy 4.1.2) |
| Scheduler, FIFO and fair-share | Implemented as a prototype |
| Usage tracker | Implemented |
| Simulated cluster | Simulated |
| Results recorder and C1/C2 checks | Implemented |
| Charts, gap filling, GPU cap | Deferred |
 
**Run instructions and CI:** Run `python3 gpu_sched.py experiment1_results.txt`, then `python3 summary.py experiment1_light_vs_heavy.txt` (requires `pip install simpy`).
 
## 10 Testing and verification
 
*Work to come in Assignments 4–6.*
 
## 11 Operation maintenance and future work
 
*Work to come in Assignments 4–6.*
 
## 12 Revision history and references
 
| Revision date | Change to my design | Reason and evidence |
|---|---|---|
| November 6, 2026 | First version: Section 1 | Assignment 1 |
| November 15, 2026 | Added fair-use rules, measures, success target, and workloads; wrote Section 2; drafted Section 3 | Feedback asked how "fair" is decided and how load is distributed |
| November 22, 2026 | Selected fair-share; changed the fairness measure; added architecture, interface, and experiment | Grading feedback on Assignments 1 and 2, and experiment 1 |
 
**Feedback response record:**
 
| Feedback received | Change made | Where |
|---|---|---|
| The workload is an example, not a documented local case | Evidence separates the published study from the simulated scenario | Section 1 evidence |
| State assumptions: strict queue, no backfilling, no preemption | Stated for both policies; made "no gap filling" a rule | Section 1 rule 7; Section 2 assumptions |
| Make the workload repeatable; list Chen's arrivals | Exact burst table; random workloads defined with seeds 1 to 10 | Section 1 |
| Priority needs explicit normalization and an active-user rule | Rules 1, 2, 5, and 6 with a worked example | Section 1 |
| C2 count check can hide a missing and a duplicate job | C2 now compares job-ID sets and requires exactly one run per ID | Section 2 |
| Jain's index needs a worked example and a stated active-user rule | Worked FIFO and fair-share examples; users with no jobs excluded; demoted to secondary after experiment | Section 1 measures; Decision 2 |
| Apply the same checks to every policy | Requirement-by-policy table | Section 3 |
| Semester II should keep the same narrow question | Same workloads, seeds, metrics, and target; only one policy added | Section 1 |
| Confirm the trace fields before using it | Checked: see open questions | Section 12 |
| Presentation: show components and trace one arrival through the priority decision | Architecture, component table, and worked t = 6 h decision | Sections 4 and 5 |
 
**Unresolved:** no real-cluster data yet; fair-share's heavy-user cost has no limit; gap filling and the GPU cap are untested.
 
| Open question | Why it matters | Next action |
|---|---|---|
| Does gap filling (backfilling) change the result for either policy? | Real schedulers often fill gaps; my results assume they do not | Add gap filling to both policies and rerun the same seeds |
| Should the heavy user's extra delay have a limit? | Ben's worst slowdown rose from 59 to 90 in one run | Ask reviewers on Monday; consider a cost limit in Q1 |
| Can I use the public trace? | Generated jobs may not match real use | The [Philly trace README](https://github.com/msr-fiddle/philly-traces) lists `submitted_time`, `user`, and attempts with start time, end time, and GPU list, so the fields fit. Next: download a sample (the full set is 6.6 GB) and convert it |
 
**Assistance and reuse:** SimPy is reused as the event engine. I used an AI assistant (Claude) to help draft text, write the prototype, and draw the diagrams; I reviewed the code and results.
 
### References
 
- SchedMD. [Slurm priority, fairshare and fair tree](https://slurm.schedmd.com/SLUG19/Priority_and_Fair_Trees.pdf). 2019. Slurm's default FIFO ordering.
- SchedMD. [Classic fairshare algorithm](https://slurm.schedmd.com/classic_fair_share.html). Slurm documentation. Fair-share formula F = 2^(−U/S) and usage decay.
- Jeon, M., et al. [Analysis of large-scale multi-tenant GPU clusters for DNN training workloads](https://www.usenix.org/conference/atc19/presentation/jeon). USENIX ATC, 2019. Measured delays in a shared GPU cluster.
- Microsoft Research. [Philly traces](https://github.com/msr-fiddle/philly-traces). GitHub repository. Public trace from the Jeon et al. study and its fields.
- Mahajan, K., et al. [Themis: Fair and efficient GPU cluster scheduling](https://www.usenix.org/conference/nsdi20/presentation/mahajan). USENIX NSDI, 2020. Finish-time fairness for AI jobs.
- Jain, R., Chiu, D., and Hawe, W. [A quantitative measure of fairness and discrimination for resource allocation in shared computer systems](https://arxiv.org/abs/cs/9809099). DEC Technical Report, 1984. Jain's fairness index.
- SimPy developers. [SimPy documentation](https://simpy.readthedocs.io/). Discrete-event simulation library used as the event engine.
- National Science Foundation. [State and Regional AI Infrastructure Hubs (NSF 26-513)](https://www.nsf.gov/funding/opportunities/us-national-science-foundation-state-regional-artificial). 2026. Published opportunity.
 
