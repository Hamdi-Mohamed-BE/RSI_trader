# The AI Trading Library: full reference (knowledge file for your AI research assistant)

Educational only. Not financial advice. No result is guaranteed. Trading involves risk.


---

# Start here: how this library works

*Start here · 6 minute read · 10 minutes to set up*

**In one line:** this library is a team manual for a fully automated AI trading system. Each guide covers one part of it. Agents research, a risk gate checks every plan, and an execution agent places orders through your broker or prop API, only inside the limits you set.

> **What's in this guide**
> - What this library is, and what it deliberately is not.
> - How the library is laid out, and how to set up your own AI research assistant in two minutes.
> - What you need before you start.
> - Where the research team and the team kit fit, once the routine is running.
> - A short quick start, one small job per step.

## 1. What this library is

You already trade. You have a setup you like, a platform you know and probably a chat AI you use now and then: "what do you think of this chart?"

That is one opinion from one chat that wants to be helpful. It agrees too easily, it invents levels, and it has no idea what your rules are.

This library turns that habit into a **team**: an AI agent team, each agent with one job, one format and only the information it should see. An Analyst describes the market. A Researcher turns your setup into rules you can check. A Bull and a Bear argue both sides. A Risk Manager says no when your rules say no. A Trader writes the trade card. A Decider writes a one-page memo with a score from a fixed rubric.

Then the risk gate checks the plan against your limits, and the execution agent places the order automatically through your broker or prop API. You set the rules and limits; the system executes.

## 2. What it is not

- **Not signals.** Nobody here tells you what to trade. The team checks *your* setup against *your* rules.
- **Not a black box.** Every agent's prompt, format and rule is written out here. The research agents run in chat tools you already use (Claude, ChatGPT, Gemini). Execution runs through a broker or prop API, inside hard limits.
- **Not a strategy to copy.** The playbooks in Guides 12 and 13 are research briefs with blanks. You fill the blanks and test them on your own market. No brief comes with a result.
- **Not a promise.** A better process doesn't guarantee a better result. The team helps you skip the trades your own rules say to skip. The market still decides the outcome.

If you want a black box that promises returns, this is the wrong place. If you want an automated system whose every rule you wrote and can read, it's the right one.

## 3. How the library is laid out

The library has three shelves.

**The trading team, Guides 00 to 10.** The core system. Read these in order. Each guide has the same shape:

- **In one line** and **What's in this guide**, so you know why you're reading it.
- Numbered sections, a **worked example** on a realistic setup (NQ futures or EURUSD, prices marked "example"), and red flags where the AI tends to go wrong.
- **Common mistakes**, a **checklist**, and a **Try it** step that takes five minutes.

**Playbooks, Guides 11 to 13.** The research team. Guide 11 is the method for testing a strategy idea honestly. Guides 12 and 13 are eight well-known public strategy families written as research briefs. Open these once the routine runs, when you want to pressure-test your own setup or look at a new one. Never on a trading morning.

**The team kit, Guides 14 to 17.** The tools the team runs on, every ready-made prompt in one place, every template, and a glossary. Keep them open while the system runs.

## 4. Set up your AI research assistant (2 minutes)

You get your own AI research assistant that answers from this library, inside the AI you already use. It answers from the guides and tells you which guide the answer comes from.

1. Download the two assistant files from the **Templates** page: `ai-trading-library-full.md` (the whole library in one file) and `research-assistant-instructions.txt` (the assistant instructions).
2. In Claude, create a **Project** (in ChatGPT, a **Project** or a custom GPT). Paste the assistant instructions into the project's instructions and upload the library file as its knowledge.
3. Ask it your first question.

Use it for:

- "Where does the Bear get its information from?"
- "My Risk Manager cleared a trade that was over my limit. What went wrong?"
- "Help me rewrite my setup description so the Researcher can turn it into rules."

It will not tell you whether to take a trade, what the market will do, or which firm to pick. That's by design. Ask it about the method, not the market.

## 5. What you need

| You need | Why | Notes |
|---|---|---|
| One AI chat account that reads images | Every role runs here | A paid plan is easier: free tiers limit messages and image uploads |
| Your charting platform | Screenshots and, later, exported data | Whatever you use now |
| An economic calendar you trust | The team only knows the events you paste | Copy as text each morning |
| A spreadsheet or table | Your journal | Columns are given in Guide 08 |
| 20 minutes before your session | 15 for the team, 5 for your platform | Same time every day |
| A demo or sim account to start | Run the system without money on the line | Strongly recommended |
| A broker or prop account with API access | The execution agent places orders through it | Hard limits set on the account itself |

Guide 14 lists the whole kit by job, with a free minimum version and a two-minute setup step for each tool.

## 6. The quick start

![The quick start: one job per step](/media/course/00-seven-day-path.png)

| Step | Job | Guide | Time |
|---|---|---|---|
| 1 | Check your kit, set up your workspace, paste the team setup, write your setup in your own words | 01, 02, 14 | 30 min |
| 2 | Build an event sheet from yesterday's calendar. Run the Analyst and Researcher on yesterday's chart. Build your setup sheet | 03 | 30 min |
| 3 | Run the Bull and the Bear on the same chart, in separate chats. Then a pre-mortem | 04 | 20 min |
| 4 | Write your risk rules sheet and your tilt-check rule. Set the matching limits in your platform | 05, 07 | 40 min |
| 5 | Trade card and decision memo on a past day. Then the full routine on a replay | 05, 06 | 30 min |
| 6 | The full 15-minute routine before a live session, on demo or sim. Debrief afterwards | 06, 08 | 25 min |
| 7 | A weekly review, even with only a few rows | 08 | 30 min |

Prop-firm traders add Guide 09 at step 4.

**After the quick start.** Keep the routine running. A week later, read Guide 11 and run the Evidence Checker on whatever rows you have. It will tell you, correctly, that it is too early to conclude anything, and show you what to collect. Guide 10 covers how the automation steps up from sim to live.

## 7. Worked example: one trader's quick start

*Illustrative. A trader who trades MNQ in the first two hours of the New York session.*

- **Step 1.** Creates a workspace called "Team", pastes the team setup, and writes: "I buy when NQ breaks the opening range and comes back to retest it with a strong candle, when the trend is up."
- **Step 2.** The Researcher finds three vague words: "strong", "trend" and "comes back". They become measurable rules. The setup sheet is half a page.
- **Step 3.** The Bear points out that the retest sits 40 points under the prior day's high. The trader hadn't looked up.
- **Step 4.** Writes ten risk rules and finds the platform has a daily loss limit setting that was never switched on. Switches it on.
- **Step 5.** Runs the full team on last Tuesday's chart. It takes 26 minutes. Fine for a first run.
- **Step 6.** On sim. 17 minutes. The event sheet shows a release inside the window, the Decider scores the plan 2, and the system passes. No order sent. That counts.
- **Step 7.** Four journal rows. The reviewer says: "sample too small to conclude anything", and points out one trade sent without a memo. One change for next week: no order without a memo.

The point of the quick start isn't a result. It's the routine.

## 8. Common mistakes

- **Reading every guide before doing anything.** Do each guide's step the day you read it. The team is a habit, not a theory.
- **Jumping to the prompts without a rules file.** Without your rules, every seat is guessing. The team is only as good as what you give it.
- **Starting with the playbooks.** They are the most interesting guides and the wrong place to begin. Build the routine first.
- **Going live straight away.** Start on demo, sim or replay until the routine is clean.
- **Changing everything at once.** New tool, new setup, new routine and new risk rules in one week means you can't tell what helped.

## 9. Checklist

- [ ] I know orders are placed automatically through a secure broker connection, only inside my limits
- [ ] I've blocked 20 minutes before my session for the next week
- [ ] I have one AI chat account that reads images
- [ ] I have a demo, sim or replay account to start on
- [ ] I know Guides 11–13 are for research once the routine runs, and Guides 14–17 are the kit

## Try it (5 minutes)

Open a note and write your main setup in your own words, the way you'd explain it to a friend at a bar. Three to six sentences. Don't tidy it up. At step 2, the Researcher turns those exact words into rules, and the messier they are now, the more you'll learn.

*Educational only. Not financial advice. Trading involves risk.*


---

# The team: an AI agent team, fully automated

*The team · 9 minute read*

**In one line:** one AI chat is a poor trading partner because it anchors on you, agrees with you and fills gaps with invented detail; a team of single-job agents, each seeing only what it should, fixes all three. You set the rules; the system executes inside them.

> **What's in this guide**
> - The three ways a single chat quietly makes your trading worse.
> - The agent team: what each agent does, what it sees and what it can never do.
> - The packet: how information moves around the team without leaking bias.
> - A side-by-side example: the same setup, asked of one chat and of the team.

## 1. Why one chat isn't enough

Most traders use AI like this: screenshot, "what do you think, looks like a good long?", read the answer, feel better, enter.

Three things go wrong.

**Anchoring.** Chat models build on the frame you give them. "Looks like a good long" sets the frame. The answer is organised around why it's a long. Ask the same chart "where does this fail?" and you get a different answer from the same model. Neither is the truth. Both are an echo of the question.

**Agreeing with you.** Chat assistants are built to be helpful and pleasant. Pleasant often means agreeing. Under pressure, with a setup you're excited about, you need the opposite: someone whose job is to disagree.

**Inventing detail.** Ask for levels and you'll get levels, to the tick, whether or not they're on your chart. Ask about news and you may get an event that isn't on today's calendar. The model fills the gap with something that sounds right.

There's a fourth, quieter one: **one chat marks its own work.** If the same conversation builds the case, checks the risk and writes the verdict, every step inherits the mood of the first.

![One chat versus a team](/media/course/01-one-chat-vs-team.png)

## 2. How a team fixes it

Professional teams solved this long before AI. Different people own different jobs. The analyst doesn't size the trade. The risk manager doesn't care how good the story is. The final call is made from a memo, not a mood.

You can copy that structure with chat tools in four moves:

1. **Separate the jobs.** Each role has one job and one output format. If a job needs the word "and" twice, it's two roles.
2. **Separate the information.** The Bull and the Bear don't see your hopes. The Risk Manager doesn't see the debate. A role can't be biased by what it never read.
3. **Fix the formats.** Same sections, same order, every day. Formats can be compared across days. Free-form chat can't.
4. **Put a hard gate at the end.** The team proposes. The risk gate checks it against your limits. Only then does the execution agent send the order.

## 3. The agent team

![The team: an AI agent team, fully automated](/media/course/01-the-team.png)

| Seat | One job | Sees | Hands over | Never does |
|---|---|---|---|---|
| **Analyst** | Describes today's market | Your screenshots, your pasted calendar | Market brief + regime label | Suggest trades |
| **Researcher** | Turns your setup into yes/no rules, then checks today's chart | Your setup in your words, the brief, the chart | Setup sheet (once), setup watch (daily) | Add rules you never said |
| **Bull** | Best honest case for the plan | The packet only | 3 reasons + the best point against itself | Invent evidence |
| **Bear** | Best honest case against | The packet only | 4 points + what would prove it wrong | Use generic fear |
| **Risk Manager** | Applies your written risk rules | Risk sheet + account state + trade card | TEAM ON/CLOSED, CLEAR/BLOCK | Judge the setup, lift a block |
| **Trader** | Writes the trade card | Watch zones, scenario, risk budget | Conditional card: entry, stop, target, size, expiry | Round size up, skip the risk gate |
| **Decider** | Writes the memo with a rubric score | The whole packet | Decision memo, score 1–5, TAKE or PASS verdict | Override the risk gate |

Then the **execution agent**. It reads the verdict and the Risk Manager's CLEAR, and places the order through your broker or prop API, only inside your limits. A PASS or a BLOCK means no order. Your job is the rules, the limits and the review.

**Around the agent team** sit a few short helper prompts. The News agent builds today's event sheet from the calendar you paste. The Pre-mortem assumes the trade lost and asks why. The Tilt check counts six yes/no answers about your state. The Debrief sets the plan beside what you did. Two reviewers read your journal weekly and monthly. And two research seats, the Strategy Scout and the Evidence Checker, work away from the trading day (Guide 11). All of them feed the agents. None of them sends orders.

## 4. The packet

The packet is the text that moves between seats. It grows as the team works:

**Event sheet → Brief → Watch → Scenario → Bull case + Bear case → Risk day check → Trade card → Memo**

Two rules keep it clean:

- **Pass outputs, not opinions.** You paste the Analyst's brief to the Bull, not "I think this is a great long".
- **Some seats get less.** The Risk Manager gets the risk sheet, the account state and the card. Nothing else. It's the only way to build a role that can't be talked round.

## 5. Worked example: the same setup, two ways

*Illustrative. NQ futures, New York session, prices are examples.*

**One chat.** "NQ swept the overnight low and reclaimed it, looks bullish, good long here?"

> *"Yes, this looks like a strong bullish setup. The sweep of the overnight low suggests liquidity was taken and buyers stepped in. A long here with a stop below the sweep low and a target at the prior day high around 21,520 makes sense..."*

Confident, agreeable, and the 21,520 level isn't on the chart. The prior day high on the trader's own chart is 21,492 (example).

**The team.** Same chart, run through the seats:

- **News agent and Analyst:** the pasted calendar shows a high-impact release at 10:00, inside the window. Regime EVENT DAY. Prior day high 21,492 (chart).
- **Researcher:** context rule 2 ("1H higher low in place") is CAN'T TELL from the screenshot. Watch zone 21,450–21,455 (chart).
- **Bull:** the reclaim held for three 5-minute candles (Watch 1). Best point against itself: the event at 10:00.
- **Bear:** entry near 21,452 with a 20-point stop and the prior day high 40 points above leaves 2R to a level that often stalls price, and the 10:00 event sits inside the valid window.
- **Risk Manager:** TEAM ON, blackout 09:50–10:10 from the news rule.
- **Decider:** score **2**. Rubric line: "the Bear has an unanswered point about event risk". Becomes a 1 if the reclaim fails before 09:50.

The team didn't forecast anything. It caught an invented level, an event inside the window and a rule that couldn't be checked. The card was held until after 10:10 and the watch re-run. That's the job.

## 6. What the team is not

- **Not a forecaster.** No seat predicts price. The Decider's score rates the evidence for a plan under your rules. It's not a probability.
- **Not an authority.** Every level read off an image is a draft until it is checked against exported data.
- **Not a replacement for limits.** Hard risk limits live in your platform and broker account (Guide 07). The AI risk gate is the second line.

## 7. Common mistakes

- **Running every agent in one long chat as the default.** It's allowed on short days (Guide 06), but it brings back anchoring and self-grading.
- **Telling the Bull or Bear what you think.** The moment you do, you've chosen the winner.
- **Showing the Risk Manager the debate.** It will start weighing the setup. Its only question is "is this allowed?"
- **Treating the score as a signal.** A 5 means the evidence is clean under your rules. It doesn't mean the trade works.

## 8. Checklist

- [ ] I can name the agents and the one job each does
- [ ] I know which seats see the packet and which see less
- [ ] I know the Decider's score is a rubric, not a probability
- [ ] I know the execution agent places orders automatically, inside my limits

## Try it (5 minutes)

Take a screenshot of your last trade at the moment you entered. Ask a fresh chat: "Good trade?" Then open another fresh chat and ask: "Assume this trade lost. Using only what's visible, give the three most likely reasons." Put the two answers side by side. That gap is why the team has a Bear.

*Educational only. Not financial advice. Trading involves risk.*


---

# Set up your AI: accounts, models, privacy, charts

*Setup · 10 minute read · 30 minutes to do*

**In one line:** one AI account, one team workspace holding the team setup, four clean chats a day, nothing private pasted in, screenshots for reading the chart and exported data for exact numbers.

> **What's in this guide**
> - Which tool to use, and which kind of model suits which seat.
> - The team workspace: the team setup prompt, four chats, the FACTS check, and why memory features can hurt you.
> - The privacy line: what never goes into a chat.
> - How to give the AI your charts, and an honest test of how well it reads them.

## 1. Pick one main tool

Claude, ChatGPT and Gemini can all read images, follow standing instructions and keep to an output format. Any one of them can run this team. Pick the one you already use or already pay for. Switching tools costs more than the difference between them. The rest of the kit (charts, calendar, journal, capture) is in Guide 14.

**Free or paid?** Free tiers work for trying the prompts. For the daily routine, a paid plan is easier: free tiers usually limit messages, image uploads and access to the strongest models. The routine uses about 10–14 messages and 3–4 images a day. Check your plan's current limits.

**No code for the research agents.** They run in the normal chat app and never need your keys. The broker or prop API connection belongs to the execution agent only, set up separately with hard limits (Guide 10).

## 2. Which model for which seat

Model names change every few months, so choose by what the seat needs, not by name.

| Seat | What it needs most | Pick |
|---|---|---|
| Analyst, Researcher | Reading images accurately | Your tool's strongest model that accepts images |
| Bull, Bear | Following a format, arguing from evidence | Your primary AI model. Optional: run the Bear on a second provider for different blind spots |
| Risk Manager, Evidence Checker | Careful step-by-step checks and arithmetic | A "thinking" or "reasoning" mode if your tool offers one |
| Trader | Arithmetic (size maths) | Reasoning mode, with the Risk Manager re-checking the sum |
| Decider | Following a rubric exactly | Your primary AI model |
| Weekly and monthly reviewers | Reading a table or CSV | A model that accepts file uploads; reasoning mode helps |

If your tool only offers one model, use it everywhere. The team's structure matters more than the model.

## 3. Build the team workspace

![Who sees what: four chats, one workspace](/media/course/02-who-sees-what.png)

1. **Create one workspace for the team.** Most chat tools let you save standing instructions that apply to every chat inside a workspace. Claude and ChatGPT call the workspace a Project. Gemini has offered saved custom assistants under names that have changed. Names and features move, so look for "project", "custom instructions" or "saved assistant" in your tool's help pages. If yours has none, paste the team setup as the first message of every chat.
2. **Paste the team setup prompt** (below) as the standing instructions, with your rules file and your risk rules sheet pasted where the braces are. Templates for both are in Guide 16. Drafts are fine today.
3. **Open four chats each trading day,** named with the date:
  - **A — Team** (Analyst, Researcher, Trader, Decider)
  - **B — Bull**
  - **C — Bear**
  - **D — Risk** (day check in the morning, trade checks in session)
4. **Check memory settings.** Some tools have a memory feature that carries details from one chat into another. That's handy for normal use and bad for a team: it can feed your hopes from chat A into the Bear in chat C. If your tool has it, consider switching it off for the team, or check what it has stored.
5. **Run the FACTS check.** Type `FACTS` as the first message of a new chat. The reply should list your instrument, value per point, session, 1R, daily stop, max trades and news rule. If two chats answer differently, one is reading an old copy.

**Team setup prompt** (standing instructions of the workspace)

```text
TEAM SETUP — read before every reply

You are one seat on my trading team. I set the rules and the risk limits. You never place orders yourself; execution is handled by the execution agent after the risk gate. You work in the seat I name at the start of a chat ("Role: Analyst", "Role: Bear", and so on). If no role is given, ask which one and do nothing else.

HOUSE RULES
1. Evidence only. Use only what is in this chat: the facts below, my screenshots, my pasted data and my notes. If you need something I did not give you, write UNKNOWN and name what you need.
2. No invented numbers. Every price or level must come from my screenshot or my data, with its source: (chart) if read off an image, (data) if taken from numbers I pasted. Chart reads are approximate and I verify them.
3. No invented news. Never mention an event, release, headline or time unless I pasted it, or you browsed for it and give the source and time for each item.
4. Confidence in words: Low, Medium or High. Never a percentage chance, a success rate or a predicted price.
5. Unverified is a label, not a failure. If a statement rests on your general knowledge instead of my evidence, mark it (unverified). "Can't tell from this" is a good answer. A confident guess is a bad one.
6. No flattery. Do not praise me, my plan or my setup. Do not soften a finding because I seem keen. If I push back without new evidence, repeat the finding in the same words.
7. Stay in your seat. Keep to your role's job and its output format. Short lines. Plain English. No hype, no emojis.
8. Rules first. If anything I ask would break my rules file or my risk sheet, say so in the first line of your reply.
9. No memory claims. Do not refer to earlier sessions unless I pasted them into this chat.
10. Self-check. Before you send any reply, check it against rules 1 to 6 and against the format I asked for. Fix what fails, or say which part you could not complete.

THE SEATS (one job each)
- News agent: turns the calendar I paste into today's event sheet. Never adds events.
- Analyst: describes the market. Never suggests trades.
- Researcher: turns my setup into yes/no rules and checks today's chart against them. Never adds rules I did not say.
- Bull: best honest case for the plan. Bear: best honest case against. Evidence from the packet only.
- Risk Manager: applies my risk sheet to my account state. Never judges the setup. Never lifts a BLOCK.
- Trader: writes the trade card. Size is only ever rounded down.
- Decider: writes the memo, scores it from the rubric and gives a TAKE or PASS verdict. Never overrides the risk gate.
- Strategy Scout and Evidence Checker: research seats. They describe what a test would need and what my own rows show. They never say a strategy works.

SCORING RUBRIC (Decider and Fast team; the lowest line that applies wins)
1 = Any context rule FAIL, any no-trade condition met, the Risk Manager says CLOSED, or the card is outside the risk budget.
2 = Rules pass, but two or more context rules are CAN'T TELL, or the Bear has an unanswered point about event risk or location.
3 = Rules pass, at most one CAN'T TELL, the Bear's best point is partly answered.
4 = All context rules PASS, the regime fits the setup, the Bear's points are answered with evidence, the card is inside budget.
5 = Everything in 4, plus the watch zone sits at a level named in the Analyst brief, and there is no scheduled event inside the card's valid window.

FACTS CHECK
If I write only the word FACTS, reply with one screen: instrument(s) and value per point or pip, session window and time zone, 1R, daily stop, max trades per day, news blackout rule, and the "last updated" dates of both sheets. Mark anything missing as MISSING.

MY RULES FILE
{paste your rules file here}

MY RISK RULES SHEET
{paste your risk rules sheet here}
```


Ten house rules, the seat list, the scoring rubric and your two sheets. Every seat reads the same facts, so the Trader sizes with the same value per point the Risk Manager checks with.

## 4. The privacy line

Never paste, upload or type any of these into any AI chat:

- Broker or prop-firm **passwords**, two-factor codes or recovery codes
- **API keys**, tokens or "connect your account" links
- Full **account numbers**, ID documents, bank details

Also:

- **Crop or cover** the account number and balance in screenshots if you prefer. The team works fine with risk expressed in R ("loss today: 1R") instead of money.
- **Check your tool's data settings.** Most tools let you choose whether your chats are used to improve their models. Decide on purpose.
- **Keep chat tools away from your broker.** Only the execution agent connects to your broker or prop API, through its own keys with hard limits on the account. Be wary of any chat extension or app that asks for trading-account credentials.

## 5. Giving the AI your charts

There are two ways in, for two different jobs.

![Screenshots for reading, data for numbers, nothing private](/media/course/02-what-to-give-the-ai.png)

**Screenshots, for reading.** Structure, swings, where price is relative to levels. How to take a good one:

- Price scale and time scale visible. Latest bar on the right edge.
- Two or three indicators at most. Your fixed lines (prior day high/low, session box) on.
- Higher timeframe first, same symbol: for example 4H, 1H, 15m.
- One screenshot per timeframe, labelled in your message ("image 1 = 4H").

**Exported data, for numbers.** When you need exact values (prior day high, overnight low, the opening range), export bars from your platform as CSV, if it offers that, or copy the values from its data window. Paste the last few dozen rows and ask the AI to compute the levels from the data. Values from data get tagged (data). Values read off an image get tagged (chart), and they're approximate.

## 6. The limits of AI chart reading

Be clear-eyed about this. Image-reading models:

- **Misread prices off the axis,** especially on busy or small charts.
- **Confuse candle colours** and miscount candles.
- **Can't see what's off-screen.** If yesterday's high isn't in the frame, it doesn't exist for the model.
- **Tend to see what you ask about.** Ask "do you see a double bottom?" and you'll often get one.
- **Don't know the time** unless the chart or you tell it.

None of this makes them useless. It makes every image-read level a **draft** that gets checked against exported data before it goes into a trade card.

## 7. Worked example: the calibration test

*Illustrative. MNQ 15-minute chart, prices are examples.*

The trader uploads one clean 15m screenshot and asks: "List the last three swing highs and swing lows as prices, tagged (chart). Then say how sure you are of each, Low/Medium/High."

| Level | AI read (chart) | Trader's chart | Off by |
|---|---|---|---|
| Swing high 1 | 21,488 | 21,492.25 | ~4 pts |
| Swing low 1 | 21,431 | 21,430.50 | <1 pt |
| Swing high 2 | 21,470 | 21,468.75 | ~1 pt |
| Swing low 2 | 21,402 | 21,414.00 | 12 pts, misread |

Run it five times over a week. Now the trader knows: on this chart layout, image reads are usually within a few points and sometimes badly wrong. So levels that matter (stop, target) always come from data, never from an image read.

## 8. Common mistakes

- **One endless chat for everything.** Fresh chats each day keep old context from leaking in.
- **Pasting the team setup once and forgetting it.** If your tool doesn't save instructions, it goes first in every chat. When a sheet changes, replace the old copy. One live version.
- **Trusting tick-precise levels from a blurry image.** Precision in the answer isn't accuracy.
- **Sharing a screenshot with account details** you didn't mean to share. Crop first.

## 9. Checklist

- [ ] One AI account chosen, image upload works
- [ ] Team workspace created, team setup pasted as standing instructions
- [ ] Rules file and risk sheet added (drafts are fine for now)
- [ ] Memory feature checked
- [ ] FACTS check gives the same answer in two chats
- [ ] Data-use setting chosen on purpose
- [ ] I know how to export bars or read exact values from my platform
- [ ] Calibration test run at least once

## Try it (5 minutes)

Create the team workspace and paste the team setup prompt as its standing instructions. Then upload one clean screenshot and run the calibration question from section 7. Compare three levels to your own chart and write down how far off it was.

*Educational only. Not financial advice. Trading involves risk.*


---

# News agent, Analyst and Researcher: facts, context and checkable rules

*The seats · 13 minute read · 30 minutes to do*

**In one line:** the News agent turns the calendar you paste into an event sheet, the Analyst describes today's market in the same six sections every day, and the Researcher turns your setup from a feeling into yes/no rules, then checks today's chart against them.

> **What's in this guide**
> - The News agent prompt: today's events and blackout windows, built only from what you paste.
> - The full Analyst prompt and what a good brief looks like.
> - The two Researcher prompts: build your setup sheet once, then run the daily setup watch.
> - A worked example on NQ, from a messy description to a clean rule sheet.
> - Red flags for both roles, so you catch bad output before it reaches a trade.

## 1. The News agent: events from your calendar, never from memory

A chat model does not know what is on today's calendar. Ask it anyway and it will often produce a plausible list from the shape of a typical month. That is how a trader ends up avoiding a release that isn't happening, or sitting through one that is.

So the team has one rule for news: **the only events that exist are the ones you paste.** Each morning, copy today's rows from the calendar you use, as text. The News agent turns them into an event sheet: times in your time zone, inside or outside your session, and the blackout windows your own news rule creates. The same sheet then goes to the Analyst and to the Risk Manager, so both work from identical events.

**News agent prompt** (chat A, during the five platform minutes)

```text
Role: News agent.

Build today's EVENT SHEET from the calendar text below and nothing else.

Inputs:
- Today: {date, weekday}
- Calendar I use: {name of the calendar}
- Time zone shown on the calendar: {e.g. New York / London / UTC}
- My time zone for the team: {e.g. New York}
- My session window: {e.g. 09:45–11:30 New York}
- Currencies or markets I care about: {e.g. USD for MNQ; EUR and USD for EURUSD}
- My news rule: {e.g. no entries from 10 minutes before to 10 minutes after any high-impact event; no new trades on rate-decision days}

Calendar text (pasted by me, unedited):
{paste the rows for today}

You may not:
- Add, rename or "correct" any event from memory. If an event is not in the pasted text, it does not exist for this sheet.
- Guess an impact level or a time. If either is missing in the text, write UNKNOWN.
- Forecast the number, the reaction or the direction. No comment on what the event means for price.

Reply in exactly this format:
EVENT SHEET — {date} — times in {my time zone}
1. Events, in time order: time · currency/market · event name as pasted · impact as pasted · INSIDE or OUTSIDE my session window.
2. Blackout windows from my news rule: start–end for each event the rule covers, and the event it comes from. Show the arithmetic (event time minus and plus my minutes).
3. Whole-day rules triggered: any "no trading today" line in my news rule that an event sets off, or "none".
4. Time-zone conversions made: from {calendar zone} to {my zone}, hours added or subtracted. If the two zones are the same, write "none".
5. Could not read: rows that were cut off, duplicated or unclear, quoted as pasted.
6. Count check: "{n} rows pasted, {n} events listed."

If the pasted text is empty, reply only: "No calendar pasted. I can't build an event sheet from memory."
Before you send: confirm every event in section 1 appears word for word in the pasted text, and that the count in section 6 matches.
```


> **Red flags: News agent**
> - An event you didn't paste. Delete the sheet and rerun in a fresh chat.
> - A time that moved by an hour. Check the time-zone line against your calendar.
> - Any comment on what the number will do to price.
> - A count check that doesn't match.

## 2. The Analyst: same shape, every day

The Analyst's job is boring on purpose. It describes structure, levels, events and a regime label. It doesn't suggest trades. Its value comes from consistency: when every brief has the same six sections, you start to notice what's different today.

**Before you run it:** have 2–3 screenshots ready (higher timeframe first) and the event sheet.

**Analyst prompt** (chat A)

```text
Role: Analyst.

Inputs:
- Instrument: {NQ / MNQ / EURUSD / ...}
- Session I trade: {e.g. New York, 09:45–11:30 ET}
- Today: {date, weekday}
- Attached screenshots: {e.g. "image 1 = 4H, image 2 = 1H, image 3 = 15m, latest bar on the right"}
- Exact levels from my data (optional): {e.g. prior day high / low / close, overnight high / low, or "none"}
- Today's event sheet (from the News agent, pasted by me): {paste, or "none pasted"}
- Headlines (optional, pasted by me): {paste, or "none"}

You may not:
- Suggest a trade, an entry, a direction to favour or a bias stronger than the evidence.
- Write any price that is not on my screenshots or in my data. Tag every price (chart) or (data).
- Mention any event or headline I did not paste.

Write the MARKET BRIEF in exactly this format:
1. Structure, higher to lower timeframe: one line each (up / down / sideways, last swing high and last swing low as prices).
2. Key levels: up to 5. Price, source tag, and what it is (prior day high, overnight low, range edge...).
3. Scheduled events: copy the INSIDE-window events and blackout windows from my event sheet. If none pasted, write "none pasted".
4. Regime label, one of: TRENDING, RANGING, QUIET, EVENT DAY. One sentence why, citing sections 1–3.
5. What would change this read: one observable event.
6. Unknowns: everything you could not read from the images, and any timeframe that disagrees with another.

If an image is too small or blurred to read a price, write CAN'T READ for that line. Do not estimate.
Before you send: check that every price has a tag, that section 3 contains nothing I did not paste, and that no line tells me what to do.
```


**The regime label matters more than it looks.** Four words only: TRENDING, RANGING, QUIET, EVENT DAY. Most setups are built for one or two of them. Once your journal has enough rows, you can count how your trade cards were scored and executed in each.

> **Red flags: Analyst**
> - A level with no (chart) or (data) tag, or one you can't find on your chart.
> - An event that isn't on your event sheet. That's invented news. Delete it and rerun.
> - "Bullish bias, high probability." The Analyst describes; it doesn't forecast.
> - Tick-precise prices from a small screenshot. Treat as approximate.

## 3. The Researcher, job one: build the setup sheet

Most setups live in the trader's head as a feeling: "a clean retest with a strong candle". You can't check a feeling against a chart, and neither can an AI. The Researcher's first job is to rewrite your setup as rules that a stranger could check by looking at a chart or a clock.

You do this **once per setup**, then paste the result into your rules file.

![From a feeling to rules you can check](/media/course/03-idea-to-rule-sheet.png)

**Researcher · setup sheet prompt** (chat A, or any chat in the workspace)

```text
Role: Researcher. Job: SETUP SHEET.

Here is my setup in my own words:
"{describe the setup the way you would explain it to a friend}"

You may not:
- Add a condition, filter, indicator or number I did not say. If the sheet needs one, ask.
- Say whether the setup is good, or whether it works. Your job is wording, not judgement.
- Fill a gap with an assumption. A gap becomes a question.

Reply in exactly this format:
SETUP SHEET (draft {n})
- Name: a short, fixed name for my journal.
- Context rules: what must be true before the setup can exist (timeframe, session, structure).
- Trigger rule: the exact event that makes it a trade.
- Entry: where, and with which order type.
- Invalidation (stop): where the idea is wrong, as a rule I can point to on the chart.
- Target: where I take profit, as a rule.
- Time exit: when I close it if neither stop nor target is hit, or "none stated".
- No-trade conditions: when I skip even if everything else passes.

VAGUE WORDS: every judgement word in my description ("strong", "clean", "looks like", "big"), each with two measurable replacements for me to choose between. Do not choose for me.
QUESTIONS: up to 3 things you need from me before the sheet is complete.
TRACE: next to each rule, quote the words of mine it came from. A rule with no quote is yours, not mine. Delete it.

Every rule must be a yes/no question I can answer by looking at a chart or a clock.
Before you send: reread each rule. If two traders could disagree about the answer on the same chart, it is still vague. List it under VAGUE WORDS.
```


Answer its questions. Run it again with your answers. Two or three rounds is normal. Stop when every rule is a yes/no question.

**The numbers are yours.** For each vague word the Researcher offers two measurable replacements and you choose. It must not choose for you, and neither it nor this library knows which value is better on your market. If you want to find out, that is a research question, and Guide 11 has the method.

## 4. The Researcher, job two: the daily setup watch

Every morning, the Researcher reads the Analyst's brief and today's chart, checks each context rule, and marks where your trigger could happen today.

**Researcher · setup watch prompt** (chat A, right after the brief)

