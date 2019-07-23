import unittest
import random
import glob
import json
import platform
from icsd.queryer import Queryer



is_mac = platform.system() == 'Darwin'

abolished_keys = ["misfit_layer"]
new_keys = [
    'doi',
    "experimental_PDF_number",
    "is_structure_prototype",
    "cell_constants_without_sd",
    "calculated_PDF_number",
    "modulated_structure",
    "only_cell_and_structure_type",
    "temperature_factors_available",
    "ICSD_version",
    'abstract',
    "data_quality",
    'crawler_version'
]
conflicting_keys = [
    'PDF_number',  # queryer ver. 2017 returns 'R-value' by a bug
    "reference",
    'reference_1',  # queryer ver. 2017 has uncleaned entry
    'reference_2',  # ICSD ver. 2017 had multiple references,
    'reference_3',  # while ICSD ver. 2019 does not have.
    "comments",
    # Order of multiple comments
    # can be different. Tested elsewhere.
    # Additional comments can be added depending on versions
    "structural_prototype",
    # Generally consistent, but can be divided
    # by different values. see ICSD195556.
    'R_value'
    # If unavailable, 2017 version returns "", while
    # this version returns None.
]



class TestRandom(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    @unittest.skipIf(not is_mac, "Use macOS to run this")
    def test_random(self):


        paths = glob.glob("expected/*")
        path = random.choice(paths)
        code = path.split("/")[-1]
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

        self.assertCountEqual(
            crawled_dict['comments'], expected_dict['comments'])
        if expected_dict['R_value'] == "":
            self.assertEqual(crawled_dict['R_value'], None)

        if expected_dict['structural_prototype'] != crawled_dict['structural_prototype']:
            print("Structural prototypes did not match: 2017ver:{} 2019ver:{}".format(
                expected_dict['structural_prototype'],
                crawled_dict['structural_prototype']
            ))

        assert "Version" in crawled_dict['ICSD_version']

        for key in new_keys + conflicting_keys:
            del crawled_dict[key]

        for key in abolished_keys + conflicting_keys:
            del expected_dict[key]

        self.assertDictEqual(expected_dict, crawled_dict)
