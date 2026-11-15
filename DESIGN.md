# **Trustworthy Drift Status for Terraform Projects**

**Author:** Benny Wen  
 **Course:** CSC 59866  
 **Selected project and option:** NSF project 06, "SHF: Small: Towards a Unified Approach for DevOps Configuration Drift Detection" (NSF award 2537321\)  
 **Current assignment:** 2  
 **Friday commit deadline:** November 13, 2026, at 11:59 p.m. New York time  (extended to November 15, 2026, at 11:59 p.m. New York time)
 **Monday presentation:** November 9, 2026, at 6:30 p.m. New York time  
 **Last updated:** November 15, 2026  
 **Document status:** Proposed

# Progress note

This is the second version of my design document. I picked the NSF project on DevOps configuration drift, and my question is whether a drift check can be trusted when its look at the real servers is lost, repeated, or old. I plan a small command line tool for Terraform that reports in sync, drifted, or unknown. This version revises Section 1 and adds Section 2, which has eight requirements that each have a check, and Section 3, which compares four approaches against them. HashiCorp's official page now confirms what Terraform's exit codes mean, but I still do not know what a refresh-only plan returns when it finds drift. I will test that on a small project, then choose a design in Assignment 3.

# Contents

1. Problem research and scope
2. Requirements and system specification
3. Alternatives and selected solution
4. Architectural design
5. Component design and interfaces
6. Data structure design
7. Algorithm design and execution
8. Failures and security
9. Implementation and feasibility
10. Testing and verification
11. Operation maintenance and future work
12. Revision history and references

# 1 Problem research and scope

**Problem and affected people.** Development and Operations (DevOps) is how many software teams build an app, test it, and put it on real servers without doing each step by hand. The settings behind those steps live in configuration files, which are text files that define how things should be set up. Those files must keep matching the code and the real servers. Configuration drift is when they slowly stop matching, because of software changes, environment changes, mistakes, or unknown errors. Think of the files as recipe cards and the servers as the kitchen. Drift is when someone changes the kitchen and never updates the recipe cards. The National Science Foundation (NSF) award associated with this problem is https://www.nsf.gov/awardsearch/show-award?AWD_ID=2537321.

Teams use a drift check to catch this. A drift check is a program that compares the files to the real servers and reports any differences. To do that, it has to look at the real servers, and that look can go wrong for a lot of reasons. The connection can drop, the same look can be sent twice, or the answer can be old. The problem is what a drift check should report when its look goes wrong.

**Problem statement.** In one sentence, the problem is that a drift check can report that nothing has changed when it never got a successful look at the real servers. A good answer for a team is a check that says in sync only after a successful look, and says unknown otherwise.

**Concrete scenario.** Many teams describe their servers and networks in files instead of setting them up by hand. This is called infrastructure as code (IaC). One tool for this is Terraform, made by HashiCorp. HashiCorp's tutorial builds a virtual machine, which is a computer rented from a cloud company, and gives it a security group, which is a set of network rules that decides who can log in. A person then swaps that group for a different one by hand, outside the files. Terraform has a check called a refresh only plan. It reads the real machine and shows the old group removed and the new group added ("Manage Resource Drift"). This is the normal behavior of IaC. https://developer.hashicorp.com/terraform/tutorials/state/resource-drift

Here comes the problem. In one case, the connection to the cloud is lost and no answer comes back. In another, a retry sends the same request twice and the two answers differ. In a third, the answer is outdated and still shows the old security group, so the check says nothing changed while the real machine has different rules. I have not documented that Terraform does this. But a research paper titled "Robust Infrastructure by Verification Agents" (RIVA) says that when tools give incomplete, stale, or misleading output, an automated agent may conclude a system is healthy even though drift has occurred (Abuzakuk et al., sec. 2.3). Its agents run on large language models (LLMs), which are artificial intelligence programs that work with text. https://arxiv.org/pdf/2603.02345

**Boundaries.** I will focus on one tool, Terraform. The question I am scoping in on is whether its drift check can be trusted when a reading is lost, repeated, or outdated. I will not try to stop drift from occurring or to repair it (tentative).

