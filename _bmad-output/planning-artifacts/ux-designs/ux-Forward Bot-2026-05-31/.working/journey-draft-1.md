# Journey draft — "Hitesh tunes a too-aggressive filter"

**Protagonist:** Hitesh, the operator. Friday evening, second coffee. He runs ~40 sources across three folders (Crypto, Tech, Politics), forwarding into three destination channels for a private Telegram group of friends.

**Why he's here:** A friend in the group pinged him: "your Crypto Hub is dead silent today — markets are moving, what gives?" Hitesh suspects the keyword filter on his Crypto rule is over-blocking after he tightened it last week.

**Goal:** Find which messages got dropped, why, and fix the rule — within 10 minutes so he can get back to the weekend.

**Climax beat:** Step 6 — the moment Logs streams a new forwarded message in green where the previous identical message was muted-grey. The dashboard *proves* the fix worked in real time.

---

1. **Hitesh opens the dashboard** at `/`. The Dashboard health cards show Telegram green, MongoDB green, 47 active rules / 38 sources, 24h: **127 forwarded / 89 blocked / 0 failed**. The blocked count is higher than he remembers — confirms his suspicion. He clicks "View recent activity" or jumps straight to the nav.

2. **He goes to Logs** (`/logs`). The live tail is rolling. He filters by `event=blocked_keyword` to see only filter-blocks. The list is mostly his Crypto rule, blocking messages he'd actually want — "BTC dropped 4%", "ETH ATH", "SOL pumping." Each muted-grey row shows the source channel, the blocked keyword, and a correlation_id.

3. **He clicks a representative blocked row.** The row expands (or he uses the correlation_id link) to reveal: blocked_keyword was `pump`. He thinks: *right, I added that to filter out shitcoin spam, but it's also catching every "SOL pumping" post from the actual signal channels.* He needs a fix — either remove `pump`, scope it tighter, or move it to a per-source filter.

4. **He jumps to the rule** by clicking the rule name in the log row → lands on `/forwards/{id}` (Forward Edit). All panels collapsed. The Filters panel header summarizes: **"Filters — Block: 14 keywords, Allow: 0, Time: off, Sampling: off, Media: all"**. He clicks Filters to expand.

5. **He edits the block list** — finds `pump`, removes it. Below the field, validation runs: no regex error, list is now 13 items. He scrolls to the bottom, clicks Save. A toast: **"Forward updated. Reload pending — effects within 60s."** The rule is still active (was already on), so the toast also shows a small clock icon ticking the cache-refresh window. He doesn't have to do anything else.

6. **[Climax]** He goes back to Logs. The blocked feed is quieter already. Within ~40 seconds, a new event streams in: a **green ↗ row** from the same Crypto channel — **"SOL pumping past $200"** — *forwarded* this time. The dashboard just proved his fix in real time, without him having to bounce to Telegram to verify. He breathes out. He didn't have to think about cache invalidation or restart the service.

7. **He spot-checks two more events**, sees the green count tick up. Pings his friend: "fixed, give it a minute." Closes the laptop.

---

**Surfaces touched:** Dashboard (S1) → Logs (S7) → Forward Edit (S3) → Logs (S7).
**IA validation:** Every step landed on a surface the addendum already names. No orphan needs.
**What this journey reveals (open for confirmation):**
- The Logs row needs a **"jump to rule"** affordance — clicking the rule name in a log row should navigate to S3 for that rule. (Not in addendum §9.3 explicitly.)
- Panel header summary strings are **load-bearing** — if "Filters — Block: 14 keywords…" doesn't compute, the all-collapsed-by-default choice fails.
- The save toast needs to communicate **cache-refresh latency** ("effects within 60s") inline, not bury it. This is the trust beat — without it, the operator restarts the service unnecessarily.
- The "blocked" log severity must look meaningfully different from "forwarded" so the climax beat (green-where-grey-was) actually pops visually.
- **Hitesh never opened the source channel in Telegram** to verify — the dashboard's Logs view is his proof. Logs is therefore not just diagnostic; it's the *verification surface*. That promotes its design priority.
