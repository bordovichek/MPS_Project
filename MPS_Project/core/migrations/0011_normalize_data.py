from django.db import migrations

from core.names import normalize_airport_name

RENAMES = {
    "Boeing-777-300ER": "Boeing 777-300ER",
    "Cessna-172": "Cessna 172 Skyhawk",
}

CORRECTIONS = {
    "Cessna 172 Skyhawk": {"year_of_manufacture": 1956, "capacity": 4, "consumption": 27, "max_distance": 1185},
}

ENGINES = {
    "Airbus A220-300": "2 × PW1500G",
    "Airbus A320": "2 × CFM56-5 / IAE V2500",
    "Airbus A320neo": "2 × CFM LEAP-1A / PW1100G",
    "Airbus A321XLR": "2 × CFM LEAP-1A / PW1100G",
    "Airbus A350-900": "2 × Rolls-Royce Trent XWB-84",
    "Airbus A380-800": "4 × Rolls-Royce Trent 900 / Engine Alliance GP7200",
    "ATR 72-600": "2 × PW127M",
    "Boeing 737-800": "2 × CFM56-7B",
    "Boeing 747-400": "4 × PW4000 / CF6-80C2 / RB211-524",
    "Boeing 757-200": "2 × RB211-535 / PW2000",
    "Boeing 777-300ER": "2 × GE90-115B",
    "Boeing 787-9 Dreamliner": "2 × GEnx-1B / Rolls-Royce Trent 1000",
    "Bombardier CRJ900": "2 × GE CF34-8C5",
    "Cessna 172 Skyhawk": "1 × Lycoming IO-360",
    "Comac C919": "2 × CFM LEAP-1C",
    "Concorde": "4 × Rolls-Royce/Snecma Olympus 593",
    "Dassault Falcon 8X": "3 × PW307D",
    "Embraer E195-E2": "2 × PW1900G",
    "Fokker 100": "2 × Rolls-Royce Tay 650",
    "Gulfstream G650ER": "2 × Rolls-Royce BR725",
    "Ilyushin Il-96": "4 × ПС-90А",
    "Pilatus PC-12": "1 × PT6A-67P",
    "Saab 340": "2 × GE CT7-9B",
    "Sukhoi Superjet 100": "2 × PowerJet SaM146",
    "Tupolev Tu-204": "2 × ПС-90А",
}


def normalize(apps, schema_editor):
    Airplane = apps.get_model("core", "Airplane")
    Airport = apps.get_model("core", "Airport")

    for old, new in RENAMES.items():
        if not Airplane.objects.filter(name=new).exists():
            Airplane.objects.filter(name=old).update(name=new)
    for name, fields in CORRECTIONS.items():
        Airplane.objects.filter(name=name).update(**fields)
    for name, engines in ENGINES.items():
        Airplane.objects.filter(name=name, engines="").update(engines=engines)

    Airport.objects.filter(description="No description").update(description="")
    airports = list(Airport.objects.only("pk", "name"))
    for airport in airports:
        airport.name = normalize_airport_name(airport.name)
    Airport.objects.bulk_update(airports, ["name"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_catalog_cleanup"),
    ]

    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
    ]