**Current workflow.**

1. A team describes its servers in Terraform files.
2. Someone changes a server by hand, so the real server no longer matches the files.
3. An engineer runs Terraform's refresh-only plan, which reads the real server.
4. The engineer reads the output and decides whether anything drifted.
5. The engineer fixes the server or updates the files.

The difficulty occurs at step 3. If the reading is lost, repeated, or outdated, the output in step 4 may be wrong or missing, and the engineer has no clear way to tell.

**Diagram (workflow.png).** Configuration files and real servers both feed a drift check that produces a report of in sync, drifted, or unknown. Three places the reading from the real servers can go wrong, which are a lost connection, a repeated request, and an old answer.

The drift check compares what should exist with what exists now. The reading from the real servers is the step my project focuses on, and it can fail in three ways.

**Who or what is affected.** The engineers who run the environment are affected first. For example, an engineer wants remote login to stay limited to approved rules. If an outdated reading hides the swap, the machine keeps the wrong rules and nobody knows. If a lost reading makes the checker report drift that is not real, the engineer may try to fix something that isn't broken. The Terraform tutorial warns that when state and configuration do not match the infrastructure, Terraform will try to reconcile them and may unintentionally destroy or recreate resources ("Manage Resource Drift"). So a false alarm can lead to a real change, and a missed alarm can leave a real problem in place.

Organizations that depend on these systems are affected too. The NSF abstract names healthcare, transportation, and technology as critical sectors that need reliable software, and it says the project aims to reduce the burden on developers. That is the NSF's claim about the project.

| Stakeholder | What they need | Basis |
|---|---|---|
| Engineers who maintain Terraform projects | A drift result they can trust, with a clear "unknown" when the check could not finish | Documented. The NSF abstract says the project aims to reduce the burden on developers who maintain these systems |
| Teams and organizations that depend on these systems | Reliable software and fewer failures and delays | Documented. The NSF abstract names healthcare, transportation, and technology as critical sectors. This is the NSF's claim about its whole project, not evidence about my case |
| Engineers who read a scheduled report | A short status that says how old the last good check is | Assumed. I have not confirmed how teams use such reports |

**Evidence.**

*Documented.* The NSF abstract says drift leads to system failures, delays, and more maintenance effort ("SHF"). HashiCorp's older guide says drift can come from changes made by hand or by other automation tools (Koehler). The RIVA authors say drift comes from bugs, manual changes, or system updates, and that checking for it is labor intensive and error prone (Abuzakuk et al., abstract and sec. 1). In their tests on a benchmark called AIOpsLab, one tool silently returning wrong data lowered detection success from 50% to 40% and success at finding where the problem was from 22.2% to 11.1% (Abuzakuk et al., sec. 1). Those numbers come from LLM agents on a benchmark, not from Terraform or CloudFormation. https://www.hashicorp.com/blog/detecting-and-managing-drift-with-terraform

*New since the first version.* HashiCorp's official page for the plan command now confirms what the detailed exit code option does. Exit code 0 means the plan succeeded with no changes, exit code 1 means an error, and exit code 2 means it succeeded with changes present. The same page describes refresh-only mode as a plan whose goal is only to update Terraform's state to match changes made to remote objects outside Terraform. It says this mode is available from Terraform 0.15.4. It also says a plan alone does not carry out the proposed changes. If Terraform cannot get the state lock, it retries for the lock timeout, if one is set, and then returns an error. HashiCorp's machine-readable output reference adds a second signal. With the JSON option (JSON is a text format programs use to exchange data), if drift is detected during planning, Terraform emits a resource_drift message for each resource that changed outside Terraform. Neither page says what exit code a refresh-only plan returns when it finds drift. https://developer.hashicorp.com/terraform/cli/commands/plan

https://developer.hashicorp.com/terraform/internals/machine-readable-ui

*Observed.* I have no observations of this problem in software development, since my experience with DevOps is limited. I have not built or measured anything yet.

