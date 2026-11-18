from __future__ import annotations

import re
from collections import Counter
from datetime import date
from html import unescape
from typing import Any

import requests
import streamlit as st

from tvmaze_client import TVMazeClient


st.set_page_config(
    page_title="ScreenScope | TVMaze Explorer",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded",
)

API = TVMazeClient()


@st.cache_data(ttl=3600, show_spinner=False)
def search_shows(query: str) -> list[dict[str, Any]]:
    return API.search_shows(query)


@st.cache_data(ttl=3600, show_spinner=False)
def search_people(query: str) -> list[dict[str, Any]]:
    return API.search_people(query)


@st.cache_data(ttl=3600, show_spinner=False)
def get_show(show_id: int) -> dict[str, Any]:
    return API.get_show(show_id)


@st.cache_data(ttl=3600, show_spinner=False)
def get_episodes(show_id: int, include_specials: bool) -> list[dict[str, Any]]:
    return API.get_episodes(show_id, include_specials)


@st.cache_data(ttl=3600, show_spinner=False)
def get_cast(show_id: int) -> list[dict[str, Any]]:
    return API.get_cast(show_id)


@st.cache_data(ttl=3600, show_spinner=False)
def get_schedule(
    selected_date: str,
    country: str,
    streaming: bool,
) -> list[dict[str, Any]]:
    return API.get_schedule(selected_date, country, streaming)


@st.cache_data(ttl=3600, show_spinner=False)
def get_person_credits(person_id: int) -> list[dict[str, Any]]:
    return API.search_person_cast_credits(person_id)


def plain_text(markup: str | None) -> str:
    if not markup:
        return ""
    with_line_breaks = re.sub(r"</(?:p|li|br)\s*>", "\n", markup, flags=re.I)
    return unescape(re.sub(r"<[^>]*>", "", with_line_breaks)).strip()


def show_rating(show: dict[str, Any]) -> str:
    rating = (show.get("rating") or {}).get("average")
    return f"{rating:.1f}" if isinstance(rating, (int, float)) else "N/A"


def show_search_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.info("No matches yet. Try another title or a shorter search.")
        return

    shows = [item["show"] for item in results if item.get("show")]
    genre_counts = Counter(
        genre for show in shows for genre in show.get("genres", [])
    )
    if genre_counts:
        st.markdown("#### What’s in these results?")
        st.bar_chart(
            {
                "Shows": dict(genre_counts.most_common(8)),
            },
            height=190,
        )

    st.markdown(f"#### {len(shows)} matching shows")
    columns = st.columns(2)
    for index, show in enumerate(shows):
        with columns[index % 2]:
            with st.container(border=True):
                image = (show.get("image") or {}).get("medium")
                poster_col, info_col = st.columns([1, 2.4])
                with poster_col:
                    if image:
                        st.image(image, use_container_width=True)
                    else:
                        st.markdown("### 🎬")
                with info_col:
                    st.markdown(f"### {show.get('name', 'Untitled')}")
                    genres = " · ".join(show.get("genres") or []) or "Genre unknown"
                    year = (show.get("premiered") or "—")[:4]
                    st.caption(f"{genres}  \n{year} · {show.get('status', 'Unknown')}")
                    st.markdown(f"**Rating:** {show_rating(show)} / 10")
                    if st.button(
                        "Open show",
                        key=f"open-show-{show['id']}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_show_id"] = show["id"]
                        st.rerun()


