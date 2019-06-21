import unittest
import sys
import os
from icsd.crawler import Crawler


class TestCrawl(unittest.TestCase):
    def test_number_range(self):
        crawler = Crawler()
        crawler.all_codes = [1, 5, 12, 15, 60, 61, 100, 101, 103, 105, 108,
                             120, 250, 500] + list(range(600, 1500)) + list(range(2000, 10000))

        crawler.crawled_codes = [60, 61, 100, 103, 105]
        crawler.not_yet_crawled = list(
            set(crawler.all_codes) - set(crawler.crawled_codes))
        self.assertEqual((1, 59), crawler.get_code_range())

        crawler.crawled_codes = crawler.crawled_codes + [1, 5, 12, 15]
        crawler.not_yet_crawled = list(
            set(crawler.all_codes) - set(crawler.crawled_codes))
        self.assertEqual((101, 102), crawler.get_code_range())

        crawler.crawled_codes += [101]
        crawler.not_yet_crawled = list(
            set(crawler.all_codes) - set(crawler.crawled_codes))
        self.assertEqual((108, 695), crawler.get_code_range())
