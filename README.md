# Agent-Based Modeling of Adaptive Water Extraction Strategies Using Q-Learning Under Climate Stress

## Overview
A Mesa-based agent-based model simulating irrigator farmers who share a common water
resource (river / aquifer) and learn extraction strategies via tabular Q-learning. The model
investigates whether sustainable resource management can emerge from decentralized
reinforcement learning, and how climate stress (drought scenarios) disrupts learned
cooperation.

**Primary research question:** How does the discount factor (γ) in Q-learning agents affect the
emergence of sustainable water extraction strategies under varying climate stress scenarios?

## Project Structure

```
ABM_Project/
├── water_abm/              # Core model package
│   ├── q_learning.py       # Q-table, ε-greedy, Bellman update
│   ├── climate.py          # Climate scenario classes
│   ├── environment.py      # Shared water resource (logistic regeneration)
│   ├── agents.py           # Irrigator + Monitor agent classes
│   ├── model.py            # Mesa Model + DataCollector
│   └── server.py           # Mesa visualization server
├── experiments/            # Batch runs & sensitivity analysis
│   ├── batch_run.py
│   ├── sensitivity.py
│   └── analyze.py
├── data/results/           # Generated CSVs from batch runs
├── figures/                # Generated plots for the report
├── report/                 # Report, ODD protocol, slides
├── requirements.txt
└── run.py                  # Entry point — launches viz server
```

## Installation

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running

**Interactive visualization (recommended):**

```powershell
python run.py
```

Opens the Mesa visualization server at http://127.0.0.1:8521 with sliders for all
parameters and live charts.

**Batch experiments:**

```powershell
python -m experiments.batch_run
python -m experiments.sensitivity
python -m experiments.analyze
```

## Parameters

| Parameter | Symbol | Range | Description |
|---|---|---|---|
| Number of farmers | N | 5–100 | Total irrigator agents |
| Learning rate | α | 0.01–0.5 | Q-learning step size |
| Discount factor | γ | 0.5–0.99 | Future reward weight |
| Initial exploration | ε₀ | 0.1–1.0 | ε-greedy starting value |
| Regeneration rate | r | 0.01–0.3 | Logistic growth rate |
| Climate scenario | — | stable/gradual/shock/stochastic | Climate factor profile |
| Monitoring probability | p_detect | 0.0–1.0 | Probability monitor catches over-extractor |
| Q-learner proportion | — | 0–100% | Mix of Q-learners vs fixed-strategy agents |


## Authors
Aleena Tahir - F23607001
Saqlain Abbas - F23607048
Aena Habib - F23607020
Eman Asghar Kiani - F23607010
Dua Kamal -F23607023

## License

Academic project — for course use only.
