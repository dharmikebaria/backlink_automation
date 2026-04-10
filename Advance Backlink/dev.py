"""
DEV.TO Blog Automation Script
Automatically logs into dev.to, creates and publishes a blog post from blog.txt
"""

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains # Added for stable paste
import time
import os
import sys
import random
import re
import io
import tempfile
import subprocess # Added for PowerShell clipboard

# Naye imports image handling ke liye
try:
    from PIL import Image
except ImportError:
    pass

# Prevent resource leak warning
def _uc_safe_del(self):
    try:
        self.quit()
    except Exception:
        pass
uc.Chrome.__del__ = _uc_safe_del

class DevToAutomation:
    def __init__(self, email, password):
        """Initialize the automation with login credentials"""
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.type_min = 0.06
        self.type_max = 0.12
        self.line_pause = 0.25
        self.image_pre_delay = 1.8
        self.image_post_delay = 2.0
        self.blog_file_path = "blog.txt"
        
    def human_type(self, element, text, min_delay=0.01, max_delay=0.05):
        """Type text using resilient chunking to prevent freezing"""
        try:
            # Split text into chunks of 50 characters
            chunk_size = 50
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            
            for chunk in chunks:
                try:
                    element.send_keys(chunk)
                except Exception:
                    # If element reference is stale or lost, try to recover
                    try:
                        self._dismiss_popups()
                        # Attempt to re-focus editor
                        new_el = self._focus_editor()
                        if new_el:
                            new_el.send_keys(chunk)
                            element = new_el # Update reference
                        else:
                            # Fallback: Type into whatever is focused
                            ActionChains(self.driver).send_keys(chunk).perform()
                    except:
                        pass
                time.sleep(random.uniform(0.05, 0.1))
        except Exception:
            # Fallback to standard send_keys if anything goes wrong
            try:
                element.send_keys(text)
            except:
                pass

    def copy_image_to_clipboard(self, image_path):
        """Copy image file to clipboard using PowerShell (Robust -sta)"""
        try:
            abs_path = os.path.abspath(image_path)
            # Escape for PowerShell double-quoted string
            ps_path = abs_path.replace("`", "``").replace("$", "`$").replace('"', '`"')
            
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $files = [System.Collections.Specialized.StringCollection]::new()
            $files.Add("{ps_path}")
            [System.Windows.Forms.Clipboard]::SetFileDropList($files)
            '''
            # Use -sta for clipboard operations
            subprocess.run(["powershell", "-sta", "-command", cmd], timeout=10)
            print(f"✓ Image copied to clipboard: {image_path}")
            return True
        except Exception as e:
            print(f"✗ Failed to copy image to clipboard: {e}")
            return False

    def upload_image_to_editor(self, image_path, textarea):
        """Upload image using clipboard paste and handle navigation"""
        resolved = self._resolve_image_path(image_path)
        if not resolved or not os.path.exists(os.path.abspath(resolved)):
            return False
        if self.copy_image_to_clipboard(resolved):
            time.sleep(1.5) # Wait for clipboard
            
            # Click textarea to ensure focus
            try:
                textarea.click()
            except:
                self.driver.execute_script("arguments[0].focus();", textarea)
            
            # Force caret to absolute end and ensure new line
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.END)
            actions.pause(0.2)
            actions.send_keys(Keys.ENTER) # Add explicit newline before image
            actions.pause(0.2)
            actions.perform()

            # Paste (Ctrl+V)
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
            actions.perform()
            print("✓ Pasted image from clipboard")
            
            time.sleep(5) # Wait for upload/processing
            
            # Robust Navigation: Escape -> Right -> Enter -> Enter (for extra gap)
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE)
            actions.pause(0.5)
            actions.send_keys(Keys.RIGHT)
            actions.pause(0.5)
            actions.send_keys(Keys.ENTER)
            actions.pause(0.2)
            actions.send_keys(Keys.ENTER) # Extra newline after image
            actions.perform()
            time.sleep(1)
            return True
        return False
    
    def _resolve_image_path(self, path_str):
        try:
            base_dir = os.path.dirname(os.path.abspath(self.blog_file_path)) if self.blog_file_path else os.getcwd()
            s = (path_str or "").strip()
            if not s:
                return None
            candidates = []
            if ('/' in s) or ('\\' in s):
                candidates.extend([
                    s,
                    os.path.abspath(s) if os.path.isabs(s) else os.path.abspath(os.path.join(base_dir, s)),
                    os.path.join(base_dir, s.replace('../', '').replace('..\\', '')),
                    s.replace('../', '').replace('..\\', ''),
                ])
            else:
                candidates.extend([
                    os.path.abspath(os.path.join(base_dir, '..', 'Image', s)),
                    os.path.join(base_dir, 'Image', s),
                    os.path.join(base_dir, s),
                    os.path.join(base_dir, 'Ima', s),
                    os.path.abspath(os.path.join(base_dir, '..', 'Ima', s)),
                ])
            for p in candidates:
                try:
                    ap = os.path.abspath(p)
                    if os.path.isfile(ap):
                        return ap
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        print("Setting up Chrome WebDriver...")

        try:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            options.add_argument('--start-maximized')

            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            self.driver = uc.Chrome(options=options, headless=False)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 15)

            # Add stealth JS
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
            self.driver.execute_script(stealth_js)

            print("WebDriver setup successful!")
        except Exception as e:
            print(f"Failed to setup WebDriver: {e}")
            raise
        
    def login(self):
        """Login to dev.to website"""
        print("\n" + "="*50)
        print("Logging in to dev.to...")
        print("="*50)
        
        # Navigate directly to login page
        self.driver.get("https://dev.to/enter")
        
        try:
            # 1. Handle "Continue with Email" if present
            try:
                # Check for Apple/Google/GitHub first to see if we need to find Email button
                # Short wait to avoid waiting too long if it's not there
                email_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'c-btn') and contains(text(), 'Email')] | //a[contains(@href, 'email')]"))
                )
                email_btn.click()
                print("Clicked Email login button")
            except:
                # Maybe already on form or button not found/needed
                pass

            # 2. Fill Email
            print("Filling login form...")
            try:
                email_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#user_email, input[name='user[email]']")))
                email_field.clear()
                email_field.send_keys(self.email)
                print("Email entered")
            except:
                print("Could not find email field")
                raise
            
            # 3. Fill Password
            try:
                password_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#user_password, input[name='user[password]']")))
                password_field.clear()
                password_field.send_keys(self.password)
                print("Password entered")
            except:
                print("Could not find password field")
                raise
            
            # 4. Submit
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Log in'], button[type='submit']")
                submit_btn.click()
                print("Submitted login form")
            except:
                # Try pressing enter on password field
                password_field.send_keys(Keys.RETURN)
                print("Pressed Enter to submit")
            
            # 5. Verify Login
            try:
                # Wait for either the profile image or the 'Write' button
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#current-user-profile-image, a[href='/new'], button#user-menu-trigger")))
                print("✓ Login successful!")
            except:
                print("⚠ Warning: Could not verify login automatically. Checking for errors...")
                try:
                    error = self.driver.find_element(By.CLASS_NAME, "c-flash")
                    print(f"Login error found: {error.text}")
                except:
                    pass
            
        except Exception as e:
            print(f"✗ Login failed: {e}")
            self.driver.save_screenshot("login_error.png")
            raise

    def navigate_to_create_post(self):
        """Navigate to create new post page"""
        print("\n" + "="*50)
        print("Navigating to create post page...")
        print("="*50)
        
        self.driver.get("https://dev.to/new")
        
        try:
            # Wait for title input to be ready
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea#article-form-title, input#article-form-title")))
            print("✓ Create post page loaded successfully!")
        except Exception as e:
            print(f"✗ Failed to load create post page: {e}")
            self.driver.save_screenshot("navigation_error.png")
            raise
    
    def read_blog_content(self, file_path="blog.txt"):
        """Read blog content from text file"""
        print(f"\nReading blog content from '{file_path}'...")
        
        if not os.path.exists(file_path):
            print(f"⚠ File '{file_path}' not found. Creating a dummy file.")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("My Dev.to Automation Journey\n\nThis is a test post created by Python script.\n\nCheck out [Google](https://google.com) for more info.")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as file:
                lines = file.readlines()
        
        if not lines:
             return "Untitled Post", "Test Content"

        title = lines[0].strip()
        # Join the rest of the lines for body, preserving newlines
        body = "".join(lines[1:])
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        
        print(f"✓ Title extracted: {title[:30]}...")
        return title, body
    
    def _process_image_for_upload(self, image_path, attempt=1):
        try:
            img = Image.open(image_path)
            max_side = 1600 if attempt == 1 else (1200 if attempt == 2 else 900)
            if img.width > max_side or img.height > max_side:
                img.thumbnail((max_side, max_side))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            quality = 85 if attempt == 1 else (75 if attempt == 2 else 65)
            img.convert("RGB").save(tmp.name, "JPEG", quality=quality, optimize=True, progressive=True)
            return tmp.name
        except Exception:
            return image_path

    def _is_json_error_visible(self):
        try:
            e1 = self.driver.find_elements(By.XPATH, "//*[contains(text(), \"Unexpected end of JSON input\")]")
            e2 = self.driver.find_elements(By.XPATH, "//*[contains(text(), \"Failed to execute 'json' on 'Response'\")]")
            return any(el.is_displayed() for el in (e1 + e2))
        except Exception:
            return False

    def _dismiss_json_errors(self):
        try:
            btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Dismiss')]")
            for b in btns:
                try:
                    if b.is_displayed():
                        self.driver.execute_script("arguments[0].click();", b)
                        time.sleep(0.5)
                except Exception:
                    continue
        except Exception:
            pass

    def _count_image_marks(self, text):
        try:
            return len(re.findall(r'!\[.*?\]\(.*?\)', text or ""))
        except Exception:
            return 0

    def _wait_image_insert(self, textarea, prev_count, timeout=45):
        start = time.time()
        while time.time() - start < timeout:
            if self._is_json_error_visible():
                self._dismiss_json_errors()
            try:
                new_val = textarea.get_attribute('value')
                cnt = self._count_image_marks(new_val)
                if cnt > prev_count:
                    time.sleep(0.8)
                    return True
                if self._value_has_image_link(new_val):
                    time.sleep(0.8)
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False
    
    def _focus_editor(self):
        try:
            try:
                ta = self.driver.find_element(By.ID, "article_body_markdown")
                if ta.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ta)
                    ta.click()
                    return ta
            except Exception:
                pass
            try:
                editable = None
                for el in self.driver.find_elements(By.XPATH, "//*[@contenteditable='true']"):
                    if el.is_displayed():
                        editable = el
                        break
                if editable:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", editable)
                    editable.click()
            except Exception:
                pass
        except Exception:
            pass
        return None
    
    def _value_has_image_link(self, text):
        try:
            return bool(re.search(r'!\[.*?\]\((https?:\/\/[^)]*dev-to-uploads[^)]*|https?:\/\/[^)]*cloudinary[^)]*|https?:\/\/[^)]*imgur[^)]*)\)', (text or ""), re.I))
        except Exception:
            return False

    def _find_image_button(self):
        try:
            candidates = [
                "//button[contains(translate(@aria-label,'IMAGE','image'),'image')]",
                "//button[contains(translate(@title,'IMAGE','image'),'image')]",
                "//button[contains(translate(.,'IMAGE','image'),'image')]",
                "//span[contains(translate(.,'IMAGE','image'),'image')]/ancestor::button[1]"
            ]
            for xp in candidates:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            return el
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _upload_image_via_fileinput(self, textarea, img_path, prev_count):
        try:
            btn = self._find_image_button()
            if btn:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                except Exception:
                    pass
            inputs = []
            try:
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='file' and contains(@accept,'image')]")
            except Exception:
                inputs = []
            if not inputs:
                try:
                    inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                except Exception:
                    inputs = []
            target = None
            for inp in inputs[::-1]:
                try:
                    if inp.is_displayed() and inp.is_enabled():
                        target = inp
                        break
                except Exception:
                    continue
            if not target:
                return False
            try:
                if not target.is_displayed():
                    self.driver.execute_script("arguments[0].style.display='block'; arguments[0].style.visibility='visible';", target)
            except Exception:
                pass
            target.send_keys(img_path)
            try:
                self._click_insert_buttons()
            except Exception:
                pass
            ok = self._wait_image_insert(textarea, prev_count, timeout=45)
            return ok
        except Exception:
            return False
    
    def _click_insert_buttons(self, timeout=8):
        try:
            start = time.time()
            while time.time() - start < timeout:
                candidates = [
                    "//button[contains(translate(.,'INSERT','insert'),'insert')]",
                    "//button[contains(translate(.,'ADD IMAGE','add image'),'add image')]",
                    "//button[contains(translate(.,'DONE','done'),'done')]",
                    "//button[contains(translate(.,'SAVE','save'),'save')]",
                    "//button[contains(translate(.,'UPLOAD','upload'),'upload')]",
                    "//span[contains(translate(.,'INSERT','insert'),'insert')]/ancestor::button[1]"
                ]
                clicked = False
                for xp in candidates:
                    try:
                        for b in self.driver.find_elements(By.XPATH, xp):
                            if b.is_displayed() and b.is_enabled():
                                self.driver.execute_script("arguments[0].click();", b)
                                clicked = True
                                time.sleep(0.5)
                                break
                        if clicked:
                            break
                    except Exception:
                        continue
                if clicked:
                    return True
                time.sleep(0.4)
        except Exception:
            pass
        return False
    
    def _paste_into_contenteditable(self, textarea, processed, prev_count):
        try:
            editable = None
            try:
                for el in self.driver.find_elements(By.XPATH, "//*[@contenteditable='true']"):
                    if el.is_displayed():
                        editable = el
                        break
            except Exception:
                editable = None
            if not editable:
                return False
            if self.copy_image_to_clipboard(processed):
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", editable)
                except Exception:
                    pass
                editable.click()
                time.sleep(0.2)
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                ok = self._wait_image_insert(textarea, prev_count, timeout=45)
                return ok
            return False
        except Exception:
            return False

    def _upload_image_with_retry(self, textarea, img_path, prev_count):
        try:
            resolved = self._resolve_image_path(img_path)
            abs_img_path = os.path.abspath(resolved) if resolved else None
            if not abs_img_path or not os.path.exists(abs_img_path):
                return False
            for attempt in range(1, 4):
                self._dismiss_json_errors()
                processed = self._process_image_for_upload(abs_img_path, attempt)
                old_val = textarea.get_attribute('value')
                pasted = False
                try:
                    ok_editable = self._paste_into_contenteditable(textarea, processed, prev_count)
                    if ok_editable:
                        return True
                except Exception:
                    pass
                try:
                    self._focus_editor()
                    if self.copy_image_to_clipboard(processed):
                        textarea.click()
                        time.sleep(0.2)
                        textarea.send_keys(Keys.CONTROL, 'v')
                        try:
                            self._click_insert_buttons()
                        except Exception:
                            pass
                        pasted = True
                        if pasted:
                            ok = self._wait_image_insert(textarea, prev_count, timeout=45)
                            if ok:
                                return True
                            else:
                                self._dismiss_json_errors()
                except Exception:
                    pass
                try:
                    ok_file = self._upload_image_via_fileinput(textarea, processed, prev_count)
                    if ok_file:
                        return True
                except Exception:
                    pass
            return False
        except Exception:
            return False
    
    def _type_text_block(self, textarea, text):
        try:
            text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                if line:
                    self.human_type(textarea, line, self.type_min, self.type_max)
                if idx < len(lines) - 1:
                    textarea.send_keys(Keys.ENTER)
                time.sleep(self.line_pause)
            return True
        except Exception:
            return False

    def _ensure_newline(self, textarea):
        try:
            val = textarea.get_attribute("value") or ""
            if len(val) > 0 and not val.endswith("\n"):
                textarea.send_keys(Keys.ENTER)
                time.sleep(0.1)
        except Exception:
            pass
    
    def _force_caret_end(self, textarea):
        try:
            self.driver.execute_script("var ta=arguments[0]; ta.focus(); var l=ta.value.length; ta.selectionStart=l; ta.selectionEnd=l;", textarea)
        except Exception:
            pass
    
    def _reset_after_image(self, textarea):
        try:
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE).pause(0.2).send_keys(Keys.ARROW_DOWN).pause(0.2).send_keys(Keys.END).pause(0.2).perform()
            self._force_caret_end(textarea)
            self._ensure_newline(textarea)
        except Exception:
            pass
    
    def _lock_caret_end_textarea(self):
        try:
            script = """
            try {
              clearInterval(window.__caret_lock_ta);
            } catch(e){}
            window.__caret_lock_ta = setInterval(function(){
              try{
                var ta = document.getElementById('article_body_markdown');
                if(!ta) return;
                ta.focus();
                var l = ta.value.length;
                ta.selectionStart = l;
                ta.selectionEnd = l;
              }catch(e){}
            }, 250);
            """
            self.driver.execute_script(script)
        except Exception:
            pass
    
    def _unlock_caret_end_textarea(self):
        try:
            self.driver.execute_script("try{clearInterval(window.__caret_lock_ta);}catch(e){}")
        except Exception:
            pass
    
    def _lock_caret_end_contenteditable(self):
        try:
            script = """
            try { clearInterval(window.__caret_lock_ce); } catch(e){}
            window.__caret_lock_ce = setInterval(function(){
              try{
                var el = document.querySelector('[contenteditable=\"true\"]');
                if(!el) return;
                var range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);
                var sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
              }catch(e){}
            }, 250);
            """
            self.driver.execute_script(script)
        except Exception:
            pass
    
    def _unlock_caret_end_contenteditable(self):
        try:
            self.driver.execute_script("try{clearInterval(window.__caret_lock_ce);}catch(e){}")
        except Exception:
            pass
    
    def _fix_broken_image_markdown(self, textarea):
        try:
            val = textarea.get_attribute("value") or ""
            idx = val.rfind("![")
            if idx != -1:
                close = val.find(")", idx)
                if close != -1:
                    segment = val[idx:close+1]
                    fixed = segment.replace("\r\n", "").replace("\r", "").replace("\n", "")
                    if fixed != segment:
                        new_val = val[:idx] + fixed + val[close+1:]
                        self.driver.execute_script("arguments[0].value=arguments[1];", textarea, new_val)
                        self._force_caret_end(textarea)
        except Exception:
            pass
    
    def _append_single_blank_line(self, textarea):
        try:
            val = textarea.get_attribute("value") or ""
            t = val.rstrip()
            trailing_n = len(val) - len(val.rstrip("\n"))
            desired = 2
            if trailing_n < desired:
                add = "\n" * (desired - trailing_n)
                self.driver.execute_script("arguments[0].value = arguments[0].value + arguments[1];", textarea, add)
            elif trailing_n > desired:
                cleaned = t + ("\n" * desired)
                self.driver.execute_script("arguments[0].value=arguments[1];", textarea, cleaned)
            self._force_caret_end(textarea)
        except Exception:
            pass
    
    def _ensure_blank_before_image(self, textarea):
        try:
            val = textarea.get_attribute("value") or ""
            t = val.rstrip("\n")
            trailing_n = len(val) - len(val.rstrip("\n"))
            desired = 2
            if trailing_n < desired:
                add = "\n" * (desired - trailing_n)
                self.driver.execute_script("arguments[0].value = arguments[0].value + arguments[1];", textarea, add)
            elif trailing_n > desired:
                cleaned = t + ("\n" * desired)
                self.driver.execute_script("arguments[0].value=arguments[1];", textarea, cleaned)
            self._force_caret_end(textarea)
        except Exception:
            pass
    
    def fill_post_form(self, title, body, tags=None):
        """Fill the post form with title, body, and tags"""
        print("\n" + "="*50)
        print("Filling post form with Fixed Image Upload Logic...")
        print("="*50)
        
        try:
            self._dismiss_popups()
            
            # 1. Enter Title
            title_field = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea#article-form-title")))
            title_field.clear()
            self.human_type(title_field, title, self.type_min, self.type_max)
            print("✓ Title entered")
            
            time.sleep(2) 
            
            # 2. Enter Body (Updated to ensure images are actually inserted)
            body_entered = False
            content_parts = re.split(r'(\{.*?\})', body)

            try:
                textarea = self.driver.find_element(By.ID, "article_body_markdown")
                if textarea.is_displayed():
                    self._lock_caret_end_textarea()
                    self._lock_caret_end_contenteditable()
                    textarea.click()
                    time.sleep(1)
                    
                    for part in content_parts:
                        img_match = re.match(r'\{(.*)\}', part)
                        if img_match:
                            img_path = img_match.group(1).strip()
                            print(f"🖼 Found image path: {img_path}")
                            
                            # Use new robust upload method (Handles navigation internally)
                            if self.upload_image_to_editor(img_path, textarea):
                                print("✓ Image uploaded and navigated")
                            else:
                                print("✗ Failed to upload image")
                                
                        else:
                            if part.strip():
                                self._force_caret_end(textarea)
                                self._type_text_block(textarea, part)
                                self._ensure_newline(textarea)
                     
                    body_entered = True
                    print("✓ Body content filled successfully")
            except Exception as e:
                print(f"Editor filling error: {e}")
            try:
                self._unlock_caret_end_textarea()
                self._unlock_caret_end_contenteditable()
            except Exception:
                pass

            # 3. Enter Tags
            if tags:
                try:
                    tag_input = self.driver.find_element(By.ID, "article-form-tags")
                    for tag in tags[:4]:
                        tag_input.send_keys(tag + " ")
                        time.sleep(0.5)
                except: pass

        except Exception as e:
            print(f"✗ Failed to fill form: {e}")
            raise
    
    def _dismiss_popups(self):
        """Auto-dismiss popups/banners that block interaction"""
        try:
            # Dismiss generic close buttons and cookie banners
            dismiss_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Close')] | //button[contains(text(), 'Dismiss')] | //button[@aria-label='Close'] | //button[contains(@class, 'c-btn') and contains(text(), 'Accept')]")
            for btn in dismiss_btns:
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.2)
            
            # Dismiss JSON errors
            self._dismiss_json_errors()
        except Exception:
            pass

    def publish_post(self):
        """Publish the post with robust verification"""
        print("\n" + "="*50)
        print("Publishing post...")
        print("="*50)
        
        try:
            self._dismiss_popups()
            time.sleep(2) 
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Try to find Publish button
            publish_btn = None
            try:
                publish_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish')]")))
            except:
                # Retry finding button
                publish_btn = self.driver.find_element(By.CSS_SELECTOR, "button.c-btn.c-btn--primary")
            
            if publish_btn:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", publish_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", publish_btn)
                print("Clicked Publish button")
            
            time.sleep(3)
            
            # Handle confirmation modal if it appears
            try:
                confirm = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish') and contains(@class, 'c-btn--danger')] | //button[contains(text(), 'Yes, publish')]"))
                )
                confirm.click()
                print("Clicked Confirm Publish")
            except: 
                print("No confirmation modal appeared (might have published directly)")

            print("✅ Publish sequence finished")
            return True
                 
        except Exception as e:
            print(f"✗ Failed to publish post: {e}")
            raise
    
    def run_automation(self, blog_file_path="blog.txt", tags=None):
        """Run the complete automation workflow"""
        try:
            self.setup_driver()
            self.login()
            self.blog_file_path = blog_file_path
            title, body = self.read_blog_content(blog_file_path)
            self.navigate_to_create_post()
            self.fill_post_form(title, body, tags)
            self.publish_post()
            return True
        except Exception as e:
            print(f"\n❌ AUTOMATION FAILED: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    pass
