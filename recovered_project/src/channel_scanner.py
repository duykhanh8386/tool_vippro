# RECOVERED: reconstructed from CPython 3.12 bytecode
import hashlib
import json
import re
import time

import requests
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.channel_store import channel_store
from src.cookie_utils import normalize_cookies_for_storage
from src.utils import create_driver, get_request_payload_from_performance_log


class ChannelFetcher:
    LOGIN_URL = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3Den%26next%3Dhttps%253A%252F%252Fstudio.youtube.com%252F%26feature%3Dredirect_login&hl=en&ifkv=AcMMx-d4fvrPkXxfIg8o7ivlOtaYz55VcK2EWUx6zTt7iSx9wGyBkzr1KUqgfL5C0oMsTMQ6Zd0U7g&passive=true&service=youtube&uilel=3&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S-1405244270%3A1731600052448568&ddm=1"
    EMAIL_XPATH = "//input[@name='identifier' and @id='identifierId']"
    PASSWORD_XPATH = "//input[@type='password' and @name='Passwd']"
    NEXT_BUTTON_XPATH = "//span[(text()='Next') or (text()='Tiếp theo')]"
    CHANNEL_SELECTION_XPATH = "//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer']"
    NEXT_CHANNEL_SELECTION_XPATH = "//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer' and @enable-ring-for-active-account]/following-sibling::ytd-account-item-renderer[1]"
    AVATAR_BUTTON_XPATH = "//*[@id='avatar-btn'] | //ytcp-topbar-menu-button-renderer[contains(concat(' ', normalize-space(@class), ' '), ' ytcpAppHeaderAccountButton ')]"
    SWTICH_ACCOUNT_BUTTON_XPATH = "//ytd-compact-link-renderer[@class='style-scope yt-multi-page-menu-section-renderer' and @has-secondary]"
    ROLE_MANAGER_XPATH = "//div[@class='sublabel style-scope ytcp-topbar-menu-button-renderer']"

    def __init__(self):
        self.driver = None

    def run(self, email, password):
        logger.info("*** Fetching channel info ***")
        self.driver = create_driver(enable_performance_log=True)
        self._login(email, password)
        channel_selection_button = WebDriverWait(self.driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, self.CHANNEL_SELECTION_XPATH))
        )
        channel_selection_button.click()
        self._get_channel_info()

        account_menu_btn = self.driver.find_element(By.XPATH, self.AVATAR_BUTTON_XPATH)
        account_menu_btn.click()
        switch_acocunt_button = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, self.SWTICH_ACCOUNT_BUTTON_XPATH))
        )
        switch_acocunt_button.click()
        time.sleep(1)
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH))
        )
        next_account_button = self.driver.find_elements(
            By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH
        )

        while len(next_account_button) > 0:
            next = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH)
                )
            )
            next.click()
            if "channel-appeal" in self.driver.current_url:
                logger.error("Kênh đã bị xóa!!!")
            else:
                try:
                    self._get_channel_info()
                except:
                    logger.error("Kênh đã bị xóa!!!")

            account_menu_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, self.AVATAR_BUTTON_XPATH))
            )
            account_menu_btn.click()
            switch_acocunt_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, self.SWTICH_ACCOUNT_BUTTON_XPATH)
                )
            )
            switch_acocunt_button.click()
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH)
                    )
                )
            except:
                break
            next_account_button = self.driver.find_elements(
                By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH
            )

        self.driver.quit()

    def _login(self, email: str, password: str):
        self.driver.get(self.LOGIN_URL)
        email_input = self.driver.find_element(By.XPATH, self.EMAIL_XPATH)
        for char in email:
            email_input.send_keys(char)
            time.sleep(0.05)

        next_button = self.driver.find_element(By.XPATH, self.NEXT_BUTTON_XPATH)
        next_button.click()
        password_input = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, self.PASSWORD_XPATH))
        )
        for char in password:
            password_input.send_keys(char)
            time.sleep(0.05)

        next_button = self.driver.find_element(By.XPATH, self.NEXT_BUTTON_XPATH)
        next_button.click()

    def _get_channel_info(self):
        img_element_xapth = "//img[@class='thumbnail image-thumbnail style-scope ytcp-navigation-drawer']"
        WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, img_element_xapth))
        )
        id = self._extract_channel_id(self.driver.current_url)
        img_element = self.driver.find_element("xpath", img_element_xapth)
        img_src = img_element.get_attribute("src")
        name = img_element.get_attribute("alt")
        cookies_raw = self.driver.get_cookies()
        cookies = normalize_cookies_for_storage(cookies_raw)
        logger.info(f"*** Channel info fetched successfully: {name} ***")

        sapisidhash = None
        for cookie in cookies:
            if cookie["name"] == "SAPISID":
                sapisid = cookie["value"]
                sapisidhash = self._generate_sapisidhash_header(sapisid)

        current_url = self.driver.current_url
        next_url = current_url + "/analytics/tab-overview/period-default"
        self.driver.get(next_url)
        try:
            payload = get_request_payload_from_performance_log(
                self.driver, "youtubei/v1/att/esr?alt=json", timeout=20.0
            )
            payload_json = json.loads(payload)
            challenge = payload_json["challenge"]
            botguardResponse = payload_json["botguardResponse"]
        except TimeoutError as e:
            logger.error(str(e))

        url = f"https://studio.youtube.com/channel/{id}"
        cookie_string = "; ".join(
            [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
        )
        header = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Cookie": cookie_string,
        }
        res = requests.get(url, headers=header)
        delegated_session_id = self._extract_datasync_id(res.text)
        role = self._get_role_type(res.text)
        channel_store.upsert_channel(
            {
                "id": id,
                "name": name,
                "img_src": img_src,
                "delegated_session_id": delegated_session_id,
                "sapisidhash": sapisidhash,
                "role": role,
                "challenge": challenge,
                "botguardResponse": botguardResponse,
                "cookies": cookies,
            }
        )
        return dict(id=id, name=name, img_src=img_src, cookies=cookies)

    @staticmethod
    def _extract_channel_id(url):
        match = re.search("channel/([A-Za-z0-9_-]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_datasync_id(text):
        pattern = '"datasyncId":"(\\d+\\|\\|\\d*)"'
        match = re.search(pattern, text)
        if match:
            res = match.group(1).split("||")[0]
            return res
        pattern = "\\|\\|(\\d+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    @staticmethod
    def _generate_sapisidhash_header(sapisid, origin="https://studio.youtube.com"):
        time_now = round(time.time())
        sapisidhash = hashlib.sha1(
            f"{time_now} {sapisid} {origin}".encode("utf-8")
        ).hexdigest()
        return f"{time_now}_{sapisidhash}"

    @staticmethod
    def _get_role_type(text):
        pattern = '"channelRoleType":"(CREATOR_CHANNEL_ROLE_TYPE_[A-Z_]+)"'
        match = re.search(pattern, text)
        res = match.group(1)
        return res


channel_fetcher = ChannelFetcher()
