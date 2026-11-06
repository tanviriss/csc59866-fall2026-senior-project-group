# Fair Scheduling for Shared AI Computing

**Author:** Tanvir Islam  
**Course:** CSC 59866  
**Selected project and option:** A02 Fair scheduling for shared AI computing; Option 1  
**Current assignment:** 1  
**Friday commit deadline:** November 6, 2026, at 11:59 p.m. New York time  
**Monday presentation:** November 9, 2026, at 6:30 p.m. New York time  
**Last updated:** November 6, 2026  
**Document status:** Proposed

## Progress note

This first version moves my A02 problem paper into the design template. Section 1 explains who is affected, how jobs are currently submitted, a specific example, and which evidence is documented or assumed.

I narrowed my six-week project to one main question: in a small simulated cluster with 8 graphics processing units (GPUs) shared by three users, can fair-share scheduling reduce the longest wait times compared to first-in, first-out (FIFO), and how much does it affect total completion time?

Writing the example also showed me that I need to clearly define fairness before comparing the policies. For now, I am measuring fairness using each user's longest wait time. The main thing I still need to figure out is whether I can find realistic job data. My next step is to write the Section 2 requirements and compare FIFO and fair-share in Section 3.

## 1 Problem research and scope

**Problem and affected people:** Students and researchers share a cluster of GPUs, which are the processors used to train artificial intelligence (AI) models. A scheduler decides which waiting job should run next. If one user submits a large batch of jobs, smaller jobs from other users can end up waiting much longer than they actually take to run. The scheduler has to balance giving users fair access while also keeping the GPUs busy.

| Stakeholder | Need | Problem today |
|---|---|---|
| User with small jobs | Quick results | Has to wait behind another user's large batch |
| User with large batches | Finish many long jobs | Fairness rules may limit how many GPUs they can use |
| Cluster administrator | A fair policy that still keeps GPUs busy | Has to choose a policy without fully knowing the trade-offs |

**Current workflow:** First, a user submits a job and says how many GPUs it needs. The scheduler then puts the job into a queue. When enough GPUs become available, the next job starts running. After it finishes, the results are returned to the user. The main problem happens when deciding which job should run next. Slurm, a widely used scheduler, uses first-in, first-out (FIFO) ordering by default ([SchedMD, 2019](https://slurm.schedmd.com/SLUG19/Priority_and_Fair_Trees.pdf)), which means jobs are mainly started based on when they were submitted.

**Scenario:** Imagine an 8-GPU cluster shared by Ana, Ben, and Chen. At 9:00 a.m., Ben submits 20 jobs, with each job needing 4 GPUs for 6 hours. These jobs fill the cluster for about 60 hours. At 9:05 a.m., Ana submits a 30-minute job that only needs 1 GPU. Under FIFO, her job waits about two and a half days. No GPU is sitting idle, so the cluster looks efficient, but the result is still unfair.

![Three users submit jobs into a first-in, first-out queue. Ben's 4-GPU jobs use all 8 GPUs while Ana's 1-GPU job waits in the queue.](workflow.png)

**Figure 1.** The current workflow in this example. Since Ben's batch arrived first and uses all the GPUs, Ana's 30-minute job waits about 2.5 days. This waiting problem is what my project focuses on.

**Evidence:**

- *Documented:* The National Science Foundation (NSF) AI Infrastructure Hubs program is expanding access to shared AI computing ([NSF 26-513](https://www.nsf.gov/funding/opportunities/us-national-science-foundation-state-regional-artificial)). This shows a growing need, but not that any policy is unfair.
- *Documented:* A study of Microsoft's shared GPU cluster found jobs delayed while waiting for their fair share and for enough GPUs to free up ([Jeon et al., 2019](https://www.usenix.org/conference/atc19/presentation/jeon)).
- *Observed:* None yet. The scenario is an illustration.
- *Assumed:* Fair-share may shorten the longest waits but increase total completion time.

**Six-week contribution:** I will build a small Python simulation of one 8-GPU cluster shared by three users. I will run the same jobs under FIFO and fair-share, then compare each user's longest wait time, average wait time, total completion time, and GPU usage.

**Semester II scope:** I will extend the simulator by adding a third policy: fair-share with a limit on how many GPUs one user can use at once. I will also test it with larger and more realistic job sets.

**Exclusions:** This project does not include real hardware, making individual jobs run faster, scheduling across multiple clusters, billing, security, or pausing jobs that are already running.

## 2 Requirements and system specification

*Work to come in Assignment 2.*

## 3 Alternatives and selected solution

*Work to come in Assignments 2–3.*

## 4 Architectural design

*Work to come in Assignment 3.*

## 5 Component design and interfaces

*Work to come in Assignment 3.*

## 6 Data structure design

*Work to come in Assignment 4.*

## 7 Algorithm design and execution

*Work to come in Assignment 4.*

## 8 Failures and security

*Work to come in Assignment 4.*

## 9 Implementation and feasibility

*Work to come in Assignments 3–6.*

## 10 Testing and verification

*Work to come in Assignments 4–6.*

## 11 Operation maintenance and future work

*Work to come in Assignments 4–6.*

## 12 Revision history and references

| Open question | Why it matters | Next action |
|---|---|---|
| Can I find realistic job data? | Invented jobs may not match real workloads | Check whether the Jeon et al. (2019) job trace is public |

### References

- SchedMD. [Slurm priority, fairshare and fair tree](https://slurm.schedmd.com/SLUG19/Priority_and_Fair_Trees.pdf). 2019. Slurm's default FIFO ordering.
- Jeon, M., et al. [Analysis of large-scale multi-tenant GPU clusters for DNN training workloads](https://www.usenix.org/conference/atc19/presentation/jeon). USENIX ATC, 2019. Measured delays in a shared GPU cluster.
- National Science Foundation. [State and Regional AI Infrastructure Hubs (NSF 26-513)](https://www.nsf.gov/funding/opportunities/us-national-science-foundation-state-regional-artificial). 2026. Published opportunity.