*Assumed.* I assume lost, repeated, and outdated readings happen often enough in real Terraform use to matter. I assume a refresh-only plan run with the detailed exit code option returns exit code 2 when it finds drift. HashiCorp documents the exit codes in general, but not for refresh-only plans, so I will test it. None of this has been proven as of now.

*Missing evidence.* I have not found data on how often drift checkers get failed or outdated readings. The NSF award is still active, but I haven't found any large studies that have produced results yet. The Amazon Web Services (AWS) CloudFormation guide is related evidence that a drift check can fail to finish, because it has a status for that case (see Section 3). https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html

**Six-week contribution.** For the first six weeks I will build the smallest working version of my tool. It checks one Terraform project by running the refresh-only plan and reports one of three answers, in sync, drifted, or unknown. If Terraform fails or cannot reach the cloud, the tool says unknown and never in sync. It never changes any infrastructure.

**Semester II scope.** I will build a small command line tool for the people who maintain Terraform projects, the same engineers the sources describe as carrying the burden of drift. Because reading is safe to repeat, the full version retries a failed check a limited number of times and asks for two matching results before it says in sync. It saves the time and result of every check, so the report shows when the last good check happened and warns when that result is too old to trust. I will also include a scheduled job file for GitHub Actions, an automation service, so a team can run the check automatically.

The comparison I will make is between running the refresh only plan by hand and running my tool, on the same small real Terraform project and the same four situations, which are a change made outside Terraform, a failed run, a repeated run, and an old result. I will judge each by correctness. I expect to use Python, the free Terraform program, and a free local setup. For tests, a fake Terraform stand in will return the exit codes I choose.

My solution direction is tentative. The three answers, the retry rule, and the age warning are my first design, and feedback from real users may change them. The work is manageable for one student because it wraps one existing command, needs little code, and needs no paid cloud account. Each feature answers one problem in my paper. Unknown and retries cover a lost reading, two matching results cover a repeated reading, and the age warning covers an outdated reading.

**Exclusions.** I will exclude every tool other than Terraform, source code and application drift, LLM agents, automatic repair, and a web dashboard.

**What I still don't know.** HashiCorp's documentation says exit code 1 is an error and exit code 2 means changes are present. So in general, a wrapper, which is a tool that runs Terraform and reads its results, can tell a failed check from a changed one. What I do not know is whether that holds for a refresh-only plan that finds drift. I also do not know whether real Terraform users will understand the three answers my tool gives.

To answer this, I have read HashiCorp's official page for the plan command, which confirms what exit codes 0, 1, and 2 mean. It does not say what a refresh-only plan returns when it finds drift. My first test is to run a refresh-only plan with the detailed exit code option on a small project, change a resource by hand, and write down the exit code. If it returns 2, the tool can use exit codes. If it does not, I will read the machine-readable output for resource_drift messages instead. Second, as I build, I will try the tool on small real Terraform projects to see what it reports when Terraform fails, repeats a check, or gives an old result. If users misunderstand the unknown answer, I would change its wording and the report layout.

# 2 Requirements and system specification

This section says what the tool must do, in behavior a person can observe. It does not say how the tool is built. Requirement IDs, which are short labels for each requirement, follow the course scheme. F means a functional requirement, which describes what the tool does. C means a correctness rule, which describes something that must always be true. Q means a quality target. A value marked proposed has not been measured and may change.

**Words used in this section.** A check is one run of Terraform's refresh-only plan with the detailed exit code option. A good check is a check that ends with exit code 0, which means no changes, or exit code 2, which means changes are present. A failed check is anything else, such as exit code 1, a lock error, a run that takes longer than the time limit, or Terraform not starting. A fake Terraform is a small stand-in program that returns the exit codes I choose and logs every command it receives, so I can test without a cloud account.

## 2.1 What the tool must do

