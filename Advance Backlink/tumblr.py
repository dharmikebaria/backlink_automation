import time
import logging
import os
import random
import re
import io
from PIL import Image
import win32clipboard
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_tumblr_logger():
    """Setup a dedicated logger for Tumblr debugging"""
    l = logging.getLogger('tumblr_debug')
    l.setLevel(logging.DEBUG)
    if not l.handlers:
        fh = logging.FileHandler('tumblr_debug.log', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        l.addHandler(fh)
    return l

t_logger = setup_tumblr_logger()

class TumblrHandler:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        t_logger.info("🚀 TumblrHandler initialized")
        try:
            from config import BLOG_FILE, DEFAULT_CONTENT, TUMBLR_DEFAULT_TAGS
            self.blog_file = BLOG_FILE
            self.default_content = DEFAULT_CONTENT
            self.default_tags = TUMBLR_DEFAULT_TAGS
        except Exception:
            self.blog_file = "blog.txt"
            self.default_content = "Automated Blog Post"
            self.default_tags = ["automation"]

    def cleanup(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    def execute_login(self, email, password) -> bool:
        """Execute Tumblr login process"""
        logger.info(f"🔐 Starting Tumblr login for {email}")
        t_logger.info(f"🔐 Starting Tumblr login for {email}")
        try:
            self.driver.get("https://www.tumblr.com/login")
            time.sleep(3)

            # Check if already logged in
            if "dashboard" in self.driver.current_url:
                logger.info("✅ Already logged in")
                t_logger.info("✅ Already logged in")
                return True

            # Step 1: Enter Email
            logger.info("1️⃣ Entering email...")
            email_input = None
            email_selectors = [
                "input[name='email']",
                "input[name='user[email]']",
                "input[type='email']",
                "input[placeholder*='Email']",
                "//input[@name='email']"
            ]
            
            for sel in email_selectors:
                try:
                    if sel.startswith("//"):
                        els = self.driver.find_elements(By.XPATH, sel)
                    else:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    
                    for el in els:
                        if el.is_displayed():
                            email_input = el
                            break
                    if email_input: break
                except: continue
            
            if not email_input:
                # Check for "Continue with email" button first
                try:
                    btns = self.driver.find_elements(By.XPATH, "//button[contains(.,'Continue with email')]")
                    for btn in btns:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(1)
                            # Retry finding email input
                            for sel in email_selectors:
                                try:
                                    if sel.startswith("//"):
                                        els = self.driver.find_elements(By.XPATH, sel)
                                    else:
                                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                    for el in els:
                                        if el.is_displayed():
                                            email_input = el
                                            break
                                    if email_input: break
                                except: continue
                            break
                except: pass

            if email_input:
                email_input.clear()
                email_input.send_keys(email)
                email_input.send_keys(Keys.ENTER)
                time.sleep(2)
            else:
                logger.error("❌ Could not find email input")
                return False

            # Step 2: Enter Password (if requested)
            logger.info("2️⃣ Checking for password field...")
            t_logger.info("2️⃣ Checking for password field...")
            
            # Wait for password field
            password_input = None
            password_selectors = [
                "input[name='password']",
                "input[name='user[password]']",
                "input[type='password']",
                "input[placeholder*='Password']",
                "//input[@name='password']"
            ]
            
            for _ in range(5): # Retry a few times
                for sel in password_selectors:
                    try:
                        if sel.startswith("//"):
                            els = self.driver.find_elements(By.XPATH, sel)
                        else:
                            els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        
                        for el in els:
                            if el.is_displayed():
                                password_input = el
                                break
                        if password_input: break
                    except: continue
                if password_input: break
                time.sleep(1)
            
            if password_input:
                password_input.click()
                password_input.send_keys(password)
                password_input.send_keys(Keys.ENTER)
                time.sleep(3)
                logger.info("✅ Password submitted")
                t_logger.info("✅ Password submitted")
            else:
                # Check for "Send me a magic link" button
                try:
                    magic_link_btns = self.driver.find_elements(By.XPATH, "//button[contains(.,'magic link')]")
                    if magic_link_btns:
                        logger.error("❌ Tumblr is asking for Magic Link login. Password login unavailable.")
                        t_logger.error("❌ Tumblr is asking for Magic Link login. Password login unavailable.")
                        return False
                except: pass

                # Sometimes it asks for "Magic Link" or something else
                logger.warning("⚠️ Password field not found (might be magic link or captcha)")
                t_logger.warning("⚠️ Password field not found (might be magic link or captcha)")
                # Check if we are logged in anyway
                if "dashboard" in self.driver.current_url:
                    return True
                
                # Check for error
                if "incorrect" in self.driver.page_source.lower():
                    logger.error("❌ Incorrect email/password")
                    return False
            
            # Step 3: Verify Login
            logger.info("3️⃣ Verifying login...")
            time.sleep(5)
            if "dashboard" in self.driver.current_url or "blog" in self.driver.current_url:
                logger.info("✅ Login successful")
                return True
            
            # Check for captcha
            if "captcha" in self.driver.page_source.lower():
                logger.warning("⚠️ Captcha detected! Please solve manually if visible.")
                time.sleep(10) # Give user time
                if "dashboard" in self.driver.current_url:
                    return True
            
            logger.error("❌ Login failed (unknown reason)")
            return False

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    def _read_blog_content(self) -> str:
        try:
            if os.path.exists(self.blog_file):
                txt = open(self.blog_file, "r", encoding="utf-8").read().strip()
                if txt:
                    logger.info(f"📖 Read blog content from {self.blog_file} ({len(txt)} characters)")
                    return txt
        except Exception:
            pass
        return self.default_content

    def _click_text_button(self) -> bool:
        """Click the 'Text' button to start a text post"""
        logger.info("🔍 Looking for 'Text' button...")
        
        # Try direct URL first (most reliable)
        try:
            self.driver.get("https://www.tumblr.com/new/text")
            time.sleep(5)
            logger.info("✅ Directly navigated to text post page")
            return True
        except Exception as e:
            logger.debug(f"Direct navigation failed: {e}")
        
        selectors = [
            "button[data-testid='post-type-selector-text']",
            "button[aria-label*='Text']",
            "//button[contains(@aria-label,'Text')]",
            "//button[contains(.,'Text')]",
        ]
        
        time.sleep(3)
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    el = self.driver.find_element(By.XPATH, sel)
                else:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    
                if el.is_displayed() and el.is_enabled():
                    logger.info(f"✅ Found 'Text' button: {sel}")
                    
                    # Scroll and click
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.5)
                    
                    try:
                        el.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", el)
                    
                    time.sleep(3)
                    return True
            except Exception:
                continue
        
        logger.warning("⚠️ Could not find Text button, trying alternative methods...")
        return False

    def _enter_title(self, title: str) -> bool:
        """Enter title in the title field"""
        logger.info(f"🔍 Looking for title field to enter: '{title}'")
        t_logger.info(f"🔍 Looking for title field to enter: '{title}'")
        
        # More specific selectors based on image
        selectors = [
            # The placeholder is specifically "Title"
            "//div[contains(@aria-label, 'Title')]",
            "//div[contains(@data-placeholder, 'Title')]",
            "//h1[contains(@class, 'editor-title')]",
            "//div[contains(@class, 'editor-title')]",
            "//div[@role='textbox' and contains(@aria-label, 'Title')]",
            
            # Generic fallbacks
            "//h1",
            "//h2",
            "textarea[placeholder*='Title']",
            "input[placeholder*='Title']",
        ]
        
        # Try finding elements
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    els = self.driver.find_elements(By.XPATH, sel)
                else:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    
                for el in els:
                    if el.is_displayed():
                        # Check if editable
                        is_editable = el.get_attribute("contenteditable") == "true" or \
                                     el.tag_name in ["input", "textarea"]
                        
                        placeholder = el.get_attribute("placeholder") or el.get_attribute("data-placeholder") or el.get_attribute("aria-label") or ""
                        
                        if is_editable or "Title" in placeholder:
                            logger.info(f"✅ Found title field: {sel}")
                            
                            # Ensure focus
                            try:
                                el.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(0.5)
                            
                            try:
                                el.clear()
                            except Exception:
                                el.send_keys(Keys.CONTROL + "a")
                                el.send_keys(Keys.DELETE)
                            
                            # Type title
                            for ch in title:
                                el.send_keys(ch)
                                time.sleep(random.uniform(0.06, 0.10))
                            
                            logger.info(f"✅ Title entered: '{title}'")
                            time.sleep(1) # Wait for UI to settle
                            return True
            except Exception:
                continue
        
        logger.warning("⚠️ Could not find title field")
        return False

    def _enter_content(self, content_data) -> bool:
        """
        Enter content in the content editor with forced block creation.
        Handles the specific Tumblr issue where newlines are ignored.
        """
        # Normalize content to a list of lines
        if isinstance(content_data, str):
            lines = content_data.split('\n')
        else:
            lines = content_data

        logger.info(f"🔍 Looking for content editor ({len(lines)} lines)")
        
        # 1. Try TAB method first - Most reliable if title was just focused
        try:
            logger.info("🔄 Trying to reach content via TAB from title...")
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)
            
            # Check if we are in a contenteditable div that is NOT the title
            active_el = self.driver.switch_to.active_element
            is_content_editor = False
            
            if active_el:
                tag = active_el.tag_name
                is_editable = active_el.get_attribute("contenteditable") == "true"
                placeholder = active_el.get_attribute("data-placeholder") or active_el.get_attribute("aria-label") or ""
                
                # Verify it's not the title
                if is_editable and "Title" not in placeholder:
                    is_content_editor = True
                    logger.info("✅ Found content editor via TAB")
            
            if is_content_editor:
                return self._type_content_into_element(active_el, lines)
        except Exception as e:
            logger.debug(f"TAB method failed: {e}")

        # 2. Try Selectors
        selectors = [
            # Specific selectors from image
            "//div[contains(@aria-label, 'Go ahead, put anything')]",
            "//div[contains(@data-placeholder, 'Go ahead, put anything')]",
            "//div[contains(text(), 'Go ahead, put anything')]",
            
            # Standard editor selectors
            "//div[contains(@class, 'editor-slot')]",
            "//div[contains(@class, 'rich-text-editor')]",
            "//p[contains(@class, 'block-editor-rich-text__editable')]",
            "//div[contains(@aria-label, 'Go ahead')]",
            "//div[contains(@data-placeholder, 'Go ahead')]",
            "//div[contains(@class, 'editor')]//p", 
            "div[role='textbox'][contenteditable='true']",
            "div[data-testid='post-content-editor']",
            "//div[@role='textbox' and @contenteditable='true']",
            "//div[@contenteditable='true']",
            # Add more generic ones
            "//div[contains(@class, 'editor')]//div[@contenteditable='true']",
            "//div[contains(@class, 'post-content')]",
            "//div[@aria-label='Body']",
            "//div[@data-placeholder='Body']",
            "//p[@class='block-editor-rich-text__editable block-editor-block-list__block']",
        ]
        time.sleep(1)
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    els = self.driver.find_elements(By.XPATH, sel)
                else:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    
                for el in els:
                    if el.is_displayed():
                        # Verify it's not the title
                        placeholder = el.get_attribute("data-placeholder") or el.get_attribute("aria-label") or ""
                        if "Title" in placeholder:
                            continue
                            
                        logger.info(f"✅ Found content editor: {sel}")
                        
                        # Enhanced click logic to ensure focus
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        time.sleep(0.5)
                        
                        # Use helper to focus and type
                        return self._type_content_into_element(el, lines)
                            
            except Exception as e:
                logger.warning(f"Error entering content: {e}")
                continue
        
        # Last resort: Try to click the general area below the title
        try:
            logger.info("⚠️ Trying last resort: Clicking area below title...")
            title_el = self.driver.switch_to.active_element
            if title_el:
                ActionChains(self.driver).move_to_element(title_el).move_by_offset(0, 100).click().perform()
                time.sleep(0.5)
                return self._type_content_into_element(self.driver.switch_to.active_element, lines)
        except:
            pass
            
        return False

    def _resolve_image_path(self, path_str):
        base_dir = os.path.dirname(os.path.abspath(self.blog_file)) if getattr(self, "blog_file", None) else os.getcwd()
        s = (path_str or "").strip()
        if not s:
            return None
        
        candidates = []
        
        # If path has separators, treat as given path with normalizations
        if ('/' in s) or ('\\' in s):
            candidates.extend([
                s,
                os.path.abspath(s) if os.path.isabs(s) else os.path.abspath(os.path.join(base_dir, s)),
                os.path.join(base_dir, s.replace('../', '').replace('..\\', '')),
                s.replace('../', '').replace('..\\', ''),
            ])
        else:
            # Bare filename: prefer ../Image/<name>, then local Image, then Ima
            candidates.extend([
                os.path.abspath(os.path.join(base_dir, '..', 'Image', s)),
                os.path.join(base_dir, 'Image', s),
                os.path.join(base_dir, s),
                os.path.join(base_dir, 'Ima', s),
                os.path.abspath(os.path.join(base_dir, '..', 'Ima', s)),
            ])
        
        for p in candidates:
            try:
                norm = os.path.abspath(p)
                if os.path.isfile(norm):
                    return norm
            except Exception:
                continue
        
        return None

    def _is_image_line(self, line):
        """Check if a line contains an image path"""
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            path = line[1:-1]
            return self._resolve_image_path(path) is not None
        return False

    def _dismiss_interfering_popups(self):
        """Dismiss common interfering popups"""
        try:
            # Common popup selectors
            popups = [
                "//button[@aria-label='Close']",
                "//div[contains(@class, 'dialog')]//button[contains(., 'Close')]",
                "//button[contains(., 'No thanks')]",
                "//button[contains(., 'Not now')]",
                "//div[@aria-label='Dismiss']",
            ]
            
            for p in popups:
                try:
                    els = self.driver.find_elements(By.XPATH, p)
                    for el in els:
                        if el.is_displayed():
                            el.click()
                            time.sleep(0.5)
                except:
                    pass
        except:
            pass

    def _send_keys_chunked(self, element, text):
        """Type text in chunks using ActionChains to ensure cursor position is respected"""
        if not text:
            return True
            
        try:
            chunk_size = 50
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            
            for chunk in chunks:
                try:
                    # Random popup check
                    if random.random() < 0.1:
                        self._dismiss_interfering_popups()
                    
                    # Always use ActionChains to type at current cursor position
                    # This prevents jumping back to start of element if element.send_keys is used
                    ActionChains(self.driver).send_keys(chunk).perform()
                    
                except Exception:
                    # If ActionChains fails, try to refocus and retry
                    try:
                        self._dismiss_interfering_popups()
                        
                        # Click active element to ensure focus
                        active_el = self.driver.switch_to.active_element
                        if active_el:
                            ActionChains(self.driver).move_to_element(active_el).click().perform()
                            ActionChains(self.driver).send_keys(chunk).perform()
                    except:
                        pass
                
                time.sleep(random.uniform(0.02, 0.08))
            return True
        except Exception as e:
            logger.error(f"Typing error: {e}")
            return False

    def _paste_image_from_clipboard(self, image_path):
        """Copy image to clipboard and paste into Tumblr post"""
        logger.info(f"📸 Copying image to clipboard and pasting: {image_path}")

        try:
            # Copy image to clipboard
            image = Image.open(image_path)
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Remove BMP header
            output.close()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()

            # Ensure we are focused on the editor
            try:
                active_el = self.driver.switch_to.active_element
                # If active element is not editor, try to find it
                if not active_el.get_attribute("contenteditable"):
                    # Try to click the last known editor area or use ActionChains
                    pass 
            except:
                pass

            # Paste into the editor
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            
            # Wait for image to upload/render
            logger.info("⏳ Waiting for image to appear...")
            time.sleep(5)  # Give it enough time
            
            # CRITICAL FIX: Do NOT use TAB. Use ENTER to create a new block below the image.
            # Pressing TAB moves focus to the Tags section, which is why text was going there.
            # Press Enter twice to be safe - one to break caption, one for new line
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)
            
            # Verify we are not in the tags section
            try:
                active_el = self.driver.switch_to.active_element
                placeholder = active_el.get_attribute("placeholder") or active_el.get_attribute("aria-label") or ""
                if "tag" in placeholder.lower() or "tags" in placeholder.lower():
                    logger.warning("⚠️ Focus moved to tags! Refocusing editor...")
                    # Click above the tags area or use shift+tab
                    ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
                    time.sleep(0.5)
            except:
                pass

            logger.info("✅ Image pasted successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to paste image: {e}")
            return False

    def _type_text_line(self, line, element=None):
        """Type a text line with link parsing"""
        # Parse line for links [text](url)
        parts = []
        last_end = 0
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', line):
            if match.start() > last_end:
                parts.append({'type': 'text', 'value': line[last_end:match.start()]})
            parts.append({'type': 'link', 'text': match.group(1), 'url': match.group(2)})
            last_end = match.end()

        if last_end < len(line):
            parts.append({'type': 'text', 'value': line[last_end:]})

        # Type content
        if not parts:
            # No links, use robust chunked typing
            if element:
                self._send_keys_chunked(element, line)
            else:
                # Fallback if no element provided
                self._send_keys_chunked(self.driver.switch_to.active_element, line)
        else:
            for part in parts:
                if part['type'] == 'text':
                    if element:
                        self._send_keys_chunked(element, part['value'])
                    else:
                         self._send_keys_chunked(self.driver.switch_to.active_element, part['value'])
                elif part['type'] == 'link':
                    link_text, link_url = part['text'], part['url']

                    # Type text
                    for char in link_text:
                        ActionChains(self.driver).send_keys(char).perform()
                        time.sleep(random.uniform(0.06, 0.10))

                    time.sleep(0.5)

                    # Select text (Shift + Left)
                    sel_actions = ActionChains(self.driver)
                    sel_actions.key_down(Keys.SHIFT)
                    for _ in range(len(link_text)):
                        sel_actions.send_keys(Keys.LEFT)
                        time.sleep(0.05)
                    sel_actions.key_up(Keys.SHIFT)
                    sel_actions.perform()
                    time.sleep(0.5)

                    # Ctrl+K
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
                    time.sleep(1.0)

                    # Type URL
                    url_actions = ActionChains(self.driver)
                    for char in link_url:
                        url_actions.send_keys(char)
                        time.sleep(0.05)
                    url_actions.send_keys(Keys.ENTER)
                    url_actions.perform()
                    time.sleep(0.8)

                    # Move cursor to right
                    ActionChains(self.driver).send_keys(Keys.RIGHT).perform()

    def _type_content_into_element(self, el, lines):
        """Helper to type content into a found element"""
        try:
            # Enhanced focus logic - Critical for cursor visibility
            # 1. Click the element
            try:
                el.click()
            except:
                self.driver.execute_script("arguments[0].click();", el)
            time.sleep(0.5)

            # 2. Focus via JS
            self.driver.execute_script("arguments[0].focus();", el)
            time.sleep(0.2)

            # 3. Click again with ActionChains to ensure cursor is placed
            try:
                ActionChains(self.driver).move_to_element(el).click().perform()
            except:
                pass
            time.sleep(0.5)

            # Clear existing content safely
            # Note: For "Go ahead" placeholder, we might not need to clear if it's empty
            # But if we do clear, we must ensure focus comes back
            try:
                # Check if it has content before clearing
                text = el.text
                if text and "Go ahead" not in text:
                     el.send_keys(Keys.CONTROL + "a")
                     time.sleep(0.1)
                     el.send_keys(Keys.DELETE)
                     time.sleep(0.2)
            except:
                pass

            # Re-click to ensure focus after clear
            try:
                el.click()
            except:
                pass
            time.sleep(0.3)

            # Process each line
            for i, line in enumerate(lines):
                line = line.strip()

                # Use ActionChains for consistent cursor tracking and human typing
                if not line:
                    # Empty line -> Just Enter
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(0.2)
                    continue

                is_image_posted = False
                if self._is_image_line(line):
                    # Paste image from clipboard
                    raw_path = line[1:-1]
                    image_path = self._resolve_image_path(raw_path)
                    
                    if image_path and self._paste_image_from_clipboard(image_path):
                        is_image_posted = True
                    else:
                        # Fallback: type the path as text
                        logger.warning(f"⚠️ Failed to paste image {raw_path}, typing as text")
                        self._type_text_line(line, element=el)
                else:
                    # Type text line
                    self._type_text_line(line, element=el)

                # --- Force New Line Block ---
                if i < len(lines) - 1:
                    time.sleep(0.5)
                    
                    # If we just posted an image, _paste_image_from_clipboard already pressed ENTER
                    # to break out of the image block. We don't need another ENTER unless we want a gap.
                    # The user wants "next line", so one ENTER (from function) is sufficient.
                    if not is_image_posted:
                        # Enter for new block for text
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(0.5)
                        
                        # Extra check: If we are still on the same line (text node), force another Enter
                        # This is hard to detect via DOM, but safe to add if we want distinct blocks
                        pass

                    # Removed Space+Backspace trick to prevent cursor moving back
                    logger.info(f"✅ Completed line {i+1}")
                    time.sleep(0.5)

            # Validation
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error in typing content: {e}")
            return False

    def _publish_post(self) -> bool:
        """Click the initial publish/post button"""
        logger.info("🔍 Looking for publish/post button...")
        
        selectors = [
            "button[aria-label*='post']",
            "button[aria-label*='Publish']",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'post')]",
        ]
        
        time.sleep(1)
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    els = self.driver.find_elements(By.XPATH, sel)
                else:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        logger.info(f"✅ Found publish button: {sel}")
                        
                        try:
                            el.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", el)
                        
                        time.sleep(2)
                        return True
            except Exception:
                continue
        
        logger.warning("⚠️ Could not find publish button")
        return False

    def _click_post_now_button(self) -> bool:
        """Click the 'Post now' button"""
        logger.info("🔘 Looking for 'Post now' button...")
        
        selectors = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'post now')]",
            "button[data-testid='post-now-button']",
        ]
        
        time.sleep(1)
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    els = self.driver.find_elements(By.XPATH, sel)
                else:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        logger.info(f"✅ Found 'Post now' button: {sel}")
                        
                        try:
                            el.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", el)
                        
                        time.sleep(1)
                        return True
            except Exception:
                continue
        
        # JavaScript fallback
        try:
            result = self.driver.execute_script("""
            var buttons = document.querySelectorAll('button');
            for (var i=0; i<buttons.length; i++) {
                var btn = buttons[i];
                var text = (btn.textContent || btn.innerText || '').toLowerCase();
                if (text.includes('post now') && btn.offsetParent && !btn.disabled) {
                    btn.click();
                    return true;
                }
            }
            return false;
            """)
            if result:
                time.sleep(1)
                return True
        except Exception:
            pass
        
        return False

    def _click_final_post_button(self) -> bool:
        """Click the FINAL 'Post' button in the popup modal after 'Post now'"""
        logger.info("🔘 Looking for FINAL 'Post' button in modal...")
        
        # Wait for modal to appear
        time.sleep(2)
        
        # यह वो मुख्य कोड है जो पॉपअप में "Post" बटन को क्लिक करेगा
        selectors = [
            # Exact text match for "Post" button in modal
            "//button[normalize-space(.)='Post']",
            "//button[contains(@class, 'modal')]//*[normalize-space(.)='Post']",
            "//div[@role='dialog']//button[normalize-space(.)='Post']",
            "//div[contains(@class,'modal')]//button[normalize-space(.)='Post']",
            "//div[contains(@class,'Modal')]//button[normalize-space(.)='Post']",
            "//button[.//span[normalize-space(.)='Post']]",
            
            # For "Post without tags" modal
            "//button[contains(.,'Post without tags')]",
            "//button[contains(@data-testid,'post-button')]",
            
            # CSS selectors
            "button[data-testid='confirm-button']",
            "button[aria-label='Post']",
        ]
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    els = self.driver.find_elements(By.XPATH, sel)
                else:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        logger.info(f"✅ Found FINAL 'Post' button: {sel}")
                        logger.info(f"   Button text: '{el.text}'")
                        
                        # Scroll into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.5)
                        
                        # Highlight the button (for debugging)
                        self.driver.execute_script("arguments[0].style.border='3px solid red';", el)
                        time.sleep(0.3)
                        
                        # Try multiple click methods
                        clicked = False
                        
                        # Method 1: Standard click
                        try:
                            el.click()
                            logger.info("✅ Clicked FINAL 'Post' button (standard)")
                            clicked = True
                        except Exception as e1:
                            logger.debug(f"Standard click failed: {e1}")
                        
                        # Method 2: JavaScript click
                        if not clicked:
                            try:
                                self.driver.execute_script("arguments[0].click();", el)
                                logger.info("✅ Clicked FINAL 'Post' button (JavaScript)")
                                clicked = True
                            except Exception as e2:
                                logger.debug(f"JS click failed: {e2}")
                        
                        # Method 3: ActionChains
                        if not clicked:
                            try:
                                actions = ActionChains(self.driver)
                                actions.move_to_element(el).click().perform()
                                logger.info("✅ Clicked FINAL 'Post' button (ActionChains)")
                                clicked = True
                            except Exception as e3:
                                logger.debug(f"ActionChains failed: {e3}")
                        
                        # Method 4: Execute script with mouse events
                        if not clicked:
                            try:
                                self.driver.execute_script("""
                                var btn = arguments[0];
                                var rect = btn.getBoundingClientRect();
                                var x = rect.left + rect.width/2;
                                var y = rect.top + rect.height/2;
                                
                                var mouseDown = new MouseEvent('mousedown', {
                                    clientX: x,
                                    clientY: y,
                                    bubbles: true
                                });
                                
                                var mouseUp = new MouseEvent('mouseup', {
                                    clientX: x,
                                    clientY: y,
                                    bubbles: true
                                });
                                
                                var clickEvt = new MouseEvent('click', {
                                    clientX: x,
                                    clientY: y,
                                    bubbles: true
                                });
                                
                                btn.dispatchEvent(mouseDown);
                                btn.dispatchEvent(mouseUp);
                                btn.dispatchEvent(clickEvt);
                                """, el)
                                logger.info("✅ Clicked FINAL 'Post' button (mouse events)")
                                clicked = True
                            except Exception as e4:
                                logger.debug(f"Mouse events failed: {e4}")
                        
                        # Remove highlight
                        self.driver.execute_script("arguments[0].style.border='';", el)
                        
                        if clicked:
                            time.sleep(3)  # Wait for post to complete
                            return True
            except Exception as e:
                logger.debug(f"Selector {sel} failed: {e}")
                continue
        
        # Try JavaScript to find the modal and click Post button
        logger.info("🔄 Trying JavaScript to find and click Post button in modal...")
        js_code = """
        // Find all modals/dialogs
        var modals = document.querySelectorAll('div[role="dialog"], div[aria-modal="true"], div.modal, div.Modal');
        
        for (var i = 0; i < modals.length; i++) {
            var modal = modals[i];
            if (modal.offsetParent) {
                console.log("Found modal:", modal);
                
                // Find all buttons in modal
                var buttons = modal.querySelectorAll('button');
                for (var j = 0; j < buttons.length; j++) {
                    var btn = buttons[j];
                    var btnText = (btn.textContent || btn.innerText || '').trim();
                    console.log("Button in modal:", btnText);
                    
                    // Check if button says "Post" (exact match or contains)
                    if (btnText === 'Post' || btnText.includes('Post without tags')) {
                        console.log("Found Post button in modal, clicking...");
                        btn.scrollIntoView({block: 'center'});
                        
                        // Try multiple click methods
                        try { btn.click(); } 
                        catch(e1) { 
                            try { 
                                var evt = new MouseEvent('click', {bubbles: true});
                                btn.dispatchEvent(evt); 
                            } 
                            catch(e2) {
                                // Try with coordinates
                                var rect = btn.getBoundingClientRect();
                                var x = rect.left + rect.width/2;
                                var y = rect.top + rect.height/2;
                                
                                var events = ['mousedown', 'mouseup', 'click'];
                                events.forEach(function(eventType) {
                                    var event = new MouseEvent(eventType, {
                                        view: window,
                                        bubbles: true,
                                        cancelable: true,
                                        clientX: x,
                                        clientY: y
                                    });
                                    btn.dispatchEvent(event);
                                });
                            }
                        }
                        
                        return true;
                    }
                }
            }
        }
        
        // If no modal found, look for any "Post" button
        var allButtons = document.querySelectorAll('button');
        for (var k = 0; k < allButtons.length; k++) {
            var btn = allButtons[k];
            var btnText = (btn.textContent || btn.innerText || '').trim();
            if (btnText === 'Post' && btn.offsetParent && !btn.disabled) {
                console.log("Found standalone Post button");
                btn.click();
                return true;
            }
        }
        
        return false;
        """
        
        try:
            result = self.driver.execute_script(js_code)
            if result:
                logger.info("✅ FINAL 'Post' button clicked via JavaScript")
                time.sleep(3)
                return True
        except Exception as e:
            logger.error(f"❌ JavaScript fallback failed: {e}")
        
        # Last resort: Try pressing Enter key
        try:
            logger.info("🔄 Trying Enter key as last resort...")
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(2)
            logger.info("✅ Sent Enter key")
            return True
        except Exception as e:
            logger.error(f"❌ Enter key failed: {e}")
        
        logger.error("❌❌ Could not find FINAL 'Post' button in modal")
        return False

    def _confirm_post_without_tags(self) -> bool:
        """Handle 'Post without tags' modal (if appears before final post)"""
        logger.info("🔍 Checking for 'Post without tags' modal...")
        
        time.sleep(1)
        
        # This is a simpler version for the initial modal
        xpaths = [
            "//div[contains(.,'Post without tags')]//button[contains(.,'Post')]",
            "//button[contains(.,'Post without tags')]",
        ]
        
        for xp in xpaths:
            try:
                btns = self.driver.find_elements(By.XPATH, xp)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click()
                            time.sleep(1)
                            logger.info("✅ Handled initial 'Post without tags' modal")
                            return True
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", b)
                            time.sleep(1)
                            return True
            except Exception:
                continue
        
        logger.info("⚠️ No initial 'Post without tags' modal found")
        return False

    def handle_post_login_actions(self) -> bool:
        """Handle Tumblr-specific actions after login"""
        try:
            logger.info("🎨 Starting Tumblr post-login workflow...")
            
            # Read and parse blog content
            title = "Automated Blog Post"
            content = "Default content"
            
            try:
                if os.path.exists("blog.txt"):
                    with open("blog.txt", "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    if lines:
                        title = lines[0].strip()
                        content = lines[1:]  # Pass list of lines directly
                        logger.info(f"📖 Read blog.txt - Title: {title[:20]}...")
                        logger.info(f"📖 Content lines: {len(content)}")
                    else:
                        logger.warning("⚠️ blog.txt is empty")
                else:
                    logger.warning("⚠️ blog.txt not found")
            except Exception as e:
                logger.error(f"Error reading blog.txt: {e}")
            
            # Step 1: Navigate directly to text post page
            logger.info("1️⃣ Navigating to text post page...")
            self.driver.get("https://www.tumblr.com/new/text")
            time.sleep(5)
            
            # Verify we are on the text post page
            if "new/text" not in self.driver.current_url and "post/text" not in self.driver.current_url:
                logger.warning("⚠️ Redirected away from text post page, trying to click Text button...")
                if not self._click_text_button():
                    logger.error("❌ Failed to access text editor")
                    return False
            
            time.sleep(2)
            
            # Step 2: Enter title
            logger.info(f"2️⃣ Entering title: {title}")
            self._enter_title(title)
            
            # Step 3: Enter content
            logger.info("3️⃣ Entering content...")
            if not self._enter_content(content):
                logger.error("❌ Failed to enter content")
                return False
            
            # Step 4: Click publish button (Post now)
            logger.info("4️⃣ Clicking 'Post now' button...")
            
            # Try to find the "Post now" button directly on the page first (as seen in image)
            post_button_clicked = False
            
            # Selectors based on the image provided by user
            post_selectors = [
                "//button[contains(., 'Post now')]",
                "//button[contains(text(), 'Post now')]",
                "//div[contains(@class, 'create_post_button')]//button",
                "//button[normalize-space()='Post now']"
            ]
            
            for sel in post_selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, sel)
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            post_button_clicked = True
                            logger.info("✅ Clicked 'Post now' button")
                            break
                    if post_button_clicked: break
                except: continue
            
            if not post_button_clicked:
                logger.info("⚠️ Direct 'Post now' not found, trying standard _publish_post sequence...")
                if not self._publish_post():
                    # If standard publish fails, try the complex sequence
                    pass

            # Step 5: Handle initial modal (if any)
            logger.info("5️⃣ Checking for initial modal...")
            self._confirm_post_without_tags()
            
            # Step 6: Click "Post now" button (if in dropdown or modal)
            logger.info("6️⃣ Clicking 'Post now' button (secondary check)...")
            self._click_post_now_button()
            
            # Step 7: FINAL "Post" button check
            logger.info("7️⃣ ⭐⭐⭐ Clicking FINAL 'Post' button if needed... ⭐⭐⭐")
            t_logger.info("7️⃣ ⭐⭐⭐ Clicking FINAL 'Post' button if needed... ⭐⭐⭐")
            final_post_success = self._click_final_post_button()
            
            # If we think we posted, verify
            time.sleep(5)
            
            # Check for error messages on page
            if "Something went wrong" in self.driver.page_source:
                logger.error("❌ Tumblr reported: Something went wrong")
                t_logger.error("❌ Tumblr reported: Something went wrong")
                return False
                
            current_url = self.driver.current_url
            if "dashboard" in current_url or "blog" in current_url:
                logger.info("✅✅✅ BLOG POST SUCCESSFULLY PUBLISHED! ✅✅✅")
                t_logger.info("✅✅✅ BLOG POST SUCCESSFULLY PUBLISHED! ✅✅✅")
                return True
            
            if "new/text" in current_url:
                logger.error("❌ Still on post page, publishing likely failed")
                t_logger.error("❌ Still on post page, publishing likely failed")
                # Take screenshot
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if not os.path.exists("screenshots"): os.makedirs("screenshots")
                    self.driver.save_screenshot(f"screenshots/tumblr_failed_{timestamp}.png")
                except: pass
                return False
                
            # Fallback assumption
            logger.warning(f"⚠️ Ends on unknown URL: {current_url}, assuming success but verification needed")
            t_logger.warning(f"⚠️ Ends on unknown URL: {current_url}, assuming success but verification needed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tumblr workflow error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            self.cleanup()
