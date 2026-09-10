# Scenario Presets

Use these when the user provides only a character or broad theme. Read `net-sense-framework.md` first. Treat presets as social jobs, not a mandatory emotion checklist.

## 8-Pack Everyday Portfolio

| Category | Trigger context | Surface message | Hidden emotion | Social move | Suggested mechanism | Meaning |
| --- | --- | --- | --- | --- | --- | --- |
| utility | conversation starts | greeting | friendly availability | open chat | character-specific entrance ritual | 你好 |
| utility | a task or message arrives | acknowledged | degree of willingness varies | acknowledge | restrained wording versus revealing body language | 收到 |
| utility | someone helps | sincere thanks | relief or warmth | strengthen relationship | small delayed emotional release | 谢谢 |
| utility | sender made a mistake | apology | embarrassment | repair relationship | confidence collapses into contrition | 抱歉 |
| persona | an unwanted request arrives | tentative agreement | reluctant surrender | comply without conflict | polite face versus body shutdown | 行吧 |
| persona | situation becomes difficult | confidence | internal panic | protect status | committed denial with visible evidence | 不慌 |
| persona | energy is gone | temporary retreat | total exhaustion | exit pressure | delayed collapse or literal flattening | 累了 |
| wildcard | something exceeds expectations | speechless reaction | overloaded disbelief | punctuate surprise | absurd overreaction with a screenshot-worthy pose | 离谱 |

## 16-Pack Work Chat Portfolio

Use 8 utility, 5 persona, and 3 wildcard concepts by default.

1. 收到: acknowledge a request; vary willingness through body language.
2. 在做了: reassure progress while exposing controlled panic.
3. 搞定: report completion with a character-specific victory ritual.
4. 我看看: buy thinking time without sounding dismissive.
5. 辛苦了: recognize effort with sincere warmth.
6. 麻烦你了: ask for help while softening the imposition.
7. 稍等: hold the conversation without disappearing.
8. 下线了: clearly close work communication.
9. 问题不大: maintain confidence while evidence says otherwise.
10. 我尽量: polite surrender without overpromising.
11. 再改改: absorb revision feedback with visible emotional cost.
12. 不是我: playful status defense without attacking anyone.
13. 我先撤: strategic social retreat.
14. 灵魂开会: body remains present while attention leaves.
15. 需求长大了: literalize scope expansion into a visual escalation.
16. 马上就好: time-distortion gag with a strong final pose.

For each item, replace the generic action with the active character's worldview, signature reaction, and visual hook.

## 24-Pack Expressive Portfolio

Start with 12 utility, 8 persona, and 4 wildcard jobs:

- Utility: greeting, acknowledge, thank, apologize, ask, encourage, wait, agree, soften refusal, comfort, good night, goodbye.
- Persona: pretend calm, reluctant surrender, claim credit, self-mockery, social retreat, suspicious agreement, shameless confidence, exhausted compliance.
- Wildcard: literalized pressure, delayed collapse, status reversal, absurd ceremonial reaction.

Do not assign final scenes from this list until every item has `trigger_utterance`, `hidden_emotion`, `social_move`, `meme_mechanism`, and `visual_hook`.

## Motion Guidance

Choose motion from the social beat, not from the emotion label.

- Use a delayed second beat when the humor comes from revealing the hidden emotion.
- Use `micro_expression`, `head_only`, or `single_limb` when restraint is the joke.
- Use `controlled_full_body` when collapse, escape, overreaction, or status reversal is the joke and the generated sequence can preserve identity.
- Keep text and props locked unless their movement is the single intended punchline.
- Make the most recognizable `punchline_frame` survive as a still image.

## Chinese Meaning Guidance

Use short Chinese metadata meanings, usually four characters or fewer. Meanings must be unique, but uniqueness alone is not enough: the underlying trigger context and social move must also be meaningfully distinct.
