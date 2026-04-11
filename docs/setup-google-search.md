# Google Custom Search Setup

The iteration 2 talent flow tracker discovers LinkedIn profiles via Google's
**Custom Search JSON API** — free tier: **100 queries/day**.

## 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com/
2. Create a new project (or reuse one). Give it any name, e.g. `aijobcrawler`.

## 2. Enable the Custom Search JSON API

1. Open https://console.cloud.google.com/apis/library/customsearch.googleapis.com
2. Make sure your project is selected.
3. Click **Enable**.

## 3. Create an API key

1. Go to https://console.cloud.google.com/apis/credentials
2. Click **Create Credentials → API key**.
3. Copy the key. Optionally restrict it to the "Custom Search API".

This is your `GOOGLE_API_KEY`.

## 4. Create a Programmable Search Engine

1. Go to https://programmablesearchengine.google.com/
2. Click **Add**.
3. Under **What to search?**, pick **Search specific sites or pages**.
4. Add this site: `linkedin.com/in/*`
5. Name the engine anything (e.g. `linkedin-profiles`).
6. Click **Create**, then **Control Panel**.
7. Copy the **Search engine ID** — that's your `GOOGLE_CX`.

Optional: in the control panel, turn on **Image search: off** and
**Search the entire web: off** — we only want `linkedin.com/in/*`.

## 5. Set the environment variables

### Bash / Git Bash

```bash
export GOOGLE_API_KEY="AIza...your-key"
export GOOGLE_CX="abcdef1234567890:xyz"
```

Add to `~/.bashrc` to persist.

### PowerShell (session)

```powershell
$env:GOOGLE_API_KEY = "AIza...your-key"
$env:GOOGLE_CX      = "abcdef1234567890:xyz"
```

### PowerShell (persistent, user scope)

```powershell
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "AIza...", "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_CX",      "abcdef...", "User")
```

You must start a new terminal for persistent values to take effect.

### cmd.exe (persistent)

```cmd
setx GOOGLE_API_KEY "AIza...your-key"
setx GOOGLE_CX      "abcdef1234567890:xyz"
```

## 6. Free tier limits

- **100 queries per day.** After that, the API returns HTTP 429 and
  `GoogleSearchClient.search()` returns an empty list and logs a warning.
- There is a paid tier ($5 per 1000 queries, up to 10k/day) if you ever need more.
- With 20 source labs × 4 query templates, a single `discover-all` run costs
  ~80 queries — well within the free quota, but only **one run per day**.
  Use `--max-queries-per-lab 2` to stay even lighter (40 queries/run).

## 7. Verify it works

```bash
python -c "from search_client import GoogleSearchClient; \
           print(GoogleSearchClient().search('site:linkedin.com/in \"ex-OpenAI\"', num=3))"
```

You should see a list of 3 result dicts. If you see `[]`, check:
- Both env vars are set (`echo $GOOGLE_API_KEY`, `echo $GOOGLE_CX`)
- The Custom Search JSON API is enabled on the same project as the key
- Your search engine includes `linkedin.com/in/*`

## 8. Run the talent flow pipeline

```bash
python main.py discover-all --max-queries-per-lab 2 --min-talent 2
```

Outputs land in `output/`:
- `tracker.md` — ranked company table
- `talent_sankey.html` — interactive Sankey diagram
- `talent_ranking.png` — bar chart
- `talent_heatmap.png` — lab × company heatmap
