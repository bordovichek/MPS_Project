import requests
from MPS_Project.settings import OPENAIP_API_KEY
from core.models_dir import Airport

API_KEY = OPENAIP_API_KEY


def get_airports_from_openaip(limit: int = 1000, country_code: str = "RU", page : int = 1):
    url = "https://api.core.openaip.net/api/airports"
    headers = {
        "x-openaip-api-key": API_KEY
    }
    params = {
        "limit": limit,
        "country": country_code,
        "page": page
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        airports = data.get("airports", data)
        return airports
    except requests.RequestException as e:
        print(response.text)
        print(f"Ошибка при запросе к OpenAIP API: {e}")
        return None
