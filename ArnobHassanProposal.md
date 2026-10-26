# Highway Radar: Problem Understanding Paper

**Arnob Hassan**

## What problem are you investigating?

Highway Radar is a proposed app for drivers who want a clearer understanding of unfamiliar highways and potential roadside enforcement locations. Some drivers may feel that community reports in apps such as Waze do not give them enough information or peace of mind. When there is no alert, they may wonder whether nobody has reported anything or whether there is actually nothing to report. My project explores whether analyzing highway images can provide an additional layer of information about the road itself.

Waze allows drivers to report police sightings and respond when a report is no longer accurate. Its documentation explains that reports remain visible for different amounts of time depending on other users’ responses [1]. These reports describe observations made by people. Highway Radar would instead examine visible roadside features, such as shoulder space, and identify areas that appear potentially suitable for enforcement activity. This would provide a different kind of information, rather than another live police report.

For example, a driver preparing to travel on an unfamiliar highway could review a map of locations identified from roadway images. Selecting a marker could show the image and explain why the location was flagged. The intended benefit is greater awareness and less uncertainty. However, a marker would not mean that an officer is present, that enforcement frequently occurs there, or that the area is legally usable. Those conclusions require evidence that a roadway image alone cannot provide.

The specific problem for this course is making the processing behind that map dependable. As more images are added, the app must keep track of which ones have been checked, save their results, and recover when processing stops unexpectedly. Otherwise, the map could contain gaps or repeated results that confuse users.

Imagine that the app is processing 1,000 image tasks. It saves the result for image 417, but the program disconnects before confirming that it finished. Another program may then process the same image again. Without proper tracking, the app could store the same prediction twice. An interruption at a different point could leave an image unfinished without making that obvious. This is a planned test scenario, not a failure I have already measured.

My research question is therefore: **How can Highway Radar process highway images efficiently while keeping its map results complete and consistent when part of the system stops working?**

## Who or what is affected by it?

The intended users are drivers who want additional road awareness, particularly people who feel uncertain about relying entirely on community reports. Potential users include commuters, delivery drivers, and people traveling outside areas they know well. Someone who feels that Waze reports are incomplete may be interested in a second source of context. This is a proposed audience, however, rather than a group whose demand I have already established through interviews or surveys.

From a user’s perspective, the value would come from understanding what the app knows and what remains uncertain. A completed prediction, an image still waiting to be checked, and a location with no available image should not all look the same. A blank section of the map must not imply that the app checked the road and found nothing. Similarly, a repeated result must not look like multiple independent observations supporting the same location.

Peace of mind is an intended benefit, not a demonstrated outcome. Too many incorrect markers could make a driver more anxious or cause them to stop trusting the app. The design should therefore explain that these are image-based estimates and make them easy to review before a trip. It should not suggest that an unmarked road is free of enforcement.

I am also affected as the developer. If processing stops, I need to know what finished and what still requires attention. Without that information, I may repeat hours of work or manually compare records. A dependable process would make it easier to test updated models and refresh the map.

Other road users could be affected indirectly if drivers misunderstand the information or become distracted by it. That makes clear wording and a simple interface part of the product’s usefulness. The system’s behavior also depends on its inputs: old images, poor visibility, or incomplete road coverage could limit what it can show even if the software works correctly.

## What evidence do you currently have that it is a real problem?

The evidence supports two separate issues: uncertainty in the information shown to drivers and the challenge of processing images reliably.

For the user-facing issue, Waze’s official explanation confirms that its police reports rely on user observations and subsequent feedback [1]. My inference is that the absence of a report does not establish that a road has been comprehensively checked. This motivates exploring an additional information source. It does not establish that Waze is generally unreliable or that Highway Radar would be more accurate. Whether drivers find this additional information useful still needs direct evaluation.

My previous project work provides a real image-analysis workload. I have trained models to distinguish roadside areas using highway images. During that work, I observed incorrect predictions involving narrow roadside areas, lane markings, and wider shoulders that were difficult to distinguish visually. These observations show that the model can make mistakes and that its outputs need careful presentation. They do not demonstrate that the processing system has already lost or duplicated results.

The reliability issue is supported by existing documentation. RabbitMQ’s Reliability Guide explains that connections and programs can fail and that messages may be delivered again during recovery [2]. In this project, those messages would represent requests to process images. The practical concern is that repeating a request must not create an extra map result.

Celery’s documentation likewise explains that the point at which a task is marked as accepted affects recovery. It recommends designing tasks so that repeating them does not cause unintended effects, and it describes exceptions to recovery behavior when a worker process is terminated [3]. This means recovery must be configured and tested; adding a task queue alone is not enough.

Dean and Ghemawat’s MapReduce research provides broader background. Their system distributes data processing across computers and handles scheduling and machine failures [4]. It establishes that coordinating large processing jobs is a recognized engineering problem. It does not prove that my smaller dataset needs the same infrastructure.

At this stage, I have not measured user demand, processing speed, recovery time, or the frequency of failures in Highway Radar. The evidence justifies investigating the problem, while the experiments will determine whether the proposed approach is worthwhile.

