import sys
import platform
import os
import shutil
import json
import time
from bs4 import BeautifulSoup
import pandas as pd
import re
import pkg_resources

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from tags import ICSD_QUERY_TAGS, ICSD_PARSE_TAGS
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.options import Options


pd.options.display.max_colwidth = 1000


class QueryerError(Exception):
    pass


class Queryer(object):
    """
    Base class to query the ICSD via the web interface using a Selenium
    WebDriver (http://selenium-python.readthedocs.io/).
    """

    def __init__(self,
                 url=None,
                 query=None,
                 save_screenshot=None,
                 structure_source='E'):
        """
        Initialize the webdriver and load the URL.
        (Also, check if the "Basic Search" page has loaded successfully.)

        **[Note 1]**: Only ChromeDriver has been implemented.
        **[Note 2]**: Only the 'Basic Search & Retrieve' form has been implemented.

        Keyword arguments:
            url:
                URL of the search page

            query:
                The query to be posted to the webform -- a dictionary of field
                names as keys and what to fill in them as the corresponding
                values. Currently supported field names:
                1. composition
                2. number_of_elements
                3. icsd_collection_code
                E.g., {'composition': 'Ni:2:2 Ti:1:1', 'number_of_elements': 2}

                **[Note]**: field names must _exactly_ match those listed above!

            save_screenshot:
                Boolean specifying whether a screenshot of the ICSD web page
                should be saved locally?
                (Default: False)

            structure_source:
                String specifying whether the search should be limited to only
                experimental structures, theoretical structures, or both.
                Options: "E"/"T"/"A" for experimental/theoretical/all structures
                (Default: "E")

        Attributes:
            url: URL of the search page
            query: query to be posted to the webform (see kwargs)
            save_screenshot: whether the ICSD page should be saved as a screenshot
            structure_source: search for experimental/theoretical/all structures
            virt_display: Display object from pyvirtualdisplay
            browser_data_dir: directory for browser user profile, related data
            driver: instance of Selenium WebDriver running PhantomJS
            hits: number of search hits for the query
        """
        self._url = None
        self.url = url

        self._query = None
        self.query = query
        sys.stdout.write('Initializing a WebDriver...\n')
        sys.stdout.flush()

        self._save_screenshot = None
        self.save_screenshot = save_screenshot

        self._structure_source = None
        self.structure_source = structure_source

        self.virt_diplay = None

        self.driver = self._initialize_driver()
        self.driver.get(self.url)

        self._check_basic_search()

        self.hits = 0

        self.page_obatained = False

        self.init_interval()

    def init_interval(self):
        self.interval = 0  # sec

    @property
    def url(self):
        return(self._url)

    @url.setter
    def url(self, url):
        if not url:
            url = 'https://icsd.fiz-karlsruhe.de/search/basic.xhtml'
        self._url = url

    @property
    def query(self):
        return(self._query)

    @query.setter
    def query(self, query):
        if not query:
            self._query = {}
        else:
            self._query = query

    @property
    def save_screenshot(self):
        return(self._save_screenshot)

    @save_screenshot.setter
    def save_screenshot(self, save_screenshot):
        if not save_screenshot:
            self._save_screenshot = False
        elif is_instance(save_screenshot, str):
            self._save_screenshot = save_screenshot.lower() == 't'
        else:
            self._save_screenshot = save_screenshot

    @property
    def structure_source(self):
        return(self._structure_source)

    @structure_source.setter
    def structure_source(self, structure_source):
        if not structure_source:
            self._structure_source = 'A'
        elif structure_source.upper()[0] not in ['E', 'T', 'A']:
            self._structure_source = 'A'
        else:
            self._structure_source = structure_source.upper()[0]

    def enable_download_in_headless_chrome(self, browser, download_dir):
        # print("DL LINK: {}".format(download_dir))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        browser.command_executor._commands["send_command"] = (
            "POST", '/session/$sessionId/chromium/send_command')

        params = {'cmd': 'Page.setDownloadBehavior', 'params': {
            'behavior': 'allow', 'downloadPath': download_dir}}
        browser.execute("send_command", params)
        # return(browser)

    def _initialize_driver(self):
        browser_data_dir = os.path.join(os.getcwd(), 'browser_data')
        if os.path.exists(browser_data_dir):
            shutil.rmtree(browser_data_dir, ignore_errors=True)
        self.download_dir = os.path.abspath(os.path.join(browser_data_dir,
                                                         'driver_downloads'))
        sys.stdout.write('Starting a ChromeDriver ')
        sys.stdout.write('with the default download directory:\n')
        sys.stdout.write(' "{}"'.format(self.download_dir))
        sys.stdout.write('...\n')
        _options = webdriver.ChromeOptions()
        # using to --no-startup-window to run Chrome in the background throws a
        # WebDriver.Exception with "Message: unknown error: Chrome failed to
        # start: exited normally"
        ##_options.add_argument('--no-startup-window ')
        _options.add_argument('user-data-dir={}'.format(browser_data_dir))
        _options.add_argument('--headless')
        _options.add_argument("--disable-gpu")
        _options.add_argument("--no-sandbox")

        prefs = {
            'download.default_directory': self.download_dir,
            'profile.default_content_setting_values.automatic_downloads': 1
        }
        _options.add_experimental_option("prefs", prefs)

        if platform.system() == "Linux":
            _options.binary_location = os.environ['CHROME']
            _options.add_argument('--headless')

            # // open Browser in maximized mode
            _options.add_argument("start-maximized")
            _options.add_argument("disable-infobars")  # // disabling infobars
            # // disabling extensions
            _options.add_argument("--disable-extensions")
            # // applicable to windows os only
            _options.add_argument("--disable-gpu")
            # // overcome limited resource problems
            _options.add_argument("--disable-dev-shm-usage")
            # // Bypass OS security model
            _options.add_argument("--no-sandbox")

            _options.add_argument("--window-size=1920,1080")
            _options.add_argument("--disable-gpu")
            _options.add_argument("--disable-extensions")
            _options.add_experimental_option("useAutomationExtension", False)
            _options.add_argument("--proxy-server='direct://'")
            _options.add_argument("--proxy-bypass-list=*")
            _options.add_argument("--start-maximized")

            _options.add_argument("--headless")
            _options.add_argument("--test-type")
            _options.add_argument("--disable-gpu")
            _options.add_argument("--no-first-run")
            _options.add_argument("--no-default-browser-check")
            _options.add_argument("--ignore-certificate-errors")
            _options.add_argument("--start-maximized")

            return(webdriver.Chrome(os.environ['CDRIVER'], options=_options))

        return(webdriver.Chrome(options=_options))

        # return()

    def _check_basic_search(self):
        """
        Use By.ID to locate the Search Panel header element; if 'Basic Search'
        is not in the element text, raise Error.
        """
        header_id = 'content_form:mainSearchPanel_header'

        try:
            header = self.driver.find_element_by_id(header_id)
        except:
            self.quit()
            error_message = 'Failed to load Basic Search & Retrieve'
            raise QueryerError(error_message)
        else:
            if 'Basic Search' not in header.text:
                self.quit()
                error_message = 'Failed to load Basic Search & Retrieve'
                raise QueryerError(error_message)

    def select_structure_source(self):
        """
        Select the appropriate radio button in the "Content Selection" panel (in
        a menu on the left of the main page) based on the specified strucure
        sources.
        """
        if self.structure_source == 'E':
            # Experim. inorganic structures
            return

        self.wait_for_ajax()
        tag_dict = {'T': 'Theoretical structures',
                    'A': 'All Structures'}

        if self.structure_source == 'T' or self.structure_source == 'A':
            number_tag = tag_dict.get(self.structure_source)
            xpath = "//table/tbody/tr/td/label["\
                "text()[contains(., 'Theoretical structures')]]"
            # radio_label = self.driver.find_element_by_xpath(xpath)
            radio_label = WebDriverWait(self.driver, 20).until(
                ec.element_to_be_clickable((By.XPATH, xpath)))
            radio_label.click()
            self._wait_until_dialogue_disappears()

        if self.structure_source == 'A':
            number_tag = tag_dict.get(self.structure_source)
            xpath = "//table/tbody/tr/td/label["\
                "text()[contains(., 'Experim. metal-organic str.')]]"
            # radio_label = self.driver.find_element_by_xpath(xpath)
            radio_label = WebDriverWait(self.driver, 20).until(
                ec.element_to_be_clickable((By.XPATH, xpath)))
            radio_label.click()

        self._wait_until_dialogue_disappears()

    def _wait_until_dialogue_disappears(self):
        for _ in range(1000):
            element = self.driver.find_element_by_id("dlgBlockUI")
            is_hidden = element.get_attribute("aria-hidden")
            time.sleep(0.1)
            if is_hidden == 'true':
                time.sleep(0.1)
                return()

    def post_query_to_form(self):
        """
        Use By.ID to locate elements in the query (using IDs stored in
        `tags.ICSD_QUERY_TAGS`), POST keys to the form in the URL `self.url`,
        and run the query.
        (Also check if the 'List View' page has been loaded successfully.)
        """
        if not self.query:
            self.quit()
            error_message = 'Empty query'
            raise QueryerError(error_message)

        sys.stdout.write('Querying the ICSD for\n')
        for k, v in self.query.items():
            element_id = ICSD_QUERY_TAGS[k]
            self.driver.find_element_by_id(element_id).send_keys(v)
            sys.stdout.write('\t{} = "{}"\n'.format(k, v))
            sys.stdout.flush()

        self._run_query()
        self._check_list_view()

    def _run_query(self):
        """
        Use By.NAME to locate the 'Run Query' button and click it.
        """
        time.sleep(3)
        self._wait_until_dialogue_disappears()
        self.wait_for_ajax()
        element = WebDriverWait(self.driver, 20).until(
            ec.element_to_be_clickable((
                By.NAME, "content_form:btnRunQuery"
            )))
        element.click()

    def _check_list_view(self):
        """
        Use id to locate the first 'display_main' element, raise Error if
        'List View' is not in the element text.
        Parse element text to get number of hits for the current query
        (last item when text is split), assign to `self.hits`.
        """
        try:
            title = self.driver.find_element_by_id('display_main')
        except Exception as e:
            self.quit()
            print("Original error: {}".format(e))
            error_message = 'No hits/too many hits. Modify your query.'
            raise QueryerError(error_message)
        else:
            if 'List View' not in title.text:
                self.quit()
                error_message = 'Failed to load "List View" of results'
                raise QueryerError(error_message)
            else:
                self.hits = int(title.text.split()[6])
                sys.stdout.write('The query yielded ')
                sys.stdout.write('{} hits.\n'.format(self.hits))
                sys.stdout.flush()

    def _click_select_all(self):
        """
        Use By.ID to locate the 'Select All' ('LVSelect') button, and click it.
        """
        self.wait_for_ajax()

        WebDriverWait(self.driver, 60).until(
            ec.presence_of_element_located((
                By.ID, 'footer_middle'
            )))

        element = self.driver.find_element_by_id(
            'display_form:listViewTable:uiSelectAllRows_input')
        self.wait_for_ajax()
        self.driver.execute_script("arguments[0].click();", element)

    def wait_for_ajax(self, second=15):
        wait = WebDriverWait(self.driver, second)
        try:
            wait.until(lambda driver: self.driver.execute_script(
                'return jQuery.active') == 0)
            wait.until(lambda driver: self.driver.execute_script(
                'return document.readyState') == 'complete')
        except Exception as e:
            pass

    def _click_show_detailed_view(self):
        """
        Use By.ID to locate the 'Show Detailed View' ('LVDetailed') button, and
        click it.
        """
        time.sleep(3)
        self.wait_for_ajax()
        self._wait_until_dialogue_disappears()

        element = WebDriverWait(self.driver, 60).until(
            ec.presence_of_element_located((
                By.XPATH, "//span[contains(.,'Show Detailed View')]"
            )))
        self._wait_until_dialogue_disappears()
        self.driver.execute_script("arguments[0].click();", element)
        self.wait_for_ajax()
        self._check_detailed_view()
        self._wait_until_dialogue_disappears()
        time.sleep(3)
        self._expand_all()

        for _ in range(1000):
            time.sleep(0.1)
            folded_elements = self.driver.find_elements_by_xpath(
                '//*[@class="ui-accordion-header '
                'ui-helper-reset ui-state-default ui-corner-all"]')

            if len(folded_elements) == 0:
                time.sleep(0.1)
                return()

    def _check_detailed_view(self):
        """
        Use By.ID to locate all 'title' elements. If none of the title texts
        have 'Detailed View', raise an Error.
        """
        try:
            titles = self.driver.find_elements_by_id('display_main')
        except Exception as e:
            self.quit()
            error_message = 'Failed to load "Detailed View" of results.'\
                ' Original error:{}'.format(e)
            raise QueryerError(error_message)

        else:
            detailed_view = any(['Detailed View' in t.text for t in titles])
            if not detailed_view:
                self.quit()
                error_message = 'Failed to load "Detailed View" of results'
                raise QueryerError(error_message)

    def _expand_all(self):
        """
        Use By.CSS_SELECTOR to locate the 'Expand All' ('a#ExpandAll.no_print')
        button, and click it.
        """
        element = WebDriverWait(self.driver, 60).until(
            ec.presence_of_element_located((
                By.LINK_TEXT, "Expand all"
            )))

        self.driver.execute_script("arguments[0].click();", element)

    def _get_number_of_entries_loaded(self):
        """
        Load the number of entries from details.xhtml.
        Use By.CLASS_NAME to locate 'display_main' elements, split the element text
        with 'Detailed View' in it and return(the last item in )the list.
        """
        for i in range(10):
            titles = self.driver.find_elements_by_id('display_main')
            for title in titles:
                if 'Detailed View' in title.text:
                    n_entries_loaded = int(title.text.split()[5])
                    return(n_entries_loaded)

            time.sleep(1)

    def parse_entries(self):
        """
        Parse all entries resulting from the query.

        If the number of entries loaded is equal to `self.hits`, raise Error.
        Loop through all the entries loaded, and for each entry:
            a. create a directory named after its ICSD Collection Code
            b. write "meta_data.json" into the directory
            c. save "screenshot.png" into the directory
            d. export the CIF into the directory
        Close the browser session and quit.

        Return: (list) A list of ICSD Collection Codes of entries parsed
        """
        hit_number = self._get_number_of_entries_loaded()
        if hit_number != self.hits:
            self.quit()
            error_message = '# Hits ({0}) != # Entries: ({1}) in Detailed View'.format(
                hit_number, self.hits)
            raise QueryerError(error_message)

        sys.stdout.write('Parsing all the entries... \n')
        sys.stdout.flush()
        entries_parsed = []
        for i in range(self.hits):
            # get entry data
            entry_data = self.parse_entry()

            # create a directory for the entry after the ICSD Collection Code
            coll_code = str(entry_data['collection_code'])
            if os.path.exists(coll_code):
                shutil.rmtree(coll_code)
            os.mkdir(coll_code)

            # write the parsed data into a JSON file in the directory
            json_file = os.path.join(coll_code, 'meta_data.json')
            with open(json_file, 'w') as fw:
                json.dump(entry_data, fw, indent=2)

            # save the screenshot the current page into the directory
            if self.save_screenshot:
                screenshot_file = os.path.join(coll_code, 'screenshot.png')
                self.save_screenshot(fname=screenshot_file)

            self.enable_download_in_headless_chrome(
                self.driver, self.download_dir)
            # get the CIF file
            self.export_CIF()
            # uncomment the next few lines for automatic copying of CIF files
            # into the correct folders
            # wait for the file download to be completed
            CIF_name = 'ICSD_CollCode{}.cif'.format(coll_code)
            CIF_source_loc = os.path.join(self.download_dir, CIF_name)

            for _ in range(1000):
                if os.path.exists(CIF_source_loc):
                    time.sleep(0.1)
                    break
                else:
                    time.sleep(0.1)
            # move it into the directory of the current entry
            CIF_dest_loc = os.path.join(coll_code, '{}.cif'.format(coll_code))
            shutil.move(CIF_source_loc, CIF_dest_loc)

            sys.stdout.write('[{}/{}]: '.format(i+1, self.hits))
            sys.stdout.write('Data exported into ')
            sys.stdout.write('folder "{}"\n'.format(coll_code))
            sys.stdout.flush()
            entries_parsed.append(coll_code)

            self.save_entire_page(coll_code)

            if self.hits != 1:
                self._go_to_next_entry()

        sys.stdout.write('Closing the browser session and exiting...')
        sys.stdout.flush()
        self.quit()
        sys.stdout.write(' done.\n')
        return(entries_parsed)

    def save_entire_page(self, coll_code):
        source = self.driver.page_source

        with open("{}/source.html".format(coll_code), "w") as f:
            f.write(source)

    def _go_to_next_entry(self):
        """
        Use By.CLASS_NAME to locate the 'Next' button ('button_vcr_next'), and
        click it.
        """
        self.wait_for_ajax()
        element = self.driver.find_element_by_xpath(
            "//button[@id='display_form:buttonNext']/span")
        self.driver.execute_script("arguments[0].click();", element)
        self.page_obatained = False

    def parse_entry(self):
        """
        Parse all `tags.ICSD_PARSE_TAGS` + the ICSD Collection Code for the
        current entry, and construct a dictionary `parsed_data` with tag:value.

        For each tag in `tags.ICSD_PARSE_TAGS`, call the method named
        `get_[tag]` or `is_[tag]` depending on whether the value to be parsed is
        a text field or checkbox, respectively, and raise an Error if the
        corresponding method is not found.

        Return: (dict) `parsed_data` with [tag]:[parsed value]
        """
        self._wait_until_dialogue_disappears()
        self.wait_for_ajax()
        time.sleep(self.interval)
        parsed_data = {}
        parsed_data['collection_code'] = self.get_collection_code()
        for tag in ICSD_PARSE_TAGS.keys():
            # assume text field
            method = 'get_{}'.format(tag)
            try:
                parsed_data[tag] = getattr(self, method)()
            except AttributeError:
                pass
            else:
                continue

            # assume checkbox
            method = 'is_{}'.format(tag)
            try:
                parsed_data[tag] = getattr(self, method)()
            except AttributeError as e:
                sys.stdout.write('"{}" parser not implemented!\n'.format(tag))
                print(e)
                continue

        parsed_data['ICSD_version'] = self._get_icsd_ver()
        parsed_data['theoretical_calculation'] = "Structure calculated theoretically" in parsed_data['comments']
        parsed_data['crawler_version'] = pkg_resources.get_distribution("icsd").version

        return(parsed_data)

    def _get_icsd_ver(self):
        source = self.driver.page_source
        search = re.search('<p>(Version[\s0-9.()A-z-]+)</p>', source)
        if search:
            return(search.group(1))

        return("")

    def get_collection_code(self):
        """
        Use By.CLASS_NAME to locate 'title' elements, parse the ICSD Collection
        Code from the element text and raise Error if unsuccessful.

        Return: (integer) ICSD Collection Code
        """

        for _ in range(1000):
            self.wait_for_ajax()
            self._wait_until_dialogue_disappears()

            titles = WebDriverWait(self.driver, 20).until(
                ec.presence_of_all_elements_located((
                    By.ID, "display_main"
                )))

            for title in titles:
                if 'Summary' in title.text:
                    # try:
                    if len(title.text.split()) > 21:
                        code = title.text.split()[21]
                        if code.isdigit():
                            return(int(code))
                        # break
                    # except Exception as e:

                        # error_message = 'Failed to parse the ICSD Collection Code. Original error:\n' + \
                        #     str(e)
                        # print(error_message)
                        # print("title text:")
                        # print(title.text)
                        # raise QueryerError(error_message)

                # return(collection_code)

            time.sleep(0.1)

        error_message = 'Failed to parse the ICSD Collection Code.'
        print(error_message)
        self.quit()
        raise QueryerError(error_message)

    def get_html_table(self, idx):
        if not self.page_obatained:
            self.wait_for_ajax()
            self.soup = BeautifulSoup(self.driver.page_source, 'lxml')
            self.page_obatained = True

        table = self.soup.find_all('table')[idx]

        return(str(table))

    # panel: "Summary"

    def get_PDF_number(self):
        """
        Use By.XPATH to locate a 'td' node with the tag name (stored in
        `tags.ICSD_PARSE_TAGS`), parse the node text.

        Return: (string) PDF-number if available, empty string otherwise
        """
        _df = self._get_experimental_information_panel()
        pdf_number = _df[_df.Name == 'PDF calc.'].Value
        if len(pdf_number) == 0:
            return("")

        pdf_number = pdf_number.to_string(index=False)
        pdf_number = pdf_number.strip()
        return(pdf_number)

    def get_authors(self):
        """
        Use By.XPATH to locate a 'td' node with the tag name (stored in
        `tags.ICSD_PARSE_TAGS`), parse the node text.

        Return: (string) Authors if available, empty string otherwise
        """
        _df = self._get_summary_panel()
        author = _df[_df.Name == 'Author'].Value.to_string(index=False)
        return(author.strip().replace('\n', ' '))

    def get_publication_title(self):
        """
        Use By.ID to locate 'Title of Article' ['textfield13'], parse the
        element text.

        Return: (string) Publication title if available, empty string otherwise
        """
        _df = self._get_summary_panel()
        title = _df[_df.Name == 'Title'].Value.to_string(index=False)
        return(title.strip().replace('\n', ' '))

    def get_doi(self):
        _df = self._get_summary_panel()
        doi = _df[_df.Name == 'DOI'].Value
        if len(doi) == 0:
            return("")

        doi = doi.to_string(index=False)
        return(doi.strip().replace('\n', ' '))

    def get_reference(self):
        """
        Use By.ID to locate 'Reference' for the publication ['textfield12'],
        parse the element text.

        Return: (string) Bibliographic reference if available, empty string
        otherwise
        """
        _df = self._get_summary_panel()
        reference = _df[_df.Name == 'Reference'].Value.to_string(index=False)
        return(reference.strip().replace('\n', ' '))

    def get_data_quality(self):

        _df = self._get_summary_panel()
        quality = _df[_df.Name == 'Data quality'].Value
        if len(quality) == 0:
            return("")

        quality = quality.to_string(index=False)
        return(quality.strip().replace('\n', ' '))

    # panel: "Summary"
    def _get_summary_panel(self):
        table = self.get_html_table(idx=0)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return(df)

    # panel: "Chemistry"
    def _get_chemistry_panel(self):
        table = self.get_html_table(idx=2)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return(df)

    def get_defect(self):
        """
        All test data has defect: false
        """

        return(False)

    def get_chemical_formula(self):
        """
        Use By.ID to locate 'Sum Form' ['textfieldChem1'], parse the elemnent
        text.

        Return: (string) Chemical formula if available, empty string otherwise
        """
        _df = self._get_chemistry_panel()
        formula = _df[_df.Name == 'Sum. formula'].Value.to_string(index=False)
        return(formula.strip())

    def get_structural_formula(self):
        """
        Use By.ID to locate 'Struct. Form.' ['textfieldChem3'], parse the
        element text.

        Return: (string) Structural formula if available, empty string otherwise
        """
        _df = self._get_chemistry_panel()
        formula = _df[_df.Name == 'Struct. formula'].Value.to_string(
            index=False)
        return(formula.strip())

    def get_AB_formula(self):
        """
        Use By.ID to locate 'AB Formula' ['textfieldChem6'], parse the element
        text.

        Return: (string) AB formula if available, empty string otherwise
        """
        _df = self._get_chemistry_panel()
        formula = _df[_df.Name == 'AB formula'].Value.to_string(index=False)
        return(formula.strip())

    # panel: "Published Crystal Structure Data"
    def get_cell_parameters(self):
        """
        Use By.ID to locate 'Cell Parameters' ['textfieldPub1'] textfield, get
        its 'value' attribute, strip uncertainties from the quantities, and
        construct a cell parameters dictionary.

        Return: (dictionary) Cell parameters with keys 'a', 'b', 'c', 'alpha',
                'beta', 'gamma', and values in float
                (Lattice vectors are in Angstrom, angles in degrees.)
        """
        _df = self._get_published_crystal_structure_data_panel()
        raw_text = _df[_df.Name ==
                       'Cell parameter'].Value.to_string(index=False)
        raw_text = raw_text.strip()

        a, b, c, alpha, beta, gamma = [float(e.split('(')[0].strip('.')) for e
                                       in raw_text.split()]
        cell_parameters = {'a': a, 'b': b, 'c': c, 'alpha': alpha, 'beta': beta,
                           'gamma': gamma}
        assert a > 0
        assert b > 0
        assert c > 0
        assert alpha > 0
        assert beta > 0
        assert gamma > 0
        assert alpha < 180
        assert beta < 180
        assert gamma < 180
        return(cell_parameters)

    def get_volume(self):
        """
        Use By.ID to locate 'Volume' ['textfieldPub2'], parse its 'value'
        attribute.

        Return: (float) Volume in cubic Angstrom
        """
        _df = self._get_published_crystal_structure_data_panel()
        raw_text = _df[_df.Name == 'Cell volume'].Value.to_string(index=False)
        raw_text.strip()
        raw_text = raw_text.split()[0]
        volume = float(raw_text)

        return(volume)

    def get_space_group(self):
        """
        Use By.ID to locate 'Space Group' ['textfieldPub5'], parse its 'value'
        attribute.

        Return: (string) Space group if available, empty string otherwise
        """

        # Published Crystal Structure Data
        _df = self._get_published_crystal_structure_data_panel()
        raw_text = _df[_df.Name == 'Space group'].Value.to_string(index=False)
        raw_text = raw_text.replace(" (", "(")
        return(raw_text.strip())

    def _get_published_crystal_structure_data_panel(self):
        table = self.get_html_table(idx=3)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return(df)

    def get_crystal_system(self):
        """
        Use By.ID to locate 'Crystal System' ['textfieldPub8'], parse its
        'value' attribute.

        Return: (string) Crystal system if available, empty string otherwise
        """
        # Published Crystal Structure Data

        _df = self._get_published_crystal_structure_data_panel()
        system = _df[_df.Name == 'Crystal system'].Value.to_string(index=False)

        if system == "Series([], )":
            return("")

        return(system.strip())

    def get_wyckoff_sequence(self):
        """
        Use By.ID to locate 'Wyckoff Sequence' ['textfieldPub11'], parse its
        'value' attribute.

        Return: (string) Wyckoff sequence if available, empty string otherwise
        """
        _df = self._get_published_crystal_structure_data_panel()
        wyckoff = _df[_df.Name == 'Wyckoff sequence'].Value.to_string(
            index=False)
        return(wyckoff.strip())

    def get_formula_units_per_cell(self):
        """
        Use By.ID to locate 'Formula Units per Cell' ['textfieldPub3'], parse
        its 'value' attribute.
        Return: (integer) Formula units per unit cell
        """
        _df = self._get_published_crystal_structure_data_panel()
        z = _df[_df.Name == 'Z'].Value.to_string(index=False)
        return(int(z.strip()))

    def get_pearson(self):
        """
        details.xhtml > Details
        > Published Crystal Structure Data > Pearson symbol

        Use By.ID to locate 'Pearson Symbol' ['textfieldPub6'], parse its
        'value' attribute.

        Return: (string) Pearson symbol if available, empty string otherwise
        """
        _df = self._get_published_crystal_structure_data_panel()

        pearson = _df[_df.Name == 'Pearson symbol'].Value.to_string(
            index=False)
        return(pearson.strip())

    def get_crystal_class(self):
        """
        details.xhtml > Details
        > Published Crystal Structure Data > Crystal class

        Use By.ID to locate 'Crystal Class' ['textfieldPub9'], parse its 'value'
        attribute.

        Return: (string) Crystal class if available, empty string otherwise
        """
        _df = self._get_published_crystal_structure_data_panel()
        crystalclass = _df[_df.Name ==
                           'Crystal class'].Value.to_string(index=False)

        if crystalclass == "Series([], )":
            return("")

        return(crystalclass.strip())

    def get_structural_prototype(self):
        """
        Use By.ID to locate 'Structure Type' ['textfieldPub12'], parse its
        'value' attribute.

        Return: (string) Structure type if available, empty string otherwise
        """
        _df = self._get_published_crystal_structure_data_panel()
        stype = _df[_df.Name == 'Structure type'].Value

        if len(stype) == 0:
            return("")

        crystalclass = stype.to_string(index=False)
        return(crystalclass.strip())
        # return("")

    # panel: "Bibliography"
    def _get_references(self, n):
        """
        Use By.XPATH to locate 'td' nodes with the tag name (stored in
        `tags.ICSD_PARSE_TAGS`), parse the text for each node.
        ['Detailed View' page has text fields for 3 references]

        Arguments:
            n: which-th reference to parse (= 0/1/2)

        Return: (string) Reference if available, empty string otherwise
        """
        tag = 'Reference'
        xpath = "//td[text()[contains(., '{}')]]/../td/div".format(tag)
        nodes = self.driver.find_elements_by_xpath(xpath)
        reference = self._clean_reference_string(nodes[n].text)
        return(reference)

    def get_reference_1(self):
        """
        Parse '1st Reference' on the 'Detailed View' page.

        Return: (string) Reference if available, empty string otherwise
        """
        return(self._get_references(0))

    def get_reference_2(self):
        """
        '2nd Reference' seems to be abolished on ICSD 4.2.0.
        Following comments are for previous versions

        Parse '2nd Reference' on the 'Detailed View' page.

        Return: (string) Reference if available, empty string otherwise
        """
        return("")  # Abolished
        # return(self._get_references(1))

    def get_reference_3(self):
        """
        '2nd Reference' seems to be abolished on ICSD 4.2.0.
        Following comments are for previous versions

        Parse '3rd Reference' on the 'Detailed View' page.

        Return: (string) Reference if available, empty string otherwise
        """
        return("")  # Abolished
        # return(self._get_references(2))

    def _clean_reference_string(self, r):
        """
        Strip the reference string of unrelated text.

        Arguments:
            r: Reference string to be cleaned

        Return: (string) r, stripped
        """
        r = r.strip()
        r = r.replace('Northwestern University Library', '').strip()
        r = r.replace('\n', ' ')
        return(r)

    def _parse_two_column_table(self, df):
        assert df.shape[1] == 5
        df1 = df.loc[:, 0:1]
        df2 = df.loc[:, 3:5]

        df1.columns = ['Name', "Value"]
        df2.columns = ['Name', "Value"]

        df = pd.concat([df1, df2], axis=0)
        return(df)

    def _get_additional_info(self, key="Warnings"):
        table = self.get_html_table(idx=18)

        if '<table class="outputcontentpanel"></table>' == table:
            return([])

        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)

        warnings = df[df.Name == key].Value.tolist()
        return(warnings)

    # panel: "Warnings & Comments"

    def get_warnings(self):
        """
        Use By.ID to locate 'Warnings & Comments' ('ir_a_8_81a3e') block, then
        use By.XPATH to locate rows in the 'Warnings' table
        ('.//table/tbody/tr'), add text in each row, if any, to a list.

        Return: (list) A list of warnings if any, empty list otherwise
        """
        return(self._get_additional_info("Warnings"))

    def get_comments(self):
        """
        Use By.ID to locate 'Warnings & Comments' ('ir_a_8_81a3e') block, then
        use By.XPATH to locate the individual 'Comments' divs, add text in each
        div, if any, to a list.

        Return: (list) A list of comments if any, empty list otherwise
        """
        return(self._get_additional_info("Comments"))

    # panel: "Experimental Conditions"
    # text fields
    def get_temperature(self):
        """
        details.xhtml > Details
        > Experimental information > Temperature

        Use By.XPATH to locate the 'input' nodes associated with the div name
        (stored in `tag.ICSD_PARSE_TAGS`), and get the 'value' attribute of the
        first node.

        Return: (string) Temperature if available, empty string otherwise
        """
        _df = self._get_experimental_information_panel()
        raw_text = _df[_df.Name == 'Temperature'].Value.to_string(index=False)
        raw_text = raw_text.replace("[", "").replace("]", "")
        return(raw_text.strip())

    def get_pressure(self):
        """
        details.xhtml > Details
        > Experimental information > Pressure

        Use By.XPATH to locate the 'input' nodes associated with the div name
        (stored in `tag.ICSD_PARSE_TAGS`), and get the 'value' attribute of the
        second node.

        Return: (string) Pressure if available, empty string otherwise
        """
        _df = self._get_experimental_information_panel()
        raw_text = _df[_df.Name == 'Pressure'].Value.to_string(index=False)
        raw_text = raw_text.replace("[", "").replace("]", "")
        return(raw_text.strip())

    def get_R_value(self):
        """
        details.xhtml > Details
        > Experimental information > R-value

        Use By.XPATH to locate the 'input' node with attribute 'text',
        associated with 'td' node with the tag name (stored in
        `tags.ICSD_PARSE_TAGS`), get its 'value' attribute.

        Return: (float) R-value if available, None otherwise
        """
        _df = self._get_experimental_information_panel()
        raw_text = _df[_df.Name == 'R-value'].Value.to_string(index=False)

        if raw_text == "Series([], )":
            return(None)
        return(float(raw_text.strip()))

    # checkboxes
    def _is_checkbox_enabled(self, tag_key):
        """
        Use By.XPATH to locate the 'input' node of type 'checkbox' associated
        with a 'td' node with the tag name (stored in `tags.ICSD_PARSE_TAGS`),
        and try to get its 'checked' attribute.

        Return: (bool) True if checked, False otherwise
        """
        tag = ICSD_PARSE_TAGS[tag_key]
        xpath = "//*[text()[contains(., '{}')]]".format(tag)
        xpath += "/../input[@type='checkbox']"
        node = self.driver.find_element_by_xpath(xpath)
        if node.get_attribute('checked') is None:
            return(False)
        else:
            return(True)

    def _get_radiation_type(self):
        """
        details.xhtml > Details
        > Experimental information > Radiation type
        """
        _df = self._get_experimental_information_panel()
        rad_type = _df[_df.Name ==
                       'Radiation type'].Value.to_string(index=False)
        return(rad_type.strip())

    # subpanel: "Radiation Type"
    def is_x_ray(self):
        """
        Is the 'X-ray' checkbox enabled?

        details.xhtml > Details
        > Experimental information > Radiation Type
        """
        rad_type = self._get_radiation_type()

        return('X-Ray' == rad_type)

    def is_electron_diffraction(self):
        """
        Is the 'Electrons' checkbox enabled?
        """
        if 'Electron' == self._get_radiation_type():
            return(True)

        if "Electron microscopy (powder)" in self._get_remarks():
            return(True)

        return(False)

        # return(self._is_checkbox_enabled('electron_diffraction'))

    def is_neutron_diffraction(self):
        """
        Is the 'Neutrons' checkbox enabled?
        """
        return('Neutron' == self._get_radiation_type())

    def is_synchrotron(self):
        """
        Is the 'Synchrotron' checkbox enabled?
        """
        return('Synchrotron' == self._get_radiation_type())

    def _get_bibliography_panel(self):
        table = self.get_html_table(idx=16)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return(df)

    def get_abstract(self):
        _df = self._get_bibliography_panel()
        abstract = _df[_df.Name == 'Abstract'].Value

        if len(abstract) == 0:
            return("")

        return(abstract.to_string(index=False))

    def _get_experimental_information_panel(self):
        table = self.get_html_table(idx=17)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return(df)

    def _get_sample_type(self):
        """
        details.xhtml > Details
        > Experimental information > Sample type
        """
        _df = self._get_experimental_information_panel()
        sample_type = _df[_df.Name ==
                          'Sample type'].Value.to_string(index=False)
        return(sample_type.strip())

    # subpanel: "Sample Type"
    def is_powder(self):
        """
        Is the 'Powder' checkbox enabled?
        """
        return("Powder data" == self._get_sample_type())

    def is_single_crystal(self):
        """
        Is the 'Single-Cystal' checkbox enabled?
        """
        return("Single crystal" == self._get_sample_type())

    def _get_remarks(self):
        """
        details.xhtml > Details
        > Experimental information > Remarks
        """
        df = self._get_experimental_information_panel()
        remarks = list(df[df.Name == 'Remarks'].Value)
        remarks = [s.strip() for s in remarks]
        return(remarks)

    # subpanel: "Additional Information"
    def is_twinned_crystal_data(self):
        """
        Is the 'Twinned Crystal Data' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Structure determined on a twinned crystal" in remarks)

    def is_rietveld_employed(self):
        """
        Is the 'Rietveld Refinement employed' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Rietveld profile refinement applied" in remarks)
        return(self._is_checkbox_enabled('rietveld_employed'))

    def is_absolute_config_determined(self):
        """
        Is the 'Absolute Configuration Determined' checkbox enabled?

        Needs to check whether "Absolute Configuration Determined" is in remarks or not.
        """
        remarks = self._get_remarks()
        return("Absolute Configuration Determined" in remarks)

    def is_experimental_PDF_number(self):
        """
        Is the 'Experimental PDF Number assigned' checkbox enabled?
        """
        _df = self._get_experimental_information_panel()
        return("PDF exp." in _df.columns.values)

    def is_temperature_factors_available(self):
        """
        Is the 'Temperature Factors available' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Temperature factors available" in remarks)

    def is_magnetic_structure_available(self):
        """
        Is the 'Magnetic Structure Available' checkbox enabled?
        """
        return(False)  # Where can I find this?

    def is_anharmonic_temperature_factors_given(self):
        """
        Is the 'Anharmonic temperature factors given' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Anharmonic temperature factors given" in remarks)

    def is_calculated_PDF_number(self):
        """
        Is the 'Calculated PDF Number assigned' checkbox enabled?
        """
        _df = self._get_experimental_information_panel()
        return("PDF calc." in _df.columns.values)

    def is_NMR_data_available(self):
        """
        Is the 'NMR Data available' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("NMR spectroscopy data given" in remarks)

    def is_correction_of_previous(self):
        """
        Is the 'Correction of Earlier Work' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("This publication corrects errors in an earlier one" in remarks)

    def is_cell_constants_without_sd(self):
        """
        Is the 'Cell Constants without s.d.' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Standard deviation missing in cell constants" in remarks)

    def is_only_cell_and_structure_type(self):
        """
        Is the 'Only Cell and Structure Type Determined' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Cell and Type only determined" in remarks)

    # subpanel: "Properties of Structure"
    def is_polytype(self):
        """
        Is the 'Polytype Structure' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Polytype structure" in remarks)

    def is_is_prototype_structure(self):
        """
        Is the 'Prototype Structure Type' checkbox enabled?
        """
        remarks = self._get_remarks()
        for remark in remarks:
            if "rototype" in remark:
                return(True)

        return(False)

    def is_order_disorder(self):
        """
        Is the 'Order/Disorder Structure' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Order-disorder structure" in remarks)

    def is_modulated_structure(self):
        """
        Is the 'Modulated Structure' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Modulated structure" in remarks)

    def is_disordered(self):
        """
        Is the 'Disordered Structure' checkbox enabled?
        """
        remarks = self._get_remarks()
        return("Disordered structure that cannot adequately be described by numerical parameters" in remarks)

    def is_mineral(self):
        """
        Is the 'Mineral' checkbox enabled?
        """
        df = self._get_chemistry_panel()
        if "Mineral name" in df.Name.values:
            return(True)

        return(False)

    def is_is_structure_prototype(self):
        """
        Is the 'Structure Prototype' checkbox enabled?
        """
        table = self.get_html_table(idx=7)
        df = pd.read_html(table)[0]
        df = self._parse_two_column_table(df)
        return("Transformation info" in df.columns.values)

    def export_CIF(self, base_filename='ICSD_Coll_Code'):
        """
        Use By.ID to locate text field for base filename for CIFs
        ('fileNameForExportToCif'), POST `base_filename` to it, and then use
        By.ID to locate 'Export to CIF File' button ('aExportCifFile'), and
        click it.

        Keyword arguments:
            base_filename: (default: 'ICSD_Coll_Code')
                           String to be prepended to the CIF file. The final
                           name is of the form
                           "[base_filename]_[ICSD Collection Code].cif", e.g.,
                           "ICSD_Coll_Code_18975.cif"
        """
        self.wait_for_ajax()
        element = self.driver.find_element_by_xpath(
            "//button[@id='display_form:btnEntryDownloadCif']/span[2]")
        self.driver.execute_script("arguments[0].click();", element)

    def save_screenshot(self, size=None, fname='ICSD.png'):
        """
        Save screenshot of the current page.

        Keyword arguments:
            size: (default: None)
                tuple (width, height) of the current window

            fname: (default: 'ICSD.png')
                save screenshot into this file
        """
        if size:
            self.driver.set_window_size(size[0], size[1])
        self.driver.save_screenshot(fname)

    def quit(self):
        self.driver.stop_client()
        self.driver.quit()

    def perform_icsd_query(self):
        """
        Post the query to form, parse data for all the entries. (wrapper)
        """
        element = WebDriverWait(self.driver, 20).until(
            ec.element_to_be_clickable((
                By.NAME, "content_form:btnRunQuery"
            )))
        # Wait until button appears
        self.select_structure_source()
        self.post_query_to_form()
        self._click_select_all()
        self._click_show_detailed_view()
        return(self.parse_entries())
