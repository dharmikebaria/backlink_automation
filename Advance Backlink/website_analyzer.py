import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

logger = logging.getLogger(__name__)

class WebsiteAnalyzer:
    """Analyzes login pages to find form elements"""

    def __init__(self):
        self.wait_timeout = 10

    def analyze_login_page(self, url: str, driver) -> dict:
        """Analyze the login page and return form element information"""
        try:
            logger.info("🔍 Analyzing login page for form elements...")

            analysis = {
                "email_fields": [],
                "username_fields": [],
                "password_fields": [],
                "submit_buttons": [],
                "method": "unknown"
            }

            # Wait for page to load
            time.sleep(2)

            # Find email fields
            email_selectors = [
                "input[type='email']",
                "input[name*='email']",
                "input[name*='mail']",
                "input[id*='email']",
                "input[id*='mail']",
                "input[placeholder*='email']",
                "input[placeholder*='mail']",
                "input[placeholder*='Email']",
                "input[placeholder*='Mail']"
            ]

            for selector in email_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            field_info = {
                                "element": element,
                                "id": element.get_attribute("id"),
                                "name": element.get_attribute("name"),
                                "type": element.get_attribute("type"),
                                "placeholder": element.get_attribute("placeholder")
                            }
                            analysis["email_fields"].append(field_info)
                except:
                    continue

            # Find username fields
            username_selectors = [
                "input[type='text']",
                "input[name*='username']",
                "input[name*='user']",
                "input[name*='login']",
                "input[id*='username']",
                "input[id*='user']",
                "input[id*='login']",
                "input[placeholder*='username']",
                "input[placeholder*='user']",
                "input[placeholder*='login']",
                "input[placeholder*='Username']",
                "input[placeholder*='User']",
                "input[placeholder*='Login']"
            ]

            for selector in username_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Skip if already in email fields
                            if any(field["element"] == element for field in analysis["email_fields"]):
                                continue

                            field_info = {
                                "element": element,
                                "id": element.get_attribute("id"),
                                "name": element.get_attribute("name"),
                                "type": element.get_attribute("type"),
                                "placeholder": element.get_attribute("placeholder")
                            }
                            analysis["username_fields"].append(field_info)
                except:
                    continue

            # Find password fields
            password_selectors = [
                "input[type='password']",
                "input[name*='password']",
                "input[name*='pass']",
                "input[name*='pwd']",
                "input[id*='password']",
                "input[id*='pass']",
                "input[id*='pwd']",
                "input[placeholder*='password']",
                "input[placeholder*='pass']",
                "input[placeholder*='Password']",
                "input[placeholder*='Pass']"
            ]

            for selector in password_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            field_info = {
                                "element": element,
                                "id": element.get_attribute("id"),
                                "name": element.get_attribute("name"),
                                "type": element.get_attribute("type"),
                                "placeholder": element.get_attribute("placeholder")
                            }
                            analysis["password_fields"].append(field_info)
                except:
                    continue

            # Find submit buttons
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Log In')",
                "button:contains('Sign In')",
                "button:contains('Login')",
                "button:contains('Sign In')",
                "button:contains('Submit')",
                "button:contains('Continue')",
                "button:contains('Next')",
                "a:contains('Log In')",
                "a:contains('Sign In')",
                "a:contains('Login')",
                "a:contains('Sign In')"
            ]

            for selector in submit_selectors:
                try:
                    if 'contains' in selector:
                        text = selector.split("contains('")[1].split("')")[0]
                        xpath = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                        elements = driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_info = {
                                "element": element,
                                "text": element.text,
                                "type": element.get_attribute("type"),
                                "tag": element.tag_name
                            }
                            analysis["submit_buttons"].append(button_info)
                except:
                    continue

            # Determine login method
            if analysis["email_fields"] or analysis["username_fields"]:
                analysis["method"] = "form"
            else:
                analysis["method"] = "unknown"

            logger.info(f"✅ Analysis complete: {len(analysis['email_fields'])} email, {len(analysis['username_fields'])} username, {len(analysis['password_fields'])} password, {len(analysis['submit_buttons'])} submit buttons")

            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing login page: {e}")
            return {
                "email_fields": [],
                "username_fields": [],
                "password_fields": [],
                "submit_buttons": [],
                "method": "unknown"
            }

    def find_login_button(self, driver):
        """Find login button on the page"""
        try:
            login_selectors = [
                "a:contains('Log In')",
                "a:contains('Sign In')",
                "a:contains('Login')",
                "a:contains('Sign In')",
                "button:contains('Log In')",
                "button:contains('Sign In')",
                "button:contains('Login')",
                "button:contains('Sign In')",
                "[href*='login']",
                "[href*='signin']",
                "[href*='auth']"
            ]

            for selector in login_selectors:
                try:
                    if 'contains' in selector:
                        text = selector.split("contains('")[1].split("')")[0]
                        xpath = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                        elements = driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"🔘 Found login button: {selector}")
                            return element
                except:
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Error finding login button: {e}")
            return None
