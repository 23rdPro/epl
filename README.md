# epl API

The epl API is designed to retrieve player statistics, fixtures, tables, and results from the Premier League web app. This API is built using Django for the backend, with FastAPI for high-performance API endpoints, BeautifulSoup for HTML parsing, and Pydantic for data validation and serialization.

## Technologies

- **Django**: A Python web framework for building the API's backend.
- **BeautifulSoup**: A Python library for parsing HTML and XML documents.
- **FastAPI**: A modern, high-performance Python web framework for building APIs.
- **Pydantic**: A data validation and serialization library for Python.

## API Endpoints

### `GET /`

This endpoint retrieves the root information of the API.

### `GET /stats/{p_name}`

Retrieves information about a Premier League player with the given name. The player name should be provided as a URL parameter. If filter returns multiple hits, it will return a list instead.

**Returns**:

```json
{
    "name": "name", 
    // todo
}

### `GET /table`

