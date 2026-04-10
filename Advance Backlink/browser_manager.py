"""
Browser management functionality for the Universal Login Bot
"""
import os
import logging
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from config import BROWSER_OPTIONS, PAGE_LOAD_TIMEOUT, ELEMENT_TIMEOUT

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manages Chrome WebDriver creation and configuration"""

    def __init__(self):
        self.driver = None
        self.wait = None

    def create_driver(self) -> bool:
        """Create Chrome driver"""
        try:
            logger.info("🚗 Creating WebDriver...")

            # Detect Chrome version
            chrome_version = self._get_chrome_version()
            logger.info(f"🔍 Detected Chrome version: {chrome_version}")

            options = uc.ChromeOptions()

            # Basic options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            # Anti-detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')

            # User agent
            options.add_argument(f'--user-agent={BROWSER_OPTIONS["user_agent"]}')

            # Window size
            options.add_argument(f'--window-size={BROWSER_OPTIONS["window_size"]}')

            # Disable save password prompt
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            # Headless mode if configured
            if BROWSER_OPTIONS['headless']:
                options.add_argument('--headless')

            driver = None
            try:
                driver = uc.Chrome(
                    options=options,
                    headless=BROWSER_OPTIONS['headless'],
                    use_subprocess=False,
                    version_main=BROWSER_OPTIONS['chrome_version']
                )
                self.driver = driver

                # Set timeouts
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

                # Create wait object
                self.wait = WebDriverWait(self.driver, ELEMENT_TIMEOUT)

                # Add stealth
                self._add_stealth_js()

                logger.info("✅ WebDriver created successfully")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to create driver: {e}")
                # Clean up partial driver object
                if driver:
                    try:
                        driver.quit()
                    except OSError as oe:
                        if '[WinError 6]' in str(oe):
                            logger.warning("Handle invalid during cleanup - expected")
                        else:
                            logger.error(f"Error cleaning up failed driver: {oe}")
                    except Exception as ce:
                        logger.error(f"Error cleaning up failed driver: {ce}")
                self.driver = None
                self.wait = None
                return False

        except Exception as e:
            logger.error(f"❌ Driver creation error: {e}")
            return False

    def _get_chrome_version(self) -> int:
        """Get installed Chrome version"""
        try:
            import subprocess
            result = subprocess.run(['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        version = line.split()[-1]
                        major_version = int(version.split('.')[0])
                        return major_version
            # Fallback: try chrome.exe --version
            result = subprocess.run(['chrome', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                major_version = int(version.split('.')[0])
                return major_version
        except Exception as e:
            logger.debug(f"Chrome version detection failed: {e}")
            pass
        # Default to configured version if detection fails
        return BROWSER_OPTIONS['chrome_version']

    def _add_stealth_js(self):
        """Add stealth JavaScript"""
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """

        try:
            self.driver.execute_script(stealth_js)
        except Exception as e:
            logger.debug(f"Stealth JS failed: {e}")

    def close_driver(self):
        """Close driver"""
        if self.driver:
            try:
                # Stop the service first to prevent handle issues
                if hasattr(self.driver, 'service') and self.driver.service:
                    self.driver.service.stop()
                self.driver.quit()
                logger.info("✅ WebDriver closed")
            except OSError as e:
                if '[WinError 6]' in str(e):
                    logger.warning("Handle invalid error during driver cleanup - this is expected")
                else:
                    logger.error(f"Error closing driver: {e}")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                # Completely remove the driver reference to prevent __del__ issues
                self.driver = None
                self.wait = None
                # Try to delete the attribute to prevent garbage collection issues
                try:
                    delattr(self, 'driver')
                except Exception as e:
                    pass

    def take_screenshot(self, prefix: str) -> str:
        """Take screenshot"""
        try:
            import os
            from datetime import datetime
            import random
            import string

            os.makedirs("screenshots", exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

            domain = "website"
            try:
                if self.driver:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(self.driver.current_url)
                    domain = parsed.netloc.replace('.', '_')[:20]
            except Exception as e:
                pass

            filename = f"{prefix}_{domain}_{timestamp}_{random_str}.png"
            path = f"screenshots/{filename}"

            self.driver.save_screenshot(path)
            logger.info(f"📸 Screenshot: {filename}")

            return filename

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""
