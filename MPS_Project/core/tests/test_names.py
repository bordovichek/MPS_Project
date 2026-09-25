from django.test import SimpleTestCase

from core.names import normalize_airport_name


class NormalizeAirportNameTests(SimpleTestCase):
    def test_title_case_and_particles(self):
        cases = {
            "DOMODEDOVO INTERNATIONAL AIRPORT": "Domodedovo International Airport",
            "PARIS CHARLES DE GAULLE": "Paris Charles de Gaulle",
            "NIKOLAYEVSK-NA-AMURE AIRPORT": "Nikolayevsk-na-Amure Airport",
            "CITY OF COLORADO SPRINGS MUNICIPAL": "City of Colorado Springs Municipal",
            "DEL RIO INTERNATIONAL AIRPORT": "Del Rio International Airport",
            "O'HARE INTERNATIONAL": "O'Hare International",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_airport_name(raw), expected)

    def test_abbreviations_and_initials_are_kept(self):
        self.assertEqual(normalize_airport_name("MICHAEL AAF"), "Michael AAF")
        self.assertEqual(normalize_airport_name("SPIRIT OF ST LOUIS AIRPORT"), "Spirit of St Louis Airport")
        self.assertEqual(normalize_airport_name("JOHNSTON LRRS"), "Johnston LRRS")
        self.assertEqual(normalize_airport_name("MARLBORO COUNTY H.E. AVENT FIELD"), "Marlboro County H.E. Avent Field")

    def test_truncated_openaip_names_are_completed(self):
        self.assertEqual(
            normalize_airport_name("CASPER-NATRONA COUNTY INTERNATIONAL AIRP"),
            "Casper-Natrona County International Airport",
        )
        self.assertEqual(
            normalize_airport_name("GENERAL JOSÉ MARÍA YÁÑEZ INTERNATIONAL A"),
            "General José María Yáñez International Airport",
        )

    def test_complete_forty_char_name_is_untouched(self):
        name = "JAMES M COX DAYTON INTERNATIONAL AIRPORT"
        self.assertEqual(len(name), 40)
        self.assertEqual(normalize_airport_name(name), "James M Cox Dayton International Airport")

    def test_mixed_case_is_left_as_is_and_function_is_idempotent(self):
        self.assertEqual(normalize_airport_name("  Pulkovo   Airport "), "Pulkovo Airport")
        once = normalize_airport_name("SHEREMETYEVO INTERNATIONAL AIRPORT")
        self.assertEqual(normalize_airport_name(once), once)
