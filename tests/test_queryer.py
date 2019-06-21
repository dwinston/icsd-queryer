from tests.test_random import abolished_keys, new_keys, conflicting_keys
import time
import random
import glob
import json
import platform
from icsd.queryer import Queryer
import unittest


is_mac = platform.system() == 'Darwin'


class TestQueryer(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_dummy_data(self):
        queryer = Queryer()

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_AlOF(self):
        query = {
            'composition': 'Al O F',
            'number_of_elements': '3'
        }
        queryer = Queryer(query=query, structure_source='theory')
        queryer.perform_icsd_query()
        self.assertEqual(2, queryer.hits)

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_metadata(self):
        query = {
            "composition": "H:18:18 Al:6:6 O:28:28 P:4:4",
        }

        queryer = Queryer(query=query)
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("expected/5013/meta_data.json") as f:
            expected_dict = json.load(f)

        with open("5013/meta_data.json") as f:
            crawled_dict = json.load(f)

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_cell_parameter(self):
        code = 251445
        query = {
            "icsd_collection_code": code,
        }

        queryer = Queryer(query=query)
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("expected/{}/meta_data.json".format(code)) as f:
            expected_dict = json.load(f)

        with open("{}/meta_data.json".format(code)) as f:
            crawled_dict = json.load(f)

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_reference_3(self):
        """
        This entry does not have DOI.
        ICSD ver. 2017 had multiple references,
        while ICSD ver. 2019 does not have.
        """
        code = 5151
        query = {
            "icsd_collection_code": code,
        }

        queryer = Queryer(query=query)
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("expected/{}/meta_data.json".format(code)) as f:
            expected_dict = json.load(f)

        with open("{}/meta_data.json".format(code)) as f:
            crawled_dict = json.load(f)

        self.assertEqual("Powder Diffraction (1987) 2, p225-p226",
                         expected_dict['reference_2'])
        self.assertEqual("", crawled_dict['reference_2'])

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_all_structures(self):
        code = 44278
        query = {
            "icsd_collection_code": code,
        }

        queryer = Queryer(query=query, structure_source="all")
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("{}/meta_data.json".format(code)) as f:
            crawled_dict = json.load(f)

        assert crawled_dict['theoretical_calculation'] == True

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_theory(self):
        code = 195347
        query = {
            "icsd_collection_code": code,
        }

        queryer = Queryer(query=query, structure_source="theory")
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("expected/{}/meta_data.json".format(code)) as f:
            expected_dict = json.load(f)

        with open("{}/meta_data.json".format(code)) as f:
            crawled_dict = json.load(f)

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_double_column(self):
        code = 251776
        query = {
            "icsd_collection_code": code,
        }

        queryer = Queryer(query=query)
        queryer.perform_icsd_query()
        self.assertEqual(1, queryer.hits)

        with open("expected/{}/meta_data.json".format(code)) as f:
            expected_dict = json.load(f)

        with open("{}/meta_data.json".format(code)) as f:
            crawled_dict = json.load(f)

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)