| ID | Type | Requirement | Acceptance check |
|---|---|---|---|
| F1 | Functional | For one project folder, the tool runs one check and records its exit code and the time it ran. The check uses the refresh-only option, the detailed exit code option, and the option that turns off prompts for input variables, so an automated run does not stop to ask a question. | The fake Terraform returns 0. Its log shows one command with those three options, and the tool saved code 0 with a time. |
| F2 | Functional | After checking, the tool prints exactly one status word, which is in sync, drifted, or unknown. | For every fake result in Section 2.2, the output has exactly one status word, and it matches the table. |
| F3 | Functional | If a check fails, the tool runs another check. It stops and reports unknown after 3 failed checks in a row. It also stops after 6 checks in total. Both limits are proposed. A check that runs longer than 120 seconds (proposed) counts as failed. | The fake returns 1 every time. The fake was run exactly 3 times and the status is unknown. The fake returns 0, 1, 0, 1, 0, 1. The fake was run exactly 6 times and the status is unknown. |
| F4 | Functional | A good check with exit code 2 gives drifted right away. A good check with exit code 0 needs the very next check to also be 0, and two 0 results in a row give in sync. If the next check is 2, the status is unknown, because the checks disagreed. If the next check fails, the earlier 0 no longer counts and the tool keeps going under F3. | The fake returns 2, which gives drifted. It returns 0 then 0, which gives in sync. It returns 0 then 2, which gives unknown. It returns 0, 1, 0, 0, which gives in sync, because the failure reset the count. |
| F5 | Functional | The tool saves the time and result of every check. The report shows the time of the last good check and says too old when that check is more than 24 hours old (proposed). | A saved good check is 30 hours old and the new run fails 3 times. The report shows that time and the words too old. A saved good check is 1 hour old, so the report does not say too old. The saved record is still there after the tool is closed and run again. |
| C1 | Correctness rule | The tool reports in sync only when its final two checks both ended with exit code 0. A failed or disagreeing check never produces in sync. | Run every sequence of up to 6 fake results using 0, 1, 2, and a timeout. Whenever the output is in sync, the final two results were both 0. |
| C2 | Correctness rule | The tool never changes infrastructure or Terraform's record of it. It only runs the refresh-only plan. | The fake Terraform logs every command it receives. In all tests, each command is a plan with the refresh-only option. None is an apply, a refresh, or a destroy. |
| Q1 | Quality target (proposed, not measured) | In at least 100 randomized runs, the tool reports in sync falsely 0 times. Each run uses the fake Terraform with a random sequence of 0, 1, 2, and timeouts. A run that times out stays in the 100 runs. | Count the runs where the output is in sync but the final two fake results were not both 0. The count must be 0. |

## 2.2 Examples

An ordinary case and some unsuccessful cases, using the fake Terraform. Results are listed in the order the fake returns them.

| Fake Terraform results | Expected output |
|---|---|
| 0, then 0 (ordinary case) | Status: in sync. Two checks agree. Last good check: now. |
| 2 | Status: drifted. Terraform reported changes. Last good check: now. |
| 0, then 2 | Status: unknown. The two checks disagreed. |
| 1, then 1, then 1 | Status: unknown. Terraform failed 3 times. The report shows the last good check and its age. |
| 1, then 0, then 0 | Status: in sync. The first check failed, but the final two checks agree. |
| 0, then 1, then 0, then 0 | Status: in sync. The failure reset the count, and the final two checks agree. |
| 0, 1, 0, 1, 0, 1 | Status: unknown. The limit of 6 checks was reached without two 0 results in a row. |
| 1, then 1, then 1, with a message that the state is locked | Status: unknown. Another run held the lock. |
| Terraform cannot start | Status: unknown. Terraform did not run. |
| Saved good check is 30 hours old, then 1, 1, 1 | Status: unknown. Last good check 30 hours ago, too old to trust. |

## 2.3 What the documentation already establishes

