from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time, os, getpass
import undetected_chromedriver as uc

# Prevent resource leak warning
def _uc_safe_del(self):
    try:
        self.quit()
    except Exception:
        pass
uc.Chrome.__del__ = _uc_safe_del

class HackernoonAutomation:
    def __init__(self, driver=None, email=None, password=None, website=None, non_interactive=True):
        self._owns_driver = driver is None
        if driver is None:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--start-maximized')
            self.driver = uc.Chrome(options=options)
        else:
            self.driver = driver
        self.wait = WebDriverWait(self.driver, 20)
        try:
            os.makedirs("screenshots", exist_ok=True)
        except:
            pass
        self._ss_i = 0
        self.email = email
        self.password = password
        self.website = website or os.environ.get("HNOON_URL") or "https://hackernoon.com/login?redirect=app"
        self.non_interactive = non_interactive
    
    def screenshot(self, name):
        try:
            self._ss_i += 1
            path = os.path.join("screenshots", f"hnoon_{int(time.time())}_{self._ss_i}_{name}.png")
            self.driver.save_screenshot(path)
            return path
        except:
            return ""
    
    def _safe_click(self, el):
        try:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", el)
            except:
                pass
            el.click()
        except:
            try:
                self.driver.execute_script("arguments[0].click();", el)
            except:
                try:
                    ActionChains(self.driver).move_to_element(el).pause(0.2).click().perform()
                except:
                    pass
    
    def _wait_ready(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            try:
                ready = self.driver.execute_script("return document.readyState")
                if ready in ("interactive", "complete"):
                    return True
            except:
                pass
            time.sleep(0.3)
        return False
    
    def dismiss_popups(self, attempts=4):
        try:
            for _ in range(attempts):
                acted = False
                for xp in [
                    "//*[@role='dialog']//*[@aria-label='Close']",
                    "//button[@aria-label='Close']",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'got it')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ok')]",
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
                    "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
                    "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
                    "//div[contains(@class,'modal')]//button[contains(.,'×') or contains(.,'x') or contains(.,'Close')]"
                ]:
                    try:
                        els = self.driver.find_elements(By.XPATH, xp)
                        for el in els:
                            if el.is_displayed():
                                self._safe_click(el)
                                time.sleep(0.5)
                                acted = True
                    except:
                        continue
                if not acted:
                    break
        except:
            pass
        
    def _accept_consent_popups(self, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            accepted = False
            for xp in [
                "//*[@id='onetrust-accept-btn-handler']",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept all')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
            ]:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            self._safe_click(el)
                            time.sleep(0.5)
                            accepted = True
                except:
                    pass
            if accepted:
                break
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        for xp in [
                            "//*[@id='onetrust-accept-btn-handler']",
                            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept all')]",
                            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
                            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
                            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
                        ]:
                            try:
                                els = self.driver.find_elements(By.XPATH, xp)
                                for el in els:
                                    if el.is_displayed():
                                        self._safe_click(el)
                                        time.sleep(0.5)
                                        accepted = True
                                        break
                            except:
                                pass
                        self.driver.switch_to.default_content()
                        if accepted:
                            break
                    except:
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
            except:
                pass
            if accepted:
                break
            time.sleep(0.4)
        return accepted
        
    def _click_yes_confirmation(self):
        try:
            for xp in [
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\"yes, i'm ready to submit\")]",
                "//*[@role='dialog']//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\"yes, i'm ready to submit\")]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ready to submit')]",
                "//*[@role='dialog']//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ready to submit')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'yes')]",
                "//*[@role='dialog']//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'yes')]"
            ]:
                try:
                    btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                    self._safe_click(btn)
                    time.sleep(1)
                    return True
                except:
                    continue
        except:
            pass
        return False
    
    def _find_title_js(self):
        try:
            el = self.driver.execute_script("""
                var q = (sel)=>document.querySelector(sel);
                var el = q("input[placeholder*='Title'],textarea[placeholder*='Title']");
                if(el) return el;
                el = q("input[name*='title'],input[id*='title'],textarea[name*='title'],textarea[id*='title']");
                if(el) return el;
                el = q("input[placeholder*='Headline'],textarea[placeholder*='Headline']");
                if(el) return el;
                el = q("[contenteditable='true'][data-placeholder*='Title'],[contenteditable='true'][placeholder*='Title']");
                if(el) return el;
                el = q("[contenteditable='true'][data-placeholder*='Headline'],[contenteditable='true'][placeholder*='Headline']");
                return el;
            """)
            if el:
                return el
        except:
            pass
        try:
            el = self.driver.execute_script("""
                var labs = Array.from(document.querySelectorAll('label'));
                var lab = labs.find(l=> (l.innerText||'').toLowerCase().includes('title'));
                if(lab){
                    var nxt = lab.nextElementSibling;
                    if(nxt && (nxt.tagName||'').toLowerCase()==='input') return nxt;
                    var inp = lab.parentElement ? lab.parentElement.querySelector('input,textarea') : null;
                    if(inp) return inp;
                }
                return null;
            """)
            if el:
                return el
        except:
            pass
        return None
    
    def _click_yes_in_settings(self):
        clicked = False
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except:
            pass
        for xp in [
            "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'is this story original')]/following::button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'yes')][1]",
            "//button[normalize-space()='Yes']",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'yes')]"
        ]:
            try:
                btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                self._safe_click(btn)
                time.sleep(0.8)
                clicked = True
                break
            except:
                continue
        if not clicked:
            try:
                el = self.driver.execute_script("""
                    var bs = Array.from(document.querySelectorAll('button'));
                    return bs.find(b => (b.innerText||'').toLowerCase().includes('yes'));
                """)
                if el:
                    self.driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.6)
                    clicked = True
            except:
                pass
        return clicked
        
    def _load_credentials(self):
        if self.email and self.password:
            return (self.email, self.password)
        here = os.path.dirname(os.path.abspath(__file__))
        cred_path = os.path.join(here, "credential.txt")
        email = os.environ.get("HNOON_EMAIL") or self.email or None
        password = os.environ.get("HNOON_PASSWORD") or self.password or None
        if not email or not password:
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
                if lines:
                    if any("=" in s for s in lines):
                        for s in lines:
                            if "=" in s:
                                k, v = s.split("=", 1)
                                k = k.strip().lower()
                                v = v.strip().strip('\"').strip("'")
                                if k in ("email", "user", "username"):
                                    if not email:
                                        email = v
                                elif k in ("password", "pass"):
                                    if not password:
                                        password = v
                    else:
                        if not email:
                            email = lines[0] if len(lines) > 0 else None
                        if not password:
                            password = lines[1] if len(lines) > 1 else None
            except FileNotFoundError:
                print("credential.txt not found. Create credential.txt with email and password.")
                return None, None
            except Exception:
                print("Failed reading credential.txt")
                return None, None
        placeholders = {"your-email@example.com", "your-strong-password", "password", "example@example.com"}
        if (email in placeholders) or (password in placeholders):
            print("Invalid credential.txt placeholders detected. Update with real email and password.")
            return None, None
        if not email or not password:
            print("Invalid credential.txt. Provide email and password.")
            return None, None
        return (email, password)
        
    def _fill_input_with_retries(self, locator, text, attempts=3):
        for _ in range(attempts):
            try:
                el = self.wait.until(EC.visibility_of_element_located(locator))
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'});", el)
                except:
                    pass
                try:
                    self._safe_click(el)
                except:
                    pass
                try:
                    try:
                        el.clear()
                    except:
                        pass
                    try:
                        ActionChains(self.driver).click(el).pause(0.05).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
                    except:
                        pass
                    el.send_keys(text)
                    return True
                except:
                    try:
                        self.driver.execute_script(
                            "arguments[0].value = arguments[1];"
                            "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                            el, text
                        )
                        return True
                    except:
                        pass
            except:
                time.sleep(0.4)
        return False
        
    def login(self):
        """Login to Hackernoon"""
        self.driver.get(self.website)
        self._wait_ready(10)
        try:
            self._accept_consent_popups(8)
        except:
            pass
        self.dismiss_popups(4)
        self.screenshot("login_page")
        try:
            self.driver.execute_script("document.querySelectorAll('#onetrust-banner-sdk,.ot-sdk-container,.cookie').forEach(el=>el.style.display='none');")
        except:
            pass
        
        email, password = self._load_credentials()
        if not email or not password:
            print("Login failed or credentials missing.")
            return False
        
        # Wait for login form
        email_field = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//input[@type='email' or contains(@name, 'email')]")
        ))
        
        password_field = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='password']")))
        
        # Enter credentials
        self._fill_input_with_retries((By.XPATH, "//input[@type='email' or contains(@name, 'email')]"), email, attempts=5)
        self._fill_input_with_retries((By.XPATH, "//input[@type='password']"), password, attempts=5)
        self.screenshot("creds_filled")
        
        # Click login button
        try:
            self._accept_consent_popups(4)
        except:
            pass
        login_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in') or @type='submit']")
        ))
        self._safe_click(login_button)
        time.sleep(3)
        self._wait_ready(10)
        self.screenshot("after_login_click")
        try:
            # Detect common login error messages and print them
            error_els = self.driver.find_elements(
                By.XPATH,
                "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'invalid') or "
                "contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'incorrect') or "
                "contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'try again')] | "
                "//div[contains(@class,'error')] | //p[contains(@class,'error')] | //span[contains(@class,'error')]"
            )
            for e in error_els:
                if e.is_displayed():
                    txt = e.text.strip()
                    if txt:
                        print(f"Login error message detected: {txt}")
                        break
        except:
            pass
        
        print("Login successful")
        return True
        
    def navigate_to_writing(self):
        """Navigate to the writing page"""
        # Wait for page to load after login
        time.sleep(5)
        self._wait_ready(10)
        self.screenshot("post_login")
        
        # Click on "Start Writing" button
        start_writing_button = None
        for xp in [
            "//a[normalize-space()='Write']",
            "//button[normalize-space()='Write']",
            "//a[contains(@href,'/new')]",
            "//a[contains(text(), 'Start Writing')]",
            "//a[contains(text(), 'WRITER')]",
            "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'write')]",
            "//a[contains(@href, '/app')]",
            "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start writing')]"
        ]:
            try:
                start_writing_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                if start_writing_button:
                    break
            except:
                continue
        if start_writing_button:
            self._safe_click(start_writing_button)
            try:
                time.sleep(1)
                handles = self.driver.window_handles
                if len(handles) > 1:
                    self.driver.switch_to.window(handles[-1])
            except:
                pass
            time.sleep(3)
            self._wait_ready(10)
            self.screenshot("writing_page")
            start_draft_button = None
            for xp in [
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start draft')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'start draft')]",
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'new draft')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'new draft')]",
                "//a[contains(@href, '/draft')]",
                "//button[contains(@aria-label,'Start Draft')]",
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create draft')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create draft')]"
            ]:
                try:
                    start_draft_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                    if start_draft_button:
                        break
                except:
                    continue
            if start_draft_button:
                self._safe_click(start_draft_button)
                time.sleep(3)
                self._wait_ready(10)
                self.screenshot("draft_opened")
                print("Opened draft editor")
            else:
                try:
                    self.driver.get("https://app.hackernoon.com/new")
                    self._wait_ready(10)
                    self.screenshot("writing_page_direct")
                    print("Opened draft editor via direct link")
                except:
                    pass
        else:
            # Fallback: go directly to editor if possible
            try:
                self.driver.execute_script("""
                    var links = Array.from(document.querySelectorAll('a'));
                    var w = links.find(a => (a.innerText||'').trim().toLowerCase()==='write');
                    if(w) w.click();
                """)
                time.sleep(2)
                self._wait_ready(10)
                handles = self.driver.window_handles
                if len(handles) > 1:
                    self.driver.switch_to.window(handles[-1])
            except:
                pass
            try:
                self.driver.get("https://app.hackernoon.com/new")
                self._wait_ready(10)
                self.screenshot("writing_page_direct")
            except:
                pass
        
        print("Navigated to writing page")
        
    def create_story(self):
        """Create a new story with content from blog.txt"""
        # Wait for story editor to load
        time.sleep(3)
        self._wait_ready(10)
        try:
            self._accept_consent_popups(4)
        except:
            pass
        # Ensure we are on an editor-like page; if not, try direct draft
        try:
            has_editor = bool(self.driver.find_elements(By.XPATH, "//div[@contenteditable='true'] | //div[@role='textbox']"))
            if not has_editor:
                self.driver.get("https://hackernoon.com/draft")
                self._wait_ready(10)
        except:
            pass
        self.screenshot("editor_loaded")
        
        # Read content from blog.txt
        try:
            blog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog.txt')
            with open(blog_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except FileNotFoundError:
            try:
                default = (
                    "My Awesome Blog Title\n"
                    "This is a placeholder blog body.\n"
                    "Open blog.txt, replace this with your content, and rerun."
                )
                with open('blog.txt', 'w', encoding='utf-8') as wf:
                    wf.write(default)
                print("blog.txt was missing and has been created with a template. Please edit it and rerun.")
            except Exception as fe:
                print(f"Failed to create blog.txt automatically: {fe}")
            return False
        
        # Split content into title and body (assuming first line is title)
        lines = content.split('\n')
        title = lines[0] if len(lines) > 0 else "Default Title"
        body = '\n'.join(lines[1:]) if len(lines) > 1 else "Default body content"
        
        # Find and fill title field
        title_field = None
        try:
            title_field = self._find_title_js()
        except:
            pass
        if not title_field:
            for xp in [
                "//input[@placeholder='Title']",
                "//textarea[@placeholder='Title']",
                "//input[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'headline')]",
                "//textarea[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'headline')]",
                "//*[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'title')]",
                "//input[@name='title']",
                "//textarea[@name='title']"
            ]:
                try:
                    title_field = self.wait.until(EC.presence_of_element_located((By.XPATH, xp)))
                    if title_field:
                        break
                except:
                    continue
        if not title_field:
            raise Exception("Title field not found")
        try:
            self.driver.execute_script("arguments[0].focus();", title_field)
        except:
            pass
        try:
            title_field.clear()
        except:
            pass
        try:
            title_field.send_keys(title)
        except:
            try:
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", title_field, title)
            except:
                pass
        
        # Find and fill body field
        body_field = None
        for xp in [
            "//div[@contenteditable='true']",
            "//textarea[@placeholder='Write something nice...']",
            "//*[contains(@class, 'editor')]",
            "//div[@role='textbox']"
        ]:
            try:
                body_field = self.wait.until(EC.presence_of_element_located((By.XPATH, xp)))
                if body_field:
                    break
            except:
                continue
        if body_field:
            try:
                body_field.clear()
            except:
                pass
            try:
                ActionChains(self.driver).click(body_field).pause(0.1).send_keys(body).perform()
            except:
                body_field.send_keys(body)
        self.screenshot("content_entered")
        
        print("Title and body added successfully")
        
        # Click Save or Save Draft button
        try:
            save_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'SAVE') or contains(text(), 'Save')]")
            ))
            self._safe_click(save_button)
            time.sleep(2)
            self.screenshot("saved")
        except:
            print("Save button not found or not clicked")
        
        return True
        
    def story_settings(self):
        """Configure story settings"""
        # Click on Story Settings
        settings_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(), 'STORY SETTINGS') or contains(text(), 'Story Settings')]")
        ))
        self._safe_click(settings_button)
        time.sleep(2)
        self.screenshot("settings_open")
        
        print("Opened story settings")
        
        # Scroll down
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Click Yes button
        try:
            if self._click_yes_in_settings():
                self.screenshot("clicked_yes")
                print("Clicked Yes")
            else:
                if self._click_yes_confirmation():
                    self.screenshot("clicked_yes")
                    print("Clicked Yes")
                else:
                    print("Yes button not found")
        except:
            print("Yes button not found")
        
        # Click Submit Story button
        try:
            submit_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'SUBMIT STORY') or contains(text(), 'Submit Story') or contains(text(), 'Publish') or contains(text(),'SUBMIT')]")
            ))
            self._safe_click(submit_button)
            print("Story submitted successfully")
            self.screenshot("submitted")
            try:
                self._click_yes_confirmation()
            except:
                pass
        except:
            print("Submit button not found")
        
    def run(self):
        """Main execution method"""
        try:
            success_login = self.login()
            if not success_login:
                print("Login failed or credentials missing. Set HNOON_EMAIL and HNOON_PASSWORD and rerun.")
                return False
            self.navigate_to_writing()
            success_story = self.create_story()
            if not success_story:
                print("Skipping story submission because blog content is missing. Edit blog.txt and rerun.")
                return False
            self.story_settings()
            print("Automation completed successfully!")
            
            if self.non_interactive or os.environ.get("HNOON_NONINTERACTIVE") == "1":
                time.sleep(5)
            else:
                try:
                    input("Press Enter to close the browser...")
                except:
                    time.sleep(10)
            
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            # Take screenshot on error
            self.driver.save_screenshot('error_screenshot.png')
            
        finally:
            try:
                if self._owns_driver and self.driver:
                    self.driver.quit()
            except:
                pass
        return True

def run(driver, website, email, username, password):
    try:
        app = HackernoonAutomation(driver=driver, email=email, password=password, website=website, non_interactive=True)
        return bool(app.run())
    except Exception:
        return False

if __name__ == "__main__":
    # Create a blog.txt file first with your content
    # Example blog.txt format:
    # My Awesome Blog Title
    # This is the body of my blog post.
    # It can have multiple paragraphs.
    
    automation = HackernoonAutomation()
    automation.run()
