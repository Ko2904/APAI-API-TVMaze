# ScreenScope — TVMaze API Explorer

An interactive Streamlit app for exploring TV shows, episodes, cast, schedules,
and performer credits using the public [TVMaze REST API](https://www.tvmaze.com/api).
It is a small, runnable project for learning how to make HTTP requests, work with
JSON responses, and turn API data into an interface.

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key or environment variables are needed. An internet connection is
required.

## Explore

- **Discover shows** — fuzzy title search, ratings, genre distribution, show
  details, seasons, episode summaries, and main cast.
- **Daily schedule** — browse local TV or streaming schedules by date and
  country; choose all countries for the global streaming schedule.
- **People & credits** — search performers and inspect the shows they appear in.

The request code lives in [`tvmaze_client.py`](./tvmaze_client.py); the UI and
cached data functions are in [`app.py`](./app.py). Responses are cached in
Streamlit for one hour to keep repeated interactions quick and limit redundant
API calls. Errors from the API are shown in the app rather than being hidden.

## Learn the API

The app demonstrates these public endpoints:

| App feature | TVMaze endpoint |
| --- | --- |
| Show search | `/search/shows?q=...` |
| People search | `/search/people?q=...` |
| Show details | `/shows/{id}` |
| Episode guide | `/shows/{id}/episodes` |
| Main cast | `/shows/{id}/cast` |
| Local schedule | `/schedule?date=...&country=...` |
| Streaming schedule | `/schedule/web?date=...&country=...` |
| Performer credits | `/people/{id}/castcredits?embed=show` |

TVMaze documents a rate limit and caching behavior in its
[API documentation](https://www.tvmaze.com/api#rate-limiting). Be considerate
with request volume. TVMaze data is licensed under
[CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/); keep attribution
and the license in mind when reusing or redistributing data. Images belong to
their respective rights holders.

## Run the tests

```bash
python -m unittest discover -s tests
```
