import glob
import pandas as pd
import os
import math
from icsd.all_entries import AllEntries
# from logging import getLogger
import logging
import time


class Crawler(object):
    def __init__(self):
        # logging = getLogger("Log")
        logging.basicConfig(filename = "selenium.log",  level = logging.INFO,
                               format='[%(asctime)s] %(module)s.%(funcName)s %(levelname)s -> %(message)s')

    def get_code_range(self):
        def get_within_value(start, end):
            for c in self.crawled_codes:
                if start <= c and c <= end:
                    return(c)

            return(-1)

        start = self.not_yet_crawled[0]
        end = self.all_codes[self.all_codes.index(start) + 99]  # 100 is the maximum of DL

        within_val = get_within_value(start, end)

        if within_val > 0:
            end = within_val - 1

        return(start, end)

    def refresh(self):
        paths = glob.glob("combined/*.csv")
        df_list = []

        for p in paths:
            if os.stat(p).st_size > 0:
                _df = pd.read_csv(p)
                df_list.append(_df)

        cdf = pd.concat(df_list, ignore_index=True, sort=False)
        cdf.to_csv('all_coolection_code.csv')

        assert(cdf["Coll. Code"].duplicated() == True).sum() == 0

        logging.info("{} structures are in Collection Code list".format(len(cdf)))

        cdf = cdf.sort_values(by=["Coll. Code"])

        crawled = glob.glob("*/source.html")
        crawled = [int(c.split("/")[0]) for c in crawled]

        cdf2 = cdf[~cdf["Coll. Code"].isin(crawled)]
        logging.info("{} structures are not retrieved".format(len(cdf2)))

        self.crawled_codes = sorted(crawled)
        self.all_codes = cdf["Coll. Code"].tolist()
        self.not_yet_crawled = cdf2["Coll. Code"].tolist()

    def run(self):
        logging.info("Awakening...")
        self.refresh()

        sleep_time = 10
        n_at_fail = 0

        while len(self.not_yet_crawled) > 0:
            try:
                self.refresh()
                start, end = self.get_code_range()

                ae = AllEntries(start, end)
                ae.run()

            except Exception as e:
                logging.error(e)
                print("Sleep {} seconds".format(sleep_time))
                time.sleep(sleep_time)
                sleep_time = sleep_time * 2

                ae.cc.q.interval += 1

                self.refresh()

                if n_at_fail - len(self.not_yet_crawled) > 1000:
                    sleep_time = 10
                    ae.cc.q.init_interval()

                n_at_fail = len(self.not_yet_crawled)


def main():
    c = Crawler()
    c.run()