- **Exit codes.** With the detailed exit code option, exit code 0 means succeeded with no changes, 1 means error, and 2 means succeeded with changes present. HashiCorp's plan command page.
- **Refresh-only mode.** A plan in this mode only updates Terraform's state to match changes made outside Terraform. It needs Terraform 0.15.4 or later, and a plan alone does not carry out changes. HashiCorp's plan command page.
- **Locking.** A state lock stops two runs from changing the same state at once. Terraform holds the lock during a plan unless locking is turned off. If a lock timeout is set, Terraform retries for that time and then returns an error. HashiCorp's plan command page.
- **Machine-readable output.** With the JSON option, Terraform emits a resource_drift message for each resource that changed outside Terraform when drift is detected during planning. HashiCorp's machine-readable output reference.

## 2.4 Assumptions

| ID | Assumption | How I will check it |
|---|---|---|
| A1 | A refresh-only plan with the detailed exit code option returns exit code 2 when something was changed outside Terraform. The documentation gives the exit codes in general but not for this mode. If it is wrong, F4 has to change, and I would read resource_drift messages from the JSON output instead. | Run it on a small project, change a resource by hand, and write down the exit code. |
| A2 | Running a refresh-only plan again is safe, because a plan alone does not carry out changes. It could still be slowed by a lock or by limits on a cloud service. | Run it twice in a row on the test project and compare the results and the saved state. |
| A3 | The test project is small and uses resources that can run on my own computer, so no paid cloud account is needed. | Pick the resources and confirm the project runs before building the tool. |
| A4 | One person runs the tool on one computer, and nobody else is changing the same project during a check. | Test with one user only. Treat a held lock as a failed check, as in the examples. |
| A5 | The JSON output reports resource_drift messages in refresh-only mode. The reference says this when drift is detected during planning, but it does not name refresh-only mode. | Run the JSON option on the same hand-changed project and look for a resource_drift message. |

## 2.5 Constraints

- The tool works with Terraform only, version 0.15.4 or later, which is when refresh-only mode became available.
- It is a command line tool written in Python.
- It uses free tools and no paid cloud account.
- It is built by one student in one semester.
- Terraform must be installed on the same computer.
- The scheduled job file for GitHub Actions is a stretch goal and not required here.

## 2.6 Not yet specified

These values are all proposed. They are the limit of 3 failed checks in a row, the limit of 6 checks in total, the time limit of 120 seconds for one check, the age limit of 24 hours, and the 100 randomized runs. I will adjust them after I test on a small project.

# 3 Alternatives and selected solution

This section compares four approaches against the same requirements. I have not chosen a final design yet. That comes in the next assignment. In the table, each entry says its basis. Documented means a source states it. Judgment means it is my own reasoning. By design means the approach is meant to meet the requirement but has not been built or tested. Not described means the pages I read do not say.

**Approach A, the baseline. An engineer runs the refresh-only plan by hand.** Terraform keeps a state file, which is its record of the resources it manages. On a plan, it updates that record from the real infrastructure, and the refresh-only option shows what would change in the record without touching the infrastructure ("Manage Resource Drift"). HashiCorp's plan page says a plan alone does not carry out the proposed changes, and the tutorial calls the refresh-only plan safer than the older refresh command, which overwrites the state file without showing the updates. The strength is a read-only view of exactly which settings differ. The limits are that Terraform only refreshes resources under its management (Koehler), and the tutorial notes that without a saved plan file, Terraform cannot guarantee that a later apply will take exactly the shown actions ("Manage Resource Drift"). The pages I read do not say what happens when a reading is lost or outdated. A person has to notice and judge. https://developer.hashicorp.com/terraform/tutorials/state/resource-drift

**Approach B. A one-shot wrapper.** This is a simple script that runs the check once and turns the exit code into a status. Exit code 0 becomes in sync, 2 becomes drifted, and anything else becomes unknown. This is my own simple candidate, based on the documented exit codes. Its strength is that it is very small and gives one plain word. Its limit is that one good check is enough for in sync, so it does not meet F4 or C1. It also remembers nothing between runs, so it does not meet F5.

**Approach C. A checked wrapper.** This is Approach B plus retries, two matching checks before in sync, and a saved history with an age warning. It is the design my paper proposes. By design, it is meant to meet F1 to F5, C1, and C2. It has not been built or tested. Its limits are that it takes more code than B, and that its retry and age limits are guesses until I test them. A variation to decide in Assignment 3 is to also read the resource_drift messages from the JSON output as a second signal, which would echo the cross-checking idea in the RIVA research below.

