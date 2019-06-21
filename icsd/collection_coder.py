from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
import math
from icsd import queryer
from selenium.webdriver.support.ui import Select
from tqdm import tqdm


class CollectionCoder():
    def __init__(self, first_code, last_code):
        self.previous_code = 0
        # last_code = first_code + n_codes - 1
        self.code_range = "{0}-{1}".format(first_code, last_code)
        self.combined_csv_path = "combined/comb_{}.csv".format(self.code_range)

    def init_driver(self):
        self.q = queryer.Queryer(structure_source="A")
        self.q.select_structure_source()
        # self.q.driver.find_element_by_link_text("DB Info").click()
        textbox = self.q.driver.find_element_by_id(
            "content_form:uiCodeCollection:input:input")
        textbox.send_keys(self.code_range)
        self.q._run_query()
        self.q._check_list_view()

    def run(self):

        self.init_driver()

        select = Select(self.q.driver.find_element_by_id(
            "display_form:listViewTable:j_id12"))
        # select.select_by_visible_text('10')
        select.select_by_value('50')

        # self.q._wait_until_dialogue_disappears()
        # self.q.wait_for_ajax()
        # self.q._wait_until_dialogue_disappears()

        # class ui-paginator-current

        n_hits = self.q.hits
        n_pages = math.ceil(n_hits / 50)

        df_list = []

        for page in range(1, n_pages + 1):

            print("({0} of {1})".format(page, n_pages))

            WebDriverWait(self.q.driver, 60).until(
                ec.text_to_be_present_in_element(
                    (By.CLASS_NAME, 'ui-paginator-current'),
                    "({0} of {1})".format(page, n_pages)
                )
            )

            self.q._wait_until_dialogue_disappears()
            self.q.wait_for_ajax()
            element = WebDriverWait(self.q.driver, 20).until(
                ec.presence_of_element_located((
                    By.CSS_SELECTOR, ".ui-icon-seek-next"
                )))
            # element.click()
            # self._save_csv(page, n_pages, self.code_range)
            _df = self._get_df()
            filename = "each/{0}-p{1}outof{2}ps.csv".format(
                self.code_range, page, n_pages)
            _df.to_csv(filename)

            df_list.append(_df)

            self.q.driver.execute_script("arguments[0].click();", element)
            # self.q.driver.find_element_by_css_selector(".ui-icon-seek-next").click()
            self.q._wait_until_dialogue_disappears()
            self.q.wait_for_ajax()

        combined_df = pd.concat(df_list)

        combined_df.to_csv(self.combined_csv_path)
        # self.q.driver.close()


    def _get_df(self):
        _df = self._get_current_df()
        while self.previous_code == _df['Coll. Code'].min():
            _df = self._get_current_df()
            time.sleep(0.1)

        self.previous_code = _df['Coll. Code'].min()
        print(_df)
        return(_df)

    def _get_current_df(self):
        table = self.q.get_html_table(idx=1)
        df = pd.read_html(table)[0]
        self.q.page_obatained = False  # Refresh
        return(df)

    def quit(self):
        self.q.quit()
    # def _save_csv(self, page, n_pages, self.code_range):


def main():
    for i in tqdm(range(100)):
        try:
            cc = CollectionCoder(i * 10000 + 1, i * 10000 + 10000)
            print(cc.combined_csv_path)
            if not os.path.exists(cc.combined_csv_path):
                cc.run()
        except queryer.QueryerError:
            with open(cc.combined_csv_path, "w") as f:
                f.write("")


            print("No entry found in this step")
            cc.quit()
            time.sleep(5)


if __name__ == '__main__':
    main()
