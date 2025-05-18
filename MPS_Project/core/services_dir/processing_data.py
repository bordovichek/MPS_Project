from core.services_dir.openaip_import import get_airports_from_openaip


def processing_and_adding_to_the_bd_data_from_json_response():
    limit = 1000
    page = 1
    all_airports = []
    while True:
        info = get_airports_from_openaip(limit, "US", page)
        airports = info.get("items", [])
        all_airports.extend(airports)
        if page >= info.get("totalPages", 1):
            break
        page += 1

    for airport in all_airports:
        try:
            iata_code = airport["iataCode"]
        except KeyError:
            continue
        country = airport["country"]
        name = airport["name"]
        latitude = airport["geometry"]["coordinates"][0]
        longitude = airport["geometry"]["coordinates"][1]
        bd_data = {
            "iataCode": iata_code,
            "country": country,
            "name": name,
            "latitude": latitude,
            "longitude": longitude
        }
        print(bd_data)