**Approach D. AWS CloudFormation drift detection.** AWS stands for Amazon Web Services, Amazon's cloud service, and CloudFormation is its own way to describe servers in files, called templates. A drift detection operation compares what a template says should exist with what exists now, for each resource that supports drift detection. Its status model is richer than most. The operation status can be DETECTION_IN_PROGRESS, DETECTION_COMPLETE, or DETECTION_FAILED, and failed means detection failed for at least one resource while results are still available for the others. The stack status can be DRIFTED, IN_SYNC, UNKNOWN, or NOT_CHECKED, where UNKNOWN means CloudFormation could not run drift detection for a resource. It also records when detection started, and each resource can carry a last check time, which is optional (DescribeStackDriftDetectionStatus; StackResourceDriftInformation). These come from AWS's API reference. An API, or application programming interface, is the way one program asks a service to do something. It has limits for this project. DETECTION_COMPLETE covers only the resources that support drift detection, and the rest remain unchecked. I did not see retries or an age warning described. It also cannot check Terraform projects. The CloudFormation guide I cited in Section 1 also says it only checks properties the template sets explicitly and does not check stacks nested inside other stacks ("Detect Unmanaged"). I include D for its status model. https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html

**A research approach, RIVA, is not in the table.** Its main idea is that two tool calls with the same goal are unlikely to both be wrong. So it checks each property through different tools and compares them (Abuzakuk et al., sec. 1). When some of its tools returned wrong data, it raised average task success from 27.3% to 50%. It depends on LLMs, each task was run only 5 times, and the authors say the benchmark gave too few diagnostic paths (Abuzakuk et al., secs. 4.4, 7). I excluded LLM agents from my scope, so I use RIVA only as support for the idea behind F4, which is to confirm a result before trusting it. https://arxiv.org/pdf/2603.02345

## Comparison against the requirements

| Requirement | A. Manual refresh-only plan | B. One-shot wrapper | C. Checked wrapper | D. CloudFormation drift detection |
|---|---|---|---|---|
| F1 Run one check without prompts | Yes. A person types the command (judgment) | Yes (by design) | Yes (by design) | Not for Terraform |
| F2 One of three status words | No. A person reads the output (judgment) | Yes (by design) | Yes (by design) | Partly. Statuses include IN_SYNC, DRIFTED, UNKNOWN, and NOT_CHECKED (documented) |
| F3 Retry a failed check | No (judgment) | No (by design) | Yes (by design) | Not described |
| F4 Confirm before in sync | No (judgment) | No (by design) | Yes (by design) | Not described |
| F5 Remember the last good check and its age | No (judgment) | No (by design) | Yes (by design) | Partly. Records when detection started and an optional per-resource last check time. No age warning described (documented) |
| C1 Never in sync after a failure | Depends on the person (judgment) | No (by design) | Yes (by design) | Partly. Has UNKNOWN and DETECTION_FAILED, but DETECTION_COMPLETE leaves unsupported resources unchecked (documented) |
| C2 Read-only | Yes. A plan alone does not carry out changes (documented) | Yes (by design) | Yes (by design) | Not described |
| Q1 Zero false in sync | Not measured | Not measured | Not measured | Not measured |

The requirements that best separate the approaches are F4, F5, and C1. Approaches A and B both fail them, and C is the only one designed to meet all three. D comes closest on the status model, since it has an unknown-style status and records a time, but it does not describe confirming a result or warning about age. If I had to separate B from C, I would test the sequence "0, then 2", because B reports in sync after the first 0 and C reports unknown.

**What I did not find.** None of the pages I read describe a ready tool that gives a small team one plain status, in sync, drifted, or unknown, with the age of the last good check. I did not search for open source tools beyond these pages, so I cannot say none exist.

# 4 Architectural design

# 5 Component design and interfaces

# 6 Data structure design

# 7 Algorithm design and execution

# 8 Failures and security

