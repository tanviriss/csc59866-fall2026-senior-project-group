Benny Wen  
Professor Kurt Brown  
CSC 59866  
30 October 2026

Identifying Microservice Changes That May Break Other Services

## Describe the Problem

A microservice app consists of separate services that communicate over a network. This allows for independent development, but services still depend on one another’s endpoints and returned information. A change that works inside one service can go on to break another.

My investigation is limited to cross service dependency, specifically HTTP endpoint removal, renaming, and HTTP method changes. It excludes network outages, database faults and message queue failures.

## Who Is Affected By It?

The main stakeholders are developers who change or update a service, developers who maintain services that are dependent on one another, and testers or reviewers responsible for checking a release. Additionally businesses with small teams are heavily affected by this when a small team is tasked with understanding multiple repositories. Likewise, users are affected indirectly by the downstream effect, customers may be unable to place orders even though the product service may be running.

A 2024 study by Lercher and other researchers interviewed 17 developers, architects and managers from 11 companies. 14 of the participants reported that manual change impact analysis was error prone. Participants also noted that unexpected API effects and the efforts required to understand changes to the APIs they consumed was time consuming. This demonstrates that the problem is relevant and has real world impacts on teams and developers, although not every team or developer may experience it to the same extent.

[https\://doi.org/10.1016/j.jss.2024.112110](https://doi.org/10.1016/j.jss.2024.112110)

## Provide Evidence

NSF Award 2520782, “I-Corps: Translation potential of a just-in-time change impact analysis of microservice-based systems”, outlines that developers lose track of dependencies as microservice systems evolve and scale. It identifies added communication, delays, and possible production errors when changes affect other services. It proposed a static analysis across codebases to show potential system wide impacts.

[https\://www\.nsf.gov/awardsearch/show-award/?AWD\_ID=2520782\&HistoricalAwards=false](https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2520782&HistoricalAwards=false)

Additionally in a 2025 paper by Cerny, Goulis, and Abdelfattah’s “Toward Change Impact Analysis in Microservices-based System Evolution”, the researchers developed a tool called ISAR to identify which parts of a software system could be affected by code changes. They tested the tool on eight Java Spring Boot Projects. In one project, they tested 25 changes that could cause problems, and the tool identified all 25\.  
[https\://arxiv.org/abs/2501.11778](https://arxiv.org/abs/2501.11778)

## What Solutions Already Exist?

Incremental Software Architecture Reconstruction (ISAR) is the closest existing research approach, private industry solutions may already exist that I am unaware of but those tools are not open sourced. ISAR reconstructs a system wide model from code, tracks changes, and uses component relationships to estimate the downstream effects. It looks beyond a single repository, but static analysis can miss dependencies hidden from source inspection or flag a possible conflict that does not break the running system. The researchers have called their prototype a proof of concept, not a customer ready product.

Pact contract testing is another approach. A consumer service records example requests and expected responses in a contract. Then the provider service is tested against that contract. Pact can catch a changed endpoint or response that violates a consumer’s documented expectation. It checks for specific interactions before deployment, but only covers interactions represented in contracts and tests. It doesn’t automatically discover every service dependency or create a complete impact map.

ISAR: [https\://arxiv.org/abs/2501.11778](https://arxiv.org/abs/2501.11778)  
PACT documentation: [https\://docs.pact.io/](https://docs.pact.io/)

## What I Still Don’t Know

 The main unknown is whether a small analyzer can correctly identify direct dependencies accurately enough to be useful without producing too many missed connections or misleading warnings. I will have to test this with three Java Spring Boot services (Product, Order, and another consumer). I will introduce known endpoint removals, renames, and HTTP method changes. Recording the affected consumers and compare analyzer warnings with Pact results. I’ll measure dependencies found, dependencies missed, incorrect warnings, and analysis time taken.

## Individual Scope

I will build a command line prototype that scans a small Java Spring Boot codebase, maps supported HTTP endpoints to service calls, detects the three specified endpoint changes between two code versions, and prints a report identifying potentially affected consumer services. I will compare the prototype’s report with Pact contract test results.

To make it manageable for a full time student, I will exclude a website, accounts, artificial intelligence, and dynamically generated addresses to save on time and feasibility of what I can build within a semester's time frame. Three services and three controlled change types should be manageable.

NSF Award The Project Is Based On: [https\://www\.nsf.gov/awardsearch/show-award/?AWD\_ID=2520782](https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2520782)  
