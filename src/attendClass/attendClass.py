import sys
from datetime import timedelta
from time import sleep
from getpass import getpass

from clockwork import Clockwork

import selenium.common.exceptions
from selenium.webdriver.firefox.webdriver import WebDriver

import os
EXECUTABLE_PATH = os.environ["HOME"] + "/geckodriver"



class AttendClass(Clockwork):
    def __init__(self, **kwargs):
        """
        Parameters:\n
            'code' (string): Meeting code\n
            'class_length' (float): Class lenght (in minutes)\n
            'hour' (int): Class' start hour\n
            'minute' (int): Class' start minute\n
        """
        super().__init__(**kwargs)
        print(__name__, "started!")
        self.driver = None
        self.login_url = ""

        try:
            self.length = float(kwargs["class_length"])
            self.set_meeting_code(kwargs["code"])
        except KeyError: print("ERROR ****** ********\nSome parameters may be missing! Check 'help(AttendClass)' for more details ******")
        except (TypeError, ValueError): print("ERROR ****** ********\n'class_length' parameter may be containing an invalid value! Check 'help(AttendClass)' for more details ******")

        self.loginData = self.getLoginData()

    def run(self):
        print("Process scheduled to", self._Clockwork__target.format_datetime(), "\n")
        while True:
            print(self.get_time().format_datetime(), end="\r")
            if self._Clockwork__time_now >= self._Clockwork__target:
                print("Time reached\nStarting process...")
                try:
                    self.execute()
                    shutTime = self.get_class_length()
                    self.shutdownConnection(hours = shutTime[0], minutes = shutTime[1])
                    break
                except selenium.common.exceptions.WebDriverException:
                    print("EXECUTABLE ERROR!\nCheck 'selenium.common.exceptions.WebDriverException' for more informations!\n")
                    print("*"*70)
                    raise selenium.common.exceptions.WebDriverException
            sleep(1)

    def shutdownConnection(self, **kwargs):
        try: self.driver.close()
        except (AttributeError, selenium.common.exceptions.InvalidSessionIdException):
            print("ERROR ****** Browser driver not implemented or it's already closed! ******")
            return

        self._Clockwork__target = self.get_time() + timedelta(hours=kwargs["hours"], minutes=kwargs["minutes"])
        print("Kill scheduled to", self._Clockwork__target.format_datetime())
        while True:
            if self.get_time() == self._Clockwork__target or self.get_time() > self._Clockwork__target:
                self.driver.close()
                break
            sleep(1)
        return

    def get_class_length(self, **kwargs):
        minutes = self.length%60
        hours = int((self.length-minutes)/60)
        return hours, minutes
    
    def getLoginData(self):
        user = str(input("User: "))
        passwd = getpass("Password: ")
        return {"user": user, "passwd": passwd}

    def execute(self, **kwargs): raise NotImplementedError

    def doLogin(self): raise NotImplementedError

    def set_meeting_code(self, meeting_code): raise NotImplementedError



class GoogleClass(AttendClass):
    def __init__(self, **kwargs):
        """
        Parameters:\n
            'code' (string): Meeting code\n
            'class_length' (float): Class lenght (in minutes)\n
            'hour' (int): Class' start hour\n
            'minute' (int): Class' start minute\n
        """
        super().__init__(**kwargs)
        self.login_url = "https://accounts.google.com/Login?hl=pt-BR"

    def execute(self, **kwargs):
        self.driver = WebDriver(executable_path=EXECUTABLE_PATH)
        self.doLogin()

        try: self.driver.get(self.MEET_URL)
        except selenium.common.exceptions.InvalidArgumentException:
            print("ERROR ****** Meeting code was not properly set. Please, provide a valid one and try again! ******")
            self.driver.close()
        except selenium.common.exceptions.InvalidSessionIdException:
            return
        return

    def doLogin(self):
        start_time = self._Clockwork__time_now
        self.driver.get(self.login_url)

        self.driver.find_element_by_id("identifierId").send_keys(self.loginData["user"])
        self.driver.find_element_by_id("identifierNext").click()

        for count in range(15):
            try:
                self.driver.find_element_by_name("password").send_keys(self.loginData["passwd"])
                break
            except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.ElementNotInteractableException):
                sleep(1)

        try:
            self.driver.find_element_by_id("passwordNext").click()
            try:
                if self.driver.find_element_by_class_name("EjBTad"):
                    print("ERROR ****** Login failed. Check your password and try again! ******")
                    self.driver.close()
                    return
            except selenium.common.exceptions.NoSuchElementException: pass
        except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.ElementClickInterceptedException):
                print("ERROR ****** Login failed. Check your connection and try again! ******")
                self.driver.close()
                return
        print("Login time: ", self.get_time() - start_time)

    def set_meeting_code(self, meeting_code):
        try:
            meeting_code + "STRING_TEST"
        except TypeError:
            print("ERROR ****** Meeting code must be string! ******")
            self.MEET_URL =  ""
            return

        code_len = len(meeting_code)
        if code_len != 12 and code_len != 10:
            print("ERROR ****** Meeting code not accepted! Please check again ******")
            self.MEET_URL =  ""
        elif (code_len == 12 and meeting_code[3] == "-" and meeting_code[8] == "-") or code_len == 10:
            for crc in meeting_code:
                try:
                    int(crc)
                    print("ERROR ****** Meeting code must not contain numbers! ******")
                    self.MEET_URL =  ""
                    return
                except ValueError: continue
            self.MEET_URL="https://meet.google.com/%s" % meeting_code



class ZoomClass(GoogleClass):
    def __init__(self, **kwargs):
        """
        Parameters:\n
            'code' (string): Meeting code\n
            'class_length' (float): Class lenght (in minutes)\n
            'hour' (int): Class' start hour\n
            'minute' (int): Class' start minute\n
        """
        super().__init__(**kwargs)
        self.login_url = "https://zoom.us/google_oauth_signin"

    def execute(self, **kwargs):
        self.driver = WebDriver(executable_path=EXECUTABLE_PATH)
        self.doLogin()

        try:
            self.driver.get(self.MEET_URL)
            self.driver.find_elements_by_tag_name("a")[4].click()
        except (selenium.common.exceptions.InvalidArgumentException, selenium.common.exceptions.NoSuchElementException):
            print("ERROR ****** Meeting code was not properly set. Please, provide a valid one and try again! ******")
            self.driver.close()
            return
        except selenium.common.exceptions.InvalidSessionIdException:
            return
        self.driver.find_element_by_id("joinBtn").click()
        return

    def set_meeting_code(self, meeting_code):
        if "https://zoom.us/j/" in meeting_code:
            self.MEET_URL = meeting_code
        else: self.MEET_URL="https://zoom.us/j/%s" % meeting_code
