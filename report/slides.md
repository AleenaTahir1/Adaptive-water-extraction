# Presentation Outline — 3-5 min demo

**Title:** Adaptive Water Extraction with Q-Learning Under Climate Stress
**Speaker:** Aleena Tahir (F23607001)

---

## Slide 1 — Title

- Project title, name, course, date
- One-line hook: *Can decentralized AI agents avoid the tragedy of the commons?*

---

## Slide 2 — The problem (30 s)

- Water scarcity, Indus Basin context (90 % of Pakistan's agriculture)
- Hardin's tragedy of the commons + climate change makes it worse
- Real farmers *learn*; existing ABMs assign fixed rules

---

## Slide 3 — The research question (15 s)

- Primary: How does γ affect emergent cooperation under climate stress?
- Sub-Qs: cooperation without enforcement? recovery from shock? minimum monitoring intensity?

---

## Slide 4 — The model in one diagram (30 s)

- 20 irrigator agents + 1 monitor + shared water with logistic regen
- Three-stage step: act → monitor → regenerate → finalize (Bellman update)
- Five discrete actions; state = (water bin, own last action, neighbor bin, climate)

---

## Slide 5 — Live demo (60-90 s)

- Launch `python run.py`
- Start with `p_detect = 0`, stable climate -> water collapses
- Reset, set `p_detect = 0.3` -> cooperation emerges
- Switch to `shock` -> watch the perturbation and recovery

---

## Slide 6 — Key result: enforcement threshold (30 s)

- Insert `figures/fig02_enforcement_effect.png`
- Final water vs `p_detect`: cooperation flips on around 0.2-0.3, saturates by 0.6
- Answers sub-Q3

---

## Slide 7 — Primary RQ: discount factor (30 s)

- Insert `figures/fig03_gamma_sweep.png`
- γ matters under shock, not under stable
- Interaction between RL hyperparameters and environment

---

## Slide 8 — Sensitivity & limitations (15 s)

- Insert `figures/fig04_sensitivity_tornado.png`
- Top sensitivities; honest caveats (tabular RL, single resource, 500-step horizon)

---

## Slide 9 — Takeaways (15 s)

1. Tragedy of the commons reproduced from pure Q-learners
2. Modest monitoring (`p_detect ≈ 0.3`) flips outcome
3. γ acts as a *resilience knob* under environmental stress
4. Full code + viz + batch infra at `github.com/.../ABM_Project`

---

## Slide 10 — Thank you / Q&A