## What solutions already exist?

For drivers, Waze already offers a way to share current police sightings [1]. Its strength is information reported by people on the road. Highway Radar’s proposed contribution is an image-based view of potential roadside locations that does not require a recent sighting. These approaches answer different questions: a reported sighting describes an observation, while an image-based marker describes an estimated property of a location. They could be complementary, but my project does not yet integrate them.

For the processing system, the simplest option is one computer checking images one at a time. It could save each result as it finishes and use a checklist to resume unfinished work after an interruption. This may be sufficient for a small dataset and would be relatively easy to maintain.

A second option is to let several processes on the same computer work on different images. Python’s ProcessPoolExecutor supports this kind of local parallel processing [5]. I would still need to implement progress tracking and recovery. The benefit would depend on whether the computer has enough processing power and memory to handle several images at once.

A third option is a shared task queue using Celery and RabbitMQ. The queue acts like a to-do list, and workers are programs that take image-processing jobs from it. With appropriate configuration, unfinished work can be made available for another attempt [2, 3]. This also creates a path toward distributing work across computers, although it introduces more components to maintain.

| Approach | Main benefit | Main limitation |
| --- | --- | --- |
| One process on one computer | Simple to build and monitor | Handles images one at a time |
| Several processes on one computer | Can process independent images together | Shares one computer’s resource limits |
| Shared queue with multiple workers | Can coordinate retries and work across computers | Requires more setup and careful failure handling |

In my proposed design, every image-processing job would have a stable identifier that includes the model version. The database would use this identifier to prevent a repeated attempt from becoming another logical result. PostgreSQL provides conflict-handling features that can support this behavior [6]. A worker would save the result and its completion status together before reporting success.

This does not mean an image can never be processed twice. It means repeated attempts should still produce one authoritative stored result for that job. All three approaches need dependable recordkeeping, and none automatically improves the model’s prediction accuracy.

## What is the most important thing you still do not know?

The main uncertainty is whether the shared-queue approach improves processing or recovery enough to justify its added complexity. More workers do not automatically mean faster results. If they all compete for the same graphics card or memory, they could slow one another down.

I will compare the three approaches using the same images, trained model, and database. I will test batches of 100, 500, and 1,000 tasks where the dataset permits. If images are repeated to create a larger workload, I will identify them as repeated test inputs rather than additional unique images.

The comparison will measure how long a batch takes, how many distinct jobs finish successfully, and how long recovery takes after an interruption. I will also check for missing results, duplicate records, and tasks that remain stuck. Each configuration will run at least five times so that the findings do not depend on one unusually fast or slow run.

The interruption tests will stop a worker before it saves a result, stop it after saving but before confirming completion, and temporarily disconnect it from the queue. I will also submit the same job more than once. A successful test should leave one authoritative result for each completed job and a clear record of any job that could not finish.

Initial testing will use one computer. If a second computer is available, I will separately test work distributed across machines. I will not describe same-computer tests as evidence that the system can survive the loss of an entire machine.

A separate product question is whether drivers understand and value the predictions. A future user study could ask participants to interpret map markers and distinguish estimates from sightings. That would be necessary before claiming that the app improves confidence or peace of mind.

## Your Individual Scope

My individual contribution will be building and evaluating the processing system around an existing highway-image model. I will compare a resumable local approach with a shared-queue approach and explain how their reliability affects the information a future user sees.

The planned tools are Python and PyTorch for image analysis, Celery and RabbitMQ for organizing jobs, and PostgreSQL for storing results. A basic map or result view will demonstrate completed predictions, unfinished work, and failures. A full navigation app is outside this project’s scope.

I will not retrain the model, collect national road coverage, detect live police presence, or build a system that survives every possible outage. Keeping these boundaries makes the work manageable for one student. The final outcome will be an evidence-based recommendation about how to process this workload dependably, together with a clear explanation of what the resulting map can and cannot tell a driver.

## References

[1] Waze. (n.d.). *Report police sightings*. Waze Help. Retrieved October 26, 2026, from https://support.google.com/waze/answer/13739289?hl=en

[2] RabbitMQ. (n.d.). *Reliability guide*. RabbitMQ documentation. Retrieved October 26, 2026, from https://www.rabbitmq.com/docs/reliability

[3] Celery Project. (n.d.). *Tasks*. Celery documentation. Retrieved October 26, 2026, from https://docs.celeryq.dev/en/stable/userguide/tasks.html

[4] Dean, J., & Ghemawat, S. (2004). MapReduce: Simplified data processing on large clusters. *Proceedings of the 6th Symposium on Operating Systems Design and Implementation (OSDI ’04)*, 137–150. https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/

[5] Python Software Foundation. (n.d.). *concurrent.futures — Launching parallel tasks*. Python documentation. Retrieved October 26, 2026, from https://docs.python.org/3/library/concurrent.futures.html

[6] PostgreSQL Global Development Group. (n.d.). *INSERT*. PostgreSQL documentation. Retrieved October 26, 2026, from https://www.postgresql.org/docs/current/sql-insert.html