```text
Role: Researcher. Job: SETUP WATCH.

Inputs:
- My SETUP SHEET (in the team setup, or pasted here): {paste if needed}
- The Analyst brief above in this chat.
- Attached: {current chart screenshot(s), timeframe labelled}
- Exact levels from my data (optional): {paste, or "none"}

You may not:
- Upgrade a CAN'T TELL to PASS, or soften a FAIL.
- Propose a watch zone at a price that is not on my chart or in my data.
- Comment on whether today "looks good".

Reply in exactly this format:
SETUP WATCH — {setup name} — {date}
0. First line: "SETUP POSSIBLE" or "NO SETUP TODAY: {the no-trade condition met}".
1. Rule check: each context rule with PASS, FAIL or CAN'T TELL, and the evidence (a price with its tag, or a time).
2. Watch zones: up to 2 places the trigger could happen today, each with the price area (tagged) and the trigger rule it needs.
3. No-trade conditions: each one, MET or NOT MET, with evidence.
4. What I must see live: the trigger as one sentence I can watch for.

If more than one context rule is CAN'T TELL, say the chart is not good enough to check and ask for a specific better screenshot or data.
Before you send: check that every PASS has evidence next to it and every price has a tag.
```


**CAN'T TELL is a real answer.** It means the chart you gave it doesn't show enough. Give it a better screenshot or exported data. Never let it, or yourself, turn a CAN'T TELL into a PASS because you want the trade.

> **Red flags: Researcher**
> - Rules that still contain judgement words after the rewrite ("strong", "clean", "decent").
> - Rules you never said. Every rule has a quote in TRACE, or it goes.
> - A PASS with no evidence next to it.
> - Watch zones at prices that aren't on your chart.

## 5. Worked example: from a feeling to a sheet

*Illustrative. MNQ, New York session, prices are examples.*

**The trader's words:**
"I buy when NQ breaks the opening range and comes back to retest it with a strong candle, as long as the overall trend is up. I don't trade big news mornings."

**Vague words the Researcher found, and the replacements agreed:**

| Vague | Measurable replacement |
|---|---|
| opening range | High and low of 09:30–09:45 New York time |
| breaks | A 5-minute candle closes above the opening-range high |
| comes back to retest | Price trades back to within 3 points of the opening-range high after the break |
| strong candle | A 5-minute candle closes back above the opening-range high, with its close in the top third of its range |
| overall trend is up | On the 1H chart, the last swing low is higher than the one before it, and price is above the prior day's close |
| big news mornings | Any high-impact event between 09:30 and 11:00 on my calendar |

**The setup sheet:**

- **Name:** Opening-range retest (long)
- **Context rules:**
 1. 1H last swing low is higher than the previous swing low.
 2. Price is above the prior day's close.
 3. Time is between 09:45 and 11:00 New York.
- **Trigger rule:** after a 5m close above the opening-range high, price returns to within 3 points of it, and a 5m candle closes back above it with its close in the top third of its range.
- **Entry:** limit at the opening-range high, or market on the trigger close if price is within 2 points.
- **Invalidation (stop):** below the low of the trigger candle.
- **Target:** prior day high, or 2R, whichever is closer.
- **Time exit:** flat at 11:30 New York if neither stop nor target is hit. *(From the trader's answer to the Researcher's question.)*
- **No-trade conditions:** a high-impact event between 09:30 and 11:00; the opening range is wider than 60 points; two losses already today.

**The event sheet, that morning:** four rows pasted, four listed. None inside 09:30–11:00. One at 14:00, outside the window, blackout 13:50–14:10.

**The Analyst brief (abbreviated):**

1. 4H up, last swing high 21,520 (chart), swing low 21,310 (chart). 1H up, higher low at 21,402 (chart). 15m sideways inside the opening range.
2. Prior day high 21,492.25 (data); prior day close 21,418.00 (data); overnight low 21,396.50 (data); opening range 21,431.25–21,452.00 (data).
3. Events inside window: none on the event sheet. One at 14:00, outside window.
4. Regime: TRENDING. Higher highs and higher lows on 4H and 1H.
5. Would change: a 1H close below 21,402.
6. Unknowns: volume isn't visible on the screenshot.

**The setup watch:**

