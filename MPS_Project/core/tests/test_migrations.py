from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class LegacyDataMigrationTests(TransactionTestCase):
    """Обновление боевой базы: данные в формате 0009 должны корректно пройти 0010–0011."""

    before = [("core", "0009_airplane_in_service")]
    after = [("core", "0011_normalize_data")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        apps = executor.loader.project_state(self.before).apps
        Airplane = apps.get_model("core", "Airplane")
        Airport = apps.get_model("core", "Airport")
        Airplane.objects.create(
            name="Cessna-172",
            year_of_manufacture=2009,
            capacity=20,
            engine_power=90000,
            consumption=40,
            cruise_speed=226,
            max_distance=2000,
            image="media_plane_photo/cessnaphoto.webp",
        )
        Airplane.objects.create(
            name="Boeing 737-800", engine_power=26000, consumption=2500, cruise_speed=850, max_distance=5665
        )
        Airport.objects.create(iata_code="SVO", country="RU", name="SHEREMETYEVO", latitude=55.97, longitude=37.41)
        Airport.objects.create(
            iata_code="LED", country="RU", name="Pulkovo", latitude=59.8, longitude=30.26, description="Питер"
        )

    def tearDown(self):
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_upgrade(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        apps = executor.loader.project_state(self.after).apps
        Airplane = apps.get_model("core", "Airplane")
        Airport = apps.get_model("core", "Airport")

        cessna = Airplane.objects.get(name="Cessna 172 Skyhawk")
        self.assertEqual((cessna.capacity, cessna.year_of_manufacture, cessna.max_distance), (4, 1956, 1185))
        self.assertEqual(cessna.engines, "1 × Lycoming IO-360")
        self.assertEqual(str(cessna.image), "media_plane_photo/cessnaphoto.webp")
        self.assertEqual(Airplane.objects.get(name="Boeing 737-800").engines, "2 × CFM56-7B")

        self.assertEqual(Airport.objects.get(iata_code="SVO").name, "Sheremetyevo")
        self.assertEqual(Airport.objects.get(iata_code="SVO").description, "")
        self.assertEqual(Airport.objects.get(iata_code="LED").description, "Питер")
