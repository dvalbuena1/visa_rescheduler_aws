# -*- coding: utf8 -*-
import configparser
import json
import locale
import logging
import random
import re
import sys
import time as tm
from datetime import datetime
from enum import Enum
from tempfile import mkdtemp

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from webdriver_manager.chrome import ChromeDriverManager

from utils import Result

console = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s:%(funcName)s - %(message)s')
console.setFormatter(formatter)
logger = logging.getLogger("Visa_Logger")
logger.addHandler(console)
logger.setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE']
FACILITY_ID = config['USVISA']['FACILITY_ID']
ASC_ID = config['USVISA']['ASC_ID']

SENDGRID_API_KEY = config['SENDGRID']['SENDGRID_API_KEY']
PUSH_TOKEN = config['PUSHOVER']['PUSH_TOKEN']
PUSH_USER = config['PUSHOVER']['PUSH_USER']

USE = config['CHROMEDRIVER']['USE']
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

REGEX_CONTINUE = "//a[contains(text(),'Continuar')]"

STEP_TIME = 0.5  # time between steps (interactions with forms): 0.5 seconds

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date={{date}}&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
DATE_URL_ASC = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{ASC_ID}.json?&consulate_id={FACILITY_ID}&consulate_date={{date}}&consulate_time={{time}}&appointments[expedite]=false"
TIME_URL_ASC = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{ASC_ID}.json?date={{date_asc}}&consulate_id={FACILITY_ID}&consulate_date={{date}}&consulate_time={{time}}&appointments[expedite]=false"

code = COUNTRY_CODE.split("-")
code[1] = code[1].upper()
code = str.join("_", code)
locale.setlocale(locale.LC_ALL, f'{code}.UTF-8')


