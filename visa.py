# -*- coding: utf8 -*-

import time as tm
import json
import random
import configparser
from datetime import datetime
from enum import Enum

import requests
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import IEDriverManager

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE']
FACILITY_ID = config['USVISA']['FACILITY_ID']
CAS_ID = config['USVISA']['CAS_ID']

SENDGRID_API_KEY = config['SENDGRID']['SENDGRID_API_KEY']
PUSH_TOKEN = config['PUSHOVER']['PUSH_TOKEN']
PUSH_USER = config['PUSHOVER']['PUSH_USER']

LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

REGEX_CONTINUE = "//a[contains(text(),'Continuar')]"

STEP_TIME = 0.5  # time between steps (interactions with forms): 0.5 seconds

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date={{date}}&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
DATE_URL_CAS = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{CAS_ID}.json?&consulate_id={FACILITY_ID}&consulate_date={{date}}&consulate_time={{time}}&appointments[expedite]=false"
TIME_URL_CAS = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{CAS_ID}.json?date={{date_cas}}&consulate_id={FACILITY_ID}&consulate_date={{date}}&consulate_time={{time}}&appointments[expedite]=false"


class Result(Enum):
    SUCCESS = 1
    RETRY = 2
    COOLDOWN = 3
    EXCEPTION = 4


class VisaScheduler:
    def __init__(self):
        self.driver = self.get_driver()

    # def MY_CONDITION(month, day): return int(month) == 11 and int(day) >= 5
    @staticmethod
    def MY_CONDITION(month, day):
        return True  # No custom condition wanted for the new scheduled date

    def login(self):
        # Bypass reCAPTCHA
        self.driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
        tm.sleep(STEP_TIME)
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        tm.sleep(STEP_TIME)

        print("Login start...")
        href = self.driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[2]/div[1]/ul/li[3]/a')
        href.click()
        tm.sleep(STEP_TIME)
        Wait(self.driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

        print("\tclick bounce")
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        tm.sleep(STEP_TIME)

        self.do_login_action()

    def do_login_action(self):
        print("\tinput email")
        user = self.driver.find_element(By.ID, 'user_email')
        user.send_keys(USERNAME)
        tm.sleep(random.randint(1, 3))

        print("\tinput pwd")
        pw = self.driver.find_element(By.ID, 'user_password')
        pw.send_keys(PASSWORD)
        tm.sleep(random.randint(1, 3))

        print("\tclick privacy")
        box = self.driver.find_element(By.CLASS_NAME, 'icheckbox')
        box.click()
        tm.sleep(random.randint(1, 3))

        print("\tcommit")
        btn = self.driver.find_element(By.NAME, 'commit')
        btn.click()
        tm.sleep(random.randint(1, 3))

        Wait(self.driver, 60).until(
            EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
        print("\tlogin successful!")

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
        print(f"Got time successfully! {date} {time}")
        return time

    def reschedule(self, date, time, cas_date, cas_time):
        print(f"Starting Reschedule ({date})")

        self.driver.get(APPOINTMENT_URL)

        tm.sleep(STEP_TIME)
        btn = self.driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/form/div[2]/div/input')
        if btn is not None:
            print("\tmultiple applicants")
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
            "appointments[asc_appointment][facility_id]": CAS_ID,
            "appointments[asc_appointment][date]": cas_date,
            "appointments[asc_appointment][time]": cas_time
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
            print(r.status_code)
            print(r.text)

    def cas_availability(self, date, time):
        print("CAS Availability")

        def get_date():
            self.driver.get(DATE_URL_CAS.format(date=date, time=time))
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

        def get_time(date_cas):
            time_url = TIME_URL_CAS.format(date_cas=date_cas, date=date, time=time)
            self.driver.get(time_url)
            content = self.driver.find_element(By.TAG_NAME, 'pre').text
            data = json.loads(content)
            available_time = data.get("available_times")[-1]
            print(f"\tGot time successfully! {date_cas} {available_time}")
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
        if LOCAL_USE:
            dr = webdriver.Edge(service=Service())
        else:
            dr = webdriver.Remote(command_executor=HUB_ADDRESS, options=webdriver.EdgeOptions())
        return dr

    @staticmethod
    def get_available_date(dates):

        def is_earlier(date):
            my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
            new_date = datetime.strptime(date, "%Y-%m-%d")
            result = my_date > new_date
            print(f'Is {my_date} > {new_date}:\t{result}')
            return result

        print("Checking for an earlier date:")
        for d in dates:
            date = d.get('date')
            if is_earlier(date):
                _, month, day = date.split('-')
                if VisaScheduler.MY_CONDITION(month, day):
                    return date

    @staticmethod
    def send_notification(msg):
        print(f"Sending notification: {msg}")

        if SENDGRID_API_KEY:
            message = Mail(
                from_email=USERNAME,
                to_emails=USERNAME,
                subject=msg,
                html_content=msg)
            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                print(response.status_code)
                print(response.body)
                print(response.headers)
            except Exception as e:
                print(e.message)

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
        print("Available dates:")
        for d in dates:
            print("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))
        print()

    @staticmethod
    def push_notification(dates):
        msg = "date: "
        for d in dates:
            msg = msg + d.get('date') + '; '
        VisaScheduler.send_notification(msg)

    def main(self) -> Result:
        # RETRY_TIME
        print("------------------")
        print(datetime.today())
        print()

        self.login()
        try:
            dates = self.get_date()[:5]
            if dates:
                self.print_dates(dates)
                date = self.get_available_date(dates)
                print()
                print(f"New date: {date}")
                if date:
                    date_time = self.get_time(date)
                    cas_date, cas_time = self.cas_availability(date, date_time)
                    self.reschedule(date, date_time, cas_date, cas_time)
                    VisaScheduler.push_notification(dates)
                    result = Result.SUCCESS
                else:
                    result = Result.RETRY
            else:
                print("No dates available")
                result = Result.COOLDOWN

        except Exception as e:
            self.send_notification("HELP! Crashed.")
            print(e)
            result = Result.EXCEPTION

        return result
