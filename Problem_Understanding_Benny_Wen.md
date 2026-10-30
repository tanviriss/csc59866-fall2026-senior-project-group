# **Detecting Breaking Endpoint Changes Between Microservices**

## **What problem are you investigating?**

A microservice application is made up of smaller services that work together to run an application. Each service is responsible for a different task and may need information from other services to do its job. For example, one service might manage products while another handles customer orders. Since these services are often developed by different teams, a change made to one service can sometimes cause problems in another.

A small online shop has two services, Product and Order. When a customer places an order, the Order service asks the Product service for details about the item, such as its name and price. A developer working on the Product service makes a change to how this information is shared with other services. The Product service continues to work normally, and all its own tests pass. However, the Order service has not been updated to work with the change. When a customer tries to place an order, the Order service can no longer get the product information it needs, causing the checkout to fail. The Product service itself never goes down, which makes the problem harder to spot. Everything appears to be working in one part of the application, but a change has caused something else to stop working.

The same problem can happen in a couple of other ways. The Product team might remove a feature because a particular product is no longer being sold. If the Order service still depends on that feature, it will no longer be able to get the information it needs, and checkout will fail. Another possibility is that the Product team changes how the information is requested. Even though the feature is still there, the Order service may no longer be able to use it because it has not been updated to match the change. In both cases, the Product service continues to work normally, while the problem appears in the Order service. 

My investigation focuses on three types of changes that can cause these problems. These are removing an existing feature, renaming it, and changing how another service is expected to request it. The focus is on situations where one service relies directly on another to get information. Issues such as network problems, database failures and message queue errors are not included, as these are caused by problems while the application is running rather than changes made to the code.

## **Who or what is affected by it?**

Developers who change a service are affected first. They usually focus on their own repository, so they cannot easily tell who calls the endpoint they are editing. Organizations pay the cost of these failures. The NSF award described below names costly errors, extra communication overhead, and delays. Small teams may feel this more, because one person may have to understand several repositories, but I treat that as an assumption (not well documented but assumed). Customers are affected indirectly, in the earlier example, a customer cannot place an order even though the Product service is up. The consequences are wasted debugging time, delayed releases, and a broken checkout in production.

## **What evidence do you currently have that it is a real problem?**

**Documented**: NSF Award \#2520782 is an I-Corps grant awarded to the University of Arizona. Its abstract describes how small and medium sized businesses adopting microservices can struggle to keep track of dependencies between services. It identifies costly errors, extra communication, and delays when changes affect other services. It also identifies the need for an analysis tool that works across multiple codebases. This shows that the problem is recognized and has received funding.

