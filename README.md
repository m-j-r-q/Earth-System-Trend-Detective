# Earth System Trend Detective

**Pick a place on Earth, pick what to measure, and find out whether it is really changing, by how much, and how sure we can be.**

Built for the NASA Space Apps Challenge 2026, challenge *"Be An Earth System Trend Detective!"*.

- Live app: https://earthsystemtrenddetective.netlify.app
- Live API: https://mjrq.pythonanywhere.com/api/health

---

## Why this project exists

NASA publishes decades of satellite and model data about our planet, but the data are large, technical and hard to read. Even when someone has a time series in front of them, two questions are hard to answer without statistics training:

1. **Is this a real trend, or just noise and the normal seasons?** Temperature and rainfall swing up and down every year. A line that slopes upward may be a genuine change, or it may be luck, or the result of choosing a convenient start date.
2. **How big is the change, and how certain are we?** A slope is not useful unless it comes with a margin of error.

This tool puts that analysis behind a map. Anyone can choose a region, choose variables such as temperature or rainfall, and get a plain-language answer, together with the evidence behind it. It also teaches as it goes: every variable has a short explanation, and guided demos show how easily a trend can be misread (for example, how a "drying" verdict can flip just by changing the start year).

## What it does

- **Interactive map.** Seven regions are drawn as soft, semi-transparent coloured shapes that follow their real outlines. Hovering shows what the region is and which variables are available. Clicking opens it.
- **Trend analysis.** For each variable you see the monthly series with the seasons removed, a 12-month average, the fitted trend line, and an illustrative verdict such as *"a significant increasing trend, 0.31 °C per decade (95% range 0.22 to 0.40)"*. A small interval "ruler" shows the margin of error against zero.
- **Adjustable question.** Change the years analysed and the confidence level (90, 95 or 99%) and watch the verdict respond.
- **Variable comparison.** Put several variables from one region on a shared axis and see how closely their anomalies move together.
- **Region comparison.** Put one variable from several regions side by side, with a flag when two regions have significant trends in opposite directions.
- **Guided demos.** Five walkthroughs (Sahel start-year dependence, the Upper Indus, opposite precipitation trends, Arctic warming, the Aral Sea). The text never states a result. Every number is filled in from live results, so the demos cannot drift out of date.
- **Variable explainers.** Each variable has a definition and a note on why it matters, shown on demand.

## The regions

| Region | Why it is interesting | Variables cached |
|---|---|---|
| Amazon Arc of Deforestation | Forest loss along the southern and eastern margin | air temperature, precipitation (satellite and model), soil moisture, evapotranspiration, aerosols |
| Aral Sea Basin | A lake that largely disappeared | same as above |
| Sahel | Semi-arid belt with a famous drought and recovery | same as above |
| Upper Indus and Karakoram | High mountains and glaciers | same as above |
| Indo-Gangetic Plain | Densely populated, heavily irrigated | same as above |
| California Central Valley | Irrigated farmland under water stress | same as above |
| Barents-Kara Arctic | Fast-warming ocean and sea ice | air temperature, precipitation (model) |

## Data

All series are **monthly area averages** (weighted by the cosine of latitude, so high-latitude grid cells count for less) over each region's bounding rectangle.

| Variable | Product | Notes |
|---|---|---|
| Air temperature at 2 m | MERRA-2 `M2TMNXSLV` v5.12.4 | 1980 onward. A reanalysis: a model constrained by observations. |
| Precipitation (model) | MERRA-2 `M2TMNXFLX` v5.12.4 | 1980 onward |
| Aerosol optical depth | MERRA-2 `M2TMNXAER` v5.12.4 | 1980 onward |
| Precipitation (satellite) | GPM IMERG Monthly `GPM_3IMERGM` v07 | 2000 onward |
| Soil moisture (0 to 10 cm), evapotranspiration | GLDAS Noah Land Surface Model `GLDAS_NOAH025_M` v2.1 | 2000 onward |
| Vegetation greenness (NDVI), land surface temperature | MODIS Terra `MOD13C2`, `MOD11C3` | **Listed in the catalogue but not yet cached.** These are HDF4 files and need a separate import. |

Data were downloaded from NASA's GES DISC archive with an Earthdata account, reduced to one small table per region and variable, and stored in `backend/data/`. The live app never calls NASA: it serves these cached files, so it is fast and cannot fail because an external service is down.

## How it works

