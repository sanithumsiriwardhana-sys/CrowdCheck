# Gate 2 - Build Checkpoint (draft answer)

Fill in the [brackets] and remove anything that isn't true for your team before submitting.

**GitHub repo:** [https://github.com/your-username/crowdcheck-177]
**Demo video (unlisted):** [YouTube / Drive link]
**Architecture diagram:** docs/architecture.png in the repo

## What's changed since Gate 1 and why

**1. The first model is trained on seed data, not real field logs (yet).**
In Gate 1 we planned to seed the model with field-logged crowd levels on Route 177. In the first week most of our time went into the survey, so we only managed [X / no] field log entries. To get a working prediction pipeline running, we generated synthetic seed data shaped by what our survey showed (peaks around 7-9am towards SLIIT and 5-7pm from SLIIT, quieter weekends and holidays, rain making buses fuller). The model currently scores [83.7]% on held-out seed data, but that only shows it learned the seed pattern. It is not real-world accuracy. We added a field log template so the team can log real buses this week, and field log rows are weighted 5x more than synthetic rows when we retrain.

**2. We brought rider reports forward from Week 3 to Week 2.**
The crowd report button was the thing 98% of survey respondents said they would use, so we built it now instead of later. Reports are saved in Supabase, and if someone checks a bus close to the current time, reports from the last 30 minutes are blended into the prediction. Reports can also be fed back into training (`python -m ml.train --with-reports`).

**3. We added a whole-day view, not just a single prediction.**
Our survey showed most students guess from experience. A single answer for one time doesn't help much with deciding when to leave, so the app also shows every bus of the day as a coloured timeline and suggests a less crowded bus within 30 minutes when there is one.

**4. The LLM part is postponed.**
In Gate 1 we said an LLM would turn the prediction into a plain-language tip. For now the tip is rule-based, because it was simpler and works fine for four crowd levels. We will decide in Week 3 if an LLM actually adds anything here, and we will drop it if it doesn't.

**5. Still Route 177 only.**
No change here. 177 was named the most crowded route by 10 of the 13 people who named one, so we are keeping the MVP to 177 before adding 17, 170 and 190.

**User feedback since Gate 1:** [Write what you learned from any follow-up conversations, e.g. "We spoke to X students who said ...". If you didn't do any yet, say so and say when you will.]

## Next (Week 3)
- Log real Route 177 buses at peak times and retrain
- Get classmates using the report button and track how many reports come in
- Add routes 17, 170, 190
- Business case, AI usage report, pitch deck, final demo