class Use(Enum):
    AWS = "AWS"
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class VisaScheduler:
    def __init__(self):
        self.driver = self.get_driver()
        self.my_schedule_date = None

    # def MY_CONDITION(month, day): return int(month) == 11 and int(day) >= 5
    @staticmethod
    def MY_CONDITION(month, day):
        return True  # No custom condition wanted for the new scheduled date

    def get_my_schedule_date(self):
        appointment = self.driver.find_element(By.XPATH,
                                               '//*[@id="main"]/div[2]/div[3]/div[1]/div/div[1]/div[2]/p[1]').text
        regex = r".+: (.+,.+),.+"
        date = re.search(regex, appointment).group(1)
        self.my_schedule_date = datetime.strptime(date, "%d %B, %Y").strftime("%Y-%m-%d")

    def login(self):
        # Bypass reCAPTCHA
        self.driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
        tm.sleep(STEP_TIME)
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        tm.sleep(STEP_TIME)

        logger.info("Login start...")
        href = self.driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[2]/div[1]/ul/li[3]/a')
        href.click()
        tm.sleep(STEP_TIME)
        Wait(self.driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

        logger.info("\tclick bounce")
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        tm.sleep(STEP_TIME)

        self.do_login_action()

    def do_login_action(self):
        logger.info("\tinput email")
        user = self.driver.find_element(By.ID, 'user_email')
        user.send_keys(USERNAME)
        tm.sleep(random.randint(1, 3))

        logger.info("\tinput pwd")
        pw = self.driver.find_element(By.ID, 'user_password')
        pw.send_keys(PASSWORD)
        tm.sleep(random.randint(1, 3))

        logger.info("\tclick privacy")
        box = self.driver.find_element(By.CLASS_NAME, 'icheckbox')
        box.click()
        tm.sleep(random.randint(1, 3))

        logger.info("\tcommit")
        btn = self.driver.find_element(By.NAME, 'commit')
        btn.click()
        tm.sleep(random.randint(1, 3))

        Wait(self.driver, 60).until(
            EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
        logger.info("\tlogin successful!")

    def get_date(self):
        self.driver.get(DATE_URL)
        if not self.is_logged_in():
            self.login()
            return self.get_date()
        else:
            content = self.driver.find_element(By.TAG_NAME, 'pre').text
            date = json.loads(content)
            return date

    def get_time(self, date):
        time_url = TIME_URL.format(date=date)
        self.driver.get(time_url)
        content = self.driver.find_element(By.TAG_NAME, 'pre').text
        data = json.loads(content)
        time = data.get("available_times")[-1]
        logger.info(f"Got time successfully! {date} {time}")
        return time

    def reschedule(self, date, time, asc_date, asc_time):
        logger.info(f"Starting Reschedule ({date})")

        self.driver.get(APPOINTMENT_URL)

        tm.sleep(STEP_TIME)
        btn = self.driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/form/div[2]/div/input')
        if btn is not None:
            logger.info("\tmultiple applicants")
            btn.click()

        data = {
            "utf8": self.driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
            "authenticity_token": self.driver.find_element(by=By.NAME, value='authenticity_token').get_attribute(
                'value'),
            "confirmed_limit_message": self.driver.find_element(by=By.NAME,
                                                                value='confirmed_limit_message').get_attribute(
                'value'),
            "use_consulate_appointment_capacity": self.driver.find_element(by=By.NAME,
                                                                           value='use_consulate_appointment_capacity').get_attribute(
                'value'),
            "appointments[consulate_appointment][facility_id]": FACILITY_ID,
            "appointments[consulate_appointment][date]": date,
            "appointments[consulate_appointment][time]": time,
            "appointments[asc_appointment][facility_id]": ASC_ID,
            "appointments[asc_appointment][date]": asc_date,
            "appointments[asc_appointment][time]": asc_time
        }

        headers = {
            "User-Agent": self.driver.execute_script("return navigator.userAgent;"),
            "Referer": APPOINTMENT_URL,
            "Cookie": "_yatri_session=" + self.driver.get_cookie("_yatri_session")["value"]
        }

        r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
        if r.status_code == 200:
            msg = f"Rescheduled Successfully! {date} {time}"
            self.send_notification(msg)
        else:
            msg = f"Reschedule Failed. {date} {time}"
            self.send_notification(msg)
            logger.error(msg + str(r.status_code) + r.text)

    def asc_availability(self, date, time):
        logger.info("ASC Availability")

        def get_date():
            self.driver.get(DATE_URL_ASC.format(date=date, time=time))
            if not self.is_logged_in():
                self.login()
                return get_date()
            else:
                content = self.driver.find_element(By.TAG_NAME, 'pre').text
                return json.loads(content)

        def get_available_date(dates):
            for d in dates:
                date = d.get('date')
                _, month, day = date.split('-')
                if VisaScheduler.MY_CONDITION(month, day):
                    return date

        def get_time(date_asc):
            time_url = TIME_URL_ASC.format(date_asc=date_asc, date=date, time=time)
            self.driver.get(time_url)
            content = self.driver.find_element(By.TAG_NAME, 'pre').text
            data = json.loads(content)
            available_time = data.get("available_times")[-1]
            logger.info(f"\tGot time successfully! {date_asc} {available_time}")
            return available_time

        dates = get_date()[:5]
        available_date = get_available_date(dates)
        available_time = get_time(available_date)

        return available_date, available_time

    def is_logged_in(self):
        content = self.driver.page_source
        if content.find("error") != -1:
            return False
        return True

    @staticmethod
    def get_driver():
        dr = None
        if USE == Use.LOCAL.value:
            dr = webdriver.Chrome(ChromeDriverManager().install())
        elif USE == Use.AWS.value:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = "/opt/chrome/chrome"
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1280x1696')
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-dev-tools")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument(f'--user-data-dir={mkdtemp()}')
            chrome_options.add_argument(f'--data-path={mkdtemp()}')
            chrome_options.add_argument(f'--disk-cache-dir={mkdtemp()}')
            dr = webdriver.Chrome(service=Service(executable_path="/opt/chromedriver"), options=chrome_options)
        elif USE == Use.REMOTE.value:
            dr = webdriver.Remote(command_executor=HUB_ADDRESS, options=webdriver.ChromeOptions())
        return dr

    def get_available_date(self, dates):

        def is_earlier(date):
            my_date = datetime.strptime(self.my_schedule_date, "%Y-%m-%d")
            new_date = datetime.strptime(date, "%Y-%m-%d")
            result = my_date > new_date
            logger.info(f'Is {my_date} > {new_date}:\t{result}')
            return result

        logger.info("Checking for an earlier date:")
        for d in dates:
            date = d.get('date')
            if is_earlier(date):
                _, month, day = date.split('-')
                if VisaScheduler.MY_CONDITION(month, day):
                    return date

    @staticmethod
    def send_notification(msg):
        logger.info(f"Sending notification: {msg}")

        if SENDGRID_API_KEY:
            message = Mail(
                from_email=USERNAME,
                to_emails=USERNAME,
                subject=msg,
                html_content=msg)
            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                logger.info(f"SendGrid response - {response.status_code} - {response.body} - {response.headers}")
            except Exception as e:
                logger.error(str(e))

        if PUSH_TOKEN:
            url = "https://api.pushover.net/1/messages.json"
            data = {
                "token": PUSH_TOKEN,
                "user": PUSH_USER,
                "message": msg
            }
            requests.post(url, data)

    @staticmethod
    def print_dates(dates):
        logger.info("Available dates:")
        for d in dates:
            logger.info("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))

    @staticmethod
    def push_notification(dates):
        msg = "date: "
        for d in dates:
            msg = msg + d.get('date') + '; '
        VisaScheduler.send_notification(msg)

    def main(self) -> Result:
        # RETRY_TIME
        logger.info(f"---START--- : {datetime.today()}")

        self.login()
        try:
            self.get_my_schedule_date()
            dates = self.get_date()[:5]
            if dates:
                self.print_dates(dates)
                date = self.get_available_date(dates)
                logger.info(f"New date: {date}")
                if date:
                    date_time = self.get_time(date)
                    asc_date, asc_time = self.asc_availability(date, date_time)
                    self.reschedule(date, date_time, asc_date, asc_time)
                    VisaScheduler.push_notification(dates)
                    result = Result.SUCCESS
                else:
                    result = Result.RETRY
            else:
                logger.info("No dates available")
                result = Result.COOLDOWN

        except Exception as e:
            self.send_notification("HELP! Crashed.")
            logger.error(e)
            result = Result.EXCEPTION

        return result
