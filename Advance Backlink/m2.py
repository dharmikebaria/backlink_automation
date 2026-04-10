import os
import time
import json
import logging
import random
import subprocess
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options 
import imaplib
import email as pyemail
from email.header import decode_header
import re
import openpyxl
import undetected_chromedriver as uc  # Import undetected chromedriver

logger = logging.getLogger(__name__)

class MediumSpecificHandler:
    def __init__(self, driver, email, password):
        self.driver = driver
        self.email = email
        self.password = password
        self.wait = WebDriverWait(driver, 25)
    
    def fast_type(self, element, text):
        """Fast typing via JavaScript insertion"""
        try:
            if not element:
                return False
            
            return self.driver.execute_script("""
                const el = arguments[0];
                const val = arguments[1];
                if (!el) return false;
                
                el.focus();
                
                const tag = (el.tagName||'').toUpperCase();
                const isInput = tag==='INPUT' || tag==='TEXTAREA';
                const isEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true';
                
                try {
                    if (isInput) {
                        el.value = val;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    } else if (isEditable) {
                        el.innerText = val;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                    } else {
                        el.textContent = val;
                    }
                    return true;
                } catch(e){
                    return false;
                }
            """, element, text)
        except Exception as e:
            logger.warning(f"Fast typing failed: {e}")
            return False

    def human_type(self, element, text, min_delay=0.08, max_delay=0.22):
        """Human-like typing with random delays.
        If element is None, types into the active element using ActionChains.
        """
        for ch in text:
            try:
                # If element is provided, check if it's still valid (not stale)
                if element:
                    try:
                        element.send_keys(ch)
                    except Exception:
                        # If direct sending fails (e.g. stale), fall back to ActionChains on active element
                        ActionChains(self.driver).send_keys(ch).perform()
                else:
                    # If no element provided, type into active element
                    ActionChains(self.driver).send_keys(ch).perform()
            except Exception as e:
                # Ultimate fallback
                try:
                    ActionChains(self.driver).send_keys(ch).perform()
                except Exception as inner_e:
                    logger.warning(f"Failed to type character '{ch}': {inner_e}")
            
            time.sleep(random.uniform(min_delay, max_delay))

    def enter_content_with_links(self, content):
        """Deprecated: Use type_line_with_links instead"""
        return self.type_line_with_links(None, content)
    def copy_image_to_clipboard(self, image_path):
        """Copy image file to clipboard using PowerShell"""
        try:
            abs_path = os.path.abspath(image_path)
            cmd = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $files = [System.Collections.Specialized.StringCollection]::new()
            $files.Add("{abs_path}")
            [System.Windows.Forms.Clipboard]::SetFileDropList($files)
            '''
            subprocess.run(["powershell", "-command", cmd], timeout=5)
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False
    
    def _resolve_image_path(self, path_str):
        try:
            base_dir = os.path.dirname(os.path.abspath("blog.txt")) if os.path.exists("blog.txt") else os.getcwd()
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

    def upload_image_to_editor(self, file_path: str) -> bool:
        """Upload image to editor using Clipboard"""
        try:
            resolved = self._resolve_image_path(file_path)
            if not resolved or not os.path.exists(resolved):
                logger.error(f"❌ Image file not found: {file_path}")
                return False
            logger.info(f"🖼️ Uploading image: {resolved}")

            # Method: Clipboard Paste (Best for rich text editors like Medium)
            if self.copy_image_to_clipboard(resolved):
                time.sleep(1)
                # Paste (Ctrl+V)
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
                actions.perform()
                logger.info("✅ Pasted image from clipboard")
                time.sleep(5) # Wait for upload
                return True
            
            return False

        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return False

    def type_line_with_links(self, element, line):
        """Type a single line and create hyperlinks robustly, and handle images"""
        normalized = line.replace("\\`", "`")
        normalized = re.sub(r"\(\s*`([^`]+)`\s*\)", r"(\1)", normalized)
        
        md = re.compile(r'\[([^\]]+)\]\s*\(\s*`?([^)`]+?)`?\s*\)')
        paren = re.compile(r'((?:\b\w+\b(?:\s+\b\w+\b){0,3}))\s*\(\s*`?(https?://[^)`]+)`?\s*\)')
        spaceurl = re.compile(r'((?:\b\w+\b(?:\s+\b\w+\b){0,3}))\s+(`?\s*https?://\S+?\s*`?)')
        img = re.compile(r'\{([^{}]+)\}')
        
        idx = 0
        n = len(normalized)
        while idx < n:
            m = md.search(normalized, idx)
            p = paren.search(normalized, idx)
            s = spaceurl.search(normalized, idx)
            i_match = img.search(normalized, idx)
            
            candidates = [x for x in [m, p, s, i_match] if x]
            if not candidates:
                self.human_type(element, normalized[idx:], 0.01, 0.03)
                break
            earliest = min(candidates, key=lambda x: x.start())
            
            before = normalized[idx:earliest.start()]
            if before:
                self.human_type(element, before, 0.01, 0.03)
            
            if earliest == i_match:
                image_path = earliest.group(1).strip()
                logger.info(f"🖼️ Found image placeholder: {image_path}")
                
                # Press Enter before image if not at start (optional)
                if idx > 0 or before:
                     ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                     time.sleep(0.5)

                resolved_path = self._resolve_image_path(image_path)
                if resolved_path:
                     ok = self.upload_image_to_editor(resolved_path)
                else:
                     ok = False
                if ok:
                     logger.info("✅ Image uploaded")
                     time.sleep(3) # Wait for image to process
                     
                     # Robustly move to new line after image
                     actions = ActionChains(self.driver)
                     actions.send_keys(Keys.ESCAPE) # Exit caption/selection
                     actions.pause(0.5)
                     actions.send_keys(Keys.RIGHT)  # Move caret past image
                     actions.pause(0.5)
                     actions.send_keys(Keys.ENTER)  # Create new paragraph
                     actions.perform()
                     time.sleep(1)
                else:
                     logger.error("❌ Image upload failed")
                     
                idx = earliest.end()
                continue

            link_text = earliest.group(1).strip()
            raw_url = earliest.group(2).strip()
            link_url = raw_url.strip().strip('`').strip('\\').strip().replace('`', '')
            logger.info(f"🔗 Inserting hyperlink: '{link_text}' -> {link_url}")
            # type link text
            self.human_type(element, link_text, 0.01, 0.03)
            # select typed text
            actions = ActionChains(self.driver)
            actions.key_down(Keys.SHIFT)
            for _ in range(len(link_text)):
                actions.send_keys(Keys.LEFT)
            actions.key_up(Keys.SHIFT)
            actions.perform()
            time.sleep(0.3)
            # open link dialog and robustly locate input
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
            time.sleep(0.4)
            link_input = None
            candidates_xpath = [
                "//input[contains(@placeholder,'Paste')]",
                "//input[contains(@placeholder,'link')]",
                "//input[contains(@aria-label,'link')]",
                "//*[@data-testid='link-entry']//input",
                "//div[contains(@class,'popover')]//input",
                "//div[contains(@class,'link')]",
                "//div[contains(@role,'dialog')]//input",
            ]
            for attempt in range(2):
                for xp in candidates_xpath:
                    try:
                        els = self.driver.find_elements(By.XPATH, xp)
                        for el in els:
                            if el.is_displayed():
                                link_input = el
                                break
                        if link_input:
                            break
                    except Exception:
                        continue
                if link_input:
                    break
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
            linked = False
            if link_input:
                try:
                    self.simulate_human_mouse_movement(link_input)
                except Exception:
                    pass
                try:
                    link_input.click()
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", link_input)
                    except Exception:
                        pass
                time.sleep(0.2)
                self.human_type(link_input, link_url, 0.005, 0.02)
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(0.3)
                linked = True
            else:
                ActionChains(self.driver).send_keys(link_url).send_keys(Keys.ENTER).perform()
                time.sleep(0.3)
                # If dialog didn't appear, try JS-based link creation on current selection
                try:
                    created = self.driver.execute_script("""
                        var url = arguments[0];
                        try {
                            if (document.queryCommandSupported && document.queryCommandSupported('createLink')) {
                                var ok = document.execCommand('createLink', false, url);
                                if (ok) return true;
                            }
                        } catch(e){}
                        var sel = window.getSelection && window.getSelection();
                        if (!sel || sel.rangeCount === 0) return false;
                        var range = sel.getRangeAt(0);
                        var txt = range.toString();
                        if (!txt) return false;
                        var a = document.createElement('a');
                        a.href = url;
                        a.textContent = txt;
                        range.deleteContents();
                        range.insertNode(a);
                        range.setStartAfter(a);
                        range.setEndAfter(a);
                        sel.removeAllRanges();
                        sel.addRange(range);
                        return true;
                    """, link_url)
                    if created:
                        linked = True
                except Exception:
                    pass
            # move cursor to end of link
            ActionChains(self.driver).send_keys(Keys.RIGHT).perform()
            time.sleep(0.05)
            # If not linked yet, force-wrap last occurrence via JS inside editor
            if not linked:
                try:
                    root_el = element
                    try:
                        if not root_el:
                            ae = self.driver.switch_to.active_element
                            root_el = ae
                    except Exception:
                        root_el = None
                    self.driver.execute_script("""
                        var root = arguments[0] || document.activeElement || document.body;
                        var txt = arguments[1];
                        var url = arguments[2];
                        if (!root) return false;
                        function findLastTextNodeWith(root, text){
                            var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
                            var nodes = [], n;
                            while((n = w.nextNode())){
                                if(n.nodeValue && n.nodeValue.indexOf(text) !== -1){
                                    nodes.push(n);
                                }
                            }
                            return nodes.length ? nodes[nodes.length-1] : null;
                        }
                        var node = findLastTextNodeWith(root, txt);
                        if(!node) return false;
                        var idx = node.nodeValue.lastIndexOf(txt);
                        if(idx < 0) return false;
                        var range = document.createRange();
                        range.setStart(node, idx);
                        range.setEnd(node, idx + txt.length);
                        var a = document.createElement('a');
                        a.href = url;
                        a.textContent = txt;
                        range.deleteContents();
                        range.insertNode(a);
                        range.setStartAfter(a);
                        range.setEndAfter(a);
                        var sel = window.getSelection();
                        if(sel){
                            sel.removeAllRanges();
                            sel.addRange(range);
                        }
                        return true;
                    """, root_el, link_text, link_url)
                except Exception:
                    pass
            idx = earliest.end()
    
    def _line_has_link(self, line):
        normalized = line.replace("\\`", "`")
        if re.search(r'\[([^\]]+)\]\s*\(\s*`?([^)`]+?)`?\s*\)', normalized):
            return True
        if re.search(r'((?:\b\w+\b(?:\s+\b\w+\b){0,3}))\s*\(\s*`?(https?://[^)`]+)`?\s*\)', normalized):
            return True
        if re.search(r'https?://\S+', normalized):
            return True
        return False

    def write_story(self):
        """Read blog.txt and write story"""
        logger.info("=== Step 8: Writing Story ===")
        try:
            # Read blog.txt
            if not os.path.exists("blog.txt"):
                logger.error("blog.txt not found")
                return False
            
            with open("blog.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if not lines:
                logger.error("blog.txt is empty")
                return False
                
            title = lines[0].strip()
            # Content lines for processing
            content_lines = [line.rstrip() for line in lines[1:]]
            
            logger.info(f"Title: {title}")
            logger.info(f"Content lines: {len(content_lines)}")
            
            # Wait for editor to load
            time.sleep(random.uniform(3, 5))
            
            # 1. Prepare Editor (Focus Body via Title + Enter)
            logger.info("Step 8.1: Preparing Editor - Clicking Title then Enter to reach Body")
            
            # Find Title Field first (It's the most reliable anchor)
            title_selectors = [
                "//h3[@data-testid='editorTitleParagraph']",
                "//h3[contains(@class, 'graf--title')]",
                "//*[@placeholder='Title']",
                "//h3[contains(text(), 'Title')]"
            ]
            
            title_field = None
            for xp in title_selectors:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            title_field = el
                            break
                    if title_field: break
                except: continue
                
            if title_field:
                # Click Title
                try:
                    self.simulate_human_mouse_movement(title_field)
                    title_field.click()
                    time.sleep(1)
                    # Press Enter to force focus to Body
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(1)
                    logger.info("Moved focus to Body section")
                except Exception as e:
                    logger.error(f"Failed to navigate to body: {e}")
            else:
                logger.error("Title field not found, cannot navigate to body reliably")
                # Fallback: Try to click vaguely in the center-ish
                try:
                    ActionChains(self.driver).move_by_offset(200, 300).click().perform()
                except: pass

            # 2. Type Body Content
            logger.info("Step 8.2: Typing Body Content")
            time.sleep(1)
            
            # Type content line by line
            # We assume focus is now in the body because of the Enter key
            for line in content_lines:
                if not line.strip():
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    continue
                    
                self.type_line_with_links(None, line) # Type into active element
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            
            logger.info("Content entered")
            time.sleep(2)

            # 3. Enter Title LAST
            logger.info("Step 8.3: Entering Title Last")
            
            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Re-find Title Field
            title_field = None
            for xp in title_selectors:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            title_field = el
                            break
                    if title_field: break
                except: continue
                
            if title_field:
                logger.info("Found Title field for typing")
                self.simulate_human_mouse_movement(title_field)
                
                # Click Title
                try:
                    title_field.click()
                    time.sleep(1)
                except:
                    pass
                
                # Type Title
                logger.info("Entering title...")
                try:
                    if not self.fast_type(title_field, title):
                         title_field.send_keys(title)
                except Exception:
                    try:
                        ActionChains(self.driver).send_keys(title).perform()
                    except Exception:
                        self.human_type(None, title, 0.001, 0.005)
                
                logger.info("Title entered")
                time.sleep(1)
                
            else:
                logger.error("Title field not found for typing")
                return False

            # 3. Click Publish (First button)
            logger.info("Looking for Publish button...")
            publish_selectors = [
                "//button[@data-testid='publish-button']",
                "//button[contains(., 'Publish')]",
            ]
            
            publish_btn = None
            for xp in publish_selectors:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            publish_btn = el
                            break
                    if publish_btn: break
                except: continue
                
            if publish_btn:
                self.simulate_human_mouse_movement(publish_btn)
                publish_btn.click()
                logger.info("First Publish button clicked")
                time.sleep(3)
                
                # 4. Handle 'Publish now' (Second button in modal)
                logger.info("Looking for 'Publish now' button...")
                publish_now_selectors = [
                    "//button[@data-action='publish-confirm']",
                    "//button[contains(., 'Publish now')]",
                    "//button[contains(@class, 'js-publishButton')]",
                ]
                
                publish_now_btn = None
                # Wait a bit for modal
                time.sleep(2)
                
                for xp in publish_now_selectors:
                    try:
                        els = self.driver.find_elements(By.XPATH, xp)
                        for el in els:
                            if el.is_displayed():
                                publish_now_btn = el
                                break
                        if publish_now_btn: break
                    except: continue
                    
                if publish_now_btn:
                    self.simulate_human_mouse_movement(publish_now_btn)
                    publish_now_btn.click()
                    logger.info("✅ 'Publish now' clicked! Story published.")
                    time.sleep(5)
                    self.take_screenshot("story_published")
                    return True
                else:
                    logger.warning("'Publish now' button not found. Check screenshot.")
                    self.take_screenshot("publish_now_missing")
                    return False
            else:
                logger.error("Publish button not found")
                self.take_screenshot("publish_button_missing")
                return False
                
        except Exception as e:
            logger.error(f"Error writing story: {e}")
            self.take_screenshot("write_story_error")
            return False

    def take_screenshot(self, step_name):
        """Take screenshot with better naming"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"debug_{step_name}_{timestamp}.png"
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
            os.makedirs(base_dir, exist_ok=True)
            full_path = os.path.join(base_dir, filename)
            self.driver.save_screenshot(full_path)
            logger.info(f"📸 Screenshot saved: {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def simulate_human_mouse_movement(self, element):
        """Simulate human-like mouse movement to element"""
        try:
            # Get element location
            location = element.location_once_scrolled_into_view
            
            # Move mouse to element with curve
            actions = ActionChains(self.driver)
            
            # Move to a random position first
            actions.move_by_offset(random.randint(-100, 100), random.randint(-50, 50))
            actions.pause(random.uniform(0.1, 0.3))
            
            # Move to element
            actions.move_to_element(element)
            actions.pause(random.uniform(0.2, 0.5))
            
            # Perform the action
            actions.perform()
            
        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")
    
    def find_and_click_sign_in(self):
        """Find and click Sign in button with multiple approaches"""
        logger.info("Looking for Sign in button...")
        
        # First try undetected approach - go to home page first
        try:
            self.driver.get("https://medium.com/")
            time.sleep(random.uniform(3, 5))
            
            # Try to find and click sign in with natural delay
            signin_selectors = [
                "//a[contains(text(), 'Sign in')]",
                "//button[contains(text(), 'Sign in')]",
                "//span[contains(text(), 'Sign in')]/parent::*",
                "//*[@data-testid='signin-button']",
                "//a[@href*='signin']",
            ]
            
            for selector in signin_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Simulate human mouse movement
                            self.simulate_human_mouse_movement(element)
                            time.sleep(random.uniform(0.5, 1.5))
                            
                            # Click with natural delay
                            element.click()
                            time.sleep(random.uniform(2, 4))
                            
                            if "signin" in self.driver.current_url.lower():
                                logger.info(f"Successfully clicked signin with selector: {selector}")
                                self.take_screenshot("after_signin_click")
                                return True
                except:
                    continue
            
            # If signin button not found, try direct URL
            logger.info("Trying direct signin URL...")
            self.driver.get("https://medium.com/m/signin")
            time.sleep(random.uniform(4, 6))
            
        except Exception as e:
            logger.error(f"Error in signin process: {e}")
            self.driver.get("https://medium.com/m/signin")
            time.sleep(5)
        
        self.take_screenshot("signin_page_loaded")
        return True
    
    def click_sign_in_with_email(self):
        """Click 'Sign in with email' button with human-like behavior"""
        logger.info("Looking for 'Sign in with email' button...")
        time.sleep(random.uniform(2, 4))
        
        # First, check if we're already on the email input page
        if len(self.driver.find_elements(By.XPATH, "//input[@type='email']")) > 0:
            logger.info("Already on email input page")
            return True
        
        strategies = [
            ("//button[contains(., 'Sign in with email')]", "Button with text"),
            ("//button[contains(., 'sign in with email')]", "Button with lowercase"),
            ("//div[contains(text(), 'Sign in with email')]", "Div with text"),
            ("//a[contains(text(), 'Sign in with email')]", "Link with text"),
            ("//*[@data-testid='email-button']", "Data testid"),
            ("//*[contains(@class, 'email-signin')]", "Class containing email"),
            ("//button[@aria-label='Sign in with email']", "Aria label"),
        ]
        
        for xpath, desc in strategies:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        logger.info(f"Found '{desc}' element")
                        
                        # Simulate human mouse movement
                        self.simulate_human_mouse_movement(element)
                        time.sleep(random.uniform(0.8, 1.5))
                        
                        # Multiple click attempts
                        try:
                            element.click()
                        except:
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                            except:
                                ActionChains(self.driver).move_to_element(element).click().perform()
                        
                        logger.info(f"Clicked '{desc}'")
                        time.sleep(random.uniform(3, 5))
                        
                        # Verify we're on email page
                        email_indicators = [
                            "//input[@type='email']",
                            "//input[@placeholder='Your email']",
                            "//input[@name='email']",
                            "//input[@id='email']"
                        ]
                        
                        for indicator in email_indicators:
                            if len(self.driver.find_elements(By.XPATH, indicator)) > 0:
                                logger.info(f"Email page detected with indicator: {indicator}")
                                self.take_screenshot("after_email_button")
                                return True
            except Exception as e:
                logger.debug(f"Strategy {desc} failed: {e}")
                continue
        
        logger.error("Could not click 'Sign in with email'")
        self.take_screenshot("email_button_not_found")
        return False
    
    def enter_email_and_continue(self):
        """Enter email and click Continue with anti-detection techniques"""
        logger.info("Entering email address...")
        
        try:
            # Wait with random delay
            time.sleep(random.uniform(2, 4))
            
            # Find email field with multiple selectors
            email_selectors = [
                (By.XPATH, "//input[@type='email']"),
                (By.XPATH, "//input[@placeholder='Your email']"),
                (By.XPATH, "//input[@name='email']"),
                (By.XPATH, "//input[contains(@id, 'email')]"),
                (By.XPATH, "//input[@data-testid='email-input']"),
                (By.XPATH, "//input[@aria-label='Your email']"),
            ]
            
            email_field = None
            for by, selector in email_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            email_field = element
                            break
                    if email_field:
                        break
                except:
                    continue
            
            if not email_field:
                logger.error("No email field found!")
                self.take_screenshot("no_email_field")
                return False
            
            # Simulate human interaction with email field
            self.simulate_human_mouse_movement(email_field)
            time.sleep(random.uniform(0.5, 1.2))
            
            # Click on the field
            try:
                email_field.click()
            except:
                self.driver.execute_script("arguments[0].click();", email_field)
            
            time.sleep(random.uniform(0.3, 0.8))
            
            # Clear field (simulate human behavior)
            for _ in range(random.randint(1, 3)):
                email_field.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(0.2, 0.5))
            
            # Enter email with realistic typing speed
            self.human_type(email_field, self.email, 0.08, 0.25)
            
            # Random pause after typing
            time.sleep(random.uniform(0.5, 1.5))
            
            # Tab out of field (like a human would)
            email_field.send_keys(Keys.TAB)
            time.sleep(random.uniform(1, 2))
            
            self.take_screenshot("email_entered")
            
            # Wait for Continue button to become active
            time.sleep(random.uniform(2, 4))
            
            # Try multiple strategies for Continue button
            continue_buttons = [
                "//button[contains(., 'Continue') and not(contains(., 'Resend'))]",
                "//button[normalize-space()='Continue']",
                "//button[text()='Continue']",
                "//button[@type='submit']",
                "//button[@data-testid='continue-button']",
                "//button[contains(@class, 'continue')]",
            ]
            
            button_clicked = False
            for xpath in continue_buttons:
                try:
                    buttons = self.driver.find_elements(By.XPATH, xpath)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"Found Continue button: {xpath}")
                            
                            # Simulate human mouse movement to button
                            self.simulate_human_mouse_movement(button)
                            time.sleep(random.uniform(0.5, 1.2))
                            
                            # Human-like click with slight delay
                            try:
                                button.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", button)
                            
                            logger.info(f"Clicked Continue button")
                            button_clicked = True
                            break
                    if button_clicked:
                        break
                except Exception as e:
                    logger.debug(f"Continue button not found with {xpath}: {e}")
                    continue
            
            # Fallback strategies
            if not button_clicked:
                # Try pressing Enter
                logger.info("Trying Enter key...")
                email_field.send_keys(Keys.ENTER)
                button_clicked = True
                time.sleep(random.uniform(0.5, 1))
            
            if button_clicked:
                logger.info("Continue button clicked successfully")
                
                # IMPORTANT: Wait longer before checking for errors
                time.sleep(random.uniform(5, 8))
                self.take_screenshot("after_continue_click")
                
                # Check for 500 error immediately
                page_source = self.driver.page_source.lower()
                if "apologies" in page_source or "something went wrong" in page_source:
                    logger.error("⚠️ 500 Error detected after Continue click!")
                    
                    # Try refreshing and waiting
                    logger.info("Refreshing page and waiting...")
                    self.driver.refresh()
                    time.sleep(random.uniform(10, 15))
                    
                    # Check if we're back on OTP page
                    if self.check_otp_page():
                        return True
                    else:
                        return False
                
                # Check for OTP page
                if self.check_otp_page():
                    logger.info("✅ OTP page loaded successfully")
                    return True
                else:
                    # Check current URL
                    current_url = self.driver.current_url
                    logger.info(f"Current URL: {current_url}")
                    
                    # Maybe we need to wait longer
                    logger.info("Waiting additional time for OTP page...")
                    time.sleep(random.uniform(5, 7))
                    
                    if self.check_otp_page():
                        return True
                    else:
                        logger.info("Trying to open code-based sign in")
                        if self.open_code_signin():
                            return True
                        logger.warning("OTP page still not detected")
                        self.take_screenshot("otp_page_not_found")
                        return False
            else:
                logger.error("Could not click Continue button")
                return False
                
        except Exception as e:
            logger.error(f"Error in email entry: {e}")
            self.take_screenshot("email_entry_error")
            return False
    
    def check_otp_page(self):
        """Check if we're on OTP page"""
        otp_indicators = [
            "//input[@autocomplete='one-time-code']",
            "//input[@inputmode='numeric']",
            "//input[@type='text' and @maxlength='6']",
            "//input[@name='code']",
            "//input[@id='code']",
            "//input[@placeholder*='code']",
            "//div[contains(text(), 'Check your email inbox')]",
            "//div[contains(text(), 'To sign in')]",
            "//p[contains(text(), 'we sent to')]",
            "//div[contains(text(), 'Enter the code')]",
            "//h1[contains(text(), 'Check your email')]",
        ]
        
        for xpath in otp_indicators:
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                logger.info(f"OTP page indicator found: {xpath}")
                return True
            except:
                continue
        
        return False
    
    def open_code_signin(self):
        """Open code-based sign-in if available"""
        try:
            probes = [
                "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'use code')]",
                "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'enter code')]",
                "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verification code')]",
                "//a[contains(., 'Use code')]",
                "//button[contains(., 'Use code')]",
            ]
            for xp in probes:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            self.simulate_human_mouse_movement(el)
                            time.sleep(random.uniform(0.5, 1.2))
                            try:
                                el.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(random.uniform(2, 4))
                            if self.check_otp_page():
                                self.take_screenshot("code_signin_opened")
                                return True
                except:
                    continue
        except Exception as e:
            logger.debug(f"open_code_signin failed: {e}")
        return False
    
    def get_otp_from_email(self):
        """Get the CURRENT NEWEST OTP from Gmail using specific Medium filters"""
        logger.info("Fetching NEWEST OTP from email...")
        
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.email, self.password)
            mail.select("inbox")
            
            logger.info("Scanning inbox for fresh Medium OTP...")
            deadline = time.time() + 180  # 3 minutes
            
            while time.time() < deadline:
                # UPDATED: Search specifically for emails from Medium to reduce noise
                # and ensure we get the right email type.
                status, messages = mail.search(None, '(FROM "noreply@medium.com")')
                
                if status == "OK" and messages[0]:
                    # Get list of email IDs and pick the LAST one (Newest)
                    email_ids = messages[0].split()
                    latest_email_id = email_ids[-1]
                    
                    res, msg_data = mail.fetch(latest_email_id, "(RFC822)")
                    
                    raw_email = msg_data[0][1]
                    msg = pyemail.message_from_bytes(raw_email)
                    
                    # Decode subject
                    subject_header = msg["Subject"]
                    decoded_list = decode_header(subject_header)
                    subject = ""
                    for content, encoding in decoded_list:
                        if isinstance(content, bytes):
                            subject += content.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            subject += str(content)
                    
                    subject = subject.lower()
                    logger.info(f"Checking email subject: {subject}")
                    
                    # Check date to ensure it's recent (optional but good practice)
                    # For now, relying on 'last' ID is usually sufficient for IMAP
                    
                    otp_found = None
                    
                    # 1. Check for OTP in subject (Common in some regions)
                    otp_match = re.search(r'\b\d{6}\b', subject)
                    if otp_match:
                        otp_found = otp_match.group(0)
                        logger.info(f"✅ OTP found in subject: {otp_found}")
                    
                    # 2. Check body if not in subject
                    if not otp_found:
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    charset = part.get_content_charset()
                                    body = payload.decode(charset or 'utf-8', errors='ignore')
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            body = payload.decode('utf-8', errors='ignore')
                        
                        # Find OTP in body
                        # Looking for 6 digits that are isolated
                        match = re.search(r'\b\d{6}\b', body)
                        if match:
                            otp_found = match.group(0)
                            logger.info(f"✅ OTP found in body: {otp_found}")

                    if otp_found:
                        mail.logout()
                        return otp_found
                    
                time.sleep(5)
            
            mail.logout()
            logger.error("OTP not found in email within time limit")
            
        except Exception as e:
            logger.error(f"Error fetching OTP: {e}")
        
        return None
    
    def enter_otp_code(self, otp_code):
        """Enter OTP code digit by digit into the 6 boxes shown in image"""
        logger.info(f"Entering OTP code: {otp_code}")
        time.sleep(random.uniform(2, 4))

        try:
            # UPDATED STRATEGY: Find the 6 separate input boxes
            # Medium usually uses 6 individual inputs for code verification

            # Find all inputs that look like digit holders
            # Look for inputs with type='tel' or inputmode='numeric' which are common for OTP
            digit_inputs = []
            otp_selectors = [
                "//input[@type='tel']",
                "//input[@inputmode='numeric']",
                "//input[@type='text' and @maxlength='1']",
                "//input[@type='number' and @maxlength='1']",
            ]

            for selector in otp_selectors:
                inputs = self.driver.find_elements(By.XPATH, selector)
                for inp in inputs:
                    if inp.is_displayed() and inp not in digit_inputs:
                        digit_inputs.append(inp)

            # Remove duplicates if any
            digit_inputs = list(set(digit_inputs))

            logger.info(f"Found {len(digit_inputs)} potential digit input boxes")

            # If we found exactly 6 boxes, this is likely the OTP form
            if len(digit_inputs) == 6:
                # Sort them by x-coordinate (left to right)
                digit_inputs.sort(key=lambda x: x.location['x'])

                for i, digit in enumerate(otp_code):
                    box = digit_inputs[i]

                    # For the first box, simulate mouse movement and click
                    if i == 0:
                        self.simulate_human_mouse_movement(box)
                        box.click()
                        time.sleep(random.uniform(0.2, 0.5))

                    # Clear the box first (in case of retry)
                    try:
                        box.clear()
                    except:
                        box.send_keys(Keys.BACKSPACE)

                    time.sleep(random.uniform(0.1, 0.2))

                    # Send the digit
                    box.send_keys(digit)
                    logger.info(f"Entered digit {i+1}: {digit} into box {i+1}")

                    # Short delay between digits
                    time.sleep(random.uniform(0.2, 0.4))

                self.take_screenshot("otp_filled_6boxes")
                return True

            elif len(digit_inputs) > 6:
                # If more than 6, sort and take first 6
                digit_inputs.sort(key=lambda x: x.location['x'])
                target_inputs = digit_inputs[:6]

                for i, digit in enumerate(otp_code):
                    box = target_inputs[i]

                    if i == 0:
                        self.simulate_human_mouse_movement(box)
                        box.click()
                        time.sleep(random.uniform(0.2, 0.5))

                    try:
                        box.clear()
                    except:
                        box.send_keys(Keys.BACKSPACE)

                    time.sleep(random.uniform(0.1, 0.2))
                    box.send_keys(digit)
                    logger.info(f"Entered digit {i+1}: {digit} into box {i+1}")
                    time.sleep(random.uniform(0.2, 0.4))

                self.take_screenshot("otp_filled_6boxes")
                return True

            else:
                # Fallback: Try finding the single main input if the UI is different
                logger.warning(f"Could not find 6 separate boxes (found {len(digit_inputs)}), trying fallback...")
                fallback_selectors = [
                    "//input[@autocomplete='one-time-code']",
                    "//input[@name='code']",
                    "//input[@inputmode='numeric' and @maxlength='6']",
                    "//input[@type='tel' and @maxlength='6']",
                    "//input[@type='text' and @maxlength='6']",
                    "//input[@placeholder*='code']",
                ]

                for xpath in fallback_selectors:
                    fallback_input = self.driver.find_elements(By.XPATH, xpath)
                    if fallback_input and fallback_input[0].is_displayed():
                        el = fallback_input[0]
                        self.simulate_human_mouse_movement(el)
                        el.click()
                        time.sleep(random.uniform(0.3, 0.7))
                        el.clear()
                        self.human_type(el, otp_code)
                        self.take_screenshot("otp_filled_single")
                        return True

            logger.error("Failed to identify OTP input structure")
            self.take_screenshot("otp_structure_failed")
            return False

        except Exception as e:
            logger.error(f"Error entering OTP: {e}")
        return True
    
    def submit_otp(self):
        """Submit OTP"""
        logger.info("Submitting OTP...")
        time.sleep(random.uniform(2, 4))
        
        # Try to find submit button first
        submit_buttons = [
            "//button[contains(., 'Submit')]",
            "//button[contains(., 'Verify')]",
            "//button[@type='submit']",
            "//button[contains(., 'Continue')]",
            "//input[@type='submit']",
        ]
        
        for xpath in submit_buttons:
            try:
                buttons = self.driver.find_elements(By.XPATH, xpath)
                for button in buttons:
                    if button.is_displayed():
                        # Check if enabled (sometimes disabled until code entered)
                        if not button.is_enabled():
                            logger.info("Submit button found but disabled. Waiting...")
                            time.sleep(2)
                        
                        if button.is_enabled():
                            self.simulate_human_mouse_movement(button)
                            time.sleep(random.uniform(0.5, 1))
                            
                            button.click()
                            logger.info(f"Submit button clicked: {xpath}")
                            time.sleep(random.uniform(3, 5))
                            return True
            except:
                continue
        
        # Try Enter key if no button found
        try:
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ENTER).perform()
            logger.info("Enter key pressed")
            time.sleep(random.uniform(3, 5))
            return True
        except:
            pass
        
        return True
    
    def click_write_on_header(self):
        logger.info("=== Step 7: Clicking 'Write' in header ===")
        try:
            if ("medium.com" not in self.driver.current_url) or ("signin" in self.driver.current_url.lower()):
                self.driver.get("https://medium.com/")
                time.sleep(random.uniform(3, 5))
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[self::a or self::button][contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'write')]")))
            except:
                time.sleep(random.uniform(2, 4))
            selectors = [
                "//*[@data-testid='header-write']",
                "//*[self::a or self::button][contains(., 'Write')]",
                "//*[self::a or self::button][contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'write')]",
                "//a[@href='/new-story']",
                "//a[contains(@href, '/new-story')]",
                "//a[contains(@href, '/new')]",
            ]
            for xp in selectors:
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            self.simulate_human_mouse_movement(el)
                            time.sleep(random.uniform(0.5, 1.2))
                            try:
                                el.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(random.uniform(3, 5))
                            self.take_screenshot("write_clicked")
                            cu = self.driver.current_url.lower()
                            if "/new" in cu or "/new-story" in cu or "/p/" in cu:
                                logger.info("✅ Navigated to write editor")
                                return True
                            return True
                except Exception as e:
                    logger.debug(f"Write selector failed: {e}")
                    continue
            logger.warning("Write button not found")
            self.take_screenshot("write_button_not_found")
            return False
        except Exception as e:
            logger.error(f"Error clicking Write: {e}")
            self.take_screenshot("write_click_error")
            return False
    

    def execute_login(self):
        """Main login execution"""
        try:
            logger.info("🚀 Starting Medium Login Automation")
            
            # Step 1: Navigate to signin
            logger.info("=== Step 1: Navigating to signin page ===")
            if not self.find_and_click_sign_in():
                return False
            
            time.sleep(random.uniform(3, 5))
            
            # Step 2: Click sign in with email
            logger.info("=== Step 2: Clicking 'Sign in with email' ===")
            if not self.click_sign_in_with_email():
                return False
            
            time.sleep(random.uniform(3, 5))
            
            # Step 3: Enter email and continue
            logger.info("=== Step 3: Entering email and clicking Continue ===")
            if not self.enter_email_and_continue():
                logger.error("Failed at email entry step")
                
                # Check if 500 error occurred
                page_source = self.driver.page_source.lower()
                if "apologies" in page_source:
                    logger.error("500 Error detected! Medium is blocking automation.")
                    logger.info("Try these solutions:")
                    logger.info("1. Wait 1-2 hours before trying again")
                    logger.info("2. Use a different network/VPN")
                    logger.info("3. Clear browser cookies and cache")
                
                return False
            
            # Step 4: Get OTP from email
            logger.info("=== Step 4: Getting OTP from email ===")
            otp = self.get_otp_from_email()
            
            if not otp:
                logger.warning("Auto-OTP failed. Manual entry required.")
                try:
                    otp = input("📧 Enter the 6-digit OTP from email: ").strip()
                except:
                    logger.error("No OTP provided")
                    return False
            
            # Step 5: Enter OTP
            logger.info("=== Step 5: Entering OTP ===")
            if not self.enter_otp_code(otp):
                return False
            
            # Step 6: Submit OTP
            logger.info("=== Step 6: Submitting OTP ===")
            if not self.submit_otp():
                return False
            
            # Final check
            time.sleep(random.uniform(5, 8))
            self.take_screenshot("final_result")
            
            # Check if login successful
            current_url = self.driver.current_url
            if "medium.com" in current_url and "signin" not in current_url:
                logger.info("🎉 Login Successful!")
                try:
                    if self.click_write_on_header():
                        self.write_story()
                except Exception as e:
                    logger.warning(f"Write click attempt failed: {e}")
                return True
            else:
                logger.info("⚠️ Process completed. Check final screenshot.")
                return True
                
        except Exception as e:
            logger.error(f"❌ Login process failed: {e}")
            self.take_screenshot("error_final")
            return False

def run(driver, website, email, username, password):
    """Global run function called by script.py"""
    try:
        logger.info(f"Starting Medium automation for {email}")
        handler = MediumSpecificHandler(driver, email, password)
        return handler.execute_login()
    except Exception as e:
        logger.error(f"Run execution failed: {e}")
        return False

def test_medium_login():
    """Test function using undetected-chromedriver"""
    try:
        # Use undetected-chromedriver for better stealth
        print("🚀 Starting Chrome with anti-detection features...")
        
        # Setup Chrome options
        options = uc.ChromeOptions()
        
        # Add arguments
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        random_agent = random.choice(user_agents)
        options.add_argument(f"user-agent={random_agent}")
        
        # Create undetected driver
        driver = uc.Chrome(
            options=options,
            headless=False,
        )
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    except Exception as e:
        print(f"❌ Undetected chromedriver failed: {e}")
        print("⚠️ Falling back to regular Chrome...")
        
        # Fallback to regular Selenium
        from selenium import webdriver
        
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        driver = webdriver.Chrome(options=options)
        
        # Stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Credentials
        test_email = "dharmikkbaria712@gmail.com"
        test_password = "sqvq hbbp klka jibf"
        
        print(f"\n{'='*60}")
        print("MEDIUM LOGIN AUTOMATION")
        print(f"{'='*60}")
        print(f"Email: {test_email}")
        print(f"{'='*60}\n")
        
        if not test_password:
            print("❌ Gmail app password not set!")
            return
        
        # Create handler and execute login
        handler = MediumSpecificHandler(driver, test_email, test_password)
        success = handler.execute_login()
        
        if success:
            print(f"\n{'='*60}")
            print("✅ Process completed!")
            print("Check the debug_*.png screenshots")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("❌ Process failed")
            print("Possible reasons:")
            print("1. Medium is blocking automation")
            print("2. Too many attempts recently")
            print("3. Network/IP issues")
            print("\nSolutions:")
            print("1. Wait 1-2 hours")
            print("2. Use VPN")
            print("3. Try manual login first")
            print(f"{'='*60}")
        
        input("\nPress Enter to close browser...")
        
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    email = os.getenv("EMAIL", "").strip()
    password = os.getenv("PASSWORD", "").strip()
    
    # Try loading from credentials.xlsx if env vars missing
    if not email or not password:
        try:
            if os.path.exists("credentials.xlsx"):
                wb = openpyxl.load_workbook("credentials.xlsx")
                sheet = wb.active
                # Assuming first row is header, take second row
                if sheet.max_row >= 2:
                    # Expected format: Website, Email, Username, Password
                    # Adjust indices as per your excel structure, assuming Email is col 2, Password col 4
                    # Or if it matches script.py: col 2 is Email, col 4 is Password
                    row = sheet[2]
                    email = row[1].value  # Col B
                    password = row[3].value  # Col D
                    logging.info(f"Loaded credentials for {email} from Excel")
        except Exception as e:
            logging.error(f"Failed to load credentials from Excel: {e}")

    if not email or not password:
        logging.error("No credentials found in env vars or credentials.xlsx")
        return

    headless = os.getenv("HEADLESS", "false").lower() == "true"
    try:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        ua = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument(f"user-agent={ua}")
        driver = uc.Chrome(options=options, headless=headless)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        handler = MediumSpecificHandler(driver, email, password)
        ok = handler.execute_login()
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        import undetected_chromedriver  # noqa
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "undetected-chromedriver"])
    main()