```
NASA GES DISC archive
        |   scripts/build_cache.py  (runs once, on a developer machine)
        v
backend/data/<region>__<variable>.csv / .parquet     (monthly area means)
        |
        v
backend API (Flask)  ->  statistics engine (app/stats.py)  ->  JSON
        |
        v
React frontend: map, charts, verdicts, comparisons, demos
```

### The statistics, step by step

The statistics are in `backend/app/stats.py`.

1. **Remove the seasons.** Each month has the long-term average of that calendar month subtracted. What remains is the *anomaly*: how unusual that month was. Without this step the yearly cycle drowns out any trend.
2. **Fit a straight line (ordinary least squares).** Its slope is a quick estimate of change per decade. Month-to-month values are not independent: a warm month tends to follow a warm month. That correlation (lag-1 autocorrelation) shrinks the *effective* number of independent observations, so the confidence interval is widened accordingly. Ignoring this makes trends look more certain than they are.
3. **Mann-Kendall test.** A rank-based test of whether the series tends to rise or fall. It does not assume a straight line or a normal distribution, so it is robust to outliers. Its variance is inflated by the same autocorrelation correction.
4. **Sen's slope.** The median of all pairwise slopes. It is a robust estimate of change per decade, reported with a confidence interval (Gilbert's method).
5. **Verdict.** A plain-language sentence built from the test result, the slope, its 95% range and the p-value. When the range includes zero, or the period is short, the sentence says so, and the app warns about short windows.

**Checked by simulation.** On pure-noise series (no trend) with autocorrelation from 0 to 0.6, the corrected test flags a "significant" trend about 4 to 5% of the time, as it should at a 5% level. Without the correction, autocorrelated noise produces more false alarms.

### Where the data are processed

`scripts/build_cache.py` searches NASA's catalogue with `earthaccess`, reads each monthly file, averages each region, and saves the result. It reads through NASA's OPeNDAP service where that works (only the requested box is transferred) and falls back to downloading whole files where it does not (GLDAS and GPM). It runs granules in parallel, resumes where it stopped, checkpoints regularly, and stops early with a clear message if every request fails. `scripts/check_cache.py` audits the output: gaps, missing values, plausible ranges, and cross-checks such as satellite versus model rainfall and Arctic versus Sahel temperature.

## How it was built

- **Backend.** Python, pandas, SciPy and `pymannkendall`. The reference API is FastAPI (`app/main.py`). The deployed API is a Flask twin (`flask_app.py`) with identical endpoints and identical JSON, verified by a test that compares them. Reason: the free hosting service runs apps in a mode where FastAPI's compiled validation library hung, and Flask runs reliably there. The statistics code is shared and unchanged.
- **Frontend.** React 18, Vite, MapLibre GL for the map and Plotly for charts. A light, notebook-like design: a verdict headline first, evidence below, no decoration for its own sake. Colour carries meaning (blue for falling, magenta for rising).
- **Real region shapes.** Outlines come from Natural Earth. Each is rasterised to an image in map space, and a distance transform fades its opacity from a faint edge to a stronger core, so the region melts into the basemap. Hovering and clicking use the real polygon. `scripts/make_region_shapes.py` regenerates `frontend/public/regions.geojson` and prints how well each outline matches its data rectangle.
- **Testing.** 33 backend tests (statistics, API, cache builder with simulated downloads, Flask/FastAPI parity) and unit tests for the frontend helpers. Statistics were validated by Monte Carlo simulation.
- **Hosting.** Backend on PythonAnywhere, frontend on Netlify, one GitHub repository.

## Honest limitations

- **Rectangles, not shapes.** The map shows each region's real outline, but the statistics are averaged over a rectangle that encloses it. For compact regions the two match well. For others, such as the Sahel, the Central Valley and the Amazon arc, the rectangle includes surrounding land or covers only part of the outline. The side panel states the rectangle used. Masking the averages with the real polygons is the next improvement.
- **Some outlines are approximate.** The Amazon "arc of deforestation" has no standard polygon, so it is drawn as a band along the southern and eastern edge of the Amazon Basin. The Indo-Gangetic outline covers the Ganges Plain only. The Upper Indus uses the Karakoram and Hindu Kush ranges.
- **Monthly area means hide detail.** Averages over large boxes mix very different places, for example mountains and valleys.
- **Reanalysis is not observation.** MERRA-2 and GLDAS are model products constrained by observations. They are good for trends but are not raw measurements. The app shows satellite (GPM) and model (MERRA-2) rainfall side by side so you can compare them.
- **Statistics answer a narrow question.** A significant trend means a change is unlikely to be chance. It does not say why it happened.
- **Short windows are noisy.** This is shown on purpose in the demos.
- **Not yet included:** MODIS vegetation and land-surface temperature, forecasting, and anomaly detection (STA/LTA).