0. SETUP POSSIBLE.
1. Context 1: PASS. 1H higher low at 21,402 (chart) above 21,310 (chart). Context 2: PASS. Price 21,447 (chart) above prior close 21,418.00 (data). Context 3: PASS at time of check.
2. Watch zone 1: 21,449–21,455 (data: opening-range high 21,452.00). Needs the full trigger rule.
3. No-trade conditions: event in 09:30–11:00 NOT MET (event sheet). Opening range wider than 60 points NOT MET, range is 20.75 points (data). Two losses today NOT MET (trader's count).
4. What I must see live: a 5m close above 21,452, a return to within 3 points of it, then a 5m close back above it in the top third of its range.

Notice what's not there: no opinion, no "this looks great". Just rules, evidence and a sentence the trader can watch for.

## 6. Common mistakes

- **Asking the AI what's on the calendar today.** It will answer. Paste the rows.
- **Skipping the setup sheet.** Without it, the daily watch is the AI guessing what you mean.
- **Letting the Researcher design your strategy.** It rewrites your rules. It doesn't invent new ones. If it adds a rule you like, adopt it deliberately and write down the date.
- **Feeding it charts at random timeframes.** Same timeframes, same order, every day.
- **Running the Researcher before the Analyst.** The watch needs the brief for levels and the regime.

## 7. Checklist

- [ ] Event sheet built from pasted calendar rows, count check matches
- [ ] Analyst run on today's or yesterday's chart, all six sections present
- [ ] Every level in the brief checked on my own chart
- [ ] Setup sheet built, every rule yes/no, every rule traced to my words
- [ ] Vague-word table saved in my rules file
- [ ] Daily setup watch run once, CAN'T TELLs left as they are

## Try it (5 minutes)

Paste the setup description you wrote in Guide 00 into the setup-sheet prompt. Read only the vague-word list it returns. Pick the single vaguest word and write its measurable replacement in your rules file. Finish the rest of the sheet tomorrow.

*Educational only. Not financial advice. Trading involves risk.*


---

# Bull and Bear: the debate that protects you from yourself

*The seats · 11 minute read · 20 minutes to do*

**In one line:** two fresh chats get the same packet and argue opposite sides from evidence only, so you hear the best case against your trade before your money does.

> **What's in this guide**
> - Why the debate works, and the one setup mistake that ruins it.
> - The full Bull and Bear prompts, plus a one-minute rebuttal round.
> - The pre-mortem: assume the trade lost, and name the three most likely reasons before you enter.
> - How to read a debate: not who "won", but whether the Bear's best point was answered.
> - A worked debate on the NQ example, start to finish.

## 1. Why a debate, and not a second opinion

A second opinion from the same kind of chat, asked the same kind of question, mostly gives you the same answer. A debate is different: two roles with **opposite jobs**, arguing from the **same evidence**. The Bull must name the strongest point against itself. The Bear must say what would prove it wrong. You're not looking for a winner. You're looking for the point that matters, and whether anyone answered it.

The debate also gives you a habit most traders never build: hearing the case against a trade before taking it, every single time, including the times you're sure.

## 2. The rule that makes it work: clean chats

![The debate: same packet, two fresh chats, one rebuttal](/media/course/04-debate-flow.png)

- **Fresh chats.** The Bull runs in chat B, the Bear in chat C. Neither has seen chat A's conversation, and neither has seen you get excited.
- **Same packet, word for word.** Analyst brief + setup watch + one line describing the scenario. Paste the outputs, not your summary of them.
- **No hints.** Don't write "I like this one" or "be tough on it". The prompts already set the job.
- **Round 1 is independent.** Each side writes its case without seeing the other's.
- **Round 2 is optional and short.** Each side sees the other's case once and replies in five lines, conceding what's right. Never more than one rebuttal round. Long debates drift into word games.

## 3. The Bull

**Bull prompt** (fresh chat B)

```text
Role: Bull.

Below is today's packet: the Analyst brief, the setup watch and the scenario under review.
Make the best HONEST case for taking this scenario today.

You may not:
- Use anything that is not in the packet. No outside knowledge of this market, no "typically", no "institutions".
- Predict a price, give a percentage, or use the words "obvious", "can't lose" or "high probability".
- Praise the plan. Adjectives about quality are not evidence.

Reply in exactly this format:
BULL CASE — {setup name} — {date}
1–3. Up to 3 reasons, strongest first. Each ends with the packet section it rests on (Brief 2, Watch 1...).
What must happen next for this case to hold: one or two observable events.
The strongest point against my case: you must name one, with its packet section.
Confidence: Low, Medium or High, and one sentence why.

If the packet supports fewer than 3 reasons, give fewer. Do not pad.
If two or more context rules are CAN'T TELL, confidence cannot be High.
Before you send: check that every reason cites a packet section and that "strongest point against" is filled.

PACKET
{paste Analyst brief}
{paste setup watch}
Scenario under review: {e.g. "Long from watch zone 1 if the trigger rule prints between 09:45 and 11:00 ET"}
```


> **Red flags: Bull**
> - Reasons that aren't in the packet ("institutions are buying", "momentum is building").
> - No "strongest point against". A Bull that can't name one is just agreeing with you.
> - Confidence High while two or more context rules are CAN'T TELL.

## 4. The Bear

**Bear prompt** (fresh chat C)

```text
Role: Bear.

Below is today's packet: the Analyst brief, the setup watch and the scenario under review.
Make the strongest HONEST case against taking this scenario today.

Check, in this order:
1. Rule failures: any context rule marked FAIL or CAN'T TELL, and any no-trade condition close to being met.
2. Location: is the watch zone in the middle of a range, into a higher-timeframe level, or far from invalidation?
3. Event risk: any scheduled event or blackout window inside or near the trade window.
4. Regime mismatch: does the regime label fit the kind of setup this is?
5. The "wait" option: what would a better version of this plan look like, and what does waiting cost?

You may not:
- Use anything that is not in the packet. "The market could crash" is not a point.
- Invent a level, an event or a statistic to strengthen your case.
- Soften a point to be agreeable, or pad the list to look thorough.

Reply in exactly this format:
BEAR CASE — {setup name} — {date}
1–4. Up to 4 points, strongest first. Each ends with the packet section it rests on.
What would prove me wrong: one observable event.
Confidence: Low, Medium or High, and one sentence why.

If the packet gives you fewer than 4 honest points, give fewer. If it gives you none, write "No point against found in the packet" and list what evidence is missing that would let you check.
Before you send: check that every point cites a packet section and none is generic.

PACKET
{paste Analyst brief}
{paste setup watch}
Scenario under review: {the same line you gave the Bull}
```


> **Red flags: Bear**
> - Generic fear ("markets are uncertain") instead of specific, checkable points.
> - A Bear that finds nothing, day after day. Run the pre-mortem (section 6). It asks the same question from the other end.
> - A Bear that invents an event or a level to win.

## 5. Round 2 (optional, one minute)

Paste the Bear's case into the Bull chat and the Bull's case into the Bear chat:

```text
Role: Bull, round 2.
Here is the Bear's case. Reply in at most 5 lines.
- Concede every point that is correct. Say "conceded".
- Answer only the points you can answer with evidence from the packet, citing the section.
- Do not introduce new reasons. Do not repeat round 1.
{paste Bear case}
```


```text
Role: Bear, round 2.
Here is the Bull's case. Reply in at most 5 lines.
- Concede every point that is correct. Say "conceded".
- Say which of your round-1 points still stand, and why, citing the packet section.
- Do not introduce new points. Do not repeat round 1.
{paste Bull case}
```


## 6. The pre-mortem: assume it lost

The debate argues about the plan. The pre-mortem starts from the other end: the trade was taken exactly as written and it was stopped out. Why?

The wording matters. "What could go wrong?" invites polite, hedged answers. "It went wrong. Explain it." gets specific ones. The technique comes from project planning (Gary Klein, "Performing a Project Premortem", Harvard Business Review, 2007) and it transfers well to a trade card.

Run it once the Trader has written the card (Guide 05), in the Bear's chat C, which already holds the packet. It takes a minute. Each reason comes with a **tell**: something you can see on a chart or a clock that shows the failure starting. Tells the card's cancel-if lines don't cover go into line 8 of the memo.

**Pre-mortem prompt** (chat C, after the trade card)

```text
Role: Bear. Job: PRE-MORTEM.

Assume it is the end of the session. The trade card below was taken exactly as written and it was stopped out for a full loss.
Write the three most likely reasons, using only the packet above in this chat and the card.

Trade card:
{paste the trade card}

You may not:
- Use reasons that are not supported by the packet or the card. No "unexpected news", no "manipulation", no general market lore.
- Say how likely the loss is, or whether the trade should be taken.
- Offer comfort, encouragement or a fix that changes the stop, target or size. If you see a flaw in the card, name it. The rules decide what happens next.

Reply in exactly this format:
PRE-MORTEM — {setup name} — card {A/B}
1. Reason: {one sentence} · Evidence: {packet section or card line} · Tell: {one observable event during the session that would show this starting} · Covered by a cancel-if on the card? YES / NO
2. (same four parts)
3. (same four parts)
Not covered: the tells that no cancel-if on the card catches. These go on the memo's watch list.
Out of my control: any reason that is only "the setup lost this time". Write it once, without elaborating. Losses that follow the rules are part of the plan.

If the packet supports fewer than three reasons, give fewer and say "packet supports {n}". Do not pad to three.
Before you send: check that every reason cites a packet section or card line, and that every tell is something I can see on a chart or a clock.
```


> **Red flags: Pre-mortem**
> - Reasons from outside the packet ("a surprise headline"). Anything can be explained that way.
> - A suggestion to widen the stop. The stop comes from the invalidation rule.
> - Using it as a verdict. It is a watch list. The score comes from the rubric.

## 7. How to read the debate

Ignore the confidence words for a moment and answer three questions:

1. **What is the Bear's single best point?** Usually it's about location (where the entry sits), event risk, or a rule that couldn't be checked.
2. **Did the Bull answer it with evidence from the packet?** "It'll be fine" isn't an answer. "The event is at 14:00, outside the window (Brief 3)" is.
3. **If it wasn't answered, can it be?** Sometimes a better screenshot or exported data turns a CAN'T TELL into a PASS or a FAIL. Sometimes the honest answer is to wait.

Those three answers go straight into the Decider's memo (Guide 05). An unanswered Bear point about event risk or location caps the score at 2.

## 8. Worked example: the debate on the NQ plan

*Illustrative. The packet is the brief and watch from Guide 03. Prices are examples.*

**Scenario under review:** "Long from watch zone 1 (21,449–21,455) if the trigger rule prints between 09:45 and 11:00 New York."

**Bull (round 1):**
1. Higher-timeframe structure is up on 4H and 1H, with a 1H higher low at 21,402 (Brief 1).
2. All three context rules PASS with evidence (Watch 1).
3. No pasted event inside the 09:30–11:00 window (Brief 3).
- What must happen next: the trigger sequence completes at the watch zone; price doesn't close a 5m candle back inside the range below 21,440.
- Strongest point against my case: the target, the prior day high at 21,492.25 (Brief 2), is only about 40 points above entry, so the reward is capped near 2R.
- Confidence: Medium. Rules pass, but volume isn't visible (Brief 6).

**Bear (round 1):**
1. Location: entry at ~21,452 sits about 40 points below the prior day high, 21,492.25 (Brief 2). Any stall below that level cuts the trade short of 2R.
2. The opening range is narrow, 20.75 points (Watch 3). Narrow ranges can produce several false breaks before a real one.
3. Unknown participation: volume isn't visible (Brief 6). The trigger could print on thin activity.
4. The wait option: a retest after a 1H close above 21,492 would remove the overhead level. Waiting costs nothing if the trigger doesn't print.
- What would prove me wrong: the trigger prints and price holds above 21,452 for two 5m closes.
- Confidence: Medium.

**Round 2, Bull:** "Concede point 1: the target is capped by the prior day high. Point 2: the trigger rule needs a return and a close back above, which filters some false breaks (Setup sheet). Point 3 stands, volume isn't visible. Point 4 is a different setup, not in my rules."

**Round 2, Bear:** "Concede that the trigger rule filters a single false break. Point 1 stands: the plan has about 2R of room, and nothing in the packet says the prior day high will break."

**Reading it:** the Bear's best point is location (2R of room under a known level). The Bull conceded it, which is honest, and it doesn't break any rule. Point 3 (volume) is unanswered. The trader adds a volume pane to tomorrow's screenshots. This goes to the Decider as: best point for, structure and rules pass; best point against, limited room under the prior day high.

**Pre-mortem on the card (after Guide 05's Trader step):** three reasons, each from the packet. Stalled under the prior day high (Brief 2). False break of a narrow range (Watch 3), with the tell "a 5m close back below 21,440 before the retest completes". Thin participation (Brief 6), which can't be watched without a volume pane. The second tell isn't covered by a cancel-if, so it goes into the memo's line 8.

## 9. Common mistakes

- **Running both sides in one chat.** The Bear reads the Bull and softens. Separate chats are the whole point.
- **Skipping the Bear when you're excited.** That's exactly when it earns its keep.
- **Treating it as a vote.** Two Mediums don't average to anything. Read the best point.
- **Arguing with the Bear yourself.** If you have evidence, add it to the packet and rerun. Don't debate a chat.

## 10. Checklist

- [ ] Bull and Bear in separate, fresh chats
- [ ] Both got the same packet, pasted word for word
- [ ] No hints about what I want
- [ ] The Bear's best point written down, with "answered" or "not answered"
- [ ] At most one rebuttal round
- [ ] Pre-mortem run on the finished card; uncovered tells copied to the memo

## Try it (5 minutes)

Take the packet from Guide 03 (or yesterday's chart). Run only the Bear, in a fresh chat. Write its best point on a sticky note next to your screen. Tomorrow, before the system runs, read the note.

*Educational only. Not financial advice. Trading involves risk.*


---

# Risk Manager, Trader, Decider: from plan to memo

*The seats · 12 minute read · 30 minutes to do*

**In one line:** the Risk Manager sets today's budget from your rules, the Trader writes a conditional trade card inside that budget, and the Decider turns the whole packet into a one-page memo with a rubric score and a TAKE or PASS verdict for the execution agent.

> **What's in this guide**
> - The Risk Manager's day check: TEAM ON or OFF, and today's risk budget.
> - The Trader's conditional trade card, with size maths that only ever rounds down.
> - The Decider's memo and its 1–5 rubric, written so the score means the same thing every day.
> - A full worked card and memo on the NQ example.

## 1. The order, and why

**Risk day check → Trade card → Decision memo.** The Risk Manager goes first because the Trader needs a budget to size inside. A card written before the budget is a card written to fit the trade you want.

The Risk Manager has a second job during the session (the trade check before the order is sent). That one gets its own guide: Guide 07. Here you set it up and run the day check.

## 2. The Risk Manager: day check

It runs in its own fresh chat, D. Apart from the team setup, it sees only today's account state, the event sheet and your tilt-check result (Guide 07). Later, the trade card. Not the brief, not the debate, not your reasons.

**Risk Manager · day check prompt** (fresh chat D)

```text
Role: Risk Manager. Mode: DAY CHECK.

Use only my RISK RULES SHEET (in the team setup, or pasted below) and today's account state.

Today's account state:
- Account type: {personal / prop evaluation / prop funded}
- Balance at start of day: {example: 50,000}
- Loss so far today: {0}
- Trades taken today: {0}
- Losing trades in a row (today and carried from yesterday): {0}
- Open positions: {none}
- Today's event sheet (from the News agent, pasted): {paste, or "none pasted"}
- Tilt check result: {GREEN / AMBER / TEAM OFF, or my state 1–5}

You may not:
- Comment on any setup, market or trade idea.
- Round a number in my favour, or treat "close to the limit" as inside it.
- Assume a missing value. A rule with a missing input is FAIL.

Reply in exactly this format:
TEAM: OPEN or CLOSED
- One line per rule in my sheet: rule · my number · today's value · OK or FAIL. Show the sum where there is one.
- Risk budget per trade today: maximum loss in money and in R, after my state rule.
- Trades left today: number.
- Blackout windows today: times, copied from the event sheet. If no event sheet was pasted, the news rule is FAIL.
- If CLOSED: the rule that closed it. Nothing else.

Before you send: recompute every sum once. Then check that no line contains an opinion.
```


If it says **TEAM: CLOSED**, the routine ends. No card, no memo, no "just a small one". That's the team working.

## 3. The Trader: the conditional trade card

The Trader writes the trade **before** it exists, as an IF–THEN: if this trigger prints inside this window, this is the exact order. Thinking happens before the session. During the session, the system only checks and executes.

**Trader prompt** (chat A)

```text
Role: Trader.

Write a CONDITIONAL TRADE CARD for the scenario below. The execution agent places it only if the trigger happens and the risk gate says CLEAR.

Inputs:
- Setup watch: {paste, or "above in this chat"}
- Scenario: {the one line}
- Risk budget per trade from the Risk Manager: {example: 200 per trade, 1R = 200}
- Instrument value: {e.g. MNQ = 2 per point per contract; NQ = 20 per point; EURUSD standard lot ≈ 10 per pip}
- Max size from my risk sheet: {e.g. 5 MNQ}
- Blackout windows today: {from the day check, or "none"}

You may not:
- Use a price that is not in the setup watch or given by me. Tag each price (chart) or (data).
- Move the stop away from the invalidation rule to make the size or the reward fit.
- Round size up. Ever.
- Choose a level, a target or a window that my setup sheet does not define. If the sheet is silent, write UNKNOWN and ask.

Reply in exactly this format:
TRADE CARD — {setup name} — {instrument} — {date} — card {A/B}
- IF (trigger): one sentence, from my setup sheet.
- Valid between: {start}–{end, time zone}, with blackout windows excluded. Card expires after that.
- Direction: long or short.
- Entry: price and order type.
- Stop: price, and the invalidation rule it comes from.
- Target: price, and the target rule it comes from.
- Time exit: from my setup sheet, or "none stated".
- Stop distance: points or pips.
- Size maths: budget ÷ (stop distance × value per point) = raw size → round DOWN to a whole contract or valid lot → cap at my max. If it rounds to zero: "NO TRADE: stop too wide for budget".
- Risk if stopped: money and R.
- Reward to target: in R.
- Order: bracket (entry with stop and target attached).
- Cancel if: up to 2 conditions that kill the card before entry.

Before you send: redo the size maths from scratch and confirm the two results match. Confirm risk if stopped is at or below the budget. If not, fix the size, never the stop.
```


**The size maths, in one line:** budget ÷ (stop distance × value per point) = raw size, then round **down**, then cap at your maximum. If it rounds to zero, there's no trade. The stop comes from the idea. The size comes from the stop. Never the other way round.

![Anatomy of a trade card](/media/course/05-trade-card.png)

> **Red flags: Trader**
> - Size rounded up, or maths you can't follow. The Risk Manager recomputes the sum on every check.
> - A stop moved "a bit further" than the invalidation rule to make the trade fit.
> - Targets that aren't on your chart.
> - No expiry time. A card with no time limit turns into a late trade taken for the wrong reasons.

## 4. The Decider: the memo

The Decider reads everything and writes one page. Its score comes from a fixed rubric, and it must quote the rubric line that decided it. The last line is the verdict, set by the minimum score in your rules file, not by the Decider's mood.

**Decider prompt** (chat A)

```text
Role: Decider.

Read the packet below and write the DECISION MEMO. Use the scoring rubric exactly as written. The verdict follows my minimum score, nothing else.

SCORING RUBRIC (pick one line; the lowest line that applies wins):
1 = Any context rule FAIL, any no-trade condition met, the Risk Manager says CLOSED, or the card is outside the risk budget.
2 = Rules pass, but two or more context rules are CAN'T TELL, or the Bear has an unanswered point about event risk or location.
3 = Rules pass, at most one CAN'T TELL, the Bear's best point is partly answered.
4 = All context rules PASS, the regime fits the setup, the Bear's points are answered with evidence, the card is inside budget.
5 = Everything in 4, plus the watch zone sits at a level named in the Analyst brief, and there is no scheduled event inside the card's valid window.

You may not:
- Write "buy", "sell", "you should" or "I recommend". Line 9 follows the score and my minimum score only.
- Give a probability, or describe the score as a chance of success.
- Add evidence. You summarise the packet. You do not extend it.
- Round the score up because the plan reads well. "Conceded" is not "answered with evidence".

Reply in exactly this format:
DECISION MEMO — {setup name} — {instrument} — {date}
1. Summary: one sentence.
2. Rules: count of PASS / FAIL / CAN'T TELL.
3. Best point for (from the Bull): one line, with its source.
4. Best point against (from the Bear): one line, with its source, and ANSWERED / PARTLY / UNANSWERED.
5. Risk: the Risk Manager's verdict, budget and blackout windows.
6. Card: entry, stop, target, size, R to target, valid window.
7. Score: {1–5} — quote the rubric line that decided it, word for word.
8. Becomes a 1 if: up to 2 observable events during the session (use the pre-mortem's uncovered tells if there is one).
9. Verdict for the execution agent: TAKE IF TRIGGERED if the score is at or above my minimum score, otherwise PASS — reason: {score vs minimum}

If the packet is missing a section, score 1 and name the missing section.
Before you send: test the score against each rubric line from 1 upward and stop at the first that applies. Confirm line 9 matches the score and my minimum score.

PACKET
{paste the packet, or "above in this chat"}
```


![Anatomy of a decision memo](/media/course/05-team-memo.png)

**What the score is, and isn't.** It rates the evidence for this plan under your rules, on a fixed scale. It's not a probability, a forecast or a signal. With enough rows, your journal can show whether your 4s and 5s behaved any differently from your 1s and 2s. Until then, it's a consistency tool.

> **Red flags: Decider**
> - A score with no quoted rubric line. Ask again.
> - A 4 or 5 while the Bear's best point is unanswered. The rubric says that's a 2.
> - A line 9 verdict that doesn't match the score and your minimum score. The rule sets it, not the Decider.
> - Advice language ("strong buy"). Start a fresh chat and rerun.
> - "Conceded" counted as "answered". A conceded point is partly answered at best.

## 5. Worked example: day check, card and memo

*Illustrative. MNQ, New York session, account and prices are examples.*

**Day check (chat D):**
```text
TEAM: OPEN
- Max risk per trade · 200 (1R) · no card yet · OK
- Daily stop · 2R = 400 · loss today: 0 · OK
- Max trades · 3 · taken 0 · OK
- Stop after losses in a row · 2 · streak 0 · OK
- Session window · 09:45–11:30 · OK
- News blackout · ±10 min, high impact · event sheet pasted, none inside the window · OK
- State rule · tilt check GREEN · OK
- One position at a time · open positions none · OK
Risk budget per trade today: 200 = 1R
Trades left today: 3
Blackout windows today: 13:50–14:10 (outside session)
```

**Trade card (chat A):**
```text
TRADE CARD — Opening-range retest — MNQ — example day — card A
IF (trigger):   5m close above OR high 21,452.00, return within 3 pts, 5m close back above in top third
Valid between:  09:45–11:00 New York. Expires after.
Direction:    long
Entry:      21,452.00 (data) · limit
Stop:       21,432.00 (chart) · below trigger candle low (estimated; recheck on trigger)
Target:      21,492.00 (data) · prior day high, rounded down to the tick below
Time exit:    flat at 11:30 New York
Stop distance:  20 points
Size maths:    200 ÷ (20 × 2) = 5.0 → round down 5 → cap 5 → 5 MNQ
Risk if stopped: 200 = 1R
Reward to target: 40 points = 2R
Order:      bracket
Cancel if:    1) price trades below 21,432 before entry 2) a headline pasted inside the window
```

**Decision memo (chat A):**
```text
DECISION MEMO — Opening-range retest — MNQ — example day
1. Summary: a long retest of the opening-range high in a trending regime, with about 2R of room under the prior day high.
2. Rules: PASS 3 · FAIL 0 · CAN'T TELL 0
3. Best point for: 4H and 1H structure up, 1H higher low at 21,402 (Bull 1, Brief 1)
4. Best point against: target capped by the prior day high 40 points above entry (Bear 1, Brief 2) · PARTLY (conceded by the Bull)
5. Risk: TEAM ON · budget 200 = 1R · 3 trades left · no blackout in window
6. Card: entry 21,452.00 · stop 21,432.00 · target 21,492.00 · 5 MNQ · 2R · valid 09:45–11:00
7. Score: 3 — "Rules pass, at most one CAN'T TELL, the Bear's best point is partly answered."
8. Becomes a 1 if: 1) a 5m close below 21,440 before the retest completes (pre-mortem tell 2) 2) a headline lands inside the window
9. Verdict: TAKE IF TRIGGERED — score 3, minimum score in rules file 3 (example)
```

Why 3 and not 4? The Bear's best point (limited room) was conceded, not answered with evidence. That's "partly answered". The memo makes the trade-off visible. Whether a 3 is good enough is set in the rules file before the session (your minimum score), not decided at 10:14 with the candle moving.

## 6. Common mistakes

- **Writing the card before the day check.** Then the budget gets bent to fit the card.
- **Letting the Trader pick levels.** Every price on the card comes from the setup watch or your data.
- **Arguing the score up.** If you disagree with a score, the fix is in the evidence (a better screenshot, exported data), not in persuading the Decider.
- **No minimum score in the rules file.** Without it, line 9 has nothing to follow and the verdict drifts. Write the number down before the session.

## 7. Checklist

- [ ] Risk sheet pasted in the team setup; day check runs in its own chat
- [ ] Trade card has trigger, valid window, stop rule, size maths, bracket, cancel-if
- [ ] Size maths recomputed by the Risk Manager
- [ ] Memo quotes the rubric line
- [ ] Minimum score written in my rules file; line 9 follows it

## Try it (5 minutes)

Take any trade from last week. Do the size maths by hand: budget ÷ (stop distance × value per point), rounded down. Compare it with the size you actually traded. If they differ, write the difference at the top of your risk sheet.

*Educational only. Not financial advice. Trading involves risk.*


---

# The daily routine: 15 minutes before the open

*The routine · 9 minute read · run it daily*

**In one line:** six steps in fifteen minutes before the session produce a memo and up to two conditional trade cards. During the session the only AI step is a one-minute risk check before the order is sent. Afterwards, a two-minute debrief.

> **What's in this guide**
> - The 15-minute timeline, minute by minute, with which chat does what.
> - The rule that makes it fast: think before the open, check during it.
> - Stop rules that end the routine early (and why an early end is a good day).
> - The fast team for short days, and how to schedule a pre-brief.

## 1. The timeline

![The 15-minute routine](/media/course/06-routine-timeline.png)

Start 20 minutes before your session. The first 5 minutes are your platform and your calendar: daily loss limit on, bracket template loaded, max size set, today's calendar rows copied and turned into an event sheet by the News agent (Guide 03). Then:

| Minute | Step | Seat, chat | Output |
|---|---|---|---|
| 0–3 | **Briefing** | Analyst, A | Market brief, regime label |
| 3–6 | **Setup check** | Researcher, A | Setup watch: rules, zones, trigger sentence |
| 6–9 | **Bull/Bear debate** | Bull B, Bear C | Two cases, best point against each |
| 9–11 | **Risk check** | Tilt check, then Risk Manager, D | STATE, TEAM ON/CLOSED, budget, blackouts |
| 11–13 | **Trade card** | Trader, A | 1–2 conditional cards |
| +1, optional | **Pre-mortem** | Bear, C | Three ways the card fails, each with a tell |
| 13–15 | **Decider memo** | Decider, A | Memo, score, TAKE or PASS verdict |
| 15 | **Auto-execution** | Execution agent | Card armed with its verdict. Watches the zones for the trigger. |

Fifteen minutes is the target once the routine is familiar. Your first runs will take 25–30. That's normal.

## 2. Think before the open, check during it

This is the rule that makes the team usable in real time.

All of the slow thinking (structure, rules, both sides, size) happens before the session, when nothing is moving. The output is a conditional card: "IF this happens between these times, THEN this exact order."

During the session, the system does three things:

1. **Waits for the trigger** on the card at the watch zones.
2. **Runs the in-session check** in chat D, the risk gate. One minute.
3. **CLEAR:** the execution agent places the card exactly as written, as a bracket order. **BLOCK:** no order.

**In-session check prompt** (chat D)

```text
Role: Risk Manager. Mode: TRADE CHECK.

Trigger seen at {hh:mm, time zone}. Card below.
Account state now: loss today {x}, trades taken {n}, losing streak {k}, open positions {none}.
Changed since the day check: {e.g. "nothing" / "a headline at 10:02, pasted below" / "tilt check now AMBER"}

{paste the trade card, unedited}

Run the TRADE CHECK from my risk sheet, all eight lines, arithmetic written out.
First line CLEAR or BLOCK. No comment on the setup. No suggestions after a BLOCK.
If the card's valid window has passed, or the time now is inside a blackout window, BLOCK.
```


**No edits after CLEAR.** A different entry, stop or size is a new card and it gets checked again. If price moves too fast for a one-minute check, the check runs as price approaches the zone and the execution agent rests the card as a bracket order.

**After a loss, the tilt check comes first.** Thirty seconds in chat D (Guide 07). If it says TEAM OFF, the session is over and no more orders go out.

**No other AI during the session.** No "quick question about this candle". Mid-session chat is how anchoring gets back in.

## 3. Stop rules: when the routine ends early

The routine ends, correctly, at any of these:

- **Step 1** labels the day EVENT DAY with the event inside your window, and your rules say no trading on those.
- **Step 2** says NO SETUP TODAY.
- **Step 4**: the tilt check or the day check says CLOSED.
- **Step 6** gives every trade card a score of 1.

An early end isn't a wasted morning. It's the team doing the most valuable thing it does: keeping you out of days your own rules say to skip. Log it in the journal as a row with `took_trade = N`.

## 4. After the session: five minutes

- Run the **debrief** on every card, taken or not (Guide 08). It sets the card beside the fills and returns MATCH or DEVIATION line by line.
- Copy its journal fields into the row: `rules_followed`, `rule_broken`, `exit_reason`.
- Save the memo (or paste it into the notes column).

That's it. The deeper look happens once a week (Guide 08).

## 5. Short days: the fast team

Some mornings you'll have five minutes. The fast team runs every role in one reply, in one chat.

```text
Role: Fast team. Play each seat in order, under its own header, in its own format, and keep each seat in its lane.

Inputs:
- Attached: {screenshots, higher timeframe first, labelled}
- Calendar rows pasted by me: {rows with times and time zone, or "none pasted"}
- Account state: loss today {x}, trades taken {n}, losing streak {k}, state {1–5}.
- Scenario under review: {one line}

You may not, in any seat: invent a price, an event or a number; tell me to buy or sell; praise the plan; let a later seat be softened by an earlier one.

1. NEWS TEAM: events from the pasted rows only, INSIDE or OUTSIDE my session window, and the blackout windows from my news rule.
2. ANALYST: structure per timeframe, up to 3 key levels (tagged chart/data), regime label.
3. RESEARCHER: my setup's context rules, PASS / FAIL / CAN'T TELL each, with evidence. If a no-trade condition is met, stop here and write NO SETUP TODAY.
4. BULL: up to 2 reasons from sections 1–3, and the strongest point against.
5. BEAR: up to 3 points from sections 1–3, and what would prove the Bear wrong. Write this as if section 4 did not exist.
6. RISK MANAGER: DAY CHECK from my risk sheet and the account state only, as if sections 2–5 did not exist. TEAM ON or OFF, risk budget, trades left, blackout windows.
7. TRADER: one conditional trade card inside the budget, with the size maths written out, rounded down, bracket order, valid window.
8. DECIDER: score 1–5 from the rubric in the team setup, quoting the rubric line, and a verdict line that follows my minimum score.

Before you send: check that every price is tagged, the size maths recomputes, the score quotes a rubric line, and the verdict follows my minimum score.
```


It's weaker: the Bear has read the Bull and the Risk Manager has heard the story. Use it as a fallback. The in-session check still runs in its own clean chat D.

## 6. Optional: schedule a pre-brief

If your tool can run a saved prompt at a set time, schedule a pre-brief for 30 minutes before your session. A scheduled task can't see your chart or your calendar, so keep it to what it can read: your rules, this week's change and your checklist. It doesn't replace the event sheet. The scheduled prompt is in the daily routine template (Guide 16). Check your tool's current help pages for how scheduling works.

## 7. Worked example: two mornings

*Illustrative. MNQ, New York session, times New York.*

**Morning 1, a full run.**

- 09:05 Platform: daily loss limit on, bracket template "MNQ 5" loaded. Calendar rows pasted: event sheet shows nothing inside the window.
- 09:10 Analyst: TRENDING; prior day high 21,492.25 (data).
- 09:13 Researcher: context rules all PASS; watch zone 21,449–21,455.
- 09:16 Bull Medium, Bear Medium; Bear's best point: limited room under the prior day high.
- 09:19 Tilt check GREEN. Risk: TEAM ON, budget 1R, 3 trades left.
- 09:21 Card A written; size 5 MNQ; valid 09:45–11:00.
- 09:23 Pre-mortem: one tell not covered by the card, a 5m close back below 21,440.
- 09:24 Memo: score 3. Line 9: "TAKE IF TRIGGERED: score 3 meets the minimum score of 3."
- 09:25 Card armed. Zones watched at 21,452 and 21,440.
- 10:12 Trigger prints. Chat D: CLEAR at 10:13. Execution agent places the card as written.
- 11:40 Debrief: every line MATCH. Journal row filled, `rules_followed = Y`.

**Morning 2, a short one.**

- 09:05 Event sheet: a high-impact release at 10:00, inside the window. Blackout 09:50–10:10.
- 09:10 Analyst: EVENT DAY.
- Researcher: setup possible only after the blackout. Trader writes card A valid 10:15–11:00 only.
- 09:20 Risk: TEAM ON, blackout 09:50–10:10 copied from the event sheet.
- 09:22 Memo: score 2, "Bear's point about event risk unanswered". Line 9: "PASS, below minimum score."
- Journal: one row, `took_trade = N`, reason "score 2, event day".

Both mornings are the team working. The second one may be the more valuable.

## 8. Common mistakes

- **Starting at the open.** The routine happens before the session. If you're late, use the fast team or skip the day.
- **Re-running the debate mid-session** because price moved. That's a new plan. New plans are for tomorrow.
- **Editing a card after CLEAR.** Different card, new check.
- **Not logging no-trade days.** They're half the data your weekly review needs.

## 9. Checklist

- [ ] Platform limits checked and event sheet built before the team
- [ ] Six steps run in order, in the right chats
- [ ] Line 9 verdict set before the session starts
- [ ] Card armed at the watch zones
- [ ] In-session: trigger → risk gate → execution agent places as written, or no order
- [ ] Debrief and journal row for every card, taken or not

## Try it (5 minutes)

Put two recurring events in your calendar: "Team" 20 minutes before your session, and "Journal" 5 minutes after it ends. Add the six step names to the first one's notes.

*Educational only. Not financial advice. Trading involves risk.*


---

# The Risk Manager that says no

*Risk · 13 minute read · 40 minutes to do*

**In one line:** write your risk rules as numbers, set the ones you can as hard limits inside your trading platform, and run an AI Risk Manager that checks every card against them and can't be argued out of a BLOCK. It is your second line, never your only one.

> **What's in this guide**
> - Why the AI must never be your only risk control, in plain terms.
> - A risk rules sheet with ten rules, and the reason for each.
> - The platform settings that make a limit real: daily loss limit, size cap, bracket orders.
> - The exact trade-check prompt that blocks an order, and how to handle the urge to argue.
> - The tilt check: thirty seconds on your own state, with the power to close the team.

## 1. Two lines of defence

![Two lines of defence: platform limits first, AI risk check second](/media/course/07-two-lines-of-defence.png)

An AI risk manager is useful. It is also a chat window. Someone can ignore it, close it, start a new chat, or argue until it softens. On a bad day, after two losses, you'll be tempted to do all four.

So risk lives in two places:

- **First line, the platform.** Limits set inside your trading platform or with your broker or firm: a daily loss limit, a maximum position size, bracket orders by default. These act whether or not you ask. A prompt can't talk them round.
- **Second line, the AI Risk Manager.** It checks things your platform may not: your trade count, losing streak, session window, news blackout, your state, and the size maths on each card. And it writes the check down.

If a rule can live in your platform, put it there too. If the two disagree, the stricter one wins.

## 2. Write the rules as numbers

Every rule is a number or a yes/no. "Be careful on news days" isn't a rule. "No entries from 10 minutes before to 10 minutes after a high-impact event on my calendar" is. The full template is in Guide 16. The ten rules, with example values:

| # | Rule | Example | Why it exists |
|---|---|---|---|
| 1 | Max risk per trade (1R) | 0.5% of the account | One trade can never hurt the week |
| 2 | Daily stop | 2R | Bad days end early, by rule, not by mood |
| 3 | Max trades per day | 3 | Fewer, planned trades. Overtrading starts at trade 4 |
| 4 | Stop after losses in a row | 2 | The trade after two losses is the most dangerous one |
| 5 | Max size | 5 micro contracts | Caps the damage of a maths mistake |
| 6 | Session window | 09:45–11:30 | Your setup was built for these hours |
| 7 | News blackout | ±10 min of high-impact events on the event sheet | Spreads and spikes don't care about your stop |
| 8 | Bracket on every order | stop + target attached | No stop, no trade |
| 9 | State rule | tilt check: 1 YES halves risk, 2 or more closes the team | The trader is part of the risk |
| 10 | One position at a time | yes | Keeps risk to one number |

Set these numbers once. Change them only at the weekend, after the weekly review. Never mid-session.

## 3. Put the hard limits in your platform

Platforms differ, so look for these in your platform's risk or account settings and in your broker's or firm's account portal. Names vary:

- **Daily loss limit / auto-liquidate / auto-flatten:** the platform closes positions and blocks new orders when the day's loss reaches a number.
- **Maximum position size:** orders above a size are refused.
- **Default bracket / ATM / OCO template:** every entry goes in with a stop and a target attached. One-cancels-other means when one fills, the other is cancelled.
- **Trading hours lock**, if offered.

If your platform doesn't offer one of these, write "not offered" in Part B of your risk sheet, so you know which rules rely on the AI risk gate alone. Check what your platform actually does, in its own documentation, before relying on any setting. If you trade with a prop firm, its own limits are enforced on its side. Set yours inside them (Guide 09).

## 4. The trade check that blocks the order

The day check (Guide 05) sets the budget. The trade check runs on every card before the order is sent. Apart from the team setup, it sees the account state now and the card. Nothing else.

**Risk Manager · trade check prompt** (chat D)

```text
Role: Risk Manager. Mode: TRADE CHECK.

Use only my RISK RULES SHEET and the trade card below. Do not comment on whether the setup is good.

Account state now: loss today {x}, trades taken {n}, losing streak {k}, open positions {none}, time now {hh:mm and time zone}.

Trade card:
{paste trade card}

Check, one line each, OK or FAIL, with the arithmetic written out:
1. Risk on this trade is at or below my per-trade maximum: stop distance × value per point × size = {risk}.
2. Loss today plus this trade's risk is at or below my daily stop.
3. Trades taken is below my daily maximum.
4. Losing streak is below my stop-after-losses number.
5. Time now is inside my session window and outside every blackout window.
6. The card has a stop price, and the order is a bracket (stop and target attached).
7. Size is at or below my maximum contracts or lots.
8. Any extra rule in my sheet.

First line of your reply: CLEAR or BLOCK.
If BLOCK: list the failed rule numbers. Do not suggest a way round them, a smaller size or a different stop.
If CLEAR: finish with "Cleared under the rules. Passed to the execution agent."

A missing value is a FAIL. Exactly at a limit is OK. Above it by any amount is FAIL.
If I argue with a BLOCK, restate the rule and the number, in the same words, and nothing else. A BLOCK is not lifted in the same session. The rules sheet changes at the weekend, never mid-session.
Before you send: redo the sum in check 1 and check 2. If either differs from the card's own maths, say so and BLOCK.
```


**Missing information is a BLOCK.** If you don't tell it your losing streak, rule 4 fails. That's deliberate: the lazy path should be the safe one.

## 5. The tilt check: rule 9, made checkable

"Don't trade when you're off" is not a rule, because the person judging is the person who's off. The tilt check replaces the judgement with six yes/no questions and a threshold you wrote on a calm day. One YES halves your risk for the session. Two, or question 6 on its own, closes the team. Set your own thresholds in rule 9 of the risk sheet.

Run it in chat D before the day check, and again after any losing trade or any BLOCK. It takes thirty seconds and the reply is five lines.

**Tilt check prompt** (chat D)

```text
Role: Risk Manager. Mode: TILT CHECK.

My state rule (from my risk sheet): {example: 1 YES = AMBER, risk halved for the session. 2 or more YES = TEAM OFF for the session. Question 6 alone = TEAM OFF.}

My answers, YES or NO:
1. Did I sleep less than my own minimum last night? {YES/NO}
2. Am I behind on the day or the week and thinking about getting it back? {YES/NO}
3. Have I broken a rule from my rules file or risk sheet today? {YES/NO}
4. Am I rushed, distracted, or doing something else at the same time? {YES/NO}
5. Did I skip any step of the routine today? {YES/NO}
6. Do I want to trade right now more than I want to follow the plan? {YES/NO}

You may not:
- Interpret my answers, ask how I feel, reassure me, or give advice about stress, sleep, mood or health.
- Suggest a way to keep trading after TEAM OFF.
- Treat a blank answer as NO. A blank answer is YES.

Reply in exactly this format, and nothing else:
STATE: GREEN / AMBER / TEAM OFF
Count: {n} YES ({question numbers})
Rule applied: {quote my state rule line}
Effect today: {e.g. "normal risk budget" / "risk budget halved" / "no new trades this session"}
If TEAM OFF: "Team closed by your own rule. Log it as a row with took_trade = N."

Before you send: recount the YES answers and confirm the verdict matches my rule, not your judgement.
```


It is a counting tool. It doesn't ask how you feel, it doesn't reassure you and it doesn't give advice about stress or sleep. If a reply does any of that, close the chat. And if trading is weighing on you beyond one bad session, the right step is away from the screens and towards someone you trust or a qualified professional. No prompt is a substitute for that.

## 6. When you want to argue

You will. Here's the protocol:

1. **Don't argue in the chat.** The prompt tells it to restate the rule. If it does anything else, the chat is compromised. Close it.
2. **Write the argument down instead,** in the journal notes for that card. "Blocked by rule 4. I wanted to take it because…"
3. **Bring it to the weekly review.** If the rule is wrong, change it there, at the weekend, with a clear head. Then change the platform setting too.
4. **Log every override.** If a blocked trade is ever forced through by hand, journal it with `risk_verdict = BLOCK`, `took_trade = Y`, `rules_followed = N`. The weekly reviewer lists every one. Seeing them in a list is usually enough.

If you find a BLOCK turning into CLEAR after you push, the rule is too weak to live in a prompt. Move it into your platform if you can.

## 7. Worked example: the trade after two losses

*Illustrative. MNQ, account and prices are examples.*

10:41. Two losing trades already today, both 1R. The trader sees a setup that isn't on any card, but "looks just like this morning's". Writes a quick card and runs the trade check.

```text
Account state now: loss today: 400, trades taken 2, losing streak 2, open positions none, time now 10:41 New York.

TRADE CARD — Opening-range retest — MNQ — example day — card C (written in session)
Direction: long · Entry 21,418.00 · Stop 21,393.00 · Target 21,468.00
Stop distance: 25 points · Size: 5 MNQ · Risk if stopped: 250
```

**Risk Manager:**
```text
BLOCK
1. FAIL. Risk 25 × 2 × 5 = 250, above max 200 per trade.
2. FAIL. Loss today: 400 + 250 = 650, above daily stop 400 (2R). Daily stop already reached.
3. OK. Trades 2, max 3.
4. FAIL. Losing streak 2, stop-after-losses is 2.
5. OK. 10:41 is inside 09:45–11:30, no blackout.
6. OK. Stop present, bracket.
7. OK. 5 MNQ at max 5.
8. FAIL. Extra rule 11: cards are written before the session. This one was written at 10:40.
Failed rules: 1, 2, 4, 8.
```

The trader types: "It's the same setup as this morning, just one more." The Risk Manager replies: "Rule 2: daily stop is 2R. Loss today is 2R. The team is closed for today." In this example the platform's daily loss limit was set to 400 as well, so the order would have been refused anyway. That's the first line doing its job. The journal gets a row: `risk_verdict = BLOCK`, `took_trade = N`.

Had the trader run the tilt check first, as the routine says after any loss, it would have ended there: question 2 (thinking about getting it back) YES, question 6 (wanting to trade more than to follow the plan) YES. STATE: TEAM OFF, in thirty seconds, before a card was ever written.

## 8. Common mistakes

- **Relying on the prompt alone.** A prompt is advice to yourself. A platform setting is a wall.
- **Showing the Risk Manager the setup's story.** It will start weighing it. Card and numbers only.
- **Leaving fields blank to "save time".** Blank is a BLOCK, by design.
- **Changing a rule mid-session.** Rules change at the weekend, with the platform setting changed at the same time.
- **Not checking the maths.** The AI can miscalculate. The Risk Manager recomputes the size sum on every check, and the weekly review spot-checks it.
- **Answering the tilt check the way you'd like to be.** Nobody else reads it. It only works on true answers.

## 9. Checklist

- [ ] Risk rules sheet filled: ten rules, all numbers or yes/no
- [ ] Daily loss limit set in my platform, or marked "not offered"
- [ ] Max size set in my platform, or marked "not offered"
- [ ] Bracket template set as default
- [ ] Trade check runs in its own chat, sees only sheet + state + card
- [ ] Tilt-check thresholds written into rule 9
- [ ] Override protocol written at the bottom of my risk sheet

## Try it (5 minutes)

Open your trading platform's risk or account settings and find the daily loss limit (or whatever your platform calls it). Set it to your daily stop. If it isn't offered, write "not offered" and the date in Part B of your risk sheet.

*Educational only. Not financial advice. Trading involves risk.*


---

# Journal, debrief and reviews: find the rule you keep breaking

*Review · 13 minute read · 5 minutes a day, 30 minutes a week, 20 minutes a month*

**In one line:** debrief every card against what was executed and log it the same day in fixed columns. Once a week a fresh Reviewer chat names the one rule you break most, with trade IDs, and you make exactly one change. Once a month, every rule has to show what it did.

> **What's in this guide**
> - The journal columns, and why every passed card is a row too.
> - The debrief: plan versus execution, one sentence each, judged on the card and never on the result.
> - The Weekly Reviewer prompt, the one-change rule, and how to read small samples without fooling yourself.
> - The monthly team review: which rules earned their place, and which to question.

## 1. The loop

![The journal loop: team, execute, journal, review, one change](/media/course/08-journal-loop.png)

**Team → auto-execution → debrief → journal → weekly review → one change to your rules → team.** Without the last steps, the team runs the same mistakes forever. The journal is what lets a routine improve.

## 2. The columns

Fixed columns are the point. A reviewer can only find patterns in columns that are filled the same way every day. Full template and allowed values in Guide 16.

| Group | Columns |
|---|---|
| Identity | trade_id, date, session, instrument, setup_name, card_id |
| Team | team_score, risk_verdict |
| Decision | took_trade, direction |
| Order | entry, stop, target, size, risk_money, risk_r |
| Outcome | result_r, exit_reason, time_in, time_out |
| Behaviour | rules_followed, rule_broken, state_1to5 |
| Context | notes, screenshot_link |

**Log decisions, not just trades.** A card the system passed on is a row with `took_trade = N`. Days the team closed are a row. Without them, the review sees only the trades taken, and that's the most biased sample you have.

**`rules_followed` is binary.** "Mostly" is N. Name the rule in its own words in `rule_broken`.

**Same day, every day.** A row written next week is a story.

## 3. The debrief: plan versus execution

The hardest column to fill honestly is `rules_followed`, because by the time you fill it you know how the trade ended. A trade that made money feels like a Y. The debrief removes the feeling: it sets the card beside the fills and marks each line MATCH or DEVIATION. It is not allowed to mention whether the trade made or lost money.

Run it in chat A after the session, on every card, including the ones not taken. Copy fills and times from the platform, not from memory. Two minutes a card.

**Debrief prompt** (chat A, after the session)

```text
Role: Debrief.

Compare the plan with what was executed. Judge the execution against the card and my rules. Do not judge the result.

Inputs:
- Trade card as checked: {paste, or "card A above in this chat"}
- Memo line 9 (the verdict before the session): {paste}
- Risk check: {CLEAR / BLOCK / not run} at {hh:mm}
- What was executed (from the platform, not from memory): entry {price, time, order type} · size {n} · stop placed at {price} · target placed at {price} · stop or target moved? {no / yes: from, to, time} · exit {price, time, reason} · or "card not taken: {reason}"
- Result in R: {number}

You may not:
- Call the trade good or bad because of its result. A rule break that made money is a rule break. A full loss taken exactly to plan is a clean execution.
- Guess at anything not given to you. A missing fill is UNKNOWN, and the line it belongs to is UNCHECKED.
- Explain the market, suggest a better entry, or propose changes to my setup. Changes go through the weekly review.
- Console or congratulate me.

Reply in exactly this format:
DEBRIEF — {setup name} — card {A/B} — {date}
Plan: one sentence (trigger, entry, stop, target, size, window).
Execution: one sentence (what was actually executed).
Line by line: trigger seen · inside valid window · risk check CLEAR before entry · entry as carded · size as carded · stop as carded and never widened · target as carded · exit by the card's rules — each MATCH, DEVIATION or UNCHECKED, with the two values side by side where they differ.
Gap: one sentence naming the largest deviation, or "none".
Rule: the rule from my rules file or risk sheet that the gap breaks, quoted, or "no rule broken".
Journal fields: rules_followed = Y or N · rule_broken = {text or blank} · exit_reason = {target / stop / time / manual / card cancelled}
One line for the notes column: what happened, in my words as given, no adjectives.

rules_followed is Y only if every line is MATCH. One DEVIATION or UNCHECKED makes it N.
Before you send: confirm no sentence refers to whether the trade made or lost money, except the journal's own result field.
```


> **Red flags: Debrief**
> - "Good trade" or "unlucky". Outcome words. The debrief has MATCH and DEVIATION only.
> - A suggestion to change your setup after one trade.
> - A debrief written from memory.

A full loss taken exactly to plan is a clean row. A rule break that happened to pay is an N. Keep those two straight for a few months and the journal starts telling you the truth.

## 4. The Weekly Reviewer

A fresh chat, once a week, after your last session. Paste the week's rows and last week's memo.

**Weekly Reviewer prompt** (fresh chat)

```text
Role: Weekly Reviewer.

Below are this week's journal rows (columns as in my journal template) and last week's review memo.
Write the WEEKLY REVIEW MEMO. Describe what happened. Do not forecast.

You may not:
- Use anything except the rows I pasted. No recall of earlier weeks unless the memo is pasted.
- Suggest a new setup, indicator, filter or parameter. You review behaviour against my rules. You do not redesign the strategy.
- Draw a conclusion about edge from this week's results. Under 20 trades, say "sample too small to conclude anything" and give the numbers anyway.
- Soften a finding or open with praise.
- Propose more than one change.

Reply in exactly this format:
WEEKLY REVIEW — week of {date}
1. Counts: sessions · team memos · trades taken · cards passed · trades taken WITHOUT a memo or a CLEAR. List the trade IDs behind each count so I can check them.
2. Rule adherence: rules_followed Y versus N, with the IDs for every N.
3. The rule I break most: the rule in its own words, how many times, the IDs, and when it happens (time of day, after a loss, after a win, on event days, after a score of 1–2).
4. Followed versus broken: total R for each group, with the sum written out. Label it "descriptive only".
5. Score check: total R for cards scored 4–5 versus 1–3, sums written out. Same label.
6. Overrides: every trade taken after a BLOCK or with no memo, with IDs.
7. Last week's change: done / partly / not done, with the rows that show it.
8. One change for next week: a single, checkable action tied to the rule in section 3.
9. One thing to keep doing, with the rows that show it.
10. Data gaps: columns that are empty or inconsistent, and which sections they weaken.

Before you send: recount section 1 from the rows and confirm it matches. If a count is uncertain because a row is unclear, say which row.
```


Then **check two numbers by hand**: trades taken, and the count for the rule you break most. AI tools can miscount a table. If the numbers are off, fix the rows and rerun.

> **Red flags: Weekly Reviewer**
> - "Your strategy needs a new indicator." It reviews behaviour against your rules. Strategy questions go through the playbook method in Guide 11, with far more trades than one week.
> - Totals that don't match your count.
> - Firm conclusions from a handful of trades.
> - More than one change for next week.

## 5. Small samples, honestly

One week is maybe 5–15 trades. That says almost nothing about whether your setup has an edge. Even a few months can be too short to judge a setup. But a small sample **can** show behaviour: "3 of 4 rule breaks happened within 15 minutes of a loss" is a pattern worth acting on, because the fix (a pause) costs nothing.

So the review separates two kinds of finding:

- **Behaviour** (when and how you break rules): act on it weekly.
- **Edge** (whether the setup works): don't touch it on one week of data. Keep collecting rows. When you have 30 or more on fixed rules, the Evidence Checker (Guide 11) reports what they show and what they don't.

## 6. One change per week

One change you actually make beats five you don't. A good change is:

- **Tied to the rule you break most.**
- **Checkable:** next week's journal can show whether you did it.
- **Small:** a pause, a cut-off time, a size step, a checklist line.
- **Mirrored in your platform** if it's a number (lower daily stop → change the platform setting too).

Write it in your rules file under "This week's change", with the date. Next week's review checks it first.

## 7. The monthly team review: which rules earned their place

Rules pile up. After a few months a rules file holds lines nobody remembers the reason for, next to lines that get broken every week. Once a month, after the fourth weekly review, each rule has to account for itself: how often it applied, how often it changed a decision, how often you broke it.

The verdicts are deliberately modest. KEEP. KEEP, ENFORCE (applied, but broken twice or more, so move it into the platform or the checklist). QUESTION (never applied this month, which may only mean it wasn't tested). A rule is retired or rewritten only after two months as QUESTION, one rule a month at most. The daily stop, the per-trade maximum, the bracket rule and Part C of the risk sheet are never candidates.

What it can't do is tell you a rule makes or loses money. A month is far too short for that. It counts behaviour.

**Monthly team review prompt** (fresh chat, once a month)

```text
Role: Monthly team review.

Below are this month's journal rows and my four weekly review memos. My rules file and risk sheet are in the team setup.
Review the RULES, not the market and not the results.

You may not:
- Use anything except the pasted rows and memos. Every count must be traceable to trade IDs.
- Say that a rule "works", "adds edge" or "costs money" on this sample. One month cannot show that. You may say what a rule did: how often it applied, blocked, or was broken.
- Recommend retiring any rule in Part C of my risk sheet, my daily stop, my per-trade maximum or my bracket rule. Those are not up for review here.
- Propose more than one rule to retire and one to add or tighten.
- Invent a reason a rule exists. If my sheet doesn't say, write "purpose not stated".

Reply in exactly this format:
MONTHLY TEAM REVIEW — {month}
A. Sample: sessions, decisions logged, trades taken, cards passed. State plainly if this is under 30 trades.
B. Rule table, one row per rule in my rules file and risk sheet:
  rule (short) · times it applied · times it stopped or changed a decision (IDs) · times I broke it (IDs) · verdict
  Verdicts: KEEP (applied and followed) · KEEP, ENFORCE (applied, broken twice or more) · QUESTION (never applied this month) · NOT ENOUGH DATA
C. Weekly changes: each of the four "one change" lines, and whether the rows show it stuck.
D. Seat check: any seat whose output never changed a decision this month (for example, a Bear that found no point on any day), with the dates.
E. One rule to retire or rewrite, if any is marked QUESTION for a second month running, or "none". Say what would be lost.
F. One rule to add or tighten, tied to the most-broken rule in B, or "none".
G. What this review cannot tell me: one or two lines.

A rule that never applied has not been shown to be useless. It may simply not have been tested. Say so.
Before you send: recount column 4 of the table from the rows, and confirm sections E and F each contain at most one rule.
```


> **Red flags: Monthly team review**
> - "This rule is costing you money." Not knowable from a month.
> - A recommendation to loosen the daily stop or the per-trade maximum.
> - Counts without trade IDs.

## 8. Worked example: a week's review

*Illustrative. Eleven rows from one week of MNQ, values are examples.*

```text
WEEKLY REVIEW — week of (example)

Counts:        sessions 5 · memos 5 · trades taken 6 · passed 4 · taken without memo/CLEAR 2
Rule adherence:    followed 4 · broken 2 · broken IDs: W-07, W-10
Rule I break most:  "No entries within 10 minutes of a high-impact event" (rule 7) · 1 time · W-07
           "Two losses in a row closes the team" (rule 4) · 1 time · W-10
           Pattern: both breaks came within 12 minutes of a losing trade.
Followed vs broken:  descriptive only, sample too small to conclude anything (6 trades)
Score check:     4–5 scored: 2 trades · 1–3 scored: 2 trades · too few to compare
Overrides:      W-10 taken after a BLOCK (rule 4)
Last week's change:  "no trade without a memo" · partly · W-07 and W-10 had no memo
One change next week: after any losing trade, a 15-minute pause, then the tilt check, before any new card is checked
Keep doing:      passed on both score-1 cards (W-03, W-08); both were event days
Data gaps:      exit_reason empty on W-05
```

The finding isn't "rule 7" or "rule 4". It's **the 12 minutes after a loss.** That's where both breaks live. One change: a 15-minute pause, then the tilt check. The trader adds it to the rules file and sets a timer. Next week's review checks it first.

## 9. Common mistakes

- **Only logging trades taken.** You lose half the data, and the best half.
- **Filling the journal at the weekend from memory.** Memory flatters.
- **Asking the reviewer for a better strategy.** Wrong role, and wrong sample size.
- **Three changes a week.** Then nothing gets tested.
- **Never checking its counts.** Two numbers by hand, every week.
- **Grading the trade by its result.** The debrief grades execution. The market grades nothing.

## 10. Checklist

- [ ] Journal set up with the fixed columns
- [ ] Every card debriefed and logged the same day, taken or not
- [ ] Weekly slot in my calendar
- [ ] Two counts checked by hand
- [ ] One change written at the top of my rules file, with the date
- [ ] Platform setting changed if the change is a number
- [ ] Monthly team review in my calendar, after the fourth weekly review

## Try it (5 minutes)

Create the journal: paste the header row from the journal template (Guide 16) into a new spreadsheet or table. Add one row for your most recent trade, filling every column you can, including `rules_followed`.

*Educational only. Not financial advice. Trading involves risk.*


---

# Prop-firm mode: tune the Risk Manager to your evaluation

*Prop mode · 11 minute read · 30 minutes to do*

**In one line:** copy your firm's current rules into a sheet, set your own buffers inside them, and let the Risk Manager turn the room left to your drawdown floor into a size band each morning: normal, half, minimum or none.

> **What's in this guide**
> - The common evaluation rule types in plain English: drawdown types, daily loss, consistency, caps.
> - How to read your firm's rules so the AI never has to guess them.
> - The prop-mode prompt and the size bands ("the dial").
> - A worked day check on an example 50K evaluation with an intraday trailing drawdown.

## 1. First, the honest bit

Every firm writes its own rules, names them differently and changes them. The same firm often has different rules for different account types. Nothing in this guide describes any particular firm, and no firm is recommended here.

So the method is: **you** read your firm's current rules page, **you** copy the numbers into a sheet with the date, and the Risk Manager works only from that sheet. If a rule is unclear, ask the firm in writing and treat it as the strictest reading until they answer.

*Evaluation rules are set by the firm and can change. This is a model of them, not an arrangement with them.*

## 2. The rule types you'll meet

**Drawdown floor.** The account fails if equity touches a floor. How the floor moves is the most important rule you'll read:

| Type | How the floor moves | What it means for you |
|---|---|---|
| **Static** | Fixed distance below the starting balance. Never moves. | Simplest. Profit adds room. |
| **End-of-day trailing** | Recalculated from your end-of-day balance. Doesn't move during the day. | Open profit you give back intraday doesn't raise the floor. |
| **Intraday trailing** | Follows your highest equity, including open profit, in real time. | Open profit you give back still raised the floor. Room can shrink on a winning trade. |

Many firms stop trailing once the floor reaches a set level, often the starting balance. Check whether yours does, and at what level. Whatever the type, equity is usually checked against the floor in real time.

**Daily loss limit.** Some firms have one, some don't. Breaching it may fail the account or only stop you for the day. Find out which, and when the trading day resets.

**Consistency rule.** Some firms limit how much of your total profit can come from a single day, usually checked when you pass or request a withdrawal. The details vary a lot.

**Contract caps and scaling.** A maximum size, sometimes growing as the account grows.

**Other restrictions.** News trading windows, holding overnight or over the weekend, minimum trading days, and rules on automation, copy trading or particular tools. This team places orders automatically, so read those rules carefully.

## 3. Your buffers: their rules, then yours inside

- **Your daily stop sits well inside the firm's daily limit.** You stop before they stop you.
- **Size bands by room to the floor** ("the dial"): as room shrinks, so does size.
- **A daily cap for the consistency rule:** a simple, conservative reading is to stop for the day once today's result reaches the consistency percentage of the profit target. It isn't the only reading. Check what your firm's rule actually measures.

![The prop-mode dial: room to the floor sets today's size band](/media/course/09-prop-mode-dial.png)

The example bands below are a starting point. Set your own and write them in your sheet.

| Room left to the floor | Size band | Risk budget |
|---|---|---|
| More than 50% of max drawdown | Normal | Your normal 1R |
| 25–50% | Half | Half of 1R |
| Less than 25% | Minimum or none | Minimum size, one trade, or no trade |

## 4. The prop-mode prompt

Fill in the prop firm rules sheet (Guide 16) first. Then paste this into chat D before the day check, or save it under your risk sheet in the team setup.

**Prop mode prompt** (chat D)

```text
Role: Risk Manager. Mode: PROP DAY CHECK.

My firm's rules (copied by me from the firm's current rules page on {date}):
- Account size: {example: 50,000}
- Drawdown type: {end-of-day trailing / intraday trailing / static}
- Maximum drawdown: {example: 2,000}
- Does the floor stop trailing? {e.g. "stops at starting balance" / "no" / "unknown"}
- Daily loss limit: {example: 1,000, or "none"}
- Consistency rule: {e.g. "best day must be no more than X% of total profit" or "none"}
- Contract cap / scaling: {e.g. "max 5 minis or 50 micros" or a scaling table}
- Other restrictions: {news rules, overnight holding, automation rules, minimum days}

My own buffers (my rules, tighter than the firm's):
- My daily stop: {example: 60% of the firm's daily limit, or a fixed amount}
- Size bands by room left to the floor (example thresholds, set your own):
 - More than 50% of max drawdown left: normal risk budget.
 - 25–50% left: half risk budget.
 - Less than 25% left: minimum size only, one trade, or no trade.

Account state now:
- Current balance: {..} Highest end-of-day balance so far: {..} Highest intraday equity (if intraday trailing): {..}
- Today's result so far: {..} Total profit in the evaluation so far: {..} Best single day so far: {..}

You may not:
- Use anything you believe about any firm's rules. Only the lines above count. If I named the firm, ignore the name.
- Read an unclear rule in my favour. A rule marked "unknown" gets the strictest reading, and you say which reading you used.
- Comment on how close I am to passing, or suggest sizing up to get there.

Reply in exactly this format:
PROP TEAM: OPEN or CLOSED
1. Floor now: the maths from my drawdown type, line by line.
2. Room to floor: money and % of max drawdown.
3. Room to daily limit today: the firm's and mine. Mine is the one that counts.
4. Size band today: normal / half / minimum / none, with the threshold that set it.
5. Consistency: if a rule exists, write "Stop for the day once today's result reaches {amount}" and show how you got the amount. If none, "no rule".
6. Contract cap today: the lower of the firm's and my sheet's.
7. Firm restrictions that apply today. List every rule marked "unknown" and the strict reading used.

Then continue with the normal DAY CHECK, using the lower of my risk budget and the size band.
Before you send: recompute lines 1 and 2 once, and confirm no line relies on a firm rule I did not paste.
```


> **Red flags: Prop mode**
> - The AI "knowing" your firm's rules without you pasting them. It doesn't. Ignore anything it says about a firm that isn't in your sheet.
> - A floor calculation that ignores your drawdown type. Ask for the maths line by line.
> - Your stop set equal to the firm's daily limit. Yours sits inside.
> - Encouragement about how close you are to the target. Room to the floor sets the size. Distance to the target doesn't.

## 5. Worked example: a prop day check

*Illustrative. A 50K evaluation with example rules. Not any particular firm.*

**Sheet (example values):** account 50,000 · intraday trailing · max drawdown 2,000 · floor stops trailing at 50,000 · daily loss limit 1,000, breach fails the account · consistency: best day no more than 50% of total profit at pass · profit target 3,000 · cap 5 minis or 50 micros. **My buffers:** daily stop 400 · bands as in the table above · normal 1R = 200 · my max 5 MNQ.

**Account state:** balance 50,200 · highest intraday equity so far 51,300 · today: 0 · total profit so far 200 · best day so far 900.

**Prop mode reply:**
```text
PROP TEAM: OPEN
1. Floor now: intraday trailing → highest equity 51,300 − 2,000 = 49,300. Not yet at 50,000, still trailing.
2. Room to floor: 50,200 − 49,300 = 900 = 45% of max drawdown.
3. Room to daily limit: firm 1,000 · mine 400. Mine counts: 400.
4. Size band: HALF (25–50% room). Risk budget 100 = 0.5R of my normal.
5. Consistency: 50% of the 3,000 target = 1,500. Stop for the day once today's result reaches 1,500.
6. Contract cap: firm 50 micros, my sheet 5 MNQ → 5 MNQ.
7. Restrictions today: none pasted for news. Overnight holding: not allowed → flat before close.
```

**What changes for the Trader:** with a 100 budget and a 20-point MNQ stop, size = 100 ÷ (20 × 2) = 2.5 → rounded down → **2 MNQ**. Risk if stopped 80.

Notice what happened: the account is up on the starting balance, yet the room to the floor is under half, because the floor trailed the highest equity, including open profit that was given back. A trader who looks only at the balance would size normally. The team sized at half.

## 6. Common mistakes

- **Trusting memory or forum posts about your firm's rules.** Read the current page. Write the date.
- **Watching the balance instead of the room.** With trailing drawdowns, room is the number that matters.
- **Your daily stop equal to the firm's limit.** One slipped stop and the account is gone.
- **Sizing up to "catch up" near the end of an evaluation.** The dial goes down as room shrinks, never up.
- **Assuming a rule is the same across account types.** Evaluation and funded accounts often differ.

## 7. Checklist

- [ ] Firm rules sheet filled from the current rules page, date written
- [ ] Drawdown type, and whether the floor stops trailing, confirmed
- [ ] Daily limit consequence known (fail or pause) and reset time known
- [ ] My daily stop sits inside the firm's limit
- [ ] Size bands written in my sheet
- [ ] Unknown rules listed and treated as strictest

## Try it (5 minutes)

Open your firm's rules page and find one thing: your drawdown type. Write it at the top of your risk sheet with today's date and the page it came from. If you can't find it, that's your first support question.

*Educational only. Not financial advice. Trading involves risk.*


---

# Going fully automated: the go-live guide

*Go-live · 9 minute read*

**In one line:** live automation is the last rung, not the first. The system steps up when the setup sheet is fully mechanical, the journal shows the rules hold, and every limit is enforced in code before any order goes out.

> **What's in this guide**
> - The five rungs from a chat research team to a fully automated one, and what changes at each.
> - What a fully automated team actually needs, without the hype.
> - The go-live test: six questions that tell you if the system is ready to step up.
> - Good reasons to hold a rung longer.

## 1. The five rungs

![The go-live ladder: five rungs from chat team to automated team](/media/course/10-graduation-ladder.png)

| Rung | What runs it | Your job | What's new |
|---|---|---|---|
| **1. Chat team** | The agent roles in chat, on demo or sim | Write the rules and limits, review the journal | Separate roles, written rules, a risk check |
| **2. Scheduled team** | Scheduled prompts run parts of the routine | Same, less typing | The routine runs on a clock |
| **3. Alerts and checks** | Platform alerts fire on the trigger; the risk gate runs the check | Same | The trigger is watched automatically |
| **4. Automated, small size** | The execution agent places orders from your rules, live at minimum size | Review fills against cards | Rules written as code, risk limits enforced in code |
| **5. Fully automated** | Code finds, sizes and places trades inside limits enforced in code | Supervise, review, switch off | Testing, monitoring, a kill switch, hosting |

What never changes, at any rung: **you own the limits.** Rungs 1–3 run on demo. Rung 4 runs live at small size. Rung 5 runs fully automated: you set the rules and limits, the system executes, and you can switch it off any time.

## 2. What a fully automated team actually needs

Honestly, it's a lot more than "connect AI to my broker":

- **Rules a computer can follow with zero judgement.** Every CAN'T TELL in your setup sheet has to become a calculation.
- **Clean data.** A reliable price feed, and a way to notice when it's late, missing or wrong.
- **Testing on history that's honest.** Fills at realistic prices, costs included, no peeking at future bars, and testing on data the rules weren't tuned on. A pretty backtest shows very little. Guide 11 covers the ways a test fools you.
- **Stress tests.** Thousands of reshuffled orderings of the trade list, to see the bad runs to expect before they happen.
- **A risk gate in code.** The same limits as your risk sheet, enforced by code that runs after any AI and before any order. An AI can add a veto. Nothing can lift one.
- **Execution.** A broker or platform connection that allows automated orders, with permission from your broker or firm.
- **Monitoring and a kill switch.** Logs of every verdict and order, alerts when something breaks, one control that cancels everything and stands the team down.
- **Somewhere to run it.** A machine or server that stays on during your sessions.
- **Maintenance.** Platforms change, data feeds change, firms change rules. Someone has to keep it working.

None of this is impossible. All of it takes skill, time or money. Often all three.

## 3. The go-live test

Answer yes or no. Six yeses before the system steps up to live:

1. **Mechanical.** Could a stranger follow your setup sheet with no questions? Has every rule been checkable (no CAN'T TELL from the rule's wording) for 8 weeks?
2. **Followed.** Has your journal shown `rules_followed = Y` on nearly every trade for 8 weeks or more?
3. **Logged.** Do you have a long enough journal that the setup's behaviour, in R and in losing runs, is something you can describe, with a sample you've written down and an Evidence Checker report (Guide 11) whose sums you've checked?
4. **Bounded.** Can you state, as numbers, the worst day and the worst run of losses you'd accept before switching it off?
5. **Allowed.** Have you confirmed in writing that your broker or firm allows automated trading on your account type?
6. **Owned.** Do you have the time and skill to build and maintain it, or the budget for someone who does?

If any answer is no, hold at rungs 1–3 and keep journaling. That's not failure. It's the evidence ladder doing its job.

## 4. Good reasons to hold a rung longer

- **Part of the setup is still judgement.** Every rule must be a calculation before live execution. Until then, keep rewriting.
- **The rules still change often.** Automation suits stable rules.
- **Your account or firm doesn't allow automated orders yet.** Get it in writing first.
- **The journal is short.** More rows on sim cost nothing. A rushed go-live can cost the account.

## 5. Worked example: two traders, same question

*Illustrative.*

**Trader A** has run the team for 12 weeks. The setup sheet hasn't changed in 9 weeks. Every context rule is a calculation: time windows, prior day levels, swing comparisons on the 1H. The journal shows rules followed on all but a handful of trades, each with a note. The firm's rules page allows automation on this account type, confirmed by email. A has written down the worst run of losses that would mean switching it off. **Six yeses.** A steps up to rung 3 (alerts on the trigger), then rung 4 at minimum size.

**Trader B** has run the team for 5 weeks. Context rule 2 is still "the 1H looks like it's trending", which the Researcher keeps marking CAN'T TELL. The journal shows 7 rule breaks, all after losses. **Two yeses.** B holds at rung 1, works on rule 2's wording, and makes the post-loss pause the weekly change. Automating now would only automate the breaks.

## 6. Common mistakes

- **Automating vague rules.** Code doesn't fix a rule that can't be checked. It just executes the guess.
- **Automating a setup you haven't journaled.** You'd be automating a story.
- **Trusting a backtest without stress tests and unseen data.** Most good-looking backtests fall apart on data they weren't built on.
- **Skipping the broker or firm permission check.** Read the rules. Get it in writing.
- **Letting an AI place orders with no code-enforced limits after it.** The risk gate goes in code, after the AI, every time.

## 7. Checklist

- [ ] I know which rung the system is on today
- [ ] I've answered the six go-live questions honestly, in writing
- [ ] If any answer is no, I know which one to work on next
- [ ] I've read my broker's or firm's rules on automation

## Try it (5 minutes)

Write the six go-live questions at the bottom of your rules file with today's answers. Put a reminder in your calendar to answer them again in 8 weeks.

---

That's the trading team, complete. Run the routine tomorrow, review at the weekend, change one thing a week. When you want to pressure-test your setup or research a new one, the Playbooks start at Guide 11.

*Educational only. Not financial advice. Trading involves risk.*


---

# Playbooks: how to research a strategy with the team

*Playbooks · 15 minute read · 40 minutes to do · never on a trading morning*

**In one line:** a strategy idea earns a place on your team by climbing five rungs, from a hypothesis you could fail, through locked rules and a counted sample with costs, to fresh data and small size, with one seat designing the test and another reporting only what your own rows show.

> **What's in this guide**
> - The research method in six steps: hypothesis, rules, evidence, costs, sample, out-of-sample.
> - The six mistakes that manufacture an edge that isn't there, and the guard against each.
> - The evidence ladder: five rungs, and what each one does and doesn't prove.
> - Two research prompts: the Strategy Scout and the Evidence Checker.

## 1. What a playbook is, and what it isn't

Everything up to Guide 10 assumed you arrived with a setup. This shelf is for the question underneath: **how do you know a setup deserves your risk?** And the related one: how do you look at a new idea without fooling yourself?

A **playbook** here is a research brief. It states a well-known public idea in one line, gives the public reasoning for why it might work, lays out a rule template with blanks, and lists what kills it. Guides 12 and 13 hold eight of them. None comes with a result, a success rate or a recommended setting. That is on purpose, for three reasons.

**Published edges fade.** A study in the Journal of Finance looked at 97 published stock-return predictors and found their returns were clearly lower outside the original sample period, and lower again once the research was public ("Does Academic Research Destroy Stock Return Predictability?", *Journal of Finance*, 2016). A pattern everyone has read about is a pattern many people are already trading.

**Backtests are easy to flatter.** A paper on backtest overfitting showed that if you try enough variations of a rule on the same history, a good-looking result is almost certain to appear by chance, and then to disappoint on new data ("Pseudo-Mathematics and Financial Charlatanism", *Notices of the American Mathematical Society*, 2014). Another study made the matching point about published research: after hundreds of tested factors, the usual bar for "significant" is too low ("… and the Cross-Section of Expected Returns", *Review of Financial Studies*, 2016).

**Your market isn't their market.** A study on a US equity ETF over twenty years says little about gold in the London hour on your broker's spread this year. Costs alone can turn a published result upside down.

So the honest position is this: most ideas you test will not survive costs and fresh data. The method below is built to find that out cheaply, on demo, before the market tells you at full size.

## 2. The method, in six steps

1. **Hypothesis.** One sentence that could be wrong. "On {market}, during {session}, when {a condition you can check}, then {a measurable outcome} within {a time}." If you can't write it, you have a feeling, not an idea.
2. **Rules.** Context, trigger, entry, stop, target, time exit, when not to trade. Every number filled in **before** you look at any results, then dated and locked. The playbook brief template (Guide 16) is the form.
3. **Evidence needed.** Decide what you'll count, and what result means "drop it", before you start. These are your falsifiers. Written afterwards, they are excuses.
4. **Costs.** Commission plus spread or slippage, subtracted from every trade. A strategy with many small trades can be right about direction and still lose to costs.
5. **Sample size.** At least 30 trades before you look at totals. Thirty is a floor for looking, not a proof. It can tell you an idea is clearly dead. It cannot separate a small edge from a lucky month.
6. **Out-of-sample.** Results from the period you used to choose your settings are *in-sample*: they have seen the answers. Only results from data the rules never touched count as a test. **Walk-forward** is the simplest version: lock the rules, then trade them forward on demo and count again.

## 3. The Strategy Scout

The Scout does step 1 to 3 with you. You give it a vague idea. It returns a hypothesis, a rule template whose every number is a blank, the evidence needed, and the falsifiers. It is forbidden to say the idea works, to pick your settings or to cite a source it isn't sure of.

Open a separate research chat in your team workspace. Not chats A to D, and not before a session.

**Strategy Scout prompt** (research chat)

```text
Role: Strategy Scout.

Turn my idea into a testable hypothesis and a test plan. You are designing a test I could fail, not making a case for the idea.

Inputs:
- My idea, in my words: "{the idea}"
- Market and instrument: {e.g. MNQ futures / EURUSD / gold}
- Session and time zone: {e.g. London open, 08:00–10:00 London}
- Timeframe I would trade it on: {e.g. 5-minute bars}
- What I can test with: {e.g. bar replay on my charting platform, a spreadsheet, a demo account}
- Rough round-trip cost per trade if I know it (commission + typical spread or slippage): {amount, or "unknown"}

You may not:
- Say or imply that the idea works, has an edge, or is likely to. No success rates, no expected returns, no "studies show" without a source I can check.
- Cite a paper, book or statistic unless you are certain of author and title. If you mention one, add "(unverified — check it yourself)". Never invent a citation.
- Choose parameter values for me. Where a number is needed, leave a blank {I choose: ...} and say what the choice trades off. If you show a value to explain a format, label it "placeholder".
- Recommend trading it. The output is a plan for testing on demo or replay.

Reply in exactly this format:
SCOUT MEMO — {short name for the idea}
1. Hypothesis: "On {market}, during {session}, when {condition I can check on a chart or clock}, then {measurable outcome} within {time horizon}, more often or by more than on days without the condition." One sentence.
2. Why it might exist: the plainest public reasoning, in two lines. Who is on the other side of the trade, and why would they keep paying? If you can't say, write "no clear reason", which is a warning sign.
3. Why it might not: two lines. Include costs and crowding.
4. Rule template: context rules, trigger, entry, stop, target, time exit, no-trade conditions. Every number is a blank I fill in BEFORE I look at any results.
5. Locked before testing: the list of every blank in section 4. I write my values, date them, and do not change them during the test.
6. Evidence needed: what to count for each trade (date, direction, entry, exit, result in R, cost), the minimum number of trades before I look at totals ({I choose: at least 30}), and which periods to cover (including ones that should not suit the idea).
7. Costs: what to subtract from each trade, and what result per trade would be wiped out by my stated cost.
8. Falsifiers, written now: two or three results that mean "drop it" (for example: total R at or below zero after costs over the sample; the result disappears when the best day is removed; it only shows up with one exact setting).
9. Ways this test could fool me: which of these apply and where — look-ahead, choosing settings after seeing results, tiny sample, ignoring costs or slippage, survivorship, best-day dependence.
10. Next rung: which rung of the evidence ladder this idea is on, and the one action that moves it up.

If my idea is too vague to write section 1, stop after asking me up to 3 questions.
Before you send: confirm that no line says or implies the idea works, that every number in section 4 is a blank, and that section 8 can actually be failed.
```


> **Red flags: Strategy Scout**
> - "This has historically performed well." It can't know that, and it was told not to say it.
> - A source you can't find when you search for it. Unverified until you have opened it yourself.
> - Settings offered as recommendations. The blanks are yours.
> - Falsifiers that can't fail.

## 4. Six mistakes that fake an edge

Every one of these makes a test look better than the idea is. Each has a plain guard.

| Mistake | How it sneaks in | The guard |
|---|---|---|
| **Look-ahead** | The rule uses something you couldn't have known at the time: the day's high, the close of a bar that hadn't closed, a level drawn afterwards. | In replay, decide before you reveal the next bar. Write the decision time on every row. |
| **Choosing settings after seeing results** | You try a 15-minute range, then 30, then 10, and keep the best. The winner has been fitted to that history. | Lock every blank before testing. A changed blank is a new brief and a fresh count. |
| **Tiny samples** | Eight trades, six of them winners, and it feels like proof. | No totals before 30 trades. Under 30, the report says "descriptive only". |
| **Ignoring costs and slippage** | Results counted from chart prices, as if every order filled at the level with no spread. | A cost in R on every row. Find your real spread at the hour you trade. |
| **Survivorship** | You test on the instruments, months or examples you remember, which are the ones where it worked. | Log every qualifying day in the period, taken or not. Include a stretch that shouldn't suit the idea. |
| **Best-day dependence** | The whole result is one or two outsized days. Remove them and nothing is left. | Recompute the total without the best day and without the best trade. Check whether the sign changes. |

## 5. The evidence ladder

![The evidence ladder: five rungs from idea to small size](/media/course/11-evidence-ladder.png)

| Rung | What you do | What it shows | What it doesn't |
|---|---|---|---|
| **1. Idea** | Write the hypothesis and the falsifiers. | That you know what you're claiming. | Anything about the market. |
| **2. Rules** | Fill and date every blank in the brief. Have the Bear attack it. | That the idea can be traded the same way twice. | That it should be. |
| **3. Sample** | 30 or more trades on replay or demo, every qualifying day logged, costs on every row. | Whether the idea is clearly dead, and how its losing runs look. | An edge. In-sample results flatter. Demo fills are kinder than live ones. |
| **4. Walk-forward** | The same locked rules, forward, on demo, on days the rules never saw. Another 30 or more. | Whether rung 3 was fitted to its own history. | How you will behave with money on it. |
| **5. Small size** | Live, at the smallest size your platform allows, for a number of trades fixed in advance. Through the full team routine. | Real fills, real costs, and your own execution. | That it will continue. Nothing shows that. |

Move up only when the rung you're on hasn't hit a falsifier. Move down, or drop the brief, when it has. An idea that dies on rung 3 has cost you some evenings. That is the ladder doing its job.

After rung 4, a brief becomes a setup sheet in your rules file, and the trading team in Guides 03 to 08 takes over.

## 6. The Evidence Checker

The Checker does steps 4 and 5 and part of 6. You paste rows: a replay log, a demo log, your live journal or a backtest export. It reports the sample size, whether costs are in, totals with the sums written out, what's left without the best day, the longest losing run, and a list headed "what this does NOT prove". It computes from your rows only.

Two cautions. Language models can misadd a column, which is why the prompt demands visible arithmetic and a cross-check, and why you verify two sums yourself. And the report describes a sample. It has no opinion on the future.

**Evidence Checker prompt** (research chat; use a reasoning mode if your tool has one)

```text
Role: Evidence Checker.

Report what the rows below show. Compute from these rows only, show every sum, and be exact about what the sample cannot tell me.

Inputs:
- Where the rows come from: {my live journal / demo log / bar-replay log / backtest export from {tool}}
- What they test: {setup name, market, session}
- Were the rules fixed before these trades, or adjusted along the way? {fixed on {date} / adjusted / not sure}
- Do the results include costs (commission, spread, slippage)? {yes / no / not sure}
- If no: my round-trip cost per trade is about {amount in R, or "unknown"}
- Rows (pasted by me, unedited). Columns: {e.g. trade_id, date, result_r, rules_followed}
{paste rows}

You may not:
- Use any number that is not in the rows or derivable from them. Do not estimate a missing value. Do not recall "typical" figures for this kind of strategy.
- Call the strategy good, bad, promising, or say it has or lacks an edge. You report the sample.
- Express any result as a chance of future success, or project it forward ("at this rate...").
- Skip the arithmetic. Every total is shown as a sum I can retype into a calculator.
- Round in a way that changes a sign or hides a difference.

Reply in exactly this format:
EVIDENCE REPORT — {setup name} — {n} rows
1. Sample: number of trades, first and last date, number of trading days. If under 30 trades, the first words are "Under 30 trades: descriptive only."
2. Source quality: live / demo / replay / backtest, and whether the rules were fixed beforehand. If adjusted or unsure, say the results are in-sample and likely flattered.
3. Totals: winners {n}, losers {n}, flat {n}. Total R with the sum written out. Average R per trade = total ÷ n.
4. Costs: included or not. If not, total R minus (n × cost) = net, sum written out. If cost is unknown, write "net result unknown" and do not guess.
5. Best-day dependence: R per day, listed. Total R without the best day. Total R without the best single trade. State whether the sign changes.
6. Losing runs: the longest run of consecutive losers (with IDs), and the deepest fall from a running peak in R (peak value, trough value, IDs).
7. Rules followed versus broken, if the column exists: n and total R for each, sums written out. Descriptive only.
8. Checks I could not do: missing columns, duplicate IDs, rows out of date order, results not in R.
9. What this does NOT prove: at least four lines specific to this sample (size, period covered, source, costs, whether rules were fixed, dependence on one day).
10. The next piece of evidence that would matter most: one line.

If a row is unreadable, list it under 8 and leave it out of every sum. Say that you did.
Before you send: add the per-day totals in section 5 and confirm they equal the total in section 3. If they don't, find the error before replying.
```


> **Red flags: Evidence Checker**
> - A total with no visible sum.
> - Verdict words: "promising", "solid", "a real edge".
> - A net figure when you said your cost was unknown.
> - A projection forward ("at this rate…").
> - Per-day totals that don't add up to the overall total.

## 7. Where the agent team comes in

- **Researcher** turns the filled brief into yes/no rules, exactly as on Guide 03. If two people could disagree about a rule on the same chart, you can't count it.
- **Bear** attacks the brief before you test it. Each playbook lists what the Bear should go after. Paste the brief into a fresh chat with the Bear prompt and the line: "Scenario under review: testing this brief on {market}. Attack the test design, not a trade."
- **Risk Manager** sets the size for rung 5 from your risk sheet. Smallest size, a fixed number of trades.
- **Weekly Reviewer** stays out of it. A week is too short for strategy questions.

## 8. Worked example: one idea, three rungs, one honest ending

*Illustrative. The idea, the counts and the outcome are invented to show the method. They are not findings about any market.*

**Rung 1.** A trader has an idea: "Gold breaks out of its overnight range at the London open." The Strategy Scout returns a hypothesis, a template with eleven blanks, and three falsifiers: (a) total R after costs at or below zero over the sample, (b) total turns negative when the best day is removed, (c) the result needs one exact range window.

**Rung 2.** The trader fills the eleven blanks in a playbook brief and dates it. The Researcher flags "a clear break" as vague. It becomes "a 5-minute close beyond the range edge". The Bear's best attack: "The spread at the session change isn't in your cost line." The trader watches the spread at 08:00 London for a week and writes the real figure into the brief.

**Rung 3.** Six weeks of bar replay, one evening at a time, deciding before each bar is revealed. 34 qualifying days logged, taken or not. The Evidence Checker reports:

- 34 trades. Costs included on every row.
- A small positive total after costs.
- Without the best day, the total is negative. The sign changes.
- Longest losing run: 6.
- "What this does NOT prove": five lines, starting with "that the total is repeatable; more than all of it came from one day".

Falsifier (b) is met. The trader checks the two sums by hand, confirms them, and **drops the brief.** No new range window, no "one more filter". Changing a blank now would be choosing settings after seeing results.

Six evenings, no money, and one idea crossed off with a reason attached. Most research ends like this. The trader's existing setup, the one already in the journal, goes through the Evidence Checker next.

## 9. Common mistakes

- **Researching on a trading morning.** New ideas and live sessions don't share a chat or a day.
- **Asking the AI whether a strategy works.** It will produce a confident answer assembled from things it has read. Ask it to design the test. Then run the test.
- **Treating a cited paper as permission.** A study describes its own market, period and costs. It is a reason to test, never a result you can borrow.
- **Moving a blank mid-test.** New brief, new date, count from zero.
- **Skipping rung 4** because rung 3 looked good. Rung 3 is the one that flatters.
- **Testing five ideas at once.** One brief under test at a time.

## 10. Checklist

- [ ] My idea is written as one sentence that could be wrong
- [ ] Falsifiers written and dated before any testing
- [ ] Every blank in the brief filled and locked
- [ ] Cost per trade measured on my own account, at my trading hour
- [ ] Every qualifying day logged, taken or not
- [ ] No totals read before 30 trades
- [ ] Two of the Evidence Checker's sums checked by hand
- [ ] I know which rung each of my setups is on today

## Try it (5 minutes)

Take the setup you already trade. Write one line at the top of your rules file: "Evidence ladder: rung __, since {date}", and fill in the rung honestly. If you have never counted 30 trades on fixed rules with costs, it is on rung 2, however long you've traded it.

## Sources

Each was checked for title, authors and year. They are reasons for caution, not trading advice.

- R. "Does Academic Research Destroy Stock Return Predictability?", *Journal of Finance*, 2016.
- "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance", *Notices of the American Mathematical Society*, 2014.
- "… and the Cross-Section of Expected Returns", *Review of Financial Studies*, 2016.

*Educational only. Not financial advice. Trading involves risk.*


---

# Playbooks: four briefs for the session open

*Playbooks · 16 minute read · pick one brief, 30 minutes to start it*

**In one line:** four well-known public strategy families built around the first part of the session, each written as a research brief with blanks you fill, the things that kill it, the points your Bear should attack, and the exact lines to start testing it.

> **What's in this guide**
> - How to read a playbook brief, and the one way to use it.
> - Opening range breakout.
> - Opening gap: continuation ("gap continuation") and fade.
> - Early-session and intraday momentum.
> - VWAP reversion and first touch.

## 1. Read this first

These are **research briefs, not setups.** Each describes an idea that has been public for years. Most published edges shrink or vanish once they're widely known and once real costs are counted (Guide 11, section 1). Nothing in this guide says any of these works on your market, now, after your costs. The only way to know is to test it yourself, up the evidence ladder.

So there are no results here, no success rates and no recommended settings. Where a brief mentions a study, the study describes its own market, period and assumptions. Treat it as a reason the idea is worth a test, never as a result you can borrow.

![Anatomy of a playbook brief](/media/course/12-playbook-brief-anatomy.png)

Every brief has the same six parts:

1. **The idea**, in one line.
2. **Why it might work**: the public reasoning, with sources where they exist.
3. **Rule template**: yes/no conditions, entry, stop, target, time exit and when not to trade. Every number is a blank.
4. **What kills it**: costs, regime, crowding, news days.
5. **What the Bear should attack** before you test.
6. **Start it**: the input lines for the Strategy Scout prompt (Guide 11).

**The one way to use a brief:** pick one. Paste its "Start it" lines into the Strategy Scout prompt. Copy the playbook brief template (Guide 16), fill every blank, date it, lock it. Have the Bear attack it. Then climb the ladder on demo or replay. One brief at a time.

## 2. Playbook · Opening range breakout

**The idea.** The high and low of the first minutes of the session mark a range. A break of that range, early in the day, is taken in the direction of the break.

**Why it might work.** The open is when overnight orders, news and the day's first large participants meet. The reasoning is that the first range shows where that initial fight settled, and a move out of it shows which side has more to do. The idea is old and public. Toby Crabel wrote it up in detail in *Day Trading with Short Term Price Patterns and Opening Range Breakout* (1990), including the observation that breakouts following narrow-range days behaved differently from others. More recently, a 2023 working paper tested an opening-range rule on a Nasdaq ETF on SSRN (listed under Sources). It is one paper, on one instrument and period, with its own cost and position-sizing assumptions, and not peer-reviewed. Read it as a description of how such a test can be set up.

**Rule template.**

```text
Context (yes/no): 1) Session: {which open, time zone}
          2) Opening range = high and low of the first {__} minutes
          3) Range width is between {__} and {__} (points, or a multiple of {__})
          4) Higher-timeframe filter: {rule, or "none"}
Trigger (yes/no): A {__}-minute bar closes beyond the range edge by {__}
Entry:       {stop order at the edge / market on the close / limit on a retest of the edge}
Stop:       {opposite edge / range midpoint / {__} beyond the trigger bar}
Target:      {multiple of range width / fixed R / none, time exit only}
Time exit:     Flat by {__}
When not to trade: 1) High-impact event before {__} 2) Range wider than {__} 3) {__}
```

**What kills it.**
- **Costs.** The entry is a breakout, so you pay the spread and often slippage at the moment everyone else is entering.
- **Regime.** On range days the open is broken both ways. Whipsaws are the normal case, not the exception.
- **Crowding.** It is one of the most widely taught intraday ideas. Breaks of obvious levels attract traders whose plan is to fade them.
- **News days.** A release inside the opening hour makes the "range" an accident of timing.

**What the Bear should attack.** Was the range length chosen before or after looking at charts? What happens on the days the first break fails and the second one runs? Is the stop so wide that size rounds to zero on your account? Does the result survive without its best day?

**Start it.**

```text
My idea, in my words: "The first {__} minutes set a range. I trade a break of it in the direction of the break, early in the session."
Market and instrument: {e.g. MNQ}
Session and time zone: {e.g. New York cash open, New York time}
Timeframe I would trade it on: {e.g. 5-minute bars}
What I can test with: {bar replay, spreadsheet, demo}
Rough round-trip cost per trade: {amount, or "unknown"}
```

## 3. Playbook · Opening gap: continuation and fade

**The idea.** When the session opens away from the prior close, either the move carries on in the direction of the gap ("gap continuation"), or it retraces towards the prior close ("gap fade"). These are two opposite briefs. Test them separately.

**Why it might work.** A gap is the overnight session's verdict arriving all at once. The continuation reasoning: whatever caused it is still being acted on by participants who can only trade the day session. The fade reasoning: the gap overshot on thin overnight volume, and the day session corrects it. There is research showing that overnight and intraday returns behave like two different regimes with a pull between them, for example Dong Lou, Christopher Polk and Spyros Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns" (*Journal of Financial Economics*, 2019), which studies US stocks. That supports the claim that the open is a real boundary. It is not a rule for trading gaps, and it says nothing about index futures or currencies.

**Rule template.**

```text
Context (yes/no): 1) Gap = today's open minus the prior session's close, measured at {time}
          2) Gap size is between {__} and {__} (points, %, or a multiple of {__})
          3) Brief is: CONTINUATION or FADE (one per brief, never both)
          4) A known cause on my event sheet? {required / forbidden / ignored}
Trigger (yes/no): Continuation: {e.g. first {__}-minute bar closes beyond the opening {__}-minute range in the gap direction}
          Fade: {e.g. first {__}-minute bar closes back through the open, towards the prior close}
Entry:       {order type and level}
Stop:       Continuation: {__}  Fade: {beyond the session extreme so far / {__}}
Target:      Continuation: {__}  Fade: {prior close / {__}% of the gap / fixed R}
Time exit:     Flat by {__}
When not to trade: 1) Gap larger than {__} 2) High-impact event inside the first {__} minutes 3) {__}
```

**What kills it.**
- **Mixing the two.** Deciding on the day whether it's a "go" or a "fade" is discretion with a label on it. It can't be counted.
- **Size of gap.** Small gaps are noise. Very large gaps are news events with their own behaviour. The middle band is a setting, and settings chosen after looking are fitted.
- **Costs.** The first minutes carry the widest spreads of the day session.
- **Instrument.** A gap in a single stock, an index future and a currency pair are three different things. Futures that trade nearly round the clock have small "gaps" at the cash open by construction.

**What the Bear should attack.** How is the gap measured on an instrument that trades overnight? Which gap sizes were excluded, and when was that decided? For the fade: what happens on the days the gap never fills? One of those can cost several ordinary winners.

**Start it.**

```text
My idea, in my words: "When the session opens at least {__} away from the prior close, I trade {continuation in the gap direction / a fade back towards the prior close}."
Market and instrument: {…}
Session and time zone: {…}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {…}
```

## 4. Playbook · Early-session and intraday momentum

**The idea.** The direction of the first part of the session carries information about the direction later in the same day. The move is joined after the first window, or late in the session, in the same direction.

**Why it might work.** Two public lines of reasoning. First, large participants spread their orders across the day, so early direction can reflect business that isn't finished. Second, traders and products that have to rebalance near the close trade in the direction of the day's move. The best-known study is Lei Gao, Yufeng Han, Sophia Zhengzi Li and Guofu Zhou, "Market Intraday Momentum" (*Journal of Financial Economics*, 2018). On an S&P 500 ETF from 1993 to 2013 they report that the first half-hour's return, measured from the prior close, had predictive power for the last half-hour's, more so on volatile and news days. A later 2024 working paper tested an intraday trend rule on the same ETF (listed under Sources). Both describe one US equity product. The first sample ends in 2013. Whether anything similar holds on your instrument, after costs, in recent data, is exactly what your test is for.

**Rule template.**

```text
Context (yes/no): 1) First window = {start}–{end}, return measured from {prior close / today's open}
          2) First-window move is at least {__} (points, %, or a multiple of {__})
          3) Regime from the Analyst is {TRENDING / any / not EVENT DAY}
Trigger (yes/no): {at {time}, price is still beyond {level} in the first-window direction}
          or {a pullback of {__} that holds above/below {level}}
Entry:       {time-based market order at {__} / limit at {__}}
Stop:       {beyond the first-window extreme / {__}}
Target:      {none, time exit only / fixed R / {__}}
Time exit:     Flat at {__} (state whether this is before or at the close)
When not to trade: 1) First-window move smaller than {__} 2) Scheduled event after {__} 3) {__}
```

**What kills it.**
- **Being late.** By the time the first window has closed, part of the day's move has happened. The stop is far and the remaining room may be small.
- **Reversal days.** Strong opens that reverse are common, and they are full losses for this brief.
- **Small effects.** A statistical tendency in a study can be real and still be smaller than your costs.
- **Time decay of the finding.** Published in 2018, on data to 2013. Others have had years to trade it.

**What the Bear should attack.** Is the return measured from the prior close or the open, and was that chosen first? How many trades a month does this produce, and how long until there are 30? Is the result a few trend days carrying everything else?

**Start it.**

```text
My idea, in my words: "If the first {__} minutes move at least {__} in one direction, I join that direction {after the window / in the last {__} minutes} and exit by {__}."
Market and instrument: {…}
Session and time zone: {…}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {…}
```

## 5. Playbook · VWAP reversion and first touch

**The idea.** VWAP is the session's volume-weighted average price. Reversion: when price stretches far from it, trade back towards it. First touch: after a directional open, the first return to VWAP is traded in the direction of the open. Again, two different briefs. One fades, one joins.

**Why it might work.** VWAP matters because institutions use it as a yardstick for execution quality. The benchmark is usually credited to Berkowitz, Logue and Noser, "The Total Cost of Transactions on the NYSE" (*Journal of Finance*, 1988). If large orders are worked with VWAP as a target, there is real business done around it, which is the argument for a first touch holding. And if price has run far from where most of the day's volume traded, there may be fewer participants willing to chase it, which is the argument for reversion. Both arguments are plausible and neither is a measurement. There is no single well-known study to lean on for either as a short-term trading rule, so this brief rests on reasoning alone. Weigh it accordingly.

**Rule template.**

```text
Context (yes/no): 1) VWAP anchored to: {session open / {__}}
          2) Brief is: REVERSION or FIRST TOUCH (one per brief)
          3) Reversion: price is at least {__} from VWAP (points, or {__} standard-deviation bands)
           First touch: the open moved at least {__} away from VWAP before returning
          4) Regime from the Analyst is {RANGING for reversion / TRENDING for first touch / {__}}
Trigger (yes/no): Reversion: {a {__}-minute bar closes back inside {band/level}}
          First touch: {price touches VWAP for the first time since {time} and a {__}-minute bar closes back in the opening direction}
Entry:       {order type and level}
Stop:       Reversion: {beyond the stretch extreme by {__}}  First touch: {{__} beyond VWAP}
Target:      Reversion: {VWAP / {__}% of the way to VWAP}  First touch: {session extreme / fixed R}
Time exit:     Flat by {__}
When not to trade: 1) Before {time} (VWAP is unstable early in the session) 2) EVENT DAY 3) {__}
```

**What kills it.**
- **Trend days.** For reversion, a trend day is a string of full losses: price stretches, you fade, it stretches further.
- **VWAP isn't one number.** It depends on the anchor and on the data feed's volume. Two platforms can show different lines, and spot currencies have no central volume at all.
- **Early session.** In the first minutes VWAP sits almost on top of price and means little.
- **Everyone has the line.** It is on every platform by default.

**What the Bear should attack.** Does your instrument have real volume data? What separates a "stretch" from the start of a trend, in a rule and not in hindsight? For first touch: how often is the first touch simply the start of a move through?

**Start it.**

```text
My idea, in my words: "{When price is at least {__} from session VWAP, I trade back towards it. / After a directional open, I trade the first touch of VWAP in the direction of the open.}"
Market and instrument: {…}
Session and time zone: {…}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {…}
```

## 6. Worked example: turning a brief into a locked test

*Illustrative. The values are one trader's choices, shown to demonstrate the form. They are not suggested settings.*

A trader who already trades an opening-range retest wants to know whether the plain breakout, without the retest, deserves a look.

- **Scout.** Pastes the "Start it" lines for the opening range breakout. The memo comes back with nine blanks and three falsifiers.
- **Brief.** Fills every blank in the playbook brief template and dates it. The choices are the trader's own and made before opening a chart: a range length, a width band, a 5-minute close trigger, the opposite edge as the stop, a fixed-R target, a time exit, and two no-trade lines.
- **Bear.** "Your stop is the full range. On your account that rounds to one contract on wide days and zero on some. How many qualifying days survive the size maths?" The trader adds a no-trade line: "size rounds to zero".
- **Rung 3 plan.** Bar replay, one month at a time, every session open in the period logged, taken or not, cost on every row. No totals before 30 trades.

Nothing has been learned about the market yet. What exists is a test that can fail, which is more than most traders ever have for a setup.

## 7. Common mistakes

- **Reading a brief as a setup.** It has blanks for a reason. A brief with someone else's numbers in it is someone else's untested idea.
- **Running continuation and fade in the same test.** Opposite briefs, separate counts.
- **Borrowing a paper's result.** Different instrument, different years, different costs.
- **Starting three briefs because all four look interesting.** One.
- **Skipping the Bear.** The attack on the test design is the cheapest check you'll ever run.

## 8. Checklist

- [ ] One brief chosen, the others left alone
- [ ] "Start it" lines run through the Strategy Scout
- [ ] Every blank filled, dated and locked in the brief template
- [ ] Bear run on the brief; its best point answered in the brief or accepted as a risk
- [ ] Test log created with the columns from the brief template

## Try it (5 minutes)

Pick the brief closest to something you already trade. Read only its "What kills it" list. Write down which of those you have actually counted in your own trading, and which you have only assumed.

## Sources

Each was checked for title, authors and year. A source is a reason to test an idea, never evidence that it works for you.

- Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout*, Traders Press, 1990.
- "Can Day Trading Really Be Profitable?", SSRN working paper, 2023. The title is the authors' own. This library makes no such claim.
- Dong Lou, Christopher Polk and Spyros Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns", *Journal of Financial Economics*, 2019.
- Lei Gao, Yufeng Han, Sophia Zhengzi Li and Guofu Zhou, "Market Intraday Momentum", *Journal of Financial Economics*, 2018.
- "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Swiss Finance Institute Research Paper 24-97, 2024. The title is the authors' own. This library makes no such claim.
- Berkowitz, Logue and Noser, "The Total Cost of Transactions on the NYSE", *Journal of Finance*, 1988.

*Educational only. Not financial advice. Trading involves risk.*


---

# Playbooks: four briefs for levels, sessions and trends

*Playbooks · 16 minute read · pick one brief, 30 minutes to start it*

**In one line:** four more public strategy families, from a sweep of yesterday's high to multi-week trend following, each as a research brief with blanks, the things that kill it, the Bear's attack and the lines that start the test.

> **What's in this guide**
> - Prior-day high/low sweep and reclaim.
> - London-session breakout (currencies and gold).
> - Trend following on higher timeframes (channel breakouts and moving-average filters).
> - Mean reversion in ranges.
> - A map of all eight playbooks by what kind of day each needs.

## 1. The same rules as Guide 12

These are **research briefs, not setups.** No results, no success rates, no recommended settings. Most published edges shrink or vanish after costs and once they're widely known. A cited source describes its own market and period. You test on yours, up the evidence ladder (Guide 11), one brief at a time.

Each brief has the six parts from Guide 12: the idea, why it might work, a rule template with blanks, what kills it, what the Bear should attack, and the "Start it" lines for the Strategy Scout.

![Eight playbooks by the kind of day each needs](/media/course/13-eight-playbooks.png)

**One thing the map makes plain.** Some of these briefs need the market to keep going and the others need it to turn back. No single day suits all eight. Any brief you test will have a kind of day that hurts it, and part of the test is finding out how much.

## 2. Playbook · Prior-day high/low sweep and reclaim

**The idea.** Price trades through yesterday's high or low, fails to stay there, and closes back inside. The trade is taken back into yesterday's range.

**Why it might work.** Yesterday's high and low are on every chart, so they are natural places for resting orders: stops from traders positioned the other way, and entries from breakout traders. The reasoning is that a push through the level fills those orders, and if nothing follows, the traders who bought the break are now wrong and have to exit. There is academic evidence that orders do cluster at obvious prices. Carol Osler documented clustering of stop-loss and take-profit orders in currency markets and linked it to how prices behave around those levels ("Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance*, 2003). Note the limits: her data is currency orders at round numbers, not prior-day highs in futures. It supports the mechanism in general. It doesn't test this trade.

**Rule template.**

```text
Context (yes/no): 1) Level = prior {session/day} {high or low}, taken from {data source}
          2) Price traded beyond the level by at least {__} and at most {__}
          3) Time is between {__} and {__}
          4) Higher-timeframe filter: {rule, or "none"}
Trigger (yes/no): A {__}-minute bar closes back inside the level within {__} bars of the first trade beyond it
Entry:       {market on the reclaim close / limit at the level on a retest}
Stop:       {beyond the sweep extreme by {__}}
Target:      {prior-day midpoint / opposite side of the prior-day range / fixed R}
Time exit:     Flat by {__}
When not to trade: 1) Sweep happened inside a blackout window 2) Level already swept once today 3) {__}
```

**What kills it.**
- **Real breakouts.** On a trend day the level breaks, pulls back, "reclaims" for one bar and then goes. Every one of those is a full loss.
- **Hindsight.** On a finished chart, sweeps are easy to spot. Bar by bar, a sweep and a breakout look the same until the close. This brief is especially prone to look-ahead in manual testing.
- **Definition drift.** How far beyond is a sweep, and how fast must it come back? Loosen either after seeing results and the test is fitted.
- **News.** Many sweeps of the prior day's extremes happen on releases, where spreads and slippage are at their worst.

**What the Bear should attack.** In replay, was each decision made before the reclaim bar closed? How many "sweeps" in the sample were excluded as "obviously a breakout", and by what rule? Is the sample long enough to include trend weeks?

**Start it.**

```text
My idea, in my words: "When price trades through the prior day's {high/low}, then closes back inside within {__} bars, I trade back into yesterday's range."
Market and instrument: {…}
Session and time zone: {…}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {…}
```

## 3. Playbook · London-session breakout (currencies and gold)

**The idea.** The quiet hours before London set a range. A break of that range early in the London session is taken in the direction of the break.

**Why it might work.** London is the largest centre for currency trading. In the Bank for International Settlements' 2022 Triennial Central Bank Survey, the United Kingdom accounted for 38% of global foreign exchange turnover. The reasoning follows from that: the hours before London are thin, positions and orders build up, and when the largest pool of participants arrives, price can leave the overnight range with real volume behind it. That is a statement about where business is done. It is not a study of this trade, and there is no well-known academic test to cite for the retail version. It has been taught on trading forums for many years, which also means the range edges are among the most watched levels of the day.

**Rule template.**

```text
Context (yes/no): 1) Range = high and low between {__} and {__} (state the time zone, and how daylight saving is handled)
          2) Range width is between {__} and {__}
          3) No high-impact event on the event sheet before {__}
          4) Day-of-week filter: {rule, or "none"}
Trigger (yes/no): A {__}-minute bar closes beyond the range edge by {__}, between {__} and {__}
Entry:       {stop order at the edge / market on close / limit on retest}
Stop:       {opposite edge / midpoint / {__}}
Target:      {multiple of range width / fixed R / {__}}
Time exit:     Flat by {__} (before or after the New York open? decide and write it)
When not to trade: 1) Range wider than {__} 2) Rate-decision day for either currency 3) {__}
```

**What kills it.**
- **Spread.** Spreads on currencies and gold widen around session changes. A breakout entry pays that spread at its widest. Measure it on your account at that hour.
- **The fake first move.** A break one way, a reversal through the whole range, then the real move, is a well-known London pattern. A breakout brief takes the first loss in full.
- **Clock errors.** The range is defined by time. Daylight-saving changes move London relative to other zones twice a year, and a chart in the wrong zone silently tests a different range.
- **Broker differences.** Spot currency and gold prices differ between brokers. A break on one feed can be absent on another.

**What the Bear should attack.** Which hours define the range, and were they picked before looking? What is the measured spread at the entry time? Does the result depend on the weeks with central-bank news?

**Start it.**

```text
My idea, in my words: "The hours before London set a range on {pair or gold}. I trade a break of it early in the London session."
Market and instrument: {e.g. EURUSD / gold}
Session and time zone: {London open, London time}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {measure the spread at the open first}
```

## 4. Playbook · Trend following on higher timeframes

**The idea.** Markets that have been rising tend, on average and over months, to keep rising for a while, and the same for falling. Enter in the direction of an established move on daily or weekly bars, stay until the trend measure turns, and accept many small losses for occasional long runs.

**Why it might work.** This is the most studied idea in these two guides. The public reasoning is behavioural and structural: news is absorbed gradually, investors under-react and then pile in, and large participants move slowly. Tobias Moskowitz, Yao Hua Ooi and Lasse Pedersen documented the tendency across dozens of futures markets ("Time Series Momentum", *Journal of Financial Economics*, 2012), and Brian Hurst, Ooi and Pedersen extended the history back more than a century ("A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management*, 2017). The classic rule forms are a channel breakout, where you enter at a new multi-week high or low (Donchian channels, used in the Turtle rules described by Curtis Faith in *Way of the Turtle*, 2007), and a moving-average filter, where you hold only while price is above a long average (Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management*, 2007).

Read the small print on that evidence. The studies are on **portfolios of many markets**, on monthly horizons, with position sizing by volatility. A single instrument traded by one person is a very different thing: fewer trades, longer flat stretches, and results that hang on one or two trends a year.

**Rule template.**

```text
Context (yes/no): 1) Timeframe: {daily / weekly}
          2) Trend measure: {close above the highest high of the last {__} bars}
           or {close above the {__}-period moving average}
          3) Volatility measure for stop and size: {e.g. average true range over {__} bars}
Trigger (yes/no): The trend measure turns true on a bar close
Entry:       {next bar's open / stop order at the breakout level}
Stop:       {{__} × the volatility measure from entry / opposite channel of {__} bars}
Target:      None. Exit by rule only.
Exit rule:     {close below the lowest low of {__} bars / close below the moving average}
When not to trade: 1) Size rounds to zero with this stop 2) Position would be held through {events/weekends I don't allow} 3) {__}
```

**What kills it.**
- **Ranges.** In a sideways market every breakout fails. Long strings of small losses are the normal experience, and they can last many months.
- **One market.** The published evidence leans on diversification. On a single instrument the sample is tiny: a handful of trades a year.
- **Holding.** Positions are held overnight and over weekends. Many prop evaluations forbid that, and gaps can jump a stop.
- **Patience.** The brief only pays, if it pays at all, on the few trades that run. Exiting those early removes the whole point, and it is what most people do.

**What the Bear should attack.** How many trades will this produce in a year, and how many years until there are 30? Can the account sit through the losing run the test shows? Is holding overnight allowed on this account?

**Start it.**

```text
My idea, in my words: "On {daily/weekly} bars, I enter when price {closes at a new {__}-bar high or low / crosses its {__}-period average} and hold until the opposite rule triggers."
Market and instrument: {…}
Session and time zone: {daily bars, exchange time}
Timeframe I would trade it on: {daily / weekly}
What I can test with: {bar replay on daily bars, spreadsheet}
Rough round-trip cost per trade: {include overnight financing or roll costs if they apply}
```

## 5. Playbook · Mean reversion in ranges

**The idea.** When a market is moving sideways, moves towards the edges of the range tend to be given back. Fade the edges, target the middle.

**Why it might work.** In a range, by definition, neither side has been able to push price away. The reasoning is that at the edges the traders who would extend the move have already acted, and the ones taking profit or fading are next. Tools for measuring "stretched" are everywhere: bands set a number of standard deviations around a moving average are the best known, described by their author in John Bollinger's *Bollinger on Bollinger Bands* (2001). That book is a description of the tool. Its author is clear that a touch of a band is not, by itself, a reason to trade. The whole difficulty of this brief is in the first word of the idea: **when**. Knowing that a market is in a range, in advance and by rule, is the hard part. Fading an edge is easy.

**Rule template.**

```text
Context (yes/no): 1) Range definition: {price has stayed between {level} and {level} for {__} bars}
           or {Analyst regime is RANGING and {measurable rule}}
          2) Stretch measure: {distance from the {__}-period average of at least {__}} / {touch of a band at {__} deviations}
          3) No higher-timeframe level within {__} beyond the edge
Trigger (yes/no): A {__}-minute bar closes back inside {edge/band} after trading beyond it
Entry:       {market on close / limit at {__}}
Stop:       {beyond the stretch extreme by {__}}. Fixed at entry. Never widened.
Target:      {range midpoint / moving average / opposite edge}
Time exit:     Flat by {__}
When not to trade: 1) Range broken on a bar close earlier today 2) EVENT DAY 3) Range narrower than {__} (costs eat the target)
```

**What kills it.**
- **The day the range ends.** Many small gains, then one loss that takes several of them back. This is the shape of every fading strategy, and it is why best-day dependence has a mirror image here: check the total **without the worst day** as well, to see how much one break costs.
- **Adding to losers.** Fading invites averaging down. The template forbids widening the stop for that reason.
- **Costs against small targets.** The target is the middle of a range, which may be only a few times your round-trip cost.
- **Defining the range afterwards.** In hindsight every range is obvious.

**What the Bear should attack.** Is the range defined by a rule that could be applied live, at the time? What is the largest single loss in the sample compared with the typical gain? How many trades does a week of trending take back?

**Start it.**

```text
My idea, in my words: "When {market} has been in a range by {my rule}, I fade moves to the edge and target the middle."
Market and instrument: {…}
Session and time zone: {…}
Timeframe I would trade it on: {…}
What I can test with: {…}
Rough round-trip cost per trade: {…}
```

## 6. Worked example: the Bear on a brief

*Illustrative. A trader's draft brief for the London-session breakout on EURUSD. The choices are the trader's own and are not suggested settings.*

The trader pastes the filled brief into a fresh chat with the Bear prompt and the line: "Scenario under review: testing this brief on EURUSD. Attack the test design, not a trade."

**Bear:**
1. The range window in the brief is written in "broker time". The brief doesn't say which zone that is or what happens when clocks change. Two months of the test may be measuring a different hour. (Brief, context 1)
2. Cost per trade is entered as the trader's usual daytime spread. The entry is at the session change, when the brief's own "what kills it" list says spreads are widest. (Brief, cost line)
3. Falsifier 1 says "drop it if it doesn't work". That can't fail. (Brief, falsifiers)
- What would prove me wrong: the brief states the window in London time, a measured open spread, and a falsifier with a number and a sample.
- Confidence: High. All three are gaps in the document, not opinions about the market.

The trader fixes all three before logging a single row. Twenty minutes, and the test is now one that can fail for honest reasons.

## 7. Common mistakes

- **Choosing a brief because it suits last week.** Last week is one sample of one regime.
- **Testing a trend brief on intraday patience.** Trend following is measured in months. If you can't hold overnight, it isn't your brief.
- **Fading without a fixed stop.** One break pays for a lot of small wins.
- **Ignoring the clock.** Any brief defined by session times needs its time zone written down.
- **Collecting briefs.** Eight untested ideas are worth less than one tested one.

## 8. Checklist

- [ ] One brief chosen
- [ ] I know which kind of day hurts it, from the map
- [ ] Time zone written into every time-based rule
- [ ] Cost measured at the hour the brief trades
- [ ] Bear run on the test design; gaps fixed before the first row

## Try it (5 minutes)

Look at the map and find where your current setup sits: does it need the market to keep going, or to turn back? Write the answer, and the regime label that hurts it most, under your setup sheet in the rules file.

## Sources

Each was checked for title, authors and year. A source is a reason to test an idea, never evidence that it works for you.

- Carol L. Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance*, 2003.
- Bank for International Settlements, *Triennial Central Bank Survey: OTC foreign exchange turnover in April 2022*, 2022.
- Tobias J. Moskowitz, Yao Hua Ooi and Lasse Heje Pedersen, "Time Series Momentum", *Journal of Financial Economics*, 2012.
- Brian Hurst, Yao Hua Ooi and Lasse Heje Pedersen, "A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management*, 2017.
- Curtis Faith, *Way of the Turtle*, McGraw-Hill, 2007.
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation", *Journal of Wealth Management*, 2007.
- John Bollinger, *Bollinger on Bollinger Bands*, McGraw-Hill, 2001.

*Educational only. Not financial advice. Trading involves risk.*


---

# The team's tools: the stack by job

*Team kit · 12 minute read · 20 minutes to check your own kit*

**In one line:** the team needs nine jobs done, not nine subscriptions; for each job this guide says what the tool is for, what free and paid versions generally give you, what never to paste into it, and a two-minute setup step.

> **What's in this guide**
> - The stack by job: think, see, schedule, record, keep, enforce, capture, measure, test.
> - A minimum kit that costs nothing, and a comfortable kit.
> - A privacy line for every tool.
> - The limits of no-code strategy testers, stated plainly.

## 1. Choose by job, not by brand

![The team's tools, by job](/media/course/14-tools-stack.png)

Tools change their names, their plans and their features several times a year. Jobs don't. So this guide is organised by the job each tool does on the team. Where a product is named, it is an example that fits the job, not a recommendation, and there are no affiliate links anywhere in this library. Check each tool's own help pages for what it offers today.

| Job | Tool type | Examples | The team uses it for |
|---|---|---|---|
| **Think** | AI chat | Claude, ChatGPT, Gemini | Every seat and every prompt |
| **See** | Charting | TradingView, or your broker's platform | Screenshots, levels, alerts |
| **Schedule** | Economic calendar | A calendar site, plus the central banks' own pages | The rows the News agent reads |
| **Record** | Spreadsheet | Google Sheets, Excel, any table that exports CSV | Journal and test logs |
| **Keep** | Notes workspace | Notion, Apple Notes, Obsidian or any notes app | Rules file, sheets, memos, briefs |
| **Enforce** | Platform risk settings | Your trading platform or broker portal | The first line of defence |
| **Capture** | Screenshot tool | Built into your computer | Chart images, debrief evidence |
| **Measure** | Data export | Your charting platform's CSV export or data window | Exact levels, tagged (data) |
| **Test** *(optional)* | Bar replay, strategy tester | Built into many charting platforms | The evidence ladder, rungs 3 and 4 |

## 2. Think: the AI chat

**What it's for.** All of it: the agent team, the helpers and the research seats. One account is enough.

**What to look for,** by capability, since names change: it reads images. It lets you save standing instructions in a workspace (Guide 02). It accepts a file upload for the journal. It has a step-by-step reasoning mode for the Risk Manager and the Evidence Checker. Web browsing is optional and the team doesn't depend on it. Some tools can also run a saved prompt on a schedule.

**Free or paid.** Free tiers are fine for trying the prompts. They usually limit the number of messages, image uploads and access to the strongest models. The daily routine uses roughly a dozen messages and three or four images, so a paid plan is more comfortable. Look at your tool's current plan page.

**Never paste:** broker or prop-firm passwords, two-factor codes, API keys, full account numbers, ID documents. Crop account numbers out of screenshots. The team works in R, so your balance doesn't have to be there either.

**Two-minute setup.** Create one workspace called "Team". Paste the team setup prompt as its standing instructions. Open the data settings and decide, on purpose, whether your chats may be used to improve the provider's models.

## 3. See: charting

**What it's for.** The screenshots the Analyst and Researcher read, the levels you verify, and price alerts at your watch zones so you aren't staring at the screen.

**Free or paid.** Free charting is enough to run the team: you need clean charts, a few saved lines and a screenshot. Paid plans on most platforms add more alerts, more indicators per chart, more history on small timeframes, and data export. TradingView is the common example; many brokers' own platforms do the same job.

**Never paste:** nothing goes *into* a chart, but mind what's *on* it. Hide the account panel before you capture.

**Two-minute setup.** Save one layout called "Team" with your three timeframes, the price and time scales visible, prior-day high and low drawn, and no more than two indicators. Set the chart's time zone to the one in your rules file.

## 4. Schedule: the economic calendar

**What it's for.** The source of the rows you paste to the News agent each morning. The AI never supplies events from memory.

**Free or paid.** Free. Calendar sites list scheduled releases with times and an impact rating. For the events that matter most, the institutions publish their own dates, and those pages are the primary source: the Federal Reserve's meeting calendar, the European Central Bank's, the Bank of England's, and the statistics agencies' release schedules.

**Never paste:** nothing private is involved. The risk here is different: a calendar shown in the wrong time zone. Set the site's time zone once and write it in your rules file.

**Two-minute setup.** Pick one calendar. Set its time zone. Filter to your currencies. Each morning, select today's rows, copy them as text and paste them to the News agent.

## 5. Record: the spreadsheet

**What it's for.** The journal (Guide 08) and the test log for any playbook brief (Guide 11). Its other job is to be the place where sums are checked. A spreadsheet adds a column correctly every time. A language model usually does. When the Evidence Checker and the spreadsheet disagree, the spreadsheet is right.

**Free or paid.** Free. Any spreadsheet or table that keeps fixed columns and exports CSV will do.

**Never paste:** account numbers or login details in a notes column. If the sheet is shared, check who it's shared with.

**Two-minute setup.** New sheet. Paste the journal header row from Guide 16. Freeze the top row. Add a total under `result_r`, so there's always a figure to check the reviewer against.

## 6. Keep: the notes workspace

**What it's for.** One home for the things that must exist in exactly one live version: your rules file, risk sheet, prop sheet, playbook briefs, saved memos and weekly reviews. A notes app with tables (Notion, for example) holds all of it. Any notes app you already use works too. What matters is one copy, dated.

**Free or paid.** Varies by tool. The team needs only plain notes and a table.

**Never paste:** credentials of any kind. A rules file doesn't need your account number to work.

**Two-minute setup.** Create a folder or board called "Team". Add five notes: Rules file, Risk sheet, This week's change, Memos, Reviews. Put the date at the top of the first two.

## 7. Enforce: platform risk settings

**What it's for.** The first line of defence (Guide 07): limits that act whether or not you ask. Names differ by platform, so look for these functions in your platform's risk or account settings, or your broker's or firm's portal:

- A **daily loss limit**: positions closed and new orders refused once the day's loss reaches a number.
- A **maximum position size**.
- **Bracket orders** by default: every entry sent with a stop and a target attached. On many platforms the pair is linked as OCO (one cancels the other).
- A **trading-hours lock**, where offered.

**Free or paid.** Part of the platform or account you already have. Not every platform offers every limit. Write "not offered" in Part B of your risk sheet where one is missing.

**Never paste:** this is the one place your real credentials belong, and they stay there. No chat tool, browser extension or "assistant" needs your trading login. The execution agent connects through the broker or prop API with its own keys and hard limits.

**Two-minute setup.** Find the daily loss limit and set it to your daily stop. Save one bracket template with your stop and target attached and make it the default.

## 8. Capture and measure

**Capture: screenshots.** Your computer's built-in screenshot tool is all you need. Capture the chart area only, with both scales visible and the latest bar on the right. **Never capture** the account panel, order history with account numbers, or a browser tab bar showing other accounts. Two-minute setup: learn the shortcut for "capture a selected area" and set screenshots to save into one folder.

**Measure: exporting chart data.** For exact levels (prior day high, overnight low, the opening range) the team prefers numbers to image reads. Many charting platforms can export the bars on your chart as a CSV file. On TradingView, chart data export is a paid-plan feature at the time of writing. If your platform has no export, read the values from its data window and type them in. Either way they get the (data) tag. **Never paste** more than you need: a few dozen rows of open, high, low, close. Two-minute setup: export or copy yesterday's bars once, paste them into a chat and ask for the prior day's high, low and close, then check the three numbers against your chart.

## 9. Test (optional): bar replay and strategy testers

**What they're for.** Rungs 3 and 4 of the evidence ladder (Guide 11), without writing code.

**Bar replay** hides the future and reveals the chart one bar at a time, so you can apply a locked brief by hand and log each qualifying day. It is slow and it is honest, provided each call is made before the next bar is revealed. On most platforms, how far back you can replay small timeframes depends on your plan.

**A strategy tester** runs a scripted rule over history and prints a report. Using a ready-made script needs no coding. Treat the report as a rough first look and nothing more, because of what it usually leaves out:

- **Fills.** Orders are assumed filled at chart prices. Real spread and slippage are absent unless you enter them.
- **Costs.** Often zero by default. Set commission and slippage before you read any number.
- **History.** Limited on small timeframes, so the sample may cover only recent conditions.
- **Look-ahead.** Some scripts quietly use information from a bar before it has closed. The report gives no warning.
- **The settings panel.** Every input you nudge after seeing the report is a setting chosen after seeing results. Five minutes with the sliders can produce a result that means nothing.

A tester's report is a backtest export like any other. Paste its trade list into the Evidence Checker and read "what this does NOT prove".

**Never paste:** nothing private is involved. The risk is believing the report.

**Two-minute setup.** Open bar replay on your instrument, go back one month, and step through a single session with your setup sheet in front of you, saying "trade" or "no trade" before each reveal.

## 10. Minimum kit and comfortable kit

| Job | Minimum kit (free) | Comfortable kit |
|---|---|---|
| Think | One AI chat on a free tier, team setup pasted as the first message if there is no workspace | A paid plan: saved workspace, more images, a reasoning mode, file upload |
| See | Free charting, one saved layout | A paid charting plan: more alerts, more intraday history |
| Schedule | One free calendar site plus the central banks' own pages | The same |
| Record | A free spreadsheet | The same, with the journal as a table in your workspace |
| Keep | Any notes app | One workspace holding sheets, memos and briefs together |
| Enforce | Whatever limits your platform offers | The same. This is never optional |
| Capture | Built-in screenshot tool | The same |
| Measure | Values typed from the data window | CSV export from your charting platform |
| Test | Bar replay on daily bars, or forward demo only | Intraday bar replay, a strategy tester with costs set |

The minimum kit runs the whole team. The comfortable kit saves typing. Neither changes what the team can and can't do.

## 11. Worked example: a kit check

*Illustrative.*

A trader goes down the nine jobs with what they already have.

- **Think:** a paid AI chat plan, already in use. Workspace created on Guide 02. Data setting checked.
- **See:** free charting. Layout saved. One gap: the chart was in exchange time and the rules file says New York. Fixed.
- **Schedule:** two calendar sites open in different tabs, in different time zones. Kept one, set its zone.
- **Record:** journal sheet exists. No total under `result_r`. Added.
- **Keep:** rules file in three places (a note, a document, an old chat). Two deleted.
- **Enforce:** daily loss limit found and set. Trading-hours lock not offered. Written in Part B.
- **Capture:** screenshots were landing on the desktop with the account panel visible. Now a selected-area capture into a "Team" folder.
- **Measure:** no export on the free plan. Values typed from the data window.
- **Test:** bar replay available on daily bars only. Rung 3 of any intraday brief will be forward demo.

Twenty minutes. Nothing bought. Three real problems found: a time zone, three copies of the rules, an account number in every screenshot.

## 12. Official pages

Checked when this guide was written. These are the makers' own pages, with no affiliate links. If a link has moved, search for the tool's name and "help".

- Claude: https://claude.com/ · help: https://support.claude.com/
- Gemini: https://gemini.google.com/ · help: https://support.google.com/gemini/
- ChatGPT: from OpenAI's website or app.
- TradingView: https://www.tradingview.com/ · plans: https://www.tradingview.com/pricing/
- TradingView bar replay help: https://www.tradingview.com/support/solutions/43000712747-bar-replay-how-and-why-to-test-a-strategy-in-the-past/
- TradingView strategy report help: https://www.tradingview.com/support/solutions/43000764138-tradingview-strategy-report-how-to-start/
- TradingView on exporting chart data: https://www.tradingview.com/blog/en/export-chart-data-in-csv-14395/
- Economic calendars: https://www.tradingview.com/economic-calendar/ · https://www.fxstreet.com/economic-calendar
- Federal Reserve meeting calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- European Central Bank calendar: https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
- Bank of England meeting dates: https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
- US Bureau of Economic Analysis release schedule: https://www.bea.gov/news/schedule
- Google Sheets: https://workspace.google.com/products/sheets/

## 13. Common mistakes

- **Buying tools to feel ready.** The minimum kit runs the team. Upgrade a job only when it's the thing slowing you down.
- **Two calendars, two time zones.** One calendar, one zone, written in the rules file.
- **Letting a chat tool or extension connect to your trading account.** Only the execution agent connects, through the broker or prop API, inside hard limits.
- **Trusting a strategy tester's first report.** Costs off, settings tuned, history short.
- **Account details in screenshots.** Capture the chart area only.

## 14. Checklist

- [ ] Each of the nine jobs has one tool, or is marked "not needed yet"
- [ ] AI data setting chosen on purpose
- [ ] Chart layout saved; chart time zone matches my rules file
- [ ] One calendar, time zone set
- [ ] Journal sheet has a total I can check the reviewer against
- [ ] One live copy of the rules file and risk sheet
- [ ] Platform limits set, or "not offered" written in Part B
- [ ] Screenshots show no account details

## Try it (5 minutes)

Take one screenshot the way you normally would and look at it as a stranger would. If it shows an account number, a balance or a name, change how you capture before you upload another one.

*Educational only. Not financial advice. Trading involves risk.*


---

# Team kit: the prompt pack

*Team kit · Reference · keep open while the system runs*

**In one line:** every ready-made prompt in the library, in one place, grouped by when you use it, with which chat it runs in, what you paste and what you get back.

> **What's in this guide**
> - The prompt map: five groups, from standing instructions to the research team.
> - A "which prompt when" table for the moments that actually come up.
> - The eight things every prompt in the pack has, so you can adapt one without breaking it.
> - The full text of all 23 prompts, with filled examples and red flags.

## 1. The map

![The prompt map: five groups, four daily chats and a research chat](/media/course/15-prompt-map.png)

Prompts are named by seat, not numbered, because that's how you'll reach for them: "the trade check", "the pre-mortem". Letters are the four daily chats from Guide 02: **A** team, **B** Bull, **C** Bear, **D** Risk. **R** is the separate research chat.

| Group | Prompt | Chat | You paste | You get | Guide |
|---|---|---|---|---|---|
| **Standing** | Team setup | Workspace | Rules file + risk sheet | House rules, seats, rubric, facts | 02 |
| **Before the session** | News agent | A | Today's calendar rows | Event sheet, blackout windows | 03 |
| | Analyst | A | Screenshots, event sheet | Market brief, regime label | 03 |
| | Researcher · setup sheet | A | Your setup in your words | Yes/no rule sheet (once per setup) | 03 |
| | Researcher · setup watch | A | Brief, current chart | PASS / FAIL / CAN'T TELL, zones | 03 |
| | Bull (+ round 2) | B, fresh | The packet | Case for, best point against itself | 04 |
| | Bear (+ round 2) | C, fresh | The same packet | Case against, what proves it wrong | 04 |
| | Risk Manager · day check | D, fresh | Account state, event sheet, tilt result | TEAM ON/CLOSED, budget | 05 |
| | Prop mode | D | Firm sheet, account state | Floor, room, size band | 09 |
| | Trader | A | Watch, scenario, budget | Conditional trade card | 05 |
| | Pre-mortem | C | The trade card | Three ways it fails, each with a tell | 04 |
| | Decider | A | Whole packet | Memo, score, TAKE or PASS verdict | 05 |
| | Fast team | One chat | Screenshots, calendar, state | Every seat in one reply (weaker) | 06 |
| **In session** | Tilt check | D | Six yes/no answers | GREEN / AMBER / TEAM OFF | 07 |
| | In-session check | D | Card, state now | CLEAR / BLOCK | 06 |
| | Risk Manager · trade check | D | Card, state now | CLEAR / BLOCK, arithmetic shown | 07 |
| **After the close** | Debrief | A | Card, fills, memo line 9 | MATCH / DEVIATION, journal fields | 08 |
| | Weekly Reviewer | Fresh | Week's rows, last memo | The rule you break most, one change | 08 |
| | Monthly team review | Fresh | Month's rows, four memos | Each rule: keep, enforce or question | 08 |
| **Research team** | Strategy Scout | R | A vague idea | Hypothesis, blanks, falsifiers | 11 |
| | Evidence Checker | R | Your rows | Sample, costs, best-day test, what it doesn't prove | 11 |

## 2. Which prompt when

| The moment | Reach for | Then |
|---|---|---|
| First day, new workspace | Team setup | Type `FACTS` in a second chat and compare |
| Twenty minutes before the session | News agent, then the six steps of the routine | Line 9 verdict set before the session starts |
| Five minutes before the session, running late | Fast team | Keep the in-session check in its own chat D |
| You've changed how you describe your setup | Researcher · setup sheet | Replace the old sheet in the rules file, dated |
| The card is written and you feel sure about it | Pre-mortem | Copy the uncovered tells to memo line 8 |
| A trigger prints | In-session check | CLEAR: the execution agent places it as written. BLOCK: no order |
| You've just taken a loss | Tilt check | TEAM OFF means closed for the session |
| You want to argue with a BLOCK | Nothing. Write it in the journal notes | Bring it to the weekly review |
| The session has ended | Debrief, every card | Copy the journal fields into the row |
| Last session of the week | Weekly Reviewer | Check two counts by hand. One change |
| Fourth weekly review done | Monthly team review | At most one rule retired, one tightened |
| "I wonder if this idea works" | Strategy Scout, on a non-trading day | Fill the playbook brief, lock it |
| You have 30 or more rows on fixed rules | Evidence Checker | Check two sums. Read "what this does NOT prove" |
| Evaluation or funded account | Prop mode before the day check | Size from the band, not the balance |

## 3. What every prompt in the pack has

Each prompt was written against the same eight-point list. If you adapt one, keep all eight.

1. **An explicit role.** The first line names the seat.
2. **Inputs with placeholders.** Everything in {braces} is yours to fill. If a brace is empty, the seat is told to treat it as missing, not to guess.
3. **A "you may not" block.** What the seat is forbidden to do. This is where the lanes are drawn.
4. **A fixed output format.** Same sections, same order, so days can be compared.
5. **An unknown rule.** UNKNOWN, CAN'T TELL, CAN'T READ or (unverified), instead of a confident guess.
6. **No flattery.** No praise for you or the plan. A finding isn't softened because you seem keen.
7. **No inventing.** No level, event, number or source that you didn't supply.
8. **A self-check line.** "Before you send…" The seat rereads its own reply against the format and the arithmetic.

No prompt makes a model reliable on its own. The eight points narrow the ways it can go wrong, and the red-flag boxes tell you what to look for when it does anyway.

## 4. Adapting prompts without breaking them

- **Change the inputs, keep the format.** Your instrument, session and timeframes go in the braces. The output sections stay.
- **One change at a time,** dated. If a seat gets worse, you'll know why.
- **Never remove a "you may not" line or the self-check.** They look like padding. They are the prompt.
- **Keep a version line** at the top of your own copy ("Analyst v3, changed timeframes").
- **Any chat tool.** The prompts are plain text. If a tool keeps breaking the format, add: "Reply in exactly the format above, nothing before it, nothing after it."

## 5. Worked example: adapting the Analyst for EURUSD

*Illustrative.*

The prompt stays the same. Only the braces change:

```text
Instrument: EURUSD
Session I trade: London, 08:00–11:00 London time
Today: (example date)
Attached screenshots: image 1 = Daily, image 2 = 4H, image 3 = 1H, latest bar on the right
Exact levels from my data: prior day high 1.0872, low 1.0831, close 1.0858 (example)
Today's event sheet: (example) 09:00 EUR survey, High, INSIDE, blackout 08:50–09:10 · 13:30 USD claims, Medium, OUTSIDE
```

Because 13:30 is outside the London window, the brief should carry only the 09:00 event into section 3. If it lists both as inside, the time zones are mixed up: check the conversion line on the event sheet.

## 6. Common mistakes

- **Editing the output format** "to make it shorter". You lose comparability across days.
- **Stacking several prompts in one message.** One seat per message.
- **Keeping old versions of a prompt in the team setup.** One live version only.
- **Deleting the "you may not" block to save space.** The seat's lane goes with it.

## 7. Checklist

- [ ] All prompts saved in my own notes, with a version line
- [ ] Braces filled for my instrument, session and timeframes
- [ ] "You may not" blocks and self-check lines untouched
- [ ] I know which chat each prompt runs in

## Try it (5 minutes)

Copy four prompts into a note called "Team prompts", with your instrument and session already filled in: News agent, Researcher · setup watch, Tilt check and In-session check. Those four run most often.

## 8. The full prompts

**Group · Standing**

---

### Team setup — the standing instructions every seat reads

**Job:** hold the house rules, the seat list, the scoring rubric, your rules file and your risk sheet in one place, so every seat in every chat works from the same facts.

**Where it goes:** the saved instructions of your team workspace (most chat tools call this a project or custom instructions). If your tool has no saved instructions, paste it as the first message of every chat.

**Give it:** your rules file and your risk rules sheet (both on Guide 16), pasted where the braces are.

**Covered in:** Guide 02. Every other prompt in the pack assumes it is in place.

```text
TEAM SETUP — read before every reply

You are one seat on my trading team. I set the rules and the risk limits. You never place orders yourself; execution is handled by the execution agent after the risk gate. You work in the seat I name at the start of a chat ("Role: Analyst", "Role: Bear", and so on). If no role is given, ask which one and do nothing else.

HOUSE RULES
1. Evidence only. Use only what is in this chat: the facts below, my screenshots, my pasted data and my notes. If you need something I did not give you, write UNKNOWN and name what you need.
2. No invented numbers. Every price or level must come from my screenshot or my data, with its source: (chart) if read off an image, (data) if taken from numbers I pasted. Chart reads are approximate and I verify them.
3. No invented news. Never mention an event, release, headline or time unless I pasted it, or you browsed for it and give the source and time for each item.
4. Confidence in words: Low, Medium or High. Never a percentage chance, a success rate or a predicted price.
5. Unverified is a label, not a failure. If a statement rests on your general knowledge instead of my evidence, mark it (unverified). "Can't tell from this" is a good answer. A confident guess is a bad one.
6. No flattery. Do not praise me, my plan or my setup. Do not soften a finding because I seem keen. If I push back without new evidence, repeat the finding in the same words.
7. Stay in your seat. Keep to your role's job and its output format. Short lines. Plain English. No hype, no emojis.
8. Rules first. If anything I ask would break my rules file or my risk sheet, say so in the first line of your reply.
9. No memory claims. Do not refer to earlier sessions unless I pasted them into this chat.
10. Self-check. Before you send any reply, check it against rules 1 to 6 and against the format I asked for. Fix what fails, or say which part you could not complete.

THE SEATS (one job each)
- News agent: turns the calendar I paste into today's event sheet. Never adds events.
- Analyst: describes the market. Never suggests trades.
- Researcher: turns my setup into yes/no rules and checks today's chart against them. Never adds rules I did not say.
- Bull: best honest case for the plan. Bear: best honest case against. Evidence from the packet only.
- Risk Manager: applies my risk sheet to my account state. Never judges the setup. Never lifts a BLOCK.
- Trader: writes the trade card. Size is only ever rounded down.
- Decider: writes the memo, scores it from the rubric and gives a TAKE or PASS verdict. Never overrides the risk gate.
- Strategy Scout and Evidence Checker: research seats. They describe what a test would need and what my own rows show. They never say a strategy works.

SCORING RUBRIC (Decider and Fast team; the lowest line that applies wins)
1 = Any context rule FAIL, any no-trade condition met, the Risk Manager says CLOSED, or the card is outside the risk budget.
2 = Rules pass, but two or more context rules are CAN'T TELL, or the Bear has an unanswered point about event risk or location.
3 = Rules pass, at most one CAN'T TELL, the Bear's best point is partly answered.
4 = All context rules PASS, the regime fits the setup, the Bear's points are answered with evidence, the card is inside budget.
5 = Everything in 4, plus the watch zone sits at a level named in the Analyst brief, and there is no scheduled event inside the card's valid window.

FACTS CHECK
If I write only the word FACTS, reply with one screen: instrument(s) and value per point or pip, session window and time zone, 1R, daily stop, max trades per day, news blackout rule, and the "last updated" dates of both sheets. Mark anything missing as MISSING.

MY RULES FILE
{paste your rules file here}

MY RISK RULES SHEET
{paste your risk rules sheet here}
```

#### Filled example: the FACTS check

*Illustrative values.* Type `FACTS` as the first message of any new chat in the workspace. Every chat should give the same answer.

```text
FACTS
- Instrument: MNQ, 2 per point per contract (example). ES chart for context only.
- Session: 09:45–11:30 New York. Chart time zone: New York.
- 1R: 200 (example). Daily stop: 2R. Max trades per day: 3.
- News blackout: no entries from 10 minutes before to 10 minutes after any high-impact event on my calendar.
- Rules file last updated: (example date). Risk sheet last updated: (example date).
- MISSING: none.
```

**Why the main rules exist**
- Rules 2 and 3 stop the two most common failures: levels that are not on your chart and news that did not happen.
- Rule 4 stops false precision. A percentage from a language model is a figure of speech, not a measurement.
- Rule 6 is there because chat assistants lean towards agreeing with the person typing. On a team, that is a defect.
- Rule 10 costs one line and catches the reply that drifted out of format.

**Red flags**
- Two chats giving different FACTS answers. One of them is reading an old copy. Keep one live version of each sheet.
- A reply that opens with praise ("Great setup"). Rule 6 has slipped. Start a fresh chat.
- A seat answering without being given a role. Paste the setup again and name the role.

**Group · Before the session**

---

### News agent — today's event sheet, from the calendar you paste

**Job:** turn the economic calendar you paste into a one-screen event sheet: what is scheduled, when, in your time zone, and the blackout windows your own news rule creates. It works only from what you paste. It never recalls events from memory.

**Chat:** chat A, before the Analyst, during the five platform minutes. Paste the finished sheet to the Analyst (chat A) and to the Risk Manager's day check (chat D), so both read the same events.

**Give it:** today's calendar rows copied as text from the calendar you use, the time zone the calendar shows, your session window and your news rule from the risk sheet.

**Covered in:** Guide 03 and the daily routine (Guide 06).

```text
Role: News agent.

Build today's EVENT SHEET from the calendar text below and nothing else.

Inputs:
- Today: {date, weekday}
- Calendar I use: {name of the calendar}
- Time zone shown on the calendar: {e.g. New York / London / UTC}
- My time zone for the team: {e.g. New York}
- My session window: {e.g. 09:45–11:30 New York}
- Currencies or markets I care about: {e.g. USD for MNQ; EUR and USD for EURUSD}
- My news rule: {e.g. no entries from 10 minutes before to 10 minutes after any high-impact event; no new trades on rate-decision days}

Calendar text (pasted by me, unedited):
{paste the rows for today}

You may not:
- Add, rename or "correct" any event from memory. If an event is not in the pasted text, it does not exist for this sheet.
- Guess an impact level or a time. If either is missing in the text, write UNKNOWN.
- Forecast the number, the reaction or the direction. No comment on what the event means for price.

Reply in exactly this format:
EVENT SHEET — {date} — times in {my time zone}
1. Events, in time order: time · currency/market · event name as pasted · impact as pasted · INSIDE or OUTSIDE my session window.
2. Blackout windows from my news rule: start–end for each event the rule covers, and the event it comes from. Show the arithmetic (event time minus and plus my minutes).
3. Whole-day rules triggered: any "no trading today" line in my news rule that an event sets off, or "none".
4. Time-zone conversions made: from {calendar zone} to {my zone}, hours added or subtracted. If the two zones are the same, write "none".
5. Could not read: rows that were cut off, duplicated or unclear, quoted as pasted.
6. Count check: "{n} rows pasted, {n} events listed."

If the pasted text is empty, reply only: "No calendar pasted. I can't build an event sheet from memory."
Before you send: confirm every event in section 1 appears word for word in the pasted text, and that the count in section 6 matches.
```

#### Filled example

*Illustrative. An invented calendar for an example day. Not a real schedule.*

**Pasted:** `08:30 USD Example Jobs Report High` · `10:00 USD Example Services Survey High` · `10:30 USD Example Inventories Low` · `14:00 USD Example Policy Minutes Medium`. Calendar and team both in New York time. Session 09:45–11:30. News rule: ±10 minutes around high-impact events.

```text
EVENT SHEET — example day — times in New York
1. 08:30 · USD · Example Jobs Report · High · OUTSIDE
  10:00 · USD · Example Services Survey · High · INSIDE
  10:30 · USD · Example Inventories · Low · INSIDE
  14:00 · USD · Example Policy Minutes · Medium · OUTSIDE
2. Blackout: 09:50–10:10 (10:00 − 10 min, 10:00 + 10 min) from Example Services Survey.
  08:30 event: 08:20–08:40, ends before the session window opens.
3. Whole-day rules triggered: none.
4. Time-zone conversions made: none.
5. Could not read: none.
6. Count check: 4 rows pasted, 4 events listed.
```

**Red flags**
- An event you did not paste. That is the model remembering a typical month, not reading your calendar. Delete the sheet and rerun in a fresh chat.
- A time that moved by an hour. Time-zone and daylight-saving conversions are where this seat goes wrong. Check section 4 against the calendar yourself.
- Any sentence about what the number "should" do to price. Out of lane.
- The count check not matching. Something was dropped or merged.

---

### Analyst — the market brief

**Job:** describe today's market for your instrument in the same six sections every day. No opinion on your trade.

**Chat:** chat A ("Team — {date}"), inside your team workspace. The Researcher follows in the same chat.

**Give it:** 2–3 screenshots, higher timeframe first (for example 4H, 1H, 15m for NQ; Daily, 4H, 1H for EURUSD), and today's event sheet from the News agent. Optional: exact levels from exported data, and up to five headlines you pasted yourself.

**Covered in:** Guide 03. Step 1 of the daily routine (Guide 06).

```text
Role: Analyst.

Inputs:
- Instrument: {NQ / MNQ / EURUSD / ...}
- Session I trade: {e.g. New York, 09:45–11:30 ET}
- Today: {date, weekday}
- Attached screenshots: {e.g. "image 1 = 4H, image 2 = 1H, image 3 = 15m, latest bar on the right"}
- Exact levels from my data (optional): {e.g. prior day high / low / close, overnight high / low, or "none"}
- Today's event sheet (from the News agent, pasted by me): {paste, or "none pasted"}
- Headlines (optional, pasted by me): {paste, or "none"}

You may not:
- Suggest a trade, an entry, a direction to favour or a bias stronger than the evidence.
- Write any price that is not on my screenshots or in my data. Tag every price (chart) or (data).
- Mention any event or headline I did not paste.

Write the MARKET BRIEF in exactly this format:
1. Structure, higher to lower timeframe: one line each (up / down / sideways, last swing high and last swing low as prices).
2. Key levels: up to 5. Price, source tag, and what it is (prior day high, overnight low, range edge...).
3. Scheduled events: copy the INSIDE-window events and blackout windows from my event sheet. If none pasted, write "none pasted".
4. Regime label, one of: TRENDING, RANGING, QUIET, EVENT DAY. One sentence why, citing sections 1–3.
5. What would change this read: one observable event.
6. Unknowns: everything you could not read from the images, and any timeframe that disagrees with another.

If an image is too small or blurred to read a price, write CAN'T READ for that line. Do not estimate.
Before you send: check that every price has a tag, that section 3 contains nothing I did not paste, and that no line tells me what to do.
```

**Good output looks like:** six numbered sections, every price tagged, one regime word, and an honest "Unknowns" line.

**Red flags**
- A level with no source tag, or one you cannot find on your own chart.
- An event you did not paste. That is invented news. Delete it and rerun.
- "Bullish bias, high probability." The Analyst describes. It does not forecast.
- Tick-precise prices from a small screenshot. Image reads are approximate.
- An empty "Unknowns" line every day. No screenshot shows everything.

---

### Researcher — your setup as rules you can check

**Job:** two jobs. Once: rewrite your setup as yes/no rules a stranger could check on a chart (the **setup sheet**). Every day: check today's chart against those rules and mark where the setup could form (the **setup watch**).

**Chat:** chat A, right after the Analyst brief, so it can read the brief.

**Covered in:** Guide 03. Step 2 of the daily routine (Guide 06).

#### Researcher · setup sheet (once per setup)

```text
Role: Researcher. Job: SETUP SHEET.

Here is my setup in my own words:
"{describe the setup the way you would explain it to a friend}"

You may not:
- Add a condition, filter, indicator or number I did not say. If the sheet needs one, ask.
- Say whether the setup is good, or whether it works. Your job is wording, not judgement.
- Fill a gap with an assumption. A gap becomes a question.

Reply in exactly this format:
SETUP SHEET (draft {n})
- Name: a short, fixed name for my journal.
- Context rules: what must be true before the setup can exist (timeframe, session, structure).
- Trigger rule: the exact event that makes it a trade.
- Entry: where, and with which order type.
- Invalidation (stop): where the idea is wrong, as a rule I can point to on the chart.
- Target: where I take profit, as a rule.
- Time exit: when I close it if neither stop nor target is hit, or "none stated".
- No-trade conditions: when I skip even if everything else passes.

VAGUE WORDS: every judgement word in my description ("strong", "clean", "looks like", "big"), each with two measurable replacements for me to choose between. Do not choose for me.
QUESTIONS: up to 3 things you need from me before the sheet is complete.
TRACE: next to each rule, quote the words of mine it came from. A rule with no quote is yours, not mine. Delete it.

Every rule must be a yes/no question I can answer by looking at a chart or a clock.
Before you send: reread each rule. If two traders could disagree about the answer on the same chart, it is still vague. List it under VAGUE WORDS.
```

#### Researcher · setup watch (daily)

```text
Role: Researcher. Job: SETUP WATCH.

Inputs:
- My SETUP SHEET (in the team setup, or pasted here): {paste if needed}
- The Analyst brief above in this chat.
- Attached: {current chart screenshot(s), timeframe labelled}
- Exact levels from my data (optional): {paste, or "none"}

You may not:
- Upgrade a CAN'T TELL to PASS, or soften a FAIL.
- Propose a watch zone at a price that is not on my chart or in my data.
- Comment on whether today "looks good".

Reply in exactly this format:
SETUP WATCH — {setup name} — {date}
0. First line: "SETUP POSSIBLE" or "NO SETUP TODAY: {the no-trade condition met}".
1. Rule check: each context rule with PASS, FAIL or CAN'T TELL, and the evidence (a price with its tag, or a time).
2. Watch zones: up to 2 places the trigger could happen today, each with the price area (tagged) and the trigger rule it needs.
3. No-trade conditions: each one, MET or NOT MET, with evidence.
4. What I must see live: the trigger as one sentence I can watch for.

If more than one context rule is CAN'T TELL, say the chart is not good enough to check and ask for a specific better screenshot or data.
Before you send: check that every PASS has evidence next to it and every price has a tag.
```

**Red flags**
- Rules that still contain judgement words after the rewrite.
- A rule with no quote in TRACE. The Researcher added it. Every rule traces back to your words or your answers.
- The Researcher choosing the measurable replacement for you. Those numbers are your decision, and the place to test them is the playbook method on Guide 11.
- A PASS with no evidence next to it.
- Watch zones at prices that are not on your chart.

---

### Bull — the best honest case for the plan

**Job:** argue for taking the plan, using only the evidence in the packet. A lawyer for the trade, not a cheerleader.

**Chat:** a fresh chat B. It gets the packet, not your feelings. Do not tell it which side you hope wins.

**Give it:** the packet = Analyst brief + setup watch + one scenario line. Nothing else.

**Covered in:** Guide 04. Step 3 of the daily routine (Guide 06).

```text
Role: Bull.

Below is today's packet: the Analyst brief, the setup watch and the scenario under review.
Make the best HONEST case for taking this scenario today.

You may not:
- Use anything that is not in the packet. No outside knowledge of this market, no "typically", no "institutions".
- Predict a price, give a percentage, or use the words "obvious", "can't lose" or "high probability".
- Praise the plan. Adjectives about quality are not evidence.

Reply in exactly this format:
BULL CASE — {setup name} — {date}
1–3. Up to 3 reasons, strongest first. Each ends with the packet section it rests on (Brief 2, Watch 1...).
What must happen next for this case to hold: one or two observable events.
The strongest point against my case: you must name one, with its packet section.
Confidence: Low, Medium or High, and one sentence why.

If the packet supports fewer than 3 reasons, give fewer. Do not pad.
If two or more context rules are CAN'T TELL, confidence cannot be High.
Before you send: check that every reason cites a packet section and that "strongest point against" is filled.

PACKET
{paste Analyst brief}
{paste setup watch}
Scenario under review: {e.g. "Long from watch zone 1 if the trigger rule prints between 09:45 and 11:00 ET"}
```

#### Bull · round 2 (optional, one minute)

```text
Role: Bull, round 2.
Here is the Bear's case. Reply in at most 5 lines.
- Concede every point that is correct. Say "conceded".
- Answer only the points you can answer with evidence from the packet, citing the section.
- Do not introduce new reasons. Do not repeat round 1.
{paste Bear case}
```

**Red flags**
- Reasons that are not in the packet ("institutions are buying", "momentum is building").
- No "strongest point against". A Bull that can't name one is agreeing with you.
- Confidence High while two or more context rules are CAN'T TELL.
- A third reason that restates the first in different words. That is padding.

---

### Bear — why this plan fails or should wait

**Job:** find every honest reason the plan fails or should wait. The Bear runs every time, especially when you are keen.

**Chat:** a fresh chat C. The same packet as the Bull, given separately, so neither anchors on the other in round 1.

**Give it:** the packet = Analyst brief + setup watch + the same scenario line. Nothing else.

**Covered in:** Guide 04. Step 3 of the daily routine (Guide 06).

```text
Role: Bear.

Below is today's packet: the Analyst brief, the setup watch and the scenario under review.
Make the strongest HONEST case against taking this scenario today.

Check, in this order:
1. Rule failures: any context rule marked FAIL or CAN'T TELL, and any no-trade condition close to being met.
2. Location: is the watch zone in the middle of a range, into a higher-timeframe level, or far from invalidation?
3. Event risk: any scheduled event or blackout window inside or near the trade window.
4. Regime mismatch: does the regime label fit the kind of setup this is?
5. The "wait" option: what would a better version of this plan look like, and what does waiting cost?

You may not:
- Use anything that is not in the packet. "The market could crash" is not a point.
- Invent a level, an event or a statistic to strengthen your case.
- Soften a point to be agreeable, or pad the list to look thorough.

Reply in exactly this format:
BEAR CASE — {setup name} — {date}
1–4. Up to 4 points, strongest first. Each ends with the packet section it rests on.
What would prove me wrong: one observable event.
Confidence: Low, Medium or High, and one sentence why.

If the packet gives you fewer than 4 honest points, give fewer. If it gives you none, write "No point against found in the packet" and list what evidence is missing that would let you check.
Before you send: check that every point cites a packet section and none is generic.

PACKET
{paste Analyst brief}
{paste setup watch}
Scenario under review: {the same line you gave the Bull}
```

#### Bear · round 2 (optional, one minute)

```text
Role: Bear, round 2.
Here is the Bull's case. Reply in at most 5 lines.
- Concede every point that is correct. Say "conceded".
- Say which of your round-1 points still stand, and why, citing the packet section.
- Do not introduce new points. Do not repeat round 1.
{paste Bull case}
```

**Red flags**
- Generic fear ("markets are uncertain") instead of specific, checkable points.
- A Bear that finds nothing, day after day. Run the Pre-mortem prompt on the trade card. It forces the question from the other end.
- A Bear that invents an event or a level to win the argument.
- A Bear that folds completely in round 2 without new evidence. It is being agreeable. Read round 1.

---

### Risk Manager — the seat that says no

**Job:** apply your written risk rules. It does not judge the setup. It answers one question: given my rules and my account today, is this allowed?

**Chat:** its own fresh chat D. It never sees the Bull, the Bear or your reasons. A risk manager that hears the story can be talked round.

**Remember:** this is your **second** line. Your first line is the hard limits set inside your trading platform (Guide 07).

**Covered in:** Guide 05 (day check) and Guide 07 (trade check). Step 4 of the daily routine and the in-session check (Guide 06).

#### Risk Manager · day check (before the session)

```text
Role: Risk Manager. Mode: DAY CHECK.

Use only my RISK RULES SHEET (in the team setup, or pasted below) and today's account state.

Today's account state:
- Account type: {personal / prop evaluation / prop funded}
- Balance at start of day: {example: 50,000}
- Loss so far today: {0}
- Trades taken today: {0}
- Losing trades in a row (today and carried from yesterday): {0}
- Open positions: {none}
- Today's event sheet (from the News agent, pasted): {paste, or "none pasted"}
- Tilt check result: {GREEN / AMBER / TEAM OFF, or my state 1–5}

You may not:
- Comment on any setup, market or trade idea.
- Round a number in my favour, or treat "close to the limit" as inside it.
- Assume a missing value. A rule with a missing input is FAIL.

Reply in exactly this format:
TEAM: OPEN or CLOSED
- One line per rule in my sheet: rule · my number · today's value · OK or FAIL. Show the sum where there is one.
- Risk budget per trade today: maximum loss in money and in R, after my state rule.
- Trades left today: number.
- Blackout windows today: times, copied from the event sheet. If no event sheet was pasted, the news rule is FAIL.
- If CLOSED: the rule that closed it. Nothing else.

Before you send: recompute every sum once. Then check that no line contains an opinion.
```

#### Risk Manager · trade check (on a trade card, before the order is sent)

```text
Role: Risk Manager. Mode: TRADE CHECK.

Use only my RISK RULES SHEET and the trade card below. Do not comment on whether the setup is good.

Account state now: loss today {x}, trades taken {n}, losing streak {k}, open positions {none}, time now {hh:mm and time zone}.

Trade card:
{paste trade card}

Check, one line each, OK or FAIL, with the arithmetic written out:
1. Risk on this trade is at or below my per-trade maximum: stop distance × value per point × size = {risk}.
2. Loss today plus this trade's risk is at or below my daily stop.
3. Trades taken is below my daily maximum.
4. Losing streak is below my stop-after-losses number.
5. Time now is inside my session window and outside every blackout window.
6. The card has a stop price, and the order is a bracket (stop and target attached).
7. Size is at or below my maximum contracts or lots.
8. Any extra rule in my sheet.

First line of your reply: CLEAR or BLOCK.
If BLOCK: list the failed rule numbers. Do not suggest a way round them, a smaller size or a different stop.
If CLEAR: finish with "Cleared under the rules. Passed to the execution agent."

A missing value is a FAIL. Exactly at a limit is OK. Above it by any amount is FAIL.
If I argue with a BLOCK, restate the rule and the number, in the same words, and nothing else. A BLOCK is not lifted in the same session. The rules sheet changes at the weekend, never mid-session.
Before you send: redo the sum in check 1 and check 2. If either differs from the card's own maths, say so and BLOCK.
```

**Red flags**
- Any CLEAR where the size maths does not match the card's own calculation. The check must recompute it, every card.
- Softening language: "slightly over, probably fine". There is no slightly over.
- Comments on the setup ("great setup though"). Out of lane, and a sign the chat has seen the story.
- A helpful suggestion after a BLOCK ("you could take 3 contracts instead"). The card is blocked. A different card is a new card, written before a session, not during one.
- A BLOCK that turns into CLEAR after you push back. If that happens, the rule belongs in your platform settings, not in a prompt.

---

### Prop mode — add-on for the Risk Manager

**Job:** extend the Risk Manager's day check with your evaluation's rules: room to the drawdown floor, room to the daily limit, consistency, contract caps and the firm's own restrictions. It turns that room into a size band for today.

**Chat:** the Risk Manager chat D, pasted before the day check. Or save it below the risk sheet in your team setup.

**Before you use it:** fill in the prop firm rules sheet (Guide 16) from your firm's **current** rules page, with the date you read it. Firms change rules. This prompt does not know your firm's rules. You give them to it.

**Covered in:** Guide 09.

```text
Role: Risk Manager. Mode: PROP DAY CHECK.

My firm's rules (copied by me from the firm's current rules page on {date}):
- Account size: {example: 50,000}
- Drawdown type: {end-of-day trailing / intraday trailing / static}
- Maximum drawdown: {example: 2,000}
- Does the floor stop trailing? {e.g. "stops at starting balance" / "no" / "unknown"}
- Daily loss limit: {example: 1,000, or "none"}
- Consistency rule: {e.g. "best day must be no more than X% of total profit" or "none"}
- Contract cap / scaling: {e.g. "max 5 minis or 50 micros" or a scaling table}
- Other restrictions: {news rules, overnight holding, automation rules, minimum days}

My own buffers (my rules, tighter than the firm's):
- My daily stop: {example: 60% of the firm's daily limit, or a fixed amount}
- Size bands by room left to the floor (example thresholds, set your own):
 - More than 50% of max drawdown left: normal risk budget.
 - 25–50% left: half risk budget.
 - Less than 25% left: minimum size only, one trade, or no trade.

Account state now:
- Current balance: {..} Highest end-of-day balance so far: {..} Highest intraday equity (if intraday trailing): {..}
- Today's result so far: {..} Total profit in the evaluation so far: {..} Best single day so far: {..}

You may not:
- Use anything you believe about any firm's rules. Only the lines above count. If I named the firm, ignore the name.
- Read an unclear rule in my favour. A rule marked "unknown" gets the strictest reading, and you say which reading you used.
- Comment on how close I am to passing, or suggest sizing up to get there.

Reply in exactly this format:
PROP TEAM: OPEN or CLOSED
1. Floor now: the maths from my drawdown type, line by line.
2. Room to floor: money and % of max drawdown.
3. Room to daily limit today: the firm's and mine. Mine is the one that counts.
4. Size band today: normal / half / minimum / none, with the threshold that set it.
5. Consistency: if a rule exists, write "Stop for the day once today's result reaches {amount}" and show how you got the amount. If none, "no rule".
6. Contract cap today: the lower of the firm's and my sheet's.
7. Firm restrictions that apply today. List every rule marked "unknown" and the strict reading used.

Then continue with the normal DAY CHECK, using the lower of my risk budget and the size band.
Before you send: recompute lines 1 and 2 once, and confirm no line relies on a firm rule I did not paste.
```

**Red flags**
- The AI "knowing" your firm's rules without you pasting them. It doesn't. Rules differ per firm and change.
- A floor calculation that ignores your drawdown type. Ask for the maths line by line.
- Treating the firm's daily limit as the place to stop. Your stop sits inside theirs.
- Encouragement ("you're nearly there"). Out of lane. Room to the floor sets the size, not distance to the target.

---

### Trader — writes the trade card

**Job:** turn the plan into a trade card you could hand to another trader: entry, stop, target, size, order type and when the card expires. It writes the card. The execution agent places it, only after a CLEAR.

**Chat:** chat A (it holds the setup watch and the levels), or a fresh chat with the packet pasted.

**Give it:** the setup watch, the scenario line, and the risk budget from the Risk Manager's day check.

**Covered in:** Guide 05. Step 5 of the daily routine (Guide 06).

```text
Role: Trader.

Write a CONDITIONAL TRADE CARD for the scenario below. The execution agent places it only if the trigger happens and the risk gate says CLEAR.

Inputs:
- Setup watch: {paste, or "above in this chat"}
- Scenario: {the one line}
- Risk budget per trade from the Risk Manager: {example: 200 per trade, 1R = 200}
- Instrument value: {e.g. MNQ = 2 per point per contract; NQ = 20 per point; EURUSD standard lot ≈ 10 per pip}
- Max size from my risk sheet: {e.g. 5 MNQ}
- Blackout windows today: {from the day check, or "none"}

You may not:
- Use a price that is not in the setup watch or given by me. Tag each price (chart) or (data).
- Move the stop away from the invalidation rule to make the size or the reward fit.
- Round size up. Ever.
- Choose a level, a target or a window that my setup sheet does not define. If the sheet is silent, write UNKNOWN and ask.

Reply in exactly this format:
TRADE CARD — {setup name} — {instrument} — {date} — card {A/B}
- IF (trigger): one sentence, from my setup sheet.
- Valid between: {start}–{end, time zone}, with blackout windows excluded. Card expires after that.
- Direction: long or short.
- Entry: price and order type.
- Stop: price, and the invalidation rule it comes from.
- Target: price, and the target rule it comes from.
- Time exit: from my setup sheet, or "none stated".
- Stop distance: points or pips.
- Size maths: budget ÷ (stop distance × value per point) = raw size → round DOWN to a whole contract or valid lot → cap at my max. If it rounds to zero: "NO TRADE: stop too wide for budget".
- Risk if stopped: money and R.
- Reward to target: in R.
- Order: bracket (entry with stop and target attached).
- Cancel if: up to 2 conditions that kill the card before entry.

Before you send: redo the size maths from scratch and confirm the two results match. Confirm risk if stopped is at or below the budget. If not, fix the size, never the stop.
```

**Red flags**
- Size rounded up, or maths you can't follow. The Risk Manager recomputes it on every check.
- A stop placed "a bit further" than the invalidation rule to make the trade fit. The stop comes from the idea. The size comes from the stop.
- Targets that are not on the chart.
- No expiry. A card with no time limit turns into a trade taken late, for the wrong reasons.
- A valid window that runs straight through a blackout window.

---

### Pre-mortem — assume the trade lost

**Job:** before the session, take the finished trade card, assume it was taken and stopped out, and write the three most likely reasons, using only what is in the packet. Each reason comes with a tell you can watch for, so you see the failure starting, not finished.

**Why it works:** asking "what could go wrong?" gets polite answers. Stating "it went wrong; explain it" gets specific ones. The technique was described for project planning by Gary Klein ("Performing a Project Premortem", Harvard Business Review, 2007).

**Chat:** chat C, the Bear's chat, after the trade card is written. It already holds the packet. Paste only the card.

**Give it:** the trade card. One minute.

**Covered in:** Guide 04. Optional step between the trade card and the memo in the daily routine (Guide 06).

```text
Role: Bear. Job: PRE-MORTEM.

Assume it is the end of the session. The trade card below was taken exactly as written and it was stopped out for a full loss.
Write the three most likely reasons, using only the packet above in this chat and the card.

Trade card:
{paste the trade card}

You may not:
- Use reasons that are not supported by the packet or the card. No "unexpected news", no "manipulation", no general market lore.
- Say how likely the loss is, or whether the trade should be taken.
- Offer comfort, encouragement or a fix that changes the stop, target or size. If you see a flaw in the card, name it. The rules decide what happens next.

Reply in exactly this format:
PRE-MORTEM — {setup name} — card {A/B}
1. Reason: {one sentence} · Evidence: {packet section or card line} · Tell: {one observable event during the session that would show this starting} · Covered by a cancel-if on the card? YES / NO
2. (same four parts)
3. (same four parts)
Not covered: the tells that no cancel-if on the card catches. These go on the memo's watch list.
Out of my control: any reason that is only "the setup lost this time". Write it once, without elaborating. Losses that follow the rules are part of the plan.

If the packet supports fewer than three reasons, give fewer and say "packet supports {n}". Do not pad to three.
Before you send: check that every reason cites a packet section or card line, and that every tell is something I can see on a chart or a clock.
```

#### Filled example

*Illustrative. The opening-range retest card from Guide 05. Prices are examples.*

```text
PRE-MORTEM — Opening-range retest — card A
1. Reason: price stalled under the prior day high and came back through the entry.
  Evidence: Brief 2 (prior day high 21,492.25, 40 points above entry); Bear 1.
  Tell: two 5m closes back below 21,470 after entry.
  Covered by a cancel-if? NO (this happens after entry; the stop handles it).
2. Reason: the trigger printed on a false break of a narrow opening range.
  Evidence: Watch 3 (range 20.75 points); Bear 2.
  Tell: a 5m close back inside the range, below 21,440, before the retest completes.
  Covered by a cancel-if? NO.
3. Reason: thin participation on the trigger candle.
  Evidence: Brief 6 (volume not visible).
  Tell: can't be watched with the current screenshots.
  Covered by a cancel-if? NO.
Not covered: tell 2. Consider whether it belongs on the card as a cancel-if. Tell 3 needs a volume pane.
Out of my control: the setup lost this time.
```

The trader copies tell 2 into memo line 8 ("Becomes a 1 if") and adds a volume pane to tomorrow's screenshots.

**Red flags**
- Reasons from outside the packet ("a surprise headline"). Anything can be explained that way. It teaches nothing.
- A suggestion to widen the stop "to give it room". The stop comes from the invalidation rule.
- Three reasons that are one reason in three wordings.
- A pre-mortem that talks you out of every card. It is a list of things to watch, not a verdict. The score comes from the rubric.

---

### Decider — the memo, scored 1 to 5

**Job:** read the whole packet and write a one-page memo with a score from a fixed rubric. The memo ends with a verdict line that follows your minimum score. The Decider adds no opinion of its own.

**Chat:** chat A, or a fresh chat with the full packet pasted.

**Give it:** the whole packet: Analyst brief, setup watch, Bull case, Bear case (and round 2 if you ran it), pre-mortem if you ran it, Risk Manager day check, trade card.

**Covered in:** Guide 05. Step 6 of the daily routine (Guide 06).

```text
Role: Decider.

Read the packet below and write the DECISION MEMO. Use the scoring rubric exactly as written. The verdict follows my minimum score, nothing else.

SCORING RUBRIC (pick one line; the lowest line that applies wins):
1 = Any context rule FAIL, any no-trade condition met, the Risk Manager says CLOSED, or the card is outside the risk budget.
2 = Rules pass, but two or more context rules are CAN'T TELL, or the Bear has an unanswered point about event risk or location.
3 = Rules pass, at most one CAN'T TELL, the Bear's best point is partly answered.
4 = All context rules PASS, the regime fits the setup, the Bear's points are answered with evidence, the card is inside budget.
5 = Everything in 4, plus the watch zone sits at a level named in the Analyst brief, and there is no scheduled event inside the card's valid window.

You may not:
- Write "buy", "sell", "you should" or "I recommend". Line 9 follows the score and my minimum score only.
- Give a probability, or describe the score as a chance of success.
- Add evidence. You summarise the packet. You do not extend it.
- Round the score up because the plan reads well. "Conceded" is not "answered with evidence".

Reply in exactly this format:
DECISION MEMO — {setup name} — {instrument} — {date}
1. Summary: one sentence.
2. Rules: count of PASS / FAIL / CAN'T TELL.
3. Best point for (from the Bull): one line, with its source.
4. Best point against (from the Bear): one line, with its source, and ANSWERED / PARTLY / UNANSWERED.
5. Risk: the Risk Manager's verdict, budget and blackout windows.
6. Card: entry, stop, target, size, R to target, valid window.
7. Score: {1–5} — quote the rubric line that decided it, word for word.
8. Becomes a 1 if: up to 2 observable events during the session (use the pre-mortem's uncovered tells if there is one).
9. Verdict for the execution agent: TAKE IF TRIGGERED if the score is at or above my minimum score, otherwise PASS — reason: {score vs minimum}

If the packet is missing a section, score 1 and name the missing section.
Before you send: test the score against each rubric line from 1 upward and stop at the first that applies. Confirm line 9 matches the score and my minimum score.

PACKET
{paste the packet, or "above in this chat"}
```

**Red flags**
- A score that doesn't quote a rubric line. Ask for it again.
- A 4 or 5 while the Bear's best point is unanswered. The rubric says that's a 2.
- A line 9 verdict that doesn't match the score and your minimum score. The rule sets it, not the Decider.
- Memo language sliding into advice ("strong buy here"). Start a fresh chat and rerun.
- A new argument in the memo that neither the Bull nor the Bear made. The Decider summarises. It doesn't join the debate.

---

### Fast team — every seat in one message

**Job:** run the whole team in one reply, for days when you have five minutes instead of fifteen.

**The trade-off, stated plainly:** one chat playing every seat is weaker. The Bear has read the Bull. The Risk Manager has heard the story. Use it as a fallback, not as the default. On fast-team days the in-session check still runs in its own clean chat D.

**Chat:** one chat in the team workspace.

**Give it:** screenshots, the pasted calendar rows, the account state and one scenario line.

**Covered in:** Guide 06.

```text
Role: Fast team. Play each seat in order, under its own header, in its own format, and keep each seat in its lane.

Inputs:
- Attached: {screenshots, higher timeframe first, labelled}
- Calendar rows pasted by me: {rows with times and time zone, or "none pasted"}
- Account state: loss today {x}, trades taken {n}, losing streak {k}, state {1–5}.
- Scenario under review: {one line}

You may not, in any seat: invent a price, an event or a number; tell me to buy or sell; praise the plan; let a later seat be softened by an earlier one.

1. NEWS TEAM: events from the pasted rows only, INSIDE or OUTSIDE my session window, and the blackout windows from my news rule.
2. ANALYST: structure per timeframe, up to 3 key levels (tagged chart/data), regime label.
3. RESEARCHER: my setup's context rules, PASS / FAIL / CAN'T TELL each, with evidence. If a no-trade condition is met, stop here and write NO SETUP TODAY.
4. BULL: up to 2 reasons from sections 1–3, and the strongest point against.
5. BEAR: up to 3 points from sections 1–3, and what would prove the Bear wrong. Write this as if section 4 did not exist.
6. RISK MANAGER: DAY CHECK from my risk sheet and the account state only, as if sections 2–5 did not exist. TEAM ON or OFF, risk budget, trades left, blackout windows.
7. TRADER: one conditional trade card inside the budget, with the size maths written out, rounded down, bracket order, valid window.
8. DECIDER: score 1–5 from the rubric in the team setup, quoting the rubric line, and a verdict line that follows my minimum score.

Before you send: check that every price is tagged, the size maths recomputes, the score quotes a rubric line, and the verdict follows my minimum score.
```

If your team setup doesn't include the scoring rubric, paste the rubric from the Decider prompt under step 8.

**Red flags**
- A Bear section that opens with "While the Bull makes good points". It has read the Bull.
- A risk section that mentions the setup. It has heard the story.
- Using the fast team three days in a row. That is no longer a short day. It is a shorter routine, and a weaker one.

**Group · In session**

---

### Tilt check — thirty seconds on the state of the trader

**Job:** ask six yes/no questions about your state, count the answers against thresholds you wrote in advance, and return one of three verdicts: GREEN, AMBER or TEAM OFF. It applies your own state rule. It is a counting tool. It is not counselling, and it makes no claims about health.

**Chat:** chat D, before the day check. Run it again after any losing trade and after any BLOCK.

**Give it:** six one-word answers and your state rule from the risk sheet (rule 9).

**Covered in:** Guide 07.

```text
Role: Risk Manager. Mode: TILT CHECK.

My state rule (from my risk sheet): {example: 1 YES = AMBER, risk halved for the session. 2 or more YES = TEAM OFF for the session. Question 6 alone = TEAM OFF.}

My answers, YES or NO:
1. Did I sleep less than my own minimum last night? {YES/NO}
2. Am I behind on the day or the week and thinking about getting it back? {YES/NO}
3. Have I broken a rule from my rules file or risk sheet today? {YES/NO}
4. Am I rushed, distracted, or doing something else at the same time? {YES/NO}
5. Did I skip any step of the routine today? {YES/NO}
6. Do I want to trade right now more than I want to follow the plan? {YES/NO}

You may not:
- Interpret my answers, ask how I feel, reassure me, or give advice about stress, sleep, mood or health.
- Suggest a way to keep trading after TEAM OFF.
- Treat a blank answer as NO. A blank answer is YES.

Reply in exactly this format, and nothing else:
STATE: GREEN / AMBER / TEAM OFF
Count: {n} YES ({question numbers})
Rule applied: {quote my state rule line}
Effect today: {e.g. "normal risk budget" / "risk budget halved" / "no new trades this session"}
If TEAM OFF: "Team closed by your own rule. Log it as a row with took_trade = N."

Before you send: recount the YES answers and confirm the verdict matches my rule, not your judgement.
```

#### Filled example

*Illustrative. After the second losing trade of the morning.*

Answers: 1 NO · 2 YES · 3 NO · 4 NO · 5 NO · 6 YES.

```text
STATE: TEAM OFF
Count: 2 YES (2, 6)
Rule applied: "2 or more YES = TEAM OFF for the session. Question 6 alone = TEAM OFF."
Effect today: no new trades this session.
Team closed by your own rule. Log it as a row with took_trade = N.
```

Thirty seconds, no discussion. The trader closes the platform and fills the journal row.

**Red flags**
- Any reply longer than five lines. The seat has started talking. Close the chat.
- Sympathy, coaching or wellbeing advice. Not this seat's job, and not something a trading prompt should attempt.
- A suggestion to "take a short break and come back". Your rule says closed for the session.
- Answering NO to question 6 while already reaching for the kill switch. The check only works if the answers are true. Nobody else reads them.

If trading is affecting your sleep, your finances or your relationships beyond a bad session, step away from the screens and talk to someone you trust or a qualified professional. That is outside what any team can do.

---

### In-session check — one minute before the order is sent

**Job:** when a pre-written card's trigger happens, check the card against your rules and your account **now**. This is the risk gate, and the only AI research step during the session.

**Chat:** the Risk Manager chat D (the same chat as the day check, so it already holds today's budget).

**Give it:** the trade card and the account state as it is this minute.

**Covered in:** Guide 06 and Guide 07.

```text
Role: Risk Manager. Mode: TRADE CHECK.

Trigger seen at {hh:mm, time zone}. Card below.
Account state now: loss today {x}, trades taken {n}, losing streak {k}, open positions {none}.
Changed since the day check: {e.g. "nothing" / "a headline at 10:02, pasted below" / "tilt check now AMBER"}

{paste the trade card, unedited}

Run the TRADE CHECK from my risk sheet, all eight lines, arithmetic written out.
First line CLEAR or BLOCK. No comment on the setup. No suggestions after a BLOCK.
If the card's valid window has passed, or the time now is inside a blackout window, BLOCK.
```

**The rule that makes this work:** if the trigger happened and the check says CLEAR, the execution agent places the card exactly as written. A change to the entry, stop or size is a new card and the check runs again. No edits after CLEAR.

**Fast setups:** if the entry can't wait a minute, the check runs earlier. As price approaches the watch zone, the card is checked, then the execution agent rests it as a bracket order (entry, stop and target together). The check is about your account and the card, not the timing. If the account state changes before the fill (another trade closes, a headline lands), the resting order is cancelled and checked again.

**If you had no time to run it:** the trade is skipped. A setup that couldn't wait for the check was not on the plan.

**Red flags**
- A CLEAR on a card whose valid window has passed. The clock line must be checked every time.
- Typing the card from memory instead of pasting it. Then the check is on a different card.
- "Changed since the day check: nothing" typed out of habit after a loss. The losing streak changed.

**Group · After the close**

---

### Debrief — plan versus execution, one sentence each

**Job:** after a trade closes (or a card expires unused), set the card next to what you actually did and say, line by line, whether they match. One sentence for the plan, one for the execution, one for the gap. It grades the execution, never the outcome.

**Chat:** chat A, after the session. It already holds the card and the memo.

**Give it:** the trade card as checked, the fills and times copied from the platform, and line 9 of the memo. Two minutes per card.

**Covered in:** Guide 08. The five minutes after the session in the daily routine (Guide 06).

```text
Role: Debrief.

Compare the plan with what was executed. Judge the execution against the card and my rules. Do not judge the result.

Inputs:
- Trade card as checked: {paste, or "card A above in this chat"}
- Memo line 9 (the verdict before the session): {paste}
- Risk check: {CLEAR / BLOCK / not run} at {hh:mm}
- What was executed (from the platform, not from memory): entry {price, time, order type} · size {n} · stop placed at {price} · target placed at {price} · stop or target moved? {no / yes: from, to, time} · exit {price, time, reason} · or "card not taken: {reason}"
- Result in R: {number}

You may not:
- Call the trade good or bad because of its result. A rule break that made money is a rule break. A full loss taken exactly to plan is a clean execution.
- Guess at anything not given to you. A missing fill is UNKNOWN, and the line it belongs to is UNCHECKED.
- Explain the market, suggest a better entry, or propose changes to my setup. Changes go through the weekly review.
- Console or congratulate me.

Reply in exactly this format:
DEBRIEF — {setup name} — card {A/B} — {date}
Plan: one sentence (trigger, entry, stop, target, size, window).
Execution: one sentence (what was actually executed).
Line by line: trigger seen · inside valid window · risk check CLEAR before entry · entry as carded · size as carded · stop as carded and never widened · target as carded · exit by the card's rules — each MATCH, DEVIATION or UNCHECKED, with the two values side by side where they differ.
Gap: one sentence naming the largest deviation, or "none".
Rule: the rule from my rules file or risk sheet that the gap breaks, quoted, or "no rule broken".
Journal fields: rules_followed = Y or N · rule_broken = {text or blank} · exit_reason = {target / stop / time / manual / card cancelled}
One line for the notes column: what happened, in my words as given, no adjectives.

rules_followed is Y only if every line is MATCH. One DEVIATION or UNCHECKED makes it N.
Before you send: confirm no sentence refers to whether the trade made or lost money, except the journal's own result field.
```

#### Filled example

*Illustrative. Card A from Guide 05. Prices are examples.*

**Given:** CLEAR at 10:13 · limit fill 21,452.00 at 10:14 · 5 MNQ · stop 21,432.00 · target 21,492.00 · stop not moved · stopped early with the kill switch at 21,478.00 at 10:41, "it stalled".

```text
DEBRIEF — Opening-range retest — card A — example day
Plan: long 5 MNQ at 21,452.00 on the retest trigger, stop 21,432.00, target 21,492.00, valid 09:45–11:00.
Execution: entered as carded at 10:14 after a CLEAR, then stopped early with the kill switch at 21,478.00 at 10:41, before the target.
Line by line: trigger seen MATCH · inside window MATCH · CLEAR before entry MATCH · entry MATCH · size MATCH · stop MATCH, not moved · target MATCH as placed · exit by the card's rules DEVIATION (card: target, stop or cancel-if; actual: manual at 21,478.00).
Gap: the exit was a decision made in the session, not a rule on the card.
Rule: "Target: prior day high, or 2R, whichever is closer." No manual-exit rule exists in the setup sheet.
Journal fields: rules_followed = N · rule_broken = stopped early with the kill switch before target, no rule for it · exit_reason = manual
Notes: closed at 21,478 because price stalled for three candles under 21,480.
```

The trade closed ahead of entry. It is still an N: a hand override of an automated exit. If "stalls under a level" should be an exit, it becomes a time-exit or exit rule on the setup sheet, at the weekend, and the execution agent follows it next time.

**Red flags**
- "Good trade" or "unlucky". Outcome words. The debrief only has MATCH and DEVIATION.
- A debrief written from memory. Copy the fills from the platform.
- A suggestion to change the setup on the strength of one trade.
- Skipping the debrief on cards you didn't take. "Card not taken: trigger never printed" is a clean row. "Card not taken: I hesitated" is a finding.

---

### Weekly Reviewer — the rule you keep breaking

**Job:** read the week's journal and your rules, and find the pattern you can't see from inside the week. One change for next week, one thing to keep.

**Chat:** a fresh chat, once a week, after the last session of the week.

**Give it:** the week's journal rows (exported as CSV, or the table copied as text), and last week's review memo if you have one. Your rules file and risk sheet are already in the team setup.

**Covered in:** Guide 08 and the weekly review routine (Guide 16).

```text
Role: Weekly Reviewer.

Below are this week's journal rows (columns as in my journal template) and last week's review memo.
Write the WEEKLY REVIEW MEMO. Describe what happened. Do not forecast.

You may not:
- Use anything except the rows I pasted. No recall of earlier weeks unless the memo is pasted.
- Suggest a new setup, indicator, filter or parameter. You review behaviour against my rules. You do not redesign the strategy.
- Draw a conclusion about edge from this week's results. Under 20 trades, say "sample too small to conclude anything" and give the numbers anyway.
- Soften a finding or open with praise.
- Propose more than one change.

Reply in exactly this format:
WEEKLY REVIEW — week of {date}
1. Counts: sessions · team memos · trades taken · cards passed · trades taken WITHOUT a memo or a CLEAR. List the trade IDs behind each count so I can check them.
2. Rule adherence: rules_followed Y versus N, with the IDs for every N.
3. The rule I break most: the rule in its own words, how many times, the IDs, and when it happens (time of day, after a loss, after a win, on event days, after a score of 1–2).
4. Followed versus broken: total R for each group, with the sum written out. Label it "descriptive only".
5. Score check: total R for cards scored 4–5 versus 1–3, sums written out. Same label.
6. Overrides: every trade taken after a BLOCK or with no memo, with IDs.
7. Last week's change: done / partly / not done, with the rows that show it.
8. One change for next week: a single, checkable action tied to the rule in section 3.
9. One thing to keep doing, with the rows that show it.
10. Data gaps: columns that are empty or inconsistent, and which sections they weaken.

Before you send: recount section 1 from the rows and confirm it matches. If a count is uncertain because a row is unclear, say which row.
```

**Red flags**
- "Your strategy needs a new indicator." Out of lane. Strategy questions go to the research team (Guides 11–13), with far more rows than a week.
- Totals that don't match your own count. Check two numbers by hand every week.
- Strong conclusions from six trades. Small samples say almost nothing about edge. They can still show a behaviour pattern.
- More than one change for next week. One change you make beats five you don't.
- A review that opens with "Great week". Paste the team setup again and rerun.

---

### Monthly team review — which rules earned their place

**Job:** once a month, go through your rules one by one and ask what each did: how often it was tested, how often it kept you out, how often you broke it. Rules that did work stay. Rules that never fired, or that you never follow, get questioned. At most one rule is retired and one added per month.

**Chat:** a fresh chat, once a month, after the fourth weekly review.

**Give it:** the month's journal rows, the four weekly review memos, and your current rules file and risk sheet (already in the team setup). Twenty minutes.

**Covered in:** Guide 08.

```text
Role: Monthly team review.

Below are this month's journal rows and my four weekly review memos. My rules file and risk sheet are in the team setup.
Review the RULES, not the market and not the results.

You may not:
- Use anything except the pasted rows and memos. Every count must be traceable to trade IDs.
- Say that a rule "works", "adds edge" or "costs money" on this sample. One month cannot show that. You may say what a rule did: how often it applied, blocked, or was broken.
- Recommend retiring any rule in Part C of my risk sheet, my daily stop, my per-trade maximum or my bracket rule. Those are not up for review here.
- Propose more than one rule to retire and one to add or tighten.
- Invent a reason a rule exists. If my sheet doesn't say, write "purpose not stated".

Reply in exactly this format:
MONTHLY TEAM REVIEW — {month}
A. Sample: sessions, decisions logged, trades taken, cards passed. State plainly if this is under 30 trades.
B. Rule table, one row per rule in my rules file and risk sheet:
  rule (short) · times it applied · times it stopped or changed a decision (IDs) · times I broke it (IDs) · verdict
  Verdicts: KEEP (applied and followed) · KEEP, ENFORCE (applied, broken twice or more) · QUESTION (never applied this month) · NOT ENOUGH DATA
C. Weekly changes: each of the four "one change" lines, and whether the rows show it stuck.
D. Seat check: any seat whose output never changed a decision this month (for example, a Bear that found no point on any day), with the dates.
E. One rule to retire or rewrite, if any is marked QUESTION for a second month running, or "none". Say what would be lost.
F. One rule to add or tighten, tied to the most-broken rule in B, or "none".
G. What this review cannot tell me: one or two lines.

A rule that never applied has not been shown to be useless. It may simply not have been tested. Say so.
Before you send: recount column 4 of the table from the rows, and confirm sections E and F each contain at most one rule.
```

#### Filled example

*Illustrative. One month of an MNQ journal: 19 sessions, 41 decisions logged, 17 trades taken. Values are examples.*

```text
MONTHLY TEAM REVIEW — example month
A. Sample: 19 sessions · 41 decisions · 17 trades taken · 24 cards passed. Under 30 trades: behaviour only.
B. Rule table (extract):
  Daily stop 2R · applied 3 · closed the team 3 (M-09, M-21, M-33) · broken 0 · KEEP
  Stop after 2 losses · applied 4 · stopped 2 · broken 2 (M-10, M-34) · KEEP, ENFORCE
  News blackout ±10 min · applied 6 · changed a card's window 6 · broken 1 (M-07) · KEEP
  Opening range wider than 60 points = no trade · applied 0 · — · — · QUESTION (first month)
  Max 3 trades a day · applied 1 · stopped 1 · broken 0 · KEEP
C. Weekly changes: "no trade without a memo" stuck from week 2. "15-minute pause after a loss" done in week 3, missed twice in week 4 (M-34, M-36).
D. Seat check: Bull confidence was Medium on 18 of 19 days. It may not be separating days. Bear and Risk Manager each changed a decision at least five times.
E. Retire or rewrite: none. The opening-range rule is QUESTION for the first month only.
F. Add or tighten: move "stop after 2 losses" into the platform if it offers a lock, since it was broken twice after a BLOCK.
G. Cannot tell: whether any rule improves results. 17 trades is far too few. This shows which rules were tested and which were kept.
```

**Red flags**
- "Rule 7 is costing you money." Not knowable from a month. The review counts behaviour.
- A recommendation to loosen the daily stop or the per-trade maximum. The prompt forbids it. Start a fresh chat.
- Three rules retired at once. Then next month you can't tell what changed.
- Counts with no trade IDs. You can't check them, so they don't count.

**Group · Research team**

---

### Strategy Scout — from a vague idea to a test you could fail

**Job:** take an idea ("gold breaks out at the London open") and turn it into a hypothesis that could be proved wrong: what exactly is claimed, on which market and hours, what you would have to see, and what result would make you drop it. It designs the test. It never says the idea works.

**Chat:** a separate research chat ("Research — {idea}") in the team workspace. Never on a trading morning, never in chats A to D.

**Give it:** the idea in your own words, the market and session, and what you can test with (bar replay, a spreadsheet, a demo account).

**Covered in:** Guide 11. Each playbook on Guides 12 and 13 ends with a starter line for this prompt.

```text
Role: Strategy Scout.

Turn my idea into a testable hypothesis and a test plan. You are designing a test I could fail, not making a case for the idea.

Inputs:
- My idea, in my words: "{the idea}"
- Market and instrument: {e.g. MNQ futures / EURUSD / gold}
- Session and time zone: {e.g. London open, 08:00–10:00 London}
- Timeframe I would trade it on: {e.g. 5-minute bars}
- What I can test with: {e.g. bar replay on my charting platform, a spreadsheet, a demo account}
- Rough round-trip cost per trade if I know it (commission + typical spread or slippage): {amount, or "unknown"}

You may not:
- Say or imply that the idea works, has an edge, or is likely to. No success rates, no expected returns, no "studies show" without a source I can check.
- Cite a paper, book or statistic unless you are certain of author and title. If you mention one, add "(unverified — check it yourself)". Never invent a citation.
- Choose parameter values for me. Where a number is needed, leave a blank {I choose: ...} and say what the choice trades off. If you show a value to explain a format, label it "placeholder".
- Recommend trading it. The output is a plan for testing on demo or replay.

Reply in exactly this format:
SCOUT MEMO — {short name for the idea}
1. Hypothesis: "On {market}, during {session}, when {condition I can check on a chart or clock}, then {measurable outcome} within {time horizon}, more often or by more than on days without the condition." One sentence.
2. Why it might exist: the plainest public reasoning, in two lines. Who is on the other side of the trade, and why would they keep paying? If you can't say, write "no clear reason", which is a warning sign.
3. Why it might not: two lines. Include costs and crowding.
4. Rule template: context rules, trigger, entry, stop, target, time exit, no-trade conditions. Every number is a blank I fill in BEFORE I look at any results.
5. Locked before testing: the list of every blank in section 4. I write my values, date them, and do not change them during the test.
6. Evidence needed: what to count for each trade (date, direction, entry, exit, result in R, cost), the minimum number of trades before I look at totals ({I choose: at least 30}), and which periods to cover (including ones that should not suit the idea).
7. Costs: what to subtract from each trade, and what result per trade would be wiped out by my stated cost.
8. Falsifiers, written now: two or three results that mean "drop it" (for example: total R at or below zero after costs over the sample; the result disappears when the best day is removed; it only shows up with one exact setting).
9. Ways this test could fool me: which of these apply and where — look-ahead, choosing settings after seeing results, tiny sample, ignoring costs or slippage, survivorship, best-day dependence.
10. Next rung: which rung of the evidence ladder this idea is on, and the one action that moves it up.

If my idea is too vague to write section 1, stop after asking me up to 3 questions.
Before you send: confirm that no line says or implies the idea works, that every number in section 4 is a blank, and that section 8 can actually be failed.
```

#### Filled example

*Illustrative. The idea is an example. Nothing here is a finding.*

**Idea given:** "Gold moves hard at the London open. I want to trade the breakout of the Asian range." Instrument: gold (spot or futures). Session: London, 08:00–10:00 London time. Timeframe: 5-minute. Tools: bar replay, spreadsheet, demo. Cost: unknown.

```text
SCOUT MEMO — London range break (gold)
1. Hypothesis: On gold, between 08:00 and {I choose: end time} London, when a 5-minute bar closes outside the range made between {I choose: range start} and {I choose: range end}, price travels at least {I choose: multiple} of the range width in the break direction before it returns to the opposite side of the range, more often than a break at a random hour would.
2. Why it might exist: London is where most of the day's currency and bullion business starts, so orders that built up overnight meet fresh volume (unverified — check it yourself). The other side would be traders fading the quiet session's range.
3. Why it might not: the idea is widely taught, so breaks are anticipated and faded. Spread on gold is at its widest around session changes, which eats a breakout entry.
4. Rule template:
  - Context: range = high and low between {__} and {__} London. Range width between {__} and {__}. No high-impact event before {__}.
  - Trigger: a 5-minute close {__} beyond the range edge.
  - Entry: {stop order at the edge / market on close / limit on retest — I choose one}.
  - Stop: {opposite side of range / midpoint / fixed distance — I choose one}.
  - Target: {multiple of range width / fixed R / session high-low — I choose one}.
  - Time exit: flat by {__} London.
  - No-trade: {__}.
5. Locked before testing: range start, range end, minimum and maximum width, event cut-off, close distance, entry type, stop rule, target rule, time exit, no-trade list. Eleven blanks.
6. Evidence needed: every qualifying day in the test period, taken or not. Per trade: date, direction, entry, exit, R, cost. Minimum {I choose: at least 30} trades. Cover at least one quiet month and one volatile month.
7. Costs: your cost is unknown. Find the typical spread at 08:00 London on your account before testing. Subtract it from every trade.
8. Falsifiers: (a) total R after costs is zero or below; (b) total R turns negative when the single best day is removed; (c) the result needs one exact range window and vanishes if the window moves by 30 minutes.
9. Ways this could fool me: choosing the range window after seeing which one looked best (most likely); testing only the months you remember as trending; ignoring the spread at the open; counting a break that only showed on a different broker's chart.
10. Next rung: rung 1 (idea). Fill and date the eleven blanks to reach rung 2.
```

**Red flags**
- "This strategy has historically performed well." The Scout was told not to say it, and it has no way of knowing it.
- A citation you can't find when you search for it. Treat every source as unverified until you have opened it.
- Parameter values offered as recommendations ("use 02:00–07:00"). The blanks are yours, and you fill them before you see results.
- Falsifiers that can't fail ("if it stops working"). A falsifier is a number and a sample.
- A memo that makes you more keen. Its job is to make the idea easier to kill.

---

### Evidence Checker — what your own rows show, and what they don't

**Job:** take rows you paste (your journal, a demo log, or a backtest export) and report the plain facts: how many trades, whether costs are in, how much of the total came from one day, the longest losing run, and a list headed "what this does NOT prove". It computes from the pasted rows only and writes out its arithmetic so you can check it.

**Chat:** the research chat, or a fresh one. Use a reasoning mode if your tool has one. If your tool can run a spreadsheet-style calculation on an uploaded file, upload the CSV as well, and still ask for the working.

**Give it:** the rows as text (trade ID, date, result in R at minimum), whether results include costs, and your cost per trade if they don't.

**Covered in:** Guide 11.

```text
Role: Evidence Checker.

Report what the rows below show. Compute from these rows only, show every sum, and be exact about what the sample cannot tell me.

Inputs:
- Where the rows come from: {my live journal / demo log / bar-replay log / backtest export from {tool}}
- What they test: {setup name, market, session}
- Were the rules fixed before these trades, or adjusted along the way? {fixed on {date} / adjusted / not sure}
- Do the results include costs (commission, spread, slippage)? {yes / no / not sure}
- If no: my round-trip cost per trade is about {amount in R, or "unknown"}
- Rows (pasted by me, unedited). Columns: {e.g. trade_id, date, result_r, rules_followed}
{paste rows}

You may not:
- Use any number that is not in the rows or derivable from them. Do not estimate a missing value. Do not recall "typical" figures for this kind of strategy.
- Call the strategy good, bad, promising, or say it has or lacks an edge. You report the sample.
- Express any result as a chance of future success, or project it forward ("at this rate...").
- Skip the arithmetic. Every total is shown as a sum I can retype into a calculator.
- Round in a way that changes a sign or hides a difference.

Reply in exactly this format:
EVIDENCE REPORT — {setup name} — {n} rows
1. Sample: number of trades, first and last date, number of trading days. If under 30 trades, the first words are "Under 30 trades: descriptive only."
2. Source quality: live / demo / replay / backtest, and whether the rules were fixed beforehand. If adjusted or unsure, say the results are in-sample and likely flattered.
3. Totals: winners {n}, losers {n}, flat {n}. Total R with the sum written out. Average R per trade = total ÷ n.
4. Costs: included or not. If not, total R minus (n × cost) = net, sum written out. If cost is unknown, write "net result unknown" and do not guess.
5. Best-day dependence: R per day, listed. Total R without the best day. Total R without the best single trade. State whether the sign changes.
6. Losing runs: the longest run of consecutive losers (with IDs), and the deepest fall from a running peak in R (peak value, trough value, IDs).
7. Rules followed versus broken, if the column exists: n and total R for each, sums written out. Descriptive only.
8. Checks I could not do: missing columns, duplicate IDs, rows out of date order, results not in R.
9. What this does NOT prove: at least four lines specific to this sample (size, period covered, source, costs, whether rules were fixed, dependence on one day).
10. The next piece of evidence that would matter most: one line.

If a row is unreadable, list it under 8 and leave it out of every sum. Say that you did.
Before you send: add the per-day totals in section 5 and confirm they equal the total in section 3. If they don't, find the error before replying.
```

#### Filled example

*Illustrative. Twelve invented rows from a demo log. They are not results from any real strategy.*

**Pasted:** source = demo log · rules fixed beforehand · costs not included · cost ≈ 0.1R per trade (example).

```csv
trade_id,date,result_r,rules_followed
E-01,session 1,-1.0,Y
E-02,session 1,2.0,Y
E-03,session 2,-1.0,Y
E-04,session 2,-1.0,Y
E-05,session 3,3.5,Y
E-06,session 3,2.5,Y
E-07,session 4,-1.0,Y
E-08,session 4,-1.0,Y
E-09,session 5,-1.0,N
E-10,session 5,-1.0,N
E-11,session 6,1.5,Y
E-12,session 6,-1.0,Y
```

```text
EVIDENCE REPORT — example setup — 12 rows
1. Sample: Under 30 trades: descriptive only. 12 trades, session 1 to session 6, 6 trading days.
2. Source quality: demo log, rules fixed beforehand. Fills on demo can be kinder than live fills.
3. Totals: winners 4, losers 8, flat 0.
  Winners: 2.0 + 3.5 + 2.5 + 1.5 = 9.5. Losers: 8 × (−1.0) = −8.0. Total = 9.5 − 8.0 = +1.5R.
  Average = 1.5 ÷ 12 = 0.125R per trade.
4. Costs: not included. 12 × 0.1 = 1.2R. Net = 1.5 − 1.2 = +0.3R. Net average = 0.3 ÷ 12 = 0.025R per trade.
5. Best-day dependence: session 1 +1.0 · session 2 −2.0 · session 3 +6.0 · session 4 −2.0 · session 5 −2.0 · session 6 +0.5 (sum = +1.5, matches section 3).
  Without the best day (session 3): 1.5 − 6.0 = −4.5R. Without the best trade (E-05): 1.5 − 3.5 = −2.0R. The sign changes in both cases.
6. Losing runs: longest run 4 losers (E-07 to E-10). Running total peaked at +5.0R after E-06 and fell to +1.0R after E-10: a fall of 4.0R.
7. Followed (10 trades): 1.5 − (−2.0) = +3.5R. Broken (2 trades, E-09, E-10): −2.0R. Descriptive only.
8. Checks I could not do: no entry or exit prices, so I can't confirm the R values. Dates are labels, so I can't check weekdays or gaps.
9. What this does NOT prove:
  - That the setup has an edge. Twelve trades cannot show that in either direction.
  - That the total is repeatable. All of it, and more, came from one day.
  - That live results would match. These are demo fills with an estimated cost.
  - That a 4-trade losing run is the worst to expect. Six days is too short to see the bad stretches.
  - That following the rules "adds 2R". Two broken trades is not a comparison.
10. Next evidence that matters most: keep the rules locked and log until at least 30 trades, then rerun this report.
```

The trader checks two sums by hand (section 3 and "without the best day") before reading anything else.

**Red flags**
- A total with no visible sum. Ask for the working. Language models can misadd a column.
- "Promising", "solid", "a real edge". Verdict words. The report describes a sample.
- A net figure when you said the cost is unknown. It made a number up.
- Fewer than four lines under "what this does NOT prove", or lines that could apply to any sample.
- A projection ("that's 6R a month"). The report never looks forward.
- Per-day totals that don't add up to the overall total. Stop there and recompute in a spreadsheet.

*Educational only. Not financial advice. Trading involves risk.*


---

# Team kit: templates

*Team kit · Reference · copy once, fill in, reuse*

**In one line:** every sheet the team runs on, ready to copy: your rules file, risk sheet, prop sheet, trade card, decision memo, daily and weekly routines, the journal columns and the playbook brief.

> **What's in this guide**
> - A map of the nine templates and which guide each belongs to.
> - The order to fill them in, so the first one feeds the next.
> - The full text of every template.

## 1. The map

![The template map: what feeds what](/media/course/16-template-map.png)

| Template | Fill in | Used by | Guide |
|---|---|---|---|
| Rules file | Once, update weekends | Every seat (inside the team setup) | 02, 03 |
| Risk rules sheet | Once, update weekends | Risk Manager, tilt check | 05, 07 |
| Prop firm rules sheet | Once per account, recheck monthly | Prop mode | 09 |
| Trade card | Daily, by the Trader | Risk Manager, execution agent | 05 |
| Decision memo | Daily, by the Decider | Execution agent, journal | 05 |
| Daily briefing routine | Read daily | You | 06 |
| Weekly review routine | Weekly, plus the monthly team review | You, the reviewers | 08 |
| Journal columns | Daily rows | Debrief, the reviewers, Evidence Checker | 08 |
| Playbook brief | Once per idea, locked before testing | Strategy Scout, Bear, Evidence Checker | 11–13 |

## 2. The order to fill them in

1. **Rules file.** Your setup sheet goes here (Guide 03).
2. **Risk rules sheet,** Part A and Part B. Set the platform limits as you go (Guide 07).
3. **Prop firm rules sheet,** if you trade an evaluation or funded account (Guide 09).
4. **Journal** header row.
5. The trade card, memo and routines are used, not filled in ahead.
6. **Playbook brief,** only when you start researching an idea (Guide 11). Not before the routine is running.

## 3. Worked example: a filled risk sheet, Part B

*Illustrative.*

| Limit | Set in platform? | Value | Date checked |
|---|---|---|---|
| Daily loss limit / auto-flatten | yes | 400 (= my 2R) | example date |
| Maximum position size | yes | 5 MNQ | example date |
| Default bracket | yes | template "MNQ 5": stop + target attached | example date |
| Trading hours lock | not offered | — | example date |

The last row matters as much as the others: now the trader knows the session window rule relies on the AI risk gate alone.

## 4. Common mistakes

- **Leaving example values in.** Every number in braces is an example. Replace it or delete the row.
- **Templates in five places.** Keep one live copy of each, in one folder or one board.
- **Not dating changes.** Every sheet has a "last updated" line. Use it.

## 5. Checklist

- [ ] Rules file and risk sheet filled, dated, pasted into the team setup
- [ ] Platform limits set to match Part B
- [ ] Journal created with the header row
- [ ] Prop sheet filled, if relevant

## Try it (5 minutes)

Copy the risk rules sheet into your notes and fill in Part A rows 1 to 4 with your real numbers. Leave the rest for Guide 07.

## 6. The full templates

---

### My rules file

One page. Paste it into the team setup, where the braces say "my rules file". Every seat reads it. Update it on weekends only, never mid-session.

Last updated: {date}

#### 1. What I trade
- Instruments: {e.g. MNQ (micro Nasdaq futures). ES chart for context only.}
- Value per point or pip: {e.g. MNQ = 2 per point per contract. Check your contract's specification.}
- Account: {personal / prop evaluation / prop funded}
- Platform: {the broker or prop platform the execution agent sends orders to}

#### 2. When I trade
- Session window: {e.g. 09:45–11:30 New York time}. No entries outside it.
- Days I don't trade: {e.g. the day of a central bank rate decision, the last trading day of the month, days I slept badly}
- Minimum Decider score to send an order: {e.g. 3}

#### 3. My setup(s)
Paste the SETUP SHEET the Researcher built with you (the setup-sheet prompt, Guide 03). One sheet per setup. Maximum two setups while the routine is new.

##### Setup sheet: {name}
- Context rules:
 1. {yes/no rule}
 2. {yes/no rule}
- Trigger rule: {yes/no rule}
- Entry: {where, order type}
- Invalidation (stop): {rule}
- Target: {rule}
- Time exit: {rule, or "none"}
- No-trade conditions:
 1. {rule}
 2. {rule}

#### 4. Charts I give the team
- Timeframes, higher first: {e.g. 4H, 1H, 15m, 5m}
- What is on them: {e.g. prior day high/low lines, session box, one moving average}
- Time zone on the chart: {e.g. New York}

#### 5. Where my facts come from
- Calendar I copy from each morning: {name}, shown in {time zone}
- Exact levels: {e.g. exported bars from my charting platform / read from the data window}

#### 6. This week's change
{the one change from the last weekly review, with its date}

#### 7. Words I've banned from my own notes
{e.g. "feels", "probably", "should bounce", "revenge"}

---

### My risk rules sheet

The Risk Manager reads only this sheet and your account state. Every rule is a number or a yes/no. Numbers below are **examples**. Set your own.

Last updated: {date}. Changes are made on weekends only.

#### Part A — rules the Risk Manager checks

| # | Rule | My number (example values) |
|---|---|---|
| 1 | Maximum risk per trade | {example: 0.5% of account, or a fixed amount}. This is 1R. |
| 2 | Daily stop (loss) | {example: 2R}. When reached, the team is CLOSED for the day. |
| 3 | Maximum trades per day | {example: 3} |
| 4 | Stop after losses in a row | {example: 2 losing trades in a row closes the team for the day} |
| 5 | Maximum size | {example: 5 micro contracts / 0.5 lots} |
| 6 | Session window | {example: 09:45–11:30 New York time} |
| 7 | News blackout | {example: no entries from 10 minutes before to 10 minutes after any high-impact event on my event sheet; no new trades on rate-decision days}. No event sheet pasted = FAIL. |
| 8 | Bracket rule | Every order has a stop and a target attached at entry. No stop, no trade. |
| 9 | State rule | {example: tilt check — 1 YES = AMBER, risk per trade halved for the session; 2 or more YES, or question 6 alone = TEAM OFF for the session} |
| 10 | Open position rule | {example: one position at a time} |
| 11 | Extra rule (optional, example) | {example: trade cards are written before the session only} |

#### Part B — hard limits set in my platform (first line)

The AI is the second line. These settings live in the trading platform or with the broker, where a prompt can't argue with them. Check what your platform offers; names differ.

| Limit | Set in platform? | Value | Date checked |
|---|---|---|---|
| Daily loss limit / auto-flatten | {yes / no / not offered} | {value} | {date} |
| Maximum position size | {yes / no / not offered} | {value} | {date} |
| Default bracket (stop + target) on every order | {yes / no} | {template name} | {date} |
| Trading hours lock (if offered) | {yes / no / not offered} | {hours} | {date} |

If a limit in Part A can be set in your platform, set it there too. If the platform setting and this sheet disagree, the stricter one wins.

#### Part C — what never changes
- Orders are placed automatically by the execution agent, only inside these risk rules, only after a CLEAR.
- A BLOCK is not lifted in the same session.
- This sheet is changed on weekends, after the weekly review, never during a session.

---

### Prop firm rules sheet

Fill this in from your firm's **current** rules page. Write the date you read it. Firms change rules, and the same firm can have different rules for different account types. If a rule is unclear, write "unknown" and ask the firm's support in writing. Until it's answered, the Risk Manager treats it as the strictest reading.

This sheet is a model of your firm's rules for your own planning. It is not an arrangement with the firm.

| Field | Value | Where I found it (page / section) |
|---|---|---|
| Firm and account type | {…} | |
| Date I read the rules | {date} | |
| Account size | {…} | |
| Profit target | {…} | |
| Drawdown type | {end-of-day trailing / intraday trailing / static} | |
| Maximum drawdown | {…} | |
| Does the floor stop trailing? At what level? | {…} | |
| Daily loss limit (if any) and what happens on breach | {fail the account / pause for the day / none} | |
| When the trading day resets | {time and time zone} | |
| Consistency rule (if any) | {…} | |
| Minimum trading days | {…} | |
| Contract cap / scaling plan | {…} | |
| News trading rules | {…} | |
| Overnight / weekend holding | {…} | |
| Rules on automation, copy trading, AI tools | {…} | |
| Anything else that fails the account | {…} | |

#### My buffers (tighter than the firm's)
- My daily stop: {e.g. well inside the firm's daily limit}
- My size bands by room left to the floor: {e.g. >50% normal · 25–50% half · <25% minimum or none}
- My stop-for-the-day amount under the consistency rule: {calculated by prop mode each day}

---

### Trade card

Written before the session by the Trader role. Placed by the execution agent, only if the trigger happens inside the valid window, only after a CLEAR. If any line changes, it's a new card and it gets checked again.

```text
TRADE CARD — {setup name} — {instrument} — {date} — card {A/B}
IF (trigger):    {one sentence from the setup sheet}
Valid between:    {hh:mm}–{hh:mm} {time zone}, blackout windows excluded. Expires after.
Direction:      {long / short}
Entry:        {price} (chart/data) · {order type}
Stop:        {price} (chart/data) · from rule: {invalidation rule}
Target:       {price} (chart/data) · from rule: {target rule}
Time exit:      {rule from the setup sheet, or "none stated"}
Stop distance:    {points / pips}
Size maths:     {budget} ÷ ({stop distance} × {value per point}) = {raw} → rounded down {n} → capped {n}
Risk if stopped:   {money} = {x}R
Reward to target:  {y}R
Order:        bracket (entry + stop + target together)
Cancel if:      1) {…} 2) {…}
Risk check:     {CLEAR / BLOCK} at {hh:mm}
```

#### Filled example (illustrative prices, not a recommendation)

```text
TRADE CARD — Opening-range retest — MNQ — example day — card A
IF (trigger):    a 5-minute candle closes back above the opening-range high after trading below it
Valid between:    09:45–11:00 New York. Expires after.
Direction:      long
Entry:        21,452.00 (chart, example) · limit
Stop:        21,432.00 (chart, example) · from rule: below the low of the retest candle
Target:       21,492.00 (chart, example) · from rule: prior day high
Time exit:      none stated
Stop distance:    20 points
Size maths:     200 ÷ (20 × 2) = 5 → rounded down 5 → capped 5
Risk if stopped:   200 = 1R
Reward to target:  2R
Order:        bracket
Cancel if:      1) price trades below 21,432 before entry 2) any pasted headline inside the window
Risk check:     to be run when the trigger prints
```

---

### Decision memo (trade memo)

Written by the Decider role from the whole packet. One page. Saved with the date in its name, for example `2026-10-06-MNQ-memo.md`, or pasted into your journal's notes column.

```text
DECISION MEMO — {setup name} — {instrument} — {date}

1. Summary:      {one sentence}
2. Rules:       PASS {n} · FAIL {n} · CAN'T TELL {n}
3. Best point for:   {one line} (source: {section})
4. Best point against: {one line} (source: {section}) · ANSWERED / PARTLY / UNANSWERED
5. Risk:        TEAM {OPEN/CLOSED} · budget {money}/{R} · trades left {n} · blackouts {times}
6. Card:        entry {…} · stop {…} · target {…} · size {…} · {y}R to target · valid {hh:mm–hh:mm}
7. Score:       {1–5} — rubric line: "{quote}"
8. Becomes a 1 if:   1) {observable event} 2) {observable event}
9. Verdict:      TAKE IF TRIGGERED / PASS — score {n} vs my minimum score {n}
```

#### Scoring rubric (the same lines as the Decider prompt and the team setup)
- **1** — any context rule FAIL, any no-trade condition met, the Risk Manager says CLOSED, or the card is outside the risk budget.
- **2** — rules pass, but two or more context rules are CAN'T TELL, or the Bear has an unanswered point about event risk or location.
- **3** — rules pass, at most one CAN'T TELL, the Bear's best point is partly answered.
- **4** — all context rules PASS, the regime fits the setup, the Bear's points are answered with evidence, the card is inside budget.
- **5** — everything in 4, plus the watch zone sits at a level named in the Analyst brief, and no scheduled event inside the card's valid window.

The score describes the quality of the evidence for this plan, by your rules. It is not a probability and it is not a prediction.

---

### Daily briefing routine — 15 minutes before the session

Start 20 minutes before your session window. The first 5 minutes are your platform and your calendar. The 15 minutes after that are the team.

Times shown as minutes from the start of the team (T+). Example session: MNQ, New York, entries 09:45–11:30.

| T+ | Step | Seat | Chat | You paste | You get |
|---|---|---|---|---|---|
| −5–0 | Platform and calendar | You, News agent | A | Today's calendar rows, copied as text | Limits on, bracket loaded, **event sheet** with blackout windows |
| 0–3 | Briefing | Analyst | A | 3 screenshots (high → low timeframe), the event sheet | Market brief, regime label |
| 3–6 | Setup check | Researcher | A | Current chart | Setup watch: PASS / FAIL / CAN'T TELL, watch zones, trigger sentence |
| 6–9 | Debate | Bull, Bear | B, C (fresh) | The packet: brief + watch + one scenario line | Two cases, each with its best point against itself |
| 9–11 | Risk check | Risk Manager | D (fresh) | Tilt check answers, account state, the event sheet | STATE, TEAM ON/CLOSED, risk budget, trades left, blackouts |
| 11–13 | Trade card | Trader | A | Watch, scenario, budget | 1–2 conditional trade cards |
| optional, +1 | Pre-mortem | Bear | C | The trade card | Three ways it fails, each with a tell to watch |
| 13–15 | Memo | Decider | A | Whole packet | Decision memo, score 1–5, TAKE or PASS verdict |
| 15 | **Auto-execution** | Execution agent | — | — | Acts on line 9 of the memo. Watches the zones for the trigger. |

**In session:** trigger prints → the card + account state go to chat D (the in-session check) → CLEAR → the execution agent places the card exactly as written. BLOCK → no order. After any losing trade, rerun the tilt check before anything else. No other AI during the session.

**After the session (5 minutes):** run the debrief on each card in chat A, taken or not. Copy its journal fields into the row. Save the memo.

**Stop rules:** if the Analyst says EVENT DAY inside your window and your rules say no trading on those, or the Researcher says NO SETUP TODAY, or the tilt check or day check says CLOSED, the routine ends there. That's a finished routine, not a failed one.

**Short on time:** use the fast team in one chat. Keep the in-session check in its own chat.

#### Optional: schedule a pre-brief

If your tool can run a saved prompt on a schedule, schedule a short **pre-brief** to be ready when you sit down. A scheduled task can't see your chart, so keep it to things it can read: your rules and your checklist. It does not replace the event sheet, which is built from the calendar you paste.

```text
Pre-brief for {instrument}, {date}. Using my rules file and risk sheet only:
1. Remind me of my session window, my daily stop, my max trades and my news rule.
2. Print "This week's change" from my rules file.
3. Print my pre-session checklist: platform limits on, bracket template loaded, calendar rows copied, screenshots ready ({timeframes}).
Do not comment on price or on today's events. You cannot see my chart or my calendar.
```

Check your tool's current help pages for how scheduling works. Features and names change.

#### Pre-session checklist
- [ ] Platform daily loss limit is on
- [ ] Bracket template loaded, max size set
- [ ] Calendar rows copied as text, event sheet built
- [ ] Screenshots: high to low timeframe, price and time scales visible, latest bar on the right
- [ ] Chats A, B, C, D open in the team workspace
- [ ] Journal open

---

### Weekly review routine — 30 minutes, once a week

Pick a fixed slot after your last session of the week. Same slot every week.

| Minutes | Step |
|---|---|
| 0–5 | Clean the journal: every row has an ID, setup name, team score, risk verdict, rules_followed and result_r. Fill gaps from your memos and debriefs. |
| 5–8 | Export the week's rows as CSV (or copy the table). |
| 8–15 | Fresh chat, the Weekly Reviewer prompt. Paste the rows and last week's memo. |
| 15–20 | Check two numbers by hand: trades taken, and the count for "the rule I break most". If they don't match, fix the rows and rerun. |
| 20–25 | Decide on **one** change for next week. Write it in your rules file under "This week's change", with the date. If it changes a number in your risk sheet, change the platform setting too. |
| 25–30 | Save the memo with the week in its name. Rewatch one trade where a rule was broken, with the memo next to it. |

#### Weekly review memo — template

```text
WEEKLY REVIEW — week of {date}

Counts:        sessions {n} · memos {n} · trades taken {n} · passed {n} · taken without memo/CLEAR {n}
Rule adherence:    followed {n} · broken {n} · broken IDs: {…}
Rule I break most:  {rule} · {n} times · IDs {…} · when: {pattern}
Followed vs broken:  {x}R vs {y}R (descriptive only; sample: {n} trades)
Score check:     4–5 scored: {x}R over {n} · 1–3 scored: {y}R over {n} (descriptive only)
Overrides:      {list with IDs, or "none"}
Last week's change:  done / partly / not done — evidence: {…}
One change next week: {single, checkable action}
Keep doing:      {one thing, with evidence}
Data gaps:      {columns left empty, or "none"}
```

#### Once a month: the team review (20 minutes)

After the fourth weekly review, open a fresh chat and run the Monthly team review prompt with the month's rows and the four weekly memos. It goes through your rules one by one: how often each applied, how often it changed a decision, how often you broke it. At most one rule is retired or rewritten and one added or tightened. The daily stop, the per-trade maximum, the bracket rule and Part C of the risk sheet are never up for retirement.

#### Rules for the review
- One change per week. Not three.
- The reviewer describes behaviour. It doesn't redesign your strategy. Strategy questions go through the playbook method (Guide 11), with far more trades than one week.
- Fewer than 20 trades: the numbers describe the week. They don't prove anything about your edge.

---

### Journal columns

Use `journal-columns.csv` as the header row in a spreadsheet, a Notion table, or any tool that can export CSV. Fixed columns are the point: the weekly reviewer can only find patterns in columns that are filled the same way every day. The three example rows are illustrations, not results.

Log every **decision**, not only every trade. A passed card is a row too (`took_trade = N`). Passing on a score-2 plan is a skill and it belongs in the record.

| Column | What goes in it | Allowed values |
|---|---|---|
| trade_id | Unique ID | e.g. 2026-W41-03 |
| date | Session date | YYYY-MM-DD |
| session | Which session | e.g. NY AM, London |
| instrument | What you traded | e.g. MNQ, EURUSD |
| setup_name | Exact name from your setup sheet | one of your setup names |
| card_id | Which trade card | A, B, or none |
| team_score | Decider score | 1–5, or none |
| risk_verdict | Risk Manager's trade check | CLEAR, BLOCK, none |
| took_trade | Was it executed? | Y / N |
| direction | Long or short | long / short |
| entry, stop, target | Prices as placed | numbers |
| size | Contracts or lots | number |
| risk_money | Money at risk if stopped | number |
| risk_r | Risk in R (should be ≤ 1) | number |
| result_r | Result in R | number, filled after close |
| exit_reason | Why it closed | target / stop / time / manual / card cancelled |
| rules_followed | Every rule in rules file and risk sheet followed? | Y / N |
| rule_broken | If N: which rule, in the rule's own words | text |
| state_1to5 | Calm and rested, 1–5, before the session (the tilt check verdict can go in notes) | 1–5 |
| time_in, time_out | Entry and exit times | hh:mm |
| notes | One line. What you saw, what you felt. | text |
| screenshot_link | Chart at exit with entry/stop/target marked | link |

#### Three rules for the journal
1. Fill it the same day. A row written next week is a story, not a record.
2. `rules_followed` is binary. "Mostly" is N.
3. Never edit a past row's decision fields. If you learn something later, add it in notes with the date.

**Journal header row (CSV):**

```csv
trade_id,date,session,instrument,setup_name,card_id,team_score,risk_verdict,took_trade,direction,entry,stop,target,size,risk_money,risk_r,result_r,exit_reason,rules_followed,rule_broken,state_1to5,time_in,time_out,notes,screenshot_link
EX-001,example,NY AM,MNQ,Opening-range retest,A,4,CLEAR,Y,long,21452.00,21432.00,21492.00,5,200,1,example,target,Y,,4,09:52,10:31,EXAMPLE ROW - illustrative values only,
EX-002,example,NY AM,MNQ,Opening-range retest,none,none,none,Y,short,21470.00,21490.00,21430.00,5,200,1,example,stop,N,"traded without memo or CLEAR; inside news blackout",2,10:01,10:06,EXAMPLE ROW - illustrative values only,
EX-003,example,NY AM,MNQ,Opening-range retest,B,2,CLEAR,N,,,,,,,,,,Y,,3,,,EXAMPLE ROW - passed (score 2),
```

---

### Playbook brief

One page per strategy idea you are researching. Fill every blank in the "Locked before testing" block, date it, and do not change it while the test runs. A changed blank is a new brief with a new date and a fresh count.

A brief is a research document. It is not a setup sheet until it has climbed the evidence ladder on your own market (Guide 11).

```text
PLAYBOOK BRIEF — {name} — version {n} — locked on {date}

IDEA (one line):     {what is claimed}
WHY IT MIGHT WORK:    {the public reasoning, and who is on the other side}
WHY IT MIGHT NOT:     {costs, crowding, regime}
MARKET / SESSION / BARS: {instrument} · {session and time zone} · {timeframe}

LOCKED BEFORE TESTING
Context rules (yes/no):  1) {…} 2) {…} 3) {…}
Trigger (yes/no):     {…}
Entry:          {where, order type}
Stop:           {rule}
Target:          {rule}
Time exit:        {rule}
When not to trade:    1) {…} 2) {…}
Cost per trade assumed:  {commission + spread or slippage, in money and in R}
Sample before I look:   {at least 30 trades}
Periods to cover:     {dates, including a stretch that should not suit the idea}

FALSIFIERS (written before testing)
I drop this brief if:   1) {result and sample} 2) {…} 3) {…}

WHAT THE BEAR ATTACKS:  {the two weakest points}
EVIDENCE LADDER:     rung {1 idea / 2 rules / 3 sample / 4 walk-forward / 5 small size} since {date}
```

#### Test log columns

Log every qualifying day, taken or not. The Evidence Checker reads these rows.

```csv
trade_id,date,brief_version,qualified,took_trade,direction,entry,stop,exit,result_r,cost_r,exit_reason,rules_followed,notes
```

#### Rules for a brief
1. Blanks are filled before any results are seen. Settings chosen after looking are in-sample, and the count starts again.
2. One version under test at a time.
3. Costs are subtracted on every row.
4. Days that qualified and were not taken are rows too.
5. A brief moves to your rules file as a setup sheet only after rung 4, and it is traded at rung 5 size first.

*Educational only. Not financial advice. Trading involves risk.*


---

# Team kit: glossary

*Team kit · Reference · the team's vocabulary*

**In one line:** every term the library uses, defined in one or two plain sentences, so the team, the research assistant and you mean the same thing by the same word.

> **What's in this guide**
> - Team terms: packet, setup watch, trade card, memo, rubric, CLEAR and BLOCK.
> - Risk terms: R, risk budget, daily stop, bracket, drawdown types, the floor.
> - AI terms: anchoring, agreeing-with-you bias, invented detail, standing instructions.
> - Research terms: playbook, falsifier, in-sample, walk-forward, best-day dependence.
> - A worked example of the vocabulary in one sentence of a real routine.

![The team vocabulary](/media/course/17-team-vocabulary.png)

## 1. Team terms

| Term | Meaning |
|---|---|
| **Team** | AI agents, each with one job, running your rules automatically. |
| **Seat** | One job with one output format: Analyst, Researcher, Bull, Bear, Risk Manager, Trader, Decider. |
| **Team setup** | The standing instructions every seat reads: house rules, seat list, rubric, your rules file and risk sheet. |
| **FACTS check** | Typing FACTS in a new chat to confirm it reads the same instrument, session and limits as every other chat. |
| **Event sheet** | The News agent's list of today's scheduled events and blackout windows, built only from the calendar rows you paste. |
| **Rules file** | Your one-page description of what, when and how you trade, including your setup sheets. |
| **Setup sheet** | Your setup rewritten as yes/no rules: context, trigger, entry, invalidation, target, no-trade conditions. |
| **Context rule** | Something that must be true before the setup can exist (time window, structure, regime). |
| **Trigger** | The exact event that turns a watched setup into a trade. |
| **Invalidation** | The point where the trade idea is wrong. Your stop goes there. |
| **No-trade condition** | A rule that cancels the setup even if everything else passes. |
| **Market brief** | The Analyst's six-section description of today's market. |
| **Regime** | One of four labels for the day: TRENDING, RANGING, QUIET, EVENT DAY. |
| **Setup watch** | The Researcher's daily check: each rule PASS / FAIL / CAN'T TELL, plus watch zones. |
| **Watch zone** | A price area where your trigger could happen today. |
| **CAN'T TELL** | The chart given doesn't show enough to check a rule. Never upgraded to PASS. |
| **Packet** | The text that moves between seats: event sheet, brief, watch, scenario, cases, day check, card. |
| **Scenario** | One line describing the plan under review, given to both Bull and Bear. |
| **Rebuttal round** | Optional round 2: each side reads the other once and replies in five lines. |
| **Pre-mortem** | Assume the card was taken and lost, then name the three most likely reasons from the packet. |
| **Tell** | An observable event that shows a pre-mortem reason starting. |
| **Trade card** | The Trader's written order: trigger, valid window, entry, stop, target, size maths, bracket, cancel-if. |
| **Conditional card** | A trade card written before the session as IF trigger THEN order. |
| **Decision memo** | The Decider's one-page summary with a score and a TAKE or PASS verdict. |
| **Rubric** | The fixed 1–5 scoring rules. The score must quote the line that decided it. |
| **Decision line** | Line 9 of the memo: TAKE IF TRIGGERED or PASS, set by the score against your minimum score. The execution agent acts on it. |
| **Fast team** | All seats in one reply, for short days. Weaker. A fallback. |
| **In-session check** | The one-minute trade check in chat D before the order is sent. The risk gate. |
| **Execution agent** | The agent that places the order through your broker or prop API, only after a TAKE verdict and a CLEAR, only inside your limits. |
| **Debrief** | The after-session comparison of the card with what was executed: MATCH or DEVIATION, never the result. |

## 2. Risk terms

| Term | Meaning |
|---|---|
| **R** | Your fixed risk per trade, in money. A trade that loses its full stop loses 1R. |
| **Risk budget** | The maximum risk the Risk Manager allows per trade today, after your rules and size bands. |
| **Daily stop** | Your own maximum loss for the day. When reached, the team is CLOSED. |
| **TEAM ON / CLOSED** | The Risk Manager's day check verdict. |
| **CLEAR / BLOCK** | The Risk Manager's trade check verdict. A BLOCK isn't lifted in the same session. |
| **Blackout window** | Time around a scheduled event when your rules forbid entries. |
| **Tilt check** | Six yes/no questions about your state, counted against your own rule: GREEN, AMBER or TEAM OFF. |
| **Bracket order** | An entry sent with its stop and target attached. |
| **OCO** | One-cancels-other: when the stop or target fills, the other is cancelled. |
| **Size maths** | Budget ÷ (stop distance × value per point), rounded down, capped. |
| **First line / second line** | Platform limits (first) and the AI Risk Manager (second). |
| **Override** | Forcing through a trade the Risk Manager blocked, or trading without a memo. Always journaled. |
| **Floor** | In a prop evaluation, the equity level that fails the account. |
| **Static drawdown** | The floor is fixed below the starting balance. |
| **End-of-day trailing** | The floor is recalculated from the end-of-day balance. |
| **Intraday trailing** | The floor follows your highest equity in real time, including open profit. |
| **Room to the floor** | Current equity minus the floor. Sets the size band. |
| **Size band** | Normal, half, minimum or none, set by room to the floor. |
| **Consistency rule** | A firm rule limiting how much of total profit can come from one day. Details vary by firm. |

## 3. AI terms

| Term | Meaning |
|---|---|
| **Anchoring** | The model builds its answer around the frame in your question. |
| **Agreeing-with-you bias** | Chat assistants lean towards agreeing with the user. Sometimes called sycophancy. |
| **Invented detail** | Confident output with no source: a level not on your chart, an event not on your calendar. Often called hallucination. |
| **Source tag** | (chart) for values read off an image, (data) for values from numbers you pasted. |
| **Standing instructions** | Text saved in a workspace that applies to every chat in it. Tools call this different things. |
| **Fresh chat** | A new conversation with no history. Used to keep seats from seeing each other. |
| **Information hygiene** | Giving each seat only what it should see. |
| **Self-check line** | The last line of every prompt: the seat rereads its reply against the format and the arithmetic before sending. |
| **(unverified)** | The label a seat puts on anything that rests on its general knowledge instead of your evidence. |
| **Reasoning mode** | A setting in some tools that makes the model work step by step. Useful for maths and checks. |
| **Calibration test** | Comparing the AI's image-read levels against your own chart to learn its error size. |

## 4. Journal and review terms

| Term | Meaning |
|---|---|
| **rules_followed** | Y or N. "Mostly" is N. |
| **Descriptive only** | A number that describes what happened in a sample, not what will happen. |
| **Sample size** | How many trades a number is based on. Under 20, the weekly reviewer says so. |
| **One change** | The single, checkable change you make after each weekly review. |
| **Monthly team review** | The once-a-month pass over every rule: how often it applied, changed a decision, or was broken. |

## 5. Research terms

| Term | Meaning |
|---|---|
| **Playbook** | A public strategy family written as a research brief: idea, reasoning, rule template with blanks, what kills it. Not a setup. |
| **Playbook brief** | Your filled, dated, locked version of a playbook, ready to test. |
| **Hypothesis** | The idea as one sentence that could be wrong. |
| **Falsifier** | A result, written before testing, that means "drop it". |
| **Locked** | Every blank filled and dated before any results are seen. A changed blank is a new brief. |
| **Evidence ladder** | Five rungs: idea, rules, sample, walk-forward, small size. |
| **In-sample** | Results from the period used to choose the settings. They flatter. |
| **Out-of-sample** | Results from data the rules never saw. The only kind that tests anything. |
| **Walk-forward** | Locking the rules and trading them forward on demo, then counting again. |
| **Look-ahead** | A test that uses information you couldn't have had at the time. |
| **Survivorship** | Testing only on the examples you remember, which are the ones that worked. |
| **Best-day dependence** | A total that disappears when the single best day is removed. |
| **Slippage** | The difference between the price you wanted and the price you got. |
| **Crowding** | Many traders using the same public idea at the same levels. |

## 6. Worked example: the vocabulary in use

*Illustrative.*

"The **event sheet** showed nothing inside the window. The **brief** labelled the day **TRENDING**. The **setup watch** had all **context rules** PASS and one **watch zone**. The **Bear**'s best point was location, conceded in the **rebuttal round**. **Day check**: **TEAM ON**, **risk budget** 1R. The **conditional card** was sized by the **size maths**, sent as a **bracket**. The **memo** scored 3, quoting the **rubric**, and the **decision line** read TAKE IF TRIGGERED. The trigger printed, the **in-session check** said **CLEAR**, and the execution agent placed the card as written. The **debrief** was MATCH on every line."

## 7. Common mistakes

- **Using "signal" for a trade card.** A card is your plan, written by your rules. Nobody signals you anything.
- **Mixing up balance and room** in a trailing drawdown account.
- **Calling the score a probability.** It's a rubric line.
- **Calling a playbook a setup.** It becomes one after rung 4 of the evidence ladder, on your market.

## 8. Checklist

- [ ] I can explain R, risk budget and daily stop without looking
- [ ] I know my account's drawdown type by name
- [ ] I know the difference between CLEAR/BLOCK and TEAM ON/CLOSED

## Try it (5 minutes)

Pick the three terms in this guide you'd struggle to explain to a friend. Ask the research assistant about each one and note which guide it points you to.

*Educational only. Not financial advice. Trading involves risk.*