[https\://www\.nsf.gov/awardsearch/show-award/?AWD\_ID=2520782\&HistoricalAwards=false](https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2520782&HistoricalAwards=false)

**Documented:** Lercher and colleagues (2024) interviewed 17 developers, architects, and managers from 11 companies about how they manage changes to microservice APIs. The paper identifies several challenges, including the time needed to understand which services are affected by a change, poor communication between teams, and services continuing to rely on outdated versions. This supports the problem as a real issue for developers and teams. However, the study is based on interviews and does not measure how often breaking changes reach production.

[https\://doi.org/10.1016/j.jss.2024.112110](https://doi.org/10.1016/j.jss.2024.112110)

**Documented:** Cerny, Goulis, and Abdelfattah (2025) explain that a change in one microservice can break other services and cause a ripple effect. Their prototype includes a rule called Invalid Call, which detects when a service calls an endpoint that no longer exists. This is the same type of failure described in my example. However, the researchers also note that not every flagged issue represents an actual problem.

[https\://arxiv.org/abs/2501.11778](https://arxiv.org/abs/2501.11778)

**Observed.** I have not built or measured anything yet, so I have no observations of my own.

**Assumptions and missing evidence.** Small teams may be more affected because they have fewer people to manage and understand multiple services. I also assume that endpoint removals, renaming, and HTTP method changes happen often enough to be worth investigating, and that real systems have similar dependencies to my three-service setup. However, none of the sources I have reviewed measure how often these changes cause failures. This is still missing evidence that my investigation will need to address.

## **What solutions already exist?**

**Incremental Software Architecture Reconstruction (ISAR)**: ISAR is a research approach developed by Cerny and colleagues. It uses static analysis, which means examining source code without running the application, to map the components of each service and how they communicate. When a code change is made, the tool records what was added, changed, or removed and updates the map. It then checks for possible problems using rules such as Invalid Call, which detects calls to endpoints that no longer exist.

ISAR is relevant to my investigation because it looks across multiple repositories and can identify potential problems before deployment. The researchers tested it on eight Java Spring Boot projects and reported that it identified all 25 manually labeled changes in one of their tests. However, there are some limitations. The authors describe it as a proof of concept rather than a finished product. Static analysis can also miss problems that only appear when the application is running, while some flagged issues may not cause actual failures. The tool also does not analyze user interface code, meaning dependencies outside the analyzed services may be missed. The version of the paper I reviewed also anonymizes the tool link, so I have not confirmed whether it is available to download and run.

[https\://arxiv.org/abs/2501.11778](https://arxiv.org/abs/2501.11778)

**Pact contract testing**: Pact is a tool used for contract testing between services. The consumer service creates a contract based on example requests and responses from its automated tests. The provider service is then tested against that contract to check that it still meets the consumer's expectations. Pact's documentation explains that only the parts of the communication actually used by the consumer are tested. This allows the provider to change other parts without breaking the contract.

Pact would catch my example if the Order service's contract included the product request that was changed. However, it only checks interactions that have been added to a contract. It does not automatically discover service dependencies or create a complete map of which services communicate with each other.

[https\://docs.pact.io/](https://docs.pact.io/)

These approaches work in different ways. ISAR tries to find service dependencies by analyzing the code, while Pact checks dependencies that developers have already defined in contracts. What remains unclear is how well a much smaller analyzer would perform on a small system compared to these existing approaches.

## **What is the most important thing you still do not know?**

The main unknown is whether a small analyzer can identify direct dependencies accurately enough to be useful without missing too many connections or producing too many false warnings. If it misses real dependencies, developers may not trust it. If it produces too many incorrect warnings, developers may start ignoring them. Analysis time also matters because the tool needs to run quickly enough for developers to use it regularly when making code changes.

To investigate this, I will build three Java Spring Boot services called Product, Order, and another consumer. I will introduce one change at a time, including endpoint removals, renames, and HTTP method changes, and record which services are actually affected. I will then run my analyzer and Pact's contract tests against the same changes. For each tool, I will measure how many dependencies it finds, how many it misses, how many incorrect warnings it produces, and how long the analysis takes.

If my analyzer misses dependencies that Pact catches, I will look at what types of calls it fails to detect before adding more features. If it produces too many incorrect warnings, I will improve how it matches endpoints to service calls. If it performs as well as or better than Pact in these tests, it will provide evidence that the smaller approach is worth developing further.

## **Individual Scope**

I will build a command line prototype that scans a small Java Spring Boot codebase and maps the HTTP endpoints it can recognize to the service calls that use them. This includes endpoints declared with Spring annotations such as @GetMapping. The tool will compare two versions of the code and detect the three specified types of changes. It will then print a report showing each change and which consumer services and calls may be affected. To compare it with Pact, I will test both tools against the same list of known breaking changes and record how many each tool detects.

I am excluding a website, user accounts, artificial intelligence, and dynamically generated addresses because they would add extra work without helping answer my research question. I will also exclude network outages, database faults, and message queue failures. My proposed approach is to compare declared endpoints with the service calls that reference them to identify the three types of changes. I expect this to be enough to detect potential problems, but this is an assumption that I will test rather than assume.

The work is manageable for one student because it uses three services, three controlled change types, and one comparison tool. All the code can run on one computer, and the measurements are simple counts and timings.

NSF award this project is based on: [https\://www\.nsf.gov/awardsearch/show-award/?AWD\_ID=2520782\&HistoricalAwards=false](https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2520782&HistoricalAwards=false)

