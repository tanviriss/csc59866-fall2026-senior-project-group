Benny Wen  
Professor Kurt Brown  
CSC 59866  
28 September 2026  
Candidate Problem Background

## 1- Describe the Problem

Data brokers harvest and collect personal information about most U.S. adults, often without their knowledge or consent. They then turn around and sell it to anyone willing to pay (van Kempen et al., abstract). Removing that information manually is slow, tedious, and burdensome. Laws like the California Consumer Privacy Act (CCPA) let individuals ask a broker to delete their data or stop selling it. Brokers must comply with these deletion requests within 45 calendar days and opt out requests within 15 business days (van Kempen et al., sec 2.1).  
For the individual consumer, going about opting out requires the individual to have to contact each broker separately, through its own form, email, or via a paid third-party service (van Kempen et al., sec 2.2). Nothing is standardized, brokers ask for different personal details, use different form layouts, and often add required CAPTCHAs, which creates what one study called an "extremely heavy” burden (van Kempen et al., sec 5.2). The need to delete or at the very least, stop the sale of private information, is important because broker profiles often enable identity theft, stalking, and scam calls. It’s also not a one time fix, since brokers periodically rescrape the internet and rebuild profiles on people who’ve already opted out. The problem compounds because so many independent brokers hold the same person’s data. In California alone, there were 535 registered data brokers as of late 2025 (van Kempen et al., sec 4.3). This is made even worse by the fact that opt-out pages change over time or break (yaelwrites), and automated attempts to keep up with these changes can quietly break when the pages themselves change (stephenlthorn).

## 2- Evidence

In one study, researchers submitted 322 deletion and 358 opt-out requests to California registered data brokers using synthetic (made up) identities. Only 97 of the 322 brokers reported the outcome of a deletion request, and 22% asked to verify identity on opt-outs, which CPPA explicitly forbids (van Kempen et al., secs 5.1, 5.4.1). The researchers were computer science students with technical backgrounds, and it still took them 45 hours combined (van Kempen et al., sec. 5.6). Since this study was California exclusive, it’s unclear how well these numbers hold nationally.  
In 2014, the FTC recommended “a centralized mechanism, such as an Internet Portal” where brokers could describe practices and offer opt-out requests (Brill, 2). California built something similar in 2026, the Delete Request and Opt-Out Platform (DROP) (van Kempen et al., sec 2.2.3).  
The github repo owner of a self opt-out guide with a mega list of the top data brokers says the process can take a long time, may need repeating, and that brokers often change their opt-out pages (yaelwrites), which lead to deprecated links. Another repo owner of an open-sourced automation opt-out request tool ran into a similar problem, citing broken form selectors that fail quietly whenever a page changes (stephenlthorn).  
Personally I believe that the complexity of automation comes from the differences between each broker’s process rather than legislation itself, and software tracking the state of each request could reduce it. However I haven’t tested either idea yet.

## 3 \- Existing Solutions

| Approach | How it address the problem | Strengths | Limitations/Questions |
| :---- | :---- | :---- | :---- |
| Manual guided lists (BADBOOL) | Volunteer maintained, prioritized instructions for opting out of each broker manually (yaelwrites) | Free, transparent, last updated June 2026 (yaelwrites) | Burdensome and time consuming to opt out of every broker Some steps include phone calls, ID, verification codes, and broken/updated websites. |
| Open-Source Automation (Auto Identity Remove) | Script that searches every broker sites, fills opt out forms, and reruns monthly while recording the state (stephenlthron) | Free and open source | Broken selectors fail quietly. “Submitted is not proof of deletion or opt-ut (stephenlthorn). |
| Commercial removal services | Paid service submit request on the consumers behalf | Convenient | Cost, a recurring monthly or yearly charge. Requires users to share personal data with another company. |
| DROP (California) | Consumer files one request, registered brokers must download requests at least every 45 days and report a status code (CPPA, secs 7612, 7614). | One request reaches 500+ brokers (yaelwrites). Legally required and continuous status reporting. | California residents only (CPPA, sec 7620). |