def show_detail(show_id: int) -> None:
    try:
        with st.spinner("Loading show, episode guide, and cast from TVMaze…"):
            show = get_show(show_id)
            episodes = get_episodes(show_id, include_specials=True)
            cast = get_cast(show_id)
    except (requests.RequestException, ValueError) as error:
        st.error(f"Could not load this show from TVMaze: {error}")
        return

    if st.button("← Back to show search"):
        st.session_state["selected_show_id"] = None
        st.rerun()

    st.divider()
    poster, overview = st.columns([1, 3])
    image = (show.get("image") or {}).get("original") or (show.get("image") or {}).get("medium")
    with poster:
        if image:
            st.image(image, use_container_width=True)
    with overview:
        st.markdown(f"## {show.get('name', 'Untitled')}")
        genres = " · ".join(show.get("genres") or []) or "Genres not listed"
        st.caption(
            f"{genres}  |  {show.get('language') or 'Language unknown'}  |  "
            f"{show.get('status') or 'Status unknown'}"
        )
        metrics = st.columns(4)
        metrics[0].metric("TVMaze rating", f"{show_rating(show)} / 10")
        metrics[1].metric("Episodes", len(episodes))
        metrics[2].metric("Runtime", f"{show.get('averageRuntime') or show.get('runtime') or '—'} min")
        network = show.get("network") or show.get("webChannel") or {}
        metrics[3].metric("Network / platform", network.get("name") or "—")
        summary = plain_text(show.get("summary"))
        if summary:
            st.write(summary)
        if show.get("url"):
            st.link_button("Open on TVMaze", show["url"])

    st.markdown("### Episode guide")
    if not episodes:
        st.info("TVMaze has no episode information for this show yet.")
    else:
        seasons = sorted({episode.get("season", 0) for episode in episodes})
        season_labels = {
            season: "Specials" if season == 0 else f"Season {season}"
            for season in seasons
        }
        selected_season = st.selectbox(
            "Choose a season",
            seasons,
            format_func=lambda season: season_labels[season],
            key=f"season-{show_id}",
        )
        season_episodes = [
            episode for episode in episodes
            if episode.get("season", 0) == selected_season
        ]
        st.caption(f"{len(season_episodes)} episodes in {season_labels[selected_season].lower()}")
        rows = [
            {
                "Episode": episode.get("number") or "Special",
                "Title": episode.get("name") or "Untitled",
                "Air date": episode.get("airdate") or "Unknown",
                "Runtime": f"{episode['runtime']} min" if episode.get("runtime") else "—",
                "Rating": show_rating(episode),
            }
            for episode in season_episodes
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        episode_names = [
            f"{episode.get('number') or 'Special'} · {episode.get('name') or 'Untitled'}"
            for episode in season_episodes
        ]
        selected_episode_index = st.selectbox(
            "Explore an episode",
            range(len(season_episodes)),
            format_func=lambda index: episode_names[index],
            key=f"episode-{show_id}-{selected_season}",
        )
        episode = season_episodes[selected_episode_index]
        with st.container(border=True):
            st.markdown(f"#### {episode.get('name') or 'Untitled'}")
            episode_summary = plain_text(episode.get("summary"))
            if episode_summary:
                st.write(episode_summary)
            else:
                st.caption("No episode summary is available.")

    st.markdown("### Main cast")
    if not cast:
        st.caption("No cast information is listed.")
    else:
        cast_columns = st.columns(4)
        for index, member in enumerate(cast[:12]):
            person = member.get("person") or {}
            character = member.get("character") or {}
            with cast_columns[index % 4]:
                portrait = (person.get("image") or {}).get("medium")
                if portrait:
                    st.image(portrait, use_container_width=True)
                st.markdown(f"**{person.get('name', 'Unknown performer')}**")
                st.caption(f"as {character.get('name', 'Unknown character')}")


def page_discover() -> None:
    st.markdown("# Find your next series")
    st.markdown(
        "Search TVMaze’s show catalogue, compare matches, then dive into episode guides and cast."
    )
    with st.form("show-search"):
        query = st.text_input(
            "Show title",
            placeholder="Try The Bear, Severance, or a typo — search is fuzzy",
        ).strip()
        submitted = st.form_submit_button("Search shows", type="primary")
    if submitted:
        st.session_state["show_results_query"] = query
        st.session_state["selected_show_id"] = None
        if query:
            try:
                with st.spinner(f"Searching TVMaze for “{query}”…"):
                    st.session_state["show_results"] = search_shows(query)
            except (requests.RequestException, ValueError) as error:
                st.error(f"TVMaze show search failed: {error}")
                st.session_state["show_results"] = []
        else:
            st.warning("Enter a show title to search.")

    selected_show_id = st.session_state.get("selected_show_id")
    if selected_show_id:
        show_detail(selected_show_id)
    elif "show_results" in st.session_state:
        query = st.session_state.get("show_results_query") or "your search"
        st.markdown(f"### Results for “{query}”")
        show_search_results(st.session_state["show_results"])
    else:
        st.markdown("### Start exploring")
        st.info(
            "Search a show above to see its ratings, episode guide, season breakdown, "
            "cast, and character information."
        )


def page_schedule() -> None:
    st.markdown("# What’s airing?")
    st.markdown("Browse TVMaze’s local TV schedule or its streaming schedule.")
    controls = st.columns([1, 1, 2])
    with controls[0]:
        selected_date = st.date_input("Air date", value=date.today())
    with controls[1]:
        country = st.selectbox(
            "Country",
            ["US", "GB", "DE", "CA", "AU", "FR", "JP"],
            format_func=lambda code: {
                "US": "🇺🇸 United States",
                "GB": "🇬🇧 United Kingdom",
                "DE": "🇩🇪 Germany",
                "CA": "🇨🇦 Canada",
                "AU": "🇦🇺 Australia",
                "FR": "🇫🇷 France",
                "JP": "🇯🇵 Japan",
            }[code],
        )
    with controls[2]:
        streaming = st.toggle("Streaming / web schedule")
        if streaming:
            st.caption("Select “All countries” to include global streaming channels.")
    if streaming and st.checkbox("All countries", value=False):
        country = ""

    date_text = selected_date.isoformat()
    try:
        with st.spinner("Fetching the schedule…"):
            episodes = get_schedule(date_text, country, streaming)
    except (requests.RequestException, ValueError) as error:
        st.error(f"Could not load the schedule: {error}")
        return

    st.markdown(f"### {len(episodes)} episodes on {selected_date:%A, %B %-d}")
    if not episodes:
        st.info("No episodes are listed for this date and selection.")
        return

    for episode in episodes:
        show = episode.get("show") or {}
        channel = show.get("webChannel") or show.get("network") or {}
        with st.container(border=True):
            columns = st.columns([1, 4])
            with columns[0]:
                image = (show.get("image") or {}).get("medium")
                if image:
                    st.image(image, use_container_width=True)
            with columns[1]:
                title = show.get("name") or "Unknown show"
                episode_name = episode.get("name") or "Untitled episode"
                st.markdown(f"### {episode.get('airtime') or 'Time TBA'} · {title}")
                season = episode.get("season")
                number = episode.get("number")
                ep_number = f"S{season:02d}E{number:02d}" if season and number else "Special"
                st.markdown(
                    f"**{ep_number}: {episode_name}**  \n"
                    f"{channel.get('name') or 'Channel unknown'}"
                )
                summary = plain_text(episode.get("summary"))
                if summary:
                    st.write(summary)


def page_people() -> None:
    st.markdown("# People & credits")
    st.markdown("Look up an actor and explore their TVMaze cast credits.")
    with st.form("people-search"):
        query = st.text_input("Actor name", placeholder="For example, Pedro Pascal").strip()
        submitted = st.form_submit_button("Search people", type="primary")
    if submitted:
        st.session_state["person_results_query"] = query
        st.session_state["selected_person_id"] = None
        if query:
            try:
                with st.spinner(f"Searching TVMaze for “{query}”…"):
                    st.session_state["person_results"] = search_people(query)
            except (requests.RequestException, ValueError) as error:
                st.error(f"TVMaze people search failed: {error}")
                st.session_state["person_results"] = []
        else:
            st.warning("Enter a name to search.")

    results = st.session_state.get("person_results", [])
    if not results:
        st.info("Search for an actor to view their TVMaze credits.")
        return

    selected_id = st.session_state.get("selected_person_id")
    if selected_id is None:
        for item in results:
            person = item.get("person") or {}
            with st.container(border=True):
                columns = st.columns([1, 4, 1])
                image = (person.get("image") or {}).get("medium")
                with columns[0]:
                    if image:
                        st.image(image, use_container_width=True)
                with columns[1]:
                    st.markdown(f"### {person.get('name', 'Unknown performer')}")
                    country_info = person.get("country") or {}
                    details = [country_info.get("name"), person.get("gender")]
                    st.caption(" · ".join(value for value in details if value) or "No details listed")
                with columns[2]:
                    if st.button("View credits", key=f"person-{person['id']}"):
                        st.session_state["selected_person_id"] = person["id"]
                        st.rerun()
    else:
        person = next(
            (
                item["person"] for item in results
                if item.get("person", {}).get("id") == selected_id
            ),
            None,
        )
        if person is None:
            st.session_state["selected_person_id"] = None
            st.rerun()
        if st.button("← Back to people"):
            st.session_state["selected_person_id"] = None
            st.rerun()
        st.markdown(f"## {person.get('name', 'Performer')} — cast credits")
        try:
            credits = get_person_credits(selected_id)
        except (requests.RequestException, ValueError) as error:
            st.error(f"Could not load cast credits: {error}")
            return
        shows = []
        for credit in credits:
            show = (credit.get("_embedded") or {}).get("show")
            if show:
                shows.append(show)
        st.metric("TV shows credited", len(shows))
        for show in shows:
            st.markdown(
                f"- **{show.get('name', 'Untitled')}** "
                f"({show.get('premiered') or 'year unknown'}) — "
                f"{show.get('status') or 'status unknown'}"
            )


def main() -> None:
    with st.sidebar:
        st.markdown("# 📺 ScreenScope")
        st.caption("A hands-on TVMaze API explorer")
        page = st.radio(
            "Explore",
            ["Discover shows", "Daily schedule", "People & credits"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("**API in use**")
        st.code("api.tvmaze.com", language="text")
        st.caption("Public REST API · JSON · cached for one hour")
        st.markdown("[TVMaze API documentation](https://www.tvmaze.com/api)")
        st.caption("Show and episode data supplied by TVMaze.")

    if page == "Discover shows":
        page_discover()
    elif page == "Daily schedule":
        page_schedule()
    else:
        page_people()


if __name__ == "__main__":
    main()