## Run it locally

Backend, from `backend/`:

```bash
pip install -r requirements.txt flask
python scripts/make_synthetic_cache.py                  # FAKE data for development only
DATA_DIR=data_synthetic python -m uvicorn app.main:app --reload    # reference API on :8000
# or the deployed variant:  DATA_DIR=data_synthetic flask --app flask_app run --port 8000
```

The app shows a banner whenever the server is using synthetic data, so fake numbers can never be mistaken for real ones.

To build the real cache, you need a free NASA Earthdata account with the *NASA GESDISC DATA ARCHIVE* application authorised in your profile:

```bash
pip install -r requirements-cache.txt pydap
python scripts/build_cache.py --vars T2M          # smoke test
python scripts/build_cache.py                     # everything (resumable)
python scripts/check_cache.py                     # audit the result
python scripts/parquet_to_csv.py                  # CSV copies for hosts without pyarrow
```

Frontend, from `frontend/`:

```bash
cp .env.example .env.local        # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Tests: `python -m pytest` in `backend/`, `npm test` in `frontend/`.

## Project structure

```
backend/
  app/main.py            reference API (FastAPI)
  app/stats.py           the statistics engine
  app/catalog/           regions.json, variables.json (definitions shown in the app)
  flask_app.py           deployed API (Flask), same endpoints and JSON
  pa_wsgi.py             entry point for PythonAnywhere
  scripts/               cache builder, audit, shape builder, converters
  data/                  cached monthly series
  tests/
frontend/
  public/regions.geojson real region outlines
  src/                   React app (map, analysis, comparisons, demos)
```

## Deploy

- **Backend (PythonAnywhere, free):** clone the repo, create a virtualenv with Flask, `pymannkendall` and the scientific stack, and point the WSGI file at `backend/pa_wsgi.py`. Set `CORS_ORIGINS` to the frontend URL to restrict access (default allows all).
- **Frontend (Netlify):** base directory `frontend`, build command `npm run build`, publish directory `frontend/dist`, and the environment variable `VITE_API_URL` set to the backend URL.

## Credits

**Data**
- MERRA-2 (Modern-Era Retrospective analysis for Research and Applications, Version 2): Global Modeling and Assimilation Office, NASA Goddard Space Flight Center. Gelaro, R., et al. (2017), *Journal of Climate*, 30(14), 5419-5454. Distributed by the NASA Goddard Earth Sciences Data and Information Services Center (GES DISC).
- GPM IMERG (Integrated Multi-satellitE Retrievals for GPM), monthly, Version 07: Huffman, G.J., et al., NASA GES DISC.
- GLDAS Noah Land Surface Model, Version 2.1: Rodell, M., et al. (2004), *Bulletin of the American Meteorological Society*, 85(3), 381-394. NASA GES DISC.
- MODIS Terra vegetation indices (MOD13C2) and land surface temperature (MOD11C3): NASA LP DAAC. *Catalogued; not yet used in the live data.*
- Region outlines: [Natural Earth](https://www.naturalearthdata.com/), public domain, via the [natural-earth-vector](https://github.com/nvkelso/natural-earth-vector) repository.
- Basemap: © [CARTO](https://carto.com/attributions), map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.

**Methods**
- Mann, H.B. (1945), *Econometrica*; Kendall, M.G. (1975), *Rank Correlation Methods*; Sen, P.K. (1968), *Journal of the American Statistical Association*; Gilbert, R.O. (1987), *Statistical Methods for Environmental Pollution Monitoring*.

**Software**
- FastAPI, Flask, pandas, NumPy, SciPy, [pymannkendall](https://github.com/mmhs013/pyMannKendall), earthaccess, xarray, React, Vite, MapLibre GL JS, Plotly.js, Vitest.
- Typefaces: Bricolage Grotesque and Newsreader (Google Fonts, SIL Open Font License).
- Hosting: PythonAnywhere (backend), Netlify (frontend).

**Built for** the NASA Space Apps Challenge 2026. This project is not endorsed by NASA.
