# What broke and how I fixed it

Add a line every time something goes wrong. This is the script for the "what broke" part of the video.

| # | What broke | Why | Fix |
|---|---|---|---|
| 1 | The first prototype could not reach any job-board API (403 from the network) | The cloud sandbox only allowed a few websites | Moved the pipeline to GitHub Actions, which can reach the APIs, and run it there daily |
| 2 | Same opening showed twice: once from a job aggregator, once from the company site | Collected from both kinds of sources | Dropped aggregators entirely; only company job boards. De-dupe keeps one copy |
| 3 | One role became 3 cards (Bengaluru, Pune, Hyderabad) | Companies list each city as a separate post | Match on company + cleaned title, merge into one card with all cities |
| 4 | "Bangalore" and "Bengaluru", "Gurgaon" and "Gurugram" split the city filter | Every company spells cities differently | One canonical city list in config; the LLM may only answer with those names (schema enum) |
| 5 | "Remote" jobs from the US slipped in | "Remote" alone says nothing about the country | Remote counts as India only if the post mentions India |
| 6 | India check missed "Bengaluru, India" in tests | First regex was case-sensitive lowercase | Split into a case-insensitive word check and a case-sensitive code check (IN / IND). Caught by a unit test |
| 7 | A board that was down for a day would have "closed" all its jobs | Missing post was read as "job closed" | Track which boards answered; only close posts from boards that answered |
| 8 | Dates from Lever came as numbers | Lever sends epoch milliseconds | Date helper accepts both ISO strings and epoch ms |
| 9 | Keyword-only tagging put ~46% of posts in "Other" (79 of 171 in the preview) | Job titles are messy ("Intern - Community & Documentation") | This is why the LLM tags role; keyword tagger kept only as a fallback and a baseline |
| 10 | LLM could skip a post or return an unknown city | Models are not perfectly obedient | Strict tool schema with enums, validation after the call, keyword fallback for anything missing |
| 11 | Re-running would pay to tag the same posts again | No memory between runs | Cache tags per post + prompt version; only new posts go to the LLM |
|  | *(add real issues from your first live run here)* | | |
