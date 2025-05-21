from core.models_dir import Airport
from core.services_dir.openaip_import import get_airports_from_openaip


def processing_and_adding_to_the_bd_data_from_json_response(country: str,
                                                            limit: int = 100,
                                                            page: int = 1,
                                                            all_pages: bool = False):
    if len(country) != 2:
        raise ValueError("Country must be 2 characters long")
    if limit <= 0 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000")
    all_airports = []
    if all_pages:
        while True:
            info = get_airports_from_openaip(limit, country.upper(), page)
            airports = info.get("items", [])
            all_airports.extend(airports)
            if page >= info.get("totalPages", 1):
                break
            page += 1
    else:
        info = get_airports_from_openaip(limit, country.upper(), page)
        airports = info.get("items", [])
        all_airports.extend(airports)

    for airport in all_airports:
        try:
            iata_code = airport["iataCode"]
        except KeyError:
            continue
        country = airport["country"]
        name = airport["name"]
        latitude = airport["geometry"]["coordinates"][1]
        longitude = airport["geometry"]["coordinates"][0]
        if iata_code and Airport.objects.filter(iata_code=iata_code).exists():
            continue
        airport_obj = Airport(
            iata_code=iata_code,
            country=country,
            name=name,
            latitude=latitude,
            longitude=longitude
        )
        airport_obj.save()