# 9 Implementation and feasibility

# 10 Testing and verification

# 11 Operation maintenance and future work

# 12 Revision history and references

| Revision date | Change to my design | Reason and evidence |
|---|---|---|
| November 6, 2026 | First version. Added the problem, workflow image, stakeholders, and scope | Assignment 1 |
| November 13, 2026 (update to your commit date) | Second version. Revised Section 1, wrote the requirements in Section 2, and drafted the comparison in Section 3 | Assignment 2. Replaced library evidence with HashiCorp's official exit code documentation, added a JSON output fallback, renamed requirements to the course scheme (F, C, Q), added Approach D evidence from the AWS API pages, and fixed an overlap between the retry and confirmation rules |

| Open question | Why it matters | Next action |
|---|---|---|
| Does a refresh-only plan with the detailed exit code option return exit code 2 when it finds drift? | Requirements F2 and F4 depend on it | Run the test on a small project. If it does not, read resource_drift messages from the JSON output |
| Are the proposed limits (3 checks, 120 seconds, 24 hours) reasonable? | Requirements F3 and F5 use them | Test on a small project and adjust |

**Assistance and reuse.** I used ChatGPT to help me better understand what the NSF was asking for to be built as the topic is new to me and I have limited experience with DevOps. For assignment 2, I used Claude to help format tables to display correctly in Markdown format. As well as using Claude to format references, and synthesis some run on sentences to be more concise.

## References

1. HashiCorp Developer. "Manage resource drift." Terraform tutorial, accessed November 6, 2026. Supports the example, the refresh-only plan, and the warning about reconciling. Used as Approach A. https://developer.hashicorp.com/terraform/tutorials/state/resource-drift
2. Koehler, Christie. "Detecting and Managing Drift with Terraform." HashiCorp blog, June 7, 2018, accessed November 6, 2026. Supports how drift arises and that Terraform only refreshes resources it manages. https://www.hashicorp.com/blog/detecting-and-managing-drift-with-terraform
3. Abuzakuk, Sami, et al. "RIVA: Leveraging LLM Agents for Reliable Configuration Drift Detection." arXiv preprint 2603.02345, March 2, 2026. Supports the effect of wrong tool output on drift checks and the idea behind confirming a result. https://arxiv.org/pdf/2603.02345
4. Amazon Web Services. "Detect unmanaged configuration changes to stacks and resources with drift detection." AWS CloudFormation User Guide, accessed November 6, 2026. Supports Approach D, including that it only checks properties the template sets and skips nested stacks. https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
5. National Science Foundation. "SHF: Small: Towards a Unified Approach for DevOps Configuration Drift Detection." Award 2537321. Abstract read in the course handout, not on nsf.gov. Supports the definition of drift and the project's goals. https://www.nsf.gov/awardsearch/show-award?AWD_ID=2537321
6. HashiCorp Developer. "terraform plan command." Terraform command line documentation, version 1.17.x, Accessed November 13, 2026. Supports the exit codes, refresh-only mode, locking, and the statement that a plan alone does not carry out changes (Sections 1 and 2). https://developer.hashicorp.com/terraform/cli/commands/plan
7. HashiCorp Developer. "Machine-readable UI (user interface) output reference." Terraform internals, version 1.17.x, Accessed November 13, 2026. Supports the resource_drift message and the JSON fallback in assumptions A1 and A5. https://developer.hashicorp.com/terraform/internals/machine-readable-ui
8. Amazon Web Services. "DescribeStackDriftDetectionStatus." AWS CloudFormation API Reference, Accessed November 13, 2026. Supports the operation statuses, the stack statuses including UNKNOWN, and the detection start time in Approach D. https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStackDriftDetectionStatus.html
9. Amazon Web Services. "StackResourceDriftInformation." AWS CloudFormation API Reference, Accessed November 13, 2026. Supports the per-resource statuses and the optional last check time in Approach D. https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_StackResourceDriftInformation.html

## Supporting media and evidence

Workflow diagram (workflow.png). Shows where the reading can go wrong.
