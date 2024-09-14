# EPL API

The EPL API provides access to Premier League player statistics, fixtures, standings, and match results. Built with Django, FastAPI, and integrated tools for data parsing and validation, the API offers high performance and simplicity.

## Core Technologies

- **Django**: Manages the API's backend and core functionality.
- **FastAPI**: Powers the high-performance, asynchronous API endpoints.
- **BeautifulSoup**: Parses HTML from the Premier League website.
- **Pydantic**: Validates and serializes data for consistent API responses.

## Endpoints

### `GET /`

Retrieves general information about the API.

### `GET /stats/{p_name}`

Fetches statistics for a Premier League player by name. If multiple players match the query, a list of players is returned.

#### Example Response Get: player statistics

```json
[
  {
    "player_name": "Player Name",
    "appearances": "10",
    "goals": "5",
    "wins": "7",
    "losses": "3",
    "attack": { /* Attack stats */ },
    "team_play": { /* Team play stats */ },
    "discipline": { /* Discipline stats */ },
    "defence": { /* Defence stats */ }
  }
]
```

### `GET /table`

Retrieves the current Premier League standings.

#### Example Response Get: table

```json
[
  {
    "position": "1",
    "club": "Club Name",
    "played": "5",
    "won": "4",
    "drawn": "1",
    "lost": "0",
    "gf": "10",
    "ga": "2",
    "gd": "8",
    "points": "13",
    "form": "WWWDW"
  }
]
```

### `GET /results`

Fetches recent Premier League match results.

#### Example Response Get: results

```json
[
  {
    "home": "Home Team",
    "away": "Away Team",
    "score": "3-1"
  }
]
```

## Setup Instructions

1. Clone the repository:

   ```sh
   git clone https://github.com/23rdPro/epl.git
   ```

2. Install the required dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Run the application:

   ```sh
   uvicorn epl_api.asgi:app --reload
   ```