DROP is one of the most useful models, free, however only open to California residents. One request reaches hundreds of brokers, with required status reports (CPPA, secs. 7601, 7614). But it relies heavily on California law requiring brokers to respond in a timely manner. In states without comparable privacy legislation, consumers take on the burden of having to contact individual data brokers themselves or by using a third party service (van Kempen et al., sec 2.2.3). If a nationwide tool were built, it’d likely follow DROP’s design. The main question is how well coordination and status tracking holds up when the brokers themselves aren’t obliged to process requests within a set time frame, outside of California.

## 4 \- Relating the Problem to My Senior Project

Option 2\. The end goal is a real world consumer privacy system, not a general purpose distributed system tool.  
Adaptive design. The course reading defines adaptive design as reusing an existing solution for a different application or need (Engineering Capstone Design, ch. 1). Tools already exist that automate the opt-outs to some degree. Though each has its limitations. DROP is the most comprehensive and standardized of them, but it only covers California residents. My project would likely adapt those ideas into a nationwide approach that extends DROP’s model to reach consumers it doesn’t currently serve.  
As for distributed systems, it still has some relevance to the project. Independent services fail unpredictably, broken websites and CAPTCHAs that kept researchers from contacting some brokers at all (van Kempen et al., sec 4.3). Persistent state and retries also matter. One open source tool skips brokers it already remove a consumer from within the last 90 days, and retires unconfirmed email requests after 14 days (stephenlthorn).

## 5 \- What I still Do Not Know

| Question | How I might investigate it |
| :---- | :---- |
| Do submitted requests actually lead to deletion of the consumer’s broker profile? | The main study could not tell since it used synthetic identities (van Kempen et al., sec. 6). I could investigate more on DROP and its success rate after brokers were required to begin processing requests in August 2026, or design a small experiment. |
| What rights do consumers have state by state? Can a tool work universally even in states with weak privacy legislation? | Review state privacy laws and broker TOS. DROP’s authorized agent rules only apply to California residents who verify state residency (California Privacy Protection Agency, secs. 7620-7621). |
| How often do automated opt-outs fail on live sites? | With the open source automation tool on github. I could test a sample and read the repository's issue history. |

## 6 \- One Early Risk

The main risk is testing and evaluating the software's efficacy. Confirming whether a removal request actually worked requires a real identity, but the closest study used only synthetic identities and couldn’t verify deletion (van Kempen et al,, sec. 6). Testing with my own data raises privacy concerns too, since it would mean handling sensitive data like name, address, and contact information.

## 7 \- Connecting the Readings

The introduction of adaptive design changed how I view this project because existing tools and DROP already solve much of the problem. So I will be adapting them for consumers they don’t cover rather than building a replacement (Engineering Capstone Design, ch. 1).  
The reading also says to study existing solutions first and decide whether an existing product can be modified or a new system is needed (Engineering Capstone Design, ch. 2). Comparing the manual, open sourced automated tool, commercial, and regulatory state level approaches, my project should focus on the gaps they leave and the consumers they don’t serve.  
The risk management process and its technical and legal risk shaped Part 6 (Engineering Capstone Design, ch. 3). Evaluating results is a technical risk as it involves the handling of personal data and adds legal risks.

## Works Cited

Brill, Julie. “Statement of Commissioner Julie Brill.” *Data Brokers: A Call for Transparency and Accountability*, Matter No. P125404, Federal Trade Commission, 27 May 2014, www\.ftc.gov/system/files/documents/public\_statements/311551/140527databrokerrptbrillstmt.pdf.

California Privacy Protection Agency. “Text of Regulations: Accessible Deletion Mechanism.” *California Code of Regulations*, title 11, div. 6, ch. 3, California Privacy Protection Agency, 6 Nov. 2025, cppa.ca.gov/regulations/pdf/drop\_ftr.pdf. Accessed 26 Sept. 2026\.

Driscoll, Mark, et al. *Engineering Capstone Design: Project Planning, Organizing, and Executing*. Wiley, 2024\.

stephenlthorn. *auto-identity-remove*. GitHub, github.com/stephenlthorn/auto-identity-remove. Accessed 26 Sept. 2026\.

van Kempen, Elina, et al. “Let My Data Go: Data Brokers' Compliance with Opt-Out and Deletion Requests.” *arXiv*, 5 July 2026, arxiv.org/abs/2607.04552.

yaelwrites. *Big Ass Data Broker Opt-Out List*. GitHub, 28 June 2026, github.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List. Accessed 26 Sept. 2026\.