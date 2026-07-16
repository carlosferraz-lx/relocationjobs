# QA Relocation Job Finder

A personal, daily job finder for **QA / test-automation roles that come with
relocation support**, targeting the UK and the Nordics (Norway, Sweden, Iceland,
Denmark, Finland). It filters by your skills, keeps only roles you could
realistically take (relocation/visa rules for an EU citizen), and flags whether
the pay preserves your current **standard of living** vs. a Portugal baseline.

Results are published as a static **GitHub Pages dashboard** — no email, no
servers, no secrets required.

## How it works

```
 sources ─▶ normalise ─▶ match (skills + relocation + country + salary) ─▶ dedupe
        ─▶ diff against seen_jobs.json ─▶ write docs/data.json ─▶ GitHub Pages
```

A scheduled GitHub Actions workflow (`.github/workflows/daily.yml`) runs the
pipeline every morning, remembers what it has already shown you, and redeploys
the dashboard with newly-found roles flagged **NEW**.

## Job sources (all free)

| Source | Coverage | Salary data | Key needed |
|--------|----------|-------------|------------|
| Platsbanken (Arbetsförmedlingen) | Sweden (official) | rare | no |
| NAV Arbeidsplassen | Norway (official) | rare | no |
| Landing.jobs | Portugal/EU tech (has `relocation_paid` + salary) | yes | no |
| Arbeitnow | EU-wide board | sometimes | no |
| Remote OK | Remote (target-country only) | sometimes | no |
| Himalayas | Remote (target-country only) | often | no |
| **Adzuna** | **UK** + more, rich salary data | **yes** | **free key** |

> Sweden and Norway have excellent official APIs, so coverage there is deep.
> Denmark, Finland and Iceland have no comparable free API, so those come from
> the EU-wide/remote boards and will be sparser. **Enable Adzuna** (below) for
> solid UK coverage with real salaries.

## The "standard of living" salary floor

Your current salary buys a certain lifestyle in Portugal. To keep it elsewhere
you need enough **net** income to cover the local cost of living, which implies a
minimum **gross** salary given local taxes:

```
portugal_net       = current_gross * net_ratio[PT]
required_net(C)    = portugal_net * (cost_of_living[C] / cost_of_living[PT]) * margin
required_gross(C)  = required_net(C) / net_ratio[C]
```

Cost-of-living indices, net-of-tax ratios and FX rates live in
[`jobfinder/cost_of_living.py`](jobfinder/cost_of_living.py) and are easy to
edit. They are approximations — treat the per-country floor shown on the
dashboard as guidance, not gospel. When an ad lists no salary (common in the
Nordics) the role is kept and marked *not stated*.

## Configure it

Everything you'd want to tune lives in [`profile.yaml`](profile.yaml):

- your skills (weighted) and QA job-title keywords
- target countries and whether to include remote roles
- `require_relocation_support` and the relocation/visa signal phrases
- salary margin and whether to keep salary-unknown roles
- which sources are enabled

### Relocation logic

You're treated as an EU/EEA citizen (`candidate.eu_eea_citizen: true`), so:

- **Nordic countries (EEA):** kept even without an explicit relocation blurb —
  you can legally move and take the job.
- **United Kingdom:** kept only if the ad mentions **visa sponsorship / work
  permit**, since that's mandatory for you post-Brexit.

Use the dashboard's *Relocation/visa only* filter to narrow to ads that
explicitly advertise a relocation package or sponsorship.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m jobfinder.run --state data/seen_jobs.json -v   # fetch + build dashboard
open docs/index.html                                     # view the dashboard

ruff check . && pytest -q                                # lint + tests
```

`--dry-run` runs the pipeline without updating the seen-jobs state.

## Enable Adzuna (optional, recommended for the UK)

1. Get a free key at <https://developer.adzuna.com/>.
2. Add two repository secrets: `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
   (Settings → Secrets and variables → Actions).

The daily workflow passes them through automatically; locally, export them
before running.

## Enable the dashboard (one-time)

In the repo: **Settings → Pages → Build and deployment → Source: GitHub
Actions**. After the first successful `Daily job finder` run, your dashboard is
live at `https://<your-user>.github.io/relocation-job-finder/`.
