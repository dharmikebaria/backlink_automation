# Alternative simpler version with webdriver-manager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time, os, random, re, io, tempfile
try:
    import win32clipboard
    from PIL import Image
except Exception:
    win32clipboard = None
    Image = None

def _send_to_clipboard(clip_type, data):
    try:
        if not win32clipboard:
            return False
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(clip_type, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        return False

def _process_image_for_clipboard(image_path):
    try:
        if not Image:
            return None
        if not os.path.exists(image_path):
            return None
        img = Image.open(image_path)
        if img.width > 1600 or img.height > 1600:
            img.thumbnail((1280, 1280))
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        return data
    except Exception:
        return None

def _copy_image_to_clipboard(image_path):
    try:
        if not win32clipboard or not Image:
            return False
        data = _process_image_for_clipboard(image_path)
        if not data:
            return False
        return _send_to_clipboard(win32clipboard.CF_DIB, data)
    except Exception:
        return False

def _resolve_image_path(p):
    try:
        if not p:
            return None
        base_dir = os.getcwd()
        s = p.strip().strip('"').strip("'")
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
        for pth in candidates:
            try:
                ap = os.path.abspath(pth)
                if os.path.isfile(ap):
                    return ap
            except Exception:
                continue
        ap = os.path.abspath(s)
        if os.path.isdir(ap):
            exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
            try:
                items = [os.path.join(ap, f) for f in os.listdir(ap) if os.path.splitext(f)[1].lower() in exts]
                if not items:
                    return None
                items.sort()
                return items[0]
            except Exception:
                return None
        return None
    except Exception:
        return None

def _find_contenteditable(driver):
    try:
        els = driver.find_elements(By.XPATH, "//*[@contenteditable='true']|//*[@role='textbox']")
        for el in els:
            try:
                if el.is_displayed():
                    return el
            except Exception:
                continue
    except Exception:
        return None
    return None

def _type_text_with_links(driver, body_field, text):
    try:
        pattern = r'\[([^\]]+)\]\s*\(\s*`?([^)`]+?)`?\s*\)'
        normalized = (text or "").replace("\\`", "`")
        normalized = re.sub(r"\(\s*`([^`]+)`\s*\)", r"(\1)", normalized)
        last_end = 0
        matches = list(re.finditer(pattern, normalized))
        if not matches:
            try:
                ActionChains(driver).send_keys(normalized).perform()
            except Exception:
                body_field.send_keys(normalized)
        else:
            for match in matches:
                plain = normalized[last_end:match.start()]
                if plain:
                    segs = plain.split("\n")
                    for i, seg in enumerate(segs):
                        if seg:
                            try:
                                ActionChains(driver).send_keys(seg).perform()
                            except Exception:
                                body_field.send_keys(seg)
                        if i < len(segs) - 1:
                            ActionChains(driver).send_keys(Keys.ENTER).perform()
                            time.sleep(0.05)
                link_text = match.group(1)
                raw_url = match.group(2)
                link_url = raw_url.strip().strip('`').strip('\\').strip().replace('`','')
                try:
                    ActionChains(driver).send_keys(link_text).perform()
                    time.sleep(0.2)
                    actions = ActionChains(driver)
                    actions.key_down(Keys.SHIFT)
                    for _ in range(len(link_text)):
                        actions.send_keys(Keys.LEFT)
                    actions.key_up(Keys.SHIFT)
                    actions.perform()
                    time.sleep(0.2)
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys('k').key_up(Keys.CONTROL).perform()
                    time.sleep(0.7)
                    link_actions = ActionChains(driver)
                    link_actions.send_keys(link_url)
                    link_actions.send_keys(Keys.ENTER)
                    link_actions.perform()
                    time.sleep(0.3)
                    ActionChains(driver).send_keys(Keys.RIGHT).perform()
                    time.sleep(0.1)
                except Exception:
                    try:
                        driver.execute_script("""
                            var text = arguments[0];
                            var url = arguments[1];
                            if (document.queryCommandSupported && document.queryCommandSupported('insertHTML')) {
                                return document.execCommand('insertHTML', false, '<a href=\"' + url + '\">' + text + '</a>');
                            }
                            return false;
                        """, link_text, link_url)
                        ActionChains(driver).send_keys(Keys.RIGHT).perform()
                    except Exception:
                        try:
                            driver.execute_script("""
                                var url = arguments[0];
                                var text = arguments[1];
                                var sel = window.getSelection();
                                var a = document.createElement('a');
                                a.href = url;
                                a.textContent = text;
                                if (sel && sel.rangeCount > 0) {
                                    var range = sel.getRangeAt(0);
                                    range.insertNode(a);
                                    range.setStartAfter(a);
                                    range.setEndAfter(a);
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                } else {
                                    var el = document.activeElement;
                                    if (el && el.isContentEditable) {
                                        el.appendChild(a);
                                    }
                                }
                            """, link_url, link_text)
                            ActionChains(driver).send_keys(Keys.RIGHT).perform()
                        except Exception:
                            pass
                last_end = match.end()
            remaining = normalized[last_end:]
            if remaining:
                segs = remaining.split("\n")
                for i, seg in enumerate(segs):
                    if seg:
                        try:
                            ActionChains(driver).send_keys(seg).perform()
                        except Exception:
                            body_field.send_keys(seg)
                    if i < len(segs) - 1:
                        ActionChains(driver).send_keys(Keys.ENTER).perform()
                        time.sleep(0.05)
        return True
    except Exception:
        return False

def _dismiss_popups(driver, wait, attempts=5):
    try:
        for _ in range(attempts):
            found = False
            for xp in [
                "//*[@role='dialog']//*[@aria-label='Close']",
                "//button[@aria-label='Close']",
                "//div[@aria-label='Close']",
                "//span[@aria-label='Close']",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'got it')]",
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'got it')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'get started')]",
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'get started')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
                "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'done')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'maybe later')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no thanks')]",
                "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'skip')]",
                "//div[@role='dialog']//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'cancel')]",
                "//div[contains(@class, 'modal')]//button[contains(@class, 'close')]",
                "//div[contains(@class, 'dialog')]//button[contains(@class, 'close')]"
            ]:
                try:
                    els = driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            try:
                                ActionChains(driver).move_to_element(el).pause(random.uniform(0.1, 0.3)).click().perform()
                            except:
                                try:
                                    driver.execute_script("arguments[0].click();", el)
                                except:
                                    try:
                                        el.click()
                                    except:
                                        pass
                            time.sleep(1)
                            found = True
                except:
                    continue
            try:
                overlays = driver.find_elements(By.XPATH, "//*[@role='dialog']|//div[contains(@class,'modal')]|//div[contains(@class,'Dialog')]|//div[contains(@class,'overlay')]")
                active = any(e.is_displayed() for e in overlays)
            except:
                active = False
            if not found and not active:
                break
            time.sleep(1)
        return True
    except:
        return False

def _close_non_patreon_windows(driver):
    try:
        main = None
        try:
            main = driver.current_window_handle
        except:
            pass
        handles = []
        try:
            handles = driver.window_handles
        except:
            handles = []
        for h in handles:
            try:
                driver.switch_to.window(h)
                u = (driver.current_url or "").lower()
                if not ("patreon.com" in u):
                    try:
                        driver.close()
                    except:
                        pass
            except:
                continue
        if main:
            try:
                driver.switch_to.window(main)
            except:
                pass
        return True
    except:
        return False

def _click_text(driver, text, timeout=10):
    try:
        t = text.lower()
        xps = [
            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]",
            f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]",
            f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]",
            f"//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]",
            f"//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]"
        ]
        for xp in xps:
            try:
                els = driver.find_elements(By.XPATH, xp)
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", el)
                        except:
                            pass
                        try:
                            ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
                        except:
                            try:
                                driver.execute_script("arguments[0].click();", el)
                            except:
                                try:
                                    el.click()
                                except:
                                    continue
                        return True
            except:
                continue
        return False
    except:
        return False

def _open_user_menu(driver):
    sels = [
        "//button[contains(@aria-label, 'Account')]",
        "//button[contains(@aria-label, 'User')]",
        "//button[contains(@class, 'user-menu')]",
        "//div[contains(@class, 'UserMenu')]//button",
        "//img[contains(@alt, 'Avatar')]/ancestor::button[1]",
        "//aside//button[contains(@aria-label, 'Account')]",
        "//nav//button[contains(@aria-label, 'Account')]",
        "//a[contains(@href, '/user')]",
        "//button[contains(., 'kavi')]",
        "//a[contains(., 'kavi')]"
    ]
    for s in sels:
        try:
            els = driver.find_elements(By.XPATH, s)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    try:
                        ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", el)
                        except:
                            try:
                                el.click()
                            except:
                                continue
                    time.sleep(1)
                    return True
        except:
            continue
    return False

def _switch_role(driver, role='Creator'):
    try:
        ok = _open_user_menu(driver)
        time.sleep(1)
        if ok:
            if _click_text(driver, role):
                time.sleep(3)
                return True
            else:
                sels = [
                    f"//div[contains(@class,'Menu') or contains(@role,'menu')]//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{role.lower()}')]",
                    f"//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{role.lower()}')]"
                ]
                for s in sels:
                    try:
                        els = driver.find_elements(By.XPATH, s)
                        for el in els:
                            if el.is_displayed() and el.is_enabled():
                                try:
                                    el.click()
                                except:
                                    driver.execute_script("arguments[0].click();", el)
                                time.sleep(3)
                                return True
                    except:
                        continue
        return False
    except:
        return False

def _verify_published(driver, title):
    try:
        # Check for immediate success indicators (toasts/alerts) or URL change
        try:
            time.sleep(2)
            page_source = (driver.page_source or "").lower()
            if any(x in page_source for x in ["post published", "post updated", "changes saved", "published!", "updated!"]):
                return True
            if "/posts/" in driver.current_url and "/edit" not in driver.current_url:
                return True
        except:
            pass

        target = (title or "").strip().lower()
        for url in ["https://www.patreon.com/creator/posts", "https://www.patreon.com/creator/home"]:
            try:
                driver.get(url)
                time.sleep(5)
                page = (driver.page_source or "").lower()
                if target and target in page:
                    return True
                try:
                    items = driver.find_elements(By.XPATH, "//a[contains(@href,'/posts/')]|//div[contains(@class,'post')]//a|//h1|//h2|//h3")
                    for it in items:
                        try:
                            txt = (it.text or "").lower()
                            if target and target in txt:
                                return True
                        except:
                            continue
                except:
                    pass
            except:
                continue
        return False
    except:
        return False

def _is_404(driver):
    try:
        t = (driver.title or "").lower()
        p = (driver.page_source or "").lower()
        if ("404" in t) or ("this page could not be found" in p):
            return True
        return False
    except:
        return False

def _wait_for_url_contains(driver, patterns, timeout=10):
    try:
        end = time.time() + timeout
        while time.time() < end:
            u = (driver.current_url or "").lower()
            if any(p in u for p in patterns):
                return True
            time.sleep(0.5)
        return False
    except:
        return False

def _confirm_publish(driver):
    try:
        texts = [
            "publish", "post", "confirm", "submit", "next", "continue",
            "publish now", "make public", "save and publish", "update"
        ]
        for t in texts:
            try:
                xpath = f"//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]"
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        try:
                            b.click()
                        except:
                            driver.execute_script("arguments[0].click();", b)
                        time.sleep(2)
                # Also try inputs
                xpath2 = f"//input[@type='submit' and contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{t}')]"
                ins = driver.find_elements(By.XPATH, xpath2)
                for i in ins:
                    if i.is_displayed() and i.is_enabled():
                        i.click()
                        time.sleep(2)
            except:
                continue
        # Select Public if visibility options exist
        try:
            vis = driver.find_elements(By.XPATH, "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'public') and (self::button or self::span or self::div or self::label)]")
            for v in vis:
                if v.is_displayed() and v.is_enabled():
                    try:
                        v.click()
                    except:
                        driver.execute_script("arguments[0].click();", v)
                    time.sleep(1)
        except:
            pass
        # Wait for URL change or toast
        ok = _wait_for_url_contains(driver, ["/posts", "creator/posts", "published", "post"], timeout=10)
        return ok
    except:
        return False

def _on_creator_area(driver):
    try:
        u = (driver.current_url or "").lower()
        return any(k in u for k in ["creator/home", "creator-home", "/creator/", "/create", "/post/new", "creator/posts", "/c/"])
    except:
        return False

def _go_to_creator(driver, wait):
    try:
        if _on_creator_area(driver):
            return True
        for xp in [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish my page')]",
            "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish my page')]",
            "//*[text()='Finish my page']",
            "//*[contains(text(), 'Finish my page')]"
        ]:
            try:
                els = driver.find_elements(By.XPATH, xp)
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        try:
                            el.click()
                        except:
                            driver.execute_script("arguments[0].click();", el)
                        time.sleep(3)
                        if _on_creator_area(driver):
                            return True
            except:
                continue
        for xp in [
            "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'patreon for creators')]",
            "//nav//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator')]",
            "//aside//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator')]",
            "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'switch to creator')]"
        ]:
            try:
                els = driver.find_elements(By.XPATH, xp)
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        try:
                            el.click()
                        except:
                            driver.execute_script("arguments[0].click();", el)
                        time.sleep(3)
                        if _on_creator_area(driver):
                            return True
            except:
                continue
        for url in [
            "https://www.patreon.com/creator/home",
            "https://www.patreon.com/creator-home",
            "https://www.patreon.com/create"
        ]:
            try:
                driver.get(url)
                time.sleep(5)
                if _on_creator_area(driver):
                    return True
            except:
                continue
        try:
            u = (driver.current_url or "").lower()
            if "profile/creators" in u:
                for xp in [
                    "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish my page')]",
                    "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish my page')]"
                ]:
                    try:
                        els = driver.find_elements(By.XPATH, xp)
                        for el in els:
                            if el.is_displayed() and el.is_enabled():
                                try:
                                    el.click()
                                except:
                                    driver.execute_script("arguments[0].click();", el)
                                time.sleep(3)
                                if _on_creator_area(driver):
                                    return True
                    except:
                        continue
        except:
            pass
        return _on_creator_area(driver)
    except:
        return False

def automate_patreon(email, password, vanity_url=None, use_profile=False, profile_path=None, profile_dir="Default", wait_for_enter=False):
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)
    if use_profile:
        try:
            if not profile_path:
                base = os.environ.get("LOCALAPPDATA", "")
                if base:
                    profile_path = os.path.join(base, "Google", "Chrome", "User Data")
            if profile_path and os.path.isdir(profile_path):
                options.add_argument(f"--user-data-dir={profile_path}")
                if profile_dir:
                    options.add_argument(f"--profile-directory={profile_dir}")
                print(f"Using Chrome profile: {profile_path} [{profile_dir}]")
            else:
                print("Profile path not found; continuing without profile")
        except Exception as e:
            print(f"Profile setup warning: {e}")
    try:
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-extensions")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            try:
                alt = Options()
                alt.add_argument("--no-sandbox")
                alt.add_argument("--disable-dev-shm-usage")
                alt.add_argument("--disable-blink-features=AutomationControlled")
                alt.add_argument("--disable-notifications")
                alt.add_argument("--disable-popup-blocking")
                alt.add_argument("--window-size=1366,768")
                alt.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                alt.add_experimental_option("prefs", prefs)
                driver = webdriver.Chrome(service=service, options=alt)
            except Exception as e:
                raise e
    wait = WebDriverWait(driver, 20)
    
    try:
        # STEP 1: Login to Patreon
        print("Step 1: Logging in...")
        driver.get("https://www.patreon.com/login")
        time.sleep(3)
        try:
            driver.execute_script("""
            (function(){
              try {
                var bad = ['google','apple','facebook','github','microsoft','twitter','linkedin'];
                document.querySelectorAll('a,button').forEach(function(el){
                  var t = (el.textContent||'').toLowerCase();
                  var dp = (el.getAttribute('data-provider')||'').toLowerCase();
                  var href = (el.getAttribute('href')||'').toLowerCase();
                  var social = t.includes('continue with') || t.includes('sign in with') || bad.some(function(k){ return t.includes(k) || dp.includes(k) || href.includes(k); });
                  if (social) {
                    el.style.display = 'none';
                    el.disabled = true;
                    el.setAttribute('aria-hidden','true');
                  }
                });
                var _open = window.open;
                window.open = function(url,name,features){
                  try {
                    var u = (url||'').toLowerCase();
                    if (u.includes('facebook.com') || u.includes('apple.com') || u.includes('google.com') || u.includes('accounts.google.com')) {
                      return null;
                    }
                  } catch(e){}
                  return _open.apply(window, arguments);
                };
                document.addEventListener('click', function(e){
                  try {
                    var el = e.target.closest('a,button');
                    if (!el) return;
                    var t = (el.textContent||'').toLowerCase();
                    var dp = (el.getAttribute('data-provider')||'').toLowerCase();
                    var href = (el.getAttribute('href')||'').toLowerCase();
                    var social = t.includes('continue with') || t.includes('sign in with') || ['google','apple','facebook','github','microsoft','twitter','linkedin'].some(function(k){ return t.includes(k) || dp.includes(k) || href.includes(k); });
                    if (social) {
                      e.preventDefault();
                      e.stopPropagation();
                    }
                  } catch(e){}
                }, true);
              } catch(e){}
            })();
            """)
        except:
            pass
        try:
            _close_non_patreon_windows(driver)
        except:
            pass
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            driver.execute_script("Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });")
            driver.execute_script("Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });")
        except:
            pass
        
        # Handle cookie consent if present
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]")
            for btn in cookie_buttons:
                if btn.is_displayed():
                    try:
                        ActionChains(driver).move_to_element(btn).pause(random.uniform(0.1, 0.3)).click().perform()
                    except:
                        btn.click()
                    time.sleep(1)
                    break
        except:
            pass
        
        # Enter email
        email_field = None
        for selector in [ (By.ID, "email"), (By.NAME, "email"), (By.CSS_SELECTOR, "input[type='email']") ]:
            try:
                email_field = driver.find_element(*selector)
                if email_field.is_displayed():
                    email_field.clear()
                    for ch in email:
                        email_field.send_keys(ch)
                        time.sleep(random.uniform(0.03, 0.09))
                    print("Email entered")
                    break
            except:
                continue
        
        # Click email continue to reveal password step
        try:
            cont_btn = None
            try:
                cont_btn = driver.find_element(By.XPATH, "//input[@type='email']/ancestor::*[1]//button[@type='submit']")
            except:
                pass
            if not cont_btn:
                buttons = driver.find_elements(By.XPATH, "//button[@type='submit']")
                for b in buttons: 
                    try:
                        txt = (b.text or "").lower()
                        if not txt or ("continue with" in txt) or ("sign in with" in txt) or any(k in txt for k in ["apple","google","facebook","github","microsoft","twitter","linkedin"]):
                            continue
                        cont_btn = b
                        break
                    except:
                        continue
            if cont_btn and cont_btn.is_displayed() and cont_btn.is_enabled():
                try:
                    ActionChains(driver).move_to_element(cont_btn).pause(random.uniform(0.1,0.3)).click().perform()
                except:
                    cont_btn.click()
                print("Clicked email continue button")
                time.sleep(3)
        except:
            pass

        # Enter password after continue
        password_field = None
        for selector in [ (By.ID, "password"), (By.NAME, "password"), (By.CSS_SELECTOR, "input[type='password']") ]:
            try:
                password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located(selector))
                if password_field.is_displayed():
                    try:
                        password_field.clear()
                    except:
                        pass
                    for ch in password:
                        password_field.send_keys(ch)
                        time.sleep(random.uniform(0.03, 0.09))
                    print("Password entered")
                    break
            except:
                continue
        
        # Click login button
        login_button = None
        for selector in ["//button[contains(text(), 'Log in')]", "//button[@type='submit' and not(contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue with'))]", "//button[contains(text(), 'Sign in')]"]:
            try:
                login_button = driver.find_element(By.XPATH, selector)
                if login_button.is_displayed():
                    try:
                        ActionChains(driver).move_to_element(login_button).pause(random.uniform(0.1, 0.3)).click().perform()
                    except:
                        login_button.click()
                    print("Login button clicked")
                    break
            except:
                continue
        
        # Wait for login to complete
        time.sleep(5)
        try:
            _close_non_patreon_windows(driver)
        except:
            pass
        try:
            _dismiss_popups(driver, wait, attempts=6)
        except:
            pass
        try:
            target_vanity = vanity_url or "https://www.patreon.com/c/kavi13?vanity=user"
            driver.get(target_vanity)
            time.sleep(4)
            try:
                _close_non_patreon_windows(driver)
            except:
                pass
            _dismiss_popups(driver, wait, attempts=6)
            page_text = (driver.page_source or "").lower()
            not_found = ("page not found" in page_text) or ("not found" in driver.title.lower())
            wrong_area = "/c/" not in driver.current_url.lower()
            if not_found or wrong_area:
                pass
        except:
            pass
        try:
            _switch_role(driver, 'Creator')
        except:
            pass
        
        # STEP 2: Handle the "Finish my page" popup
        print("\nStep 2: Looking for 'Finish my page' popup...")
        
        # Wait a bit for any popup to appear
        time.sleep(3)
        
        # Method 1: Try to find and click "Finish my page" button
        finish_button_found = False
        finish_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'finish my page')]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'finish my page')]",
            "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'finish my page')]",
            "//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'finish my page')]",
            "//*[text()='Finish my page']",
            "//*[contains(text(), 'Finish my page')]",
            "//button[.//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'finish my page')]]"
        ]
        
        for selector in finish_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        print(f"Found 'Finish my page' button with selector: {selector}")
                        print(f"Button text: {btn.text}")
                        
                        # Scroll into view
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(1)
                        
                        # Try regular click
                        try:
                            btn.click()
                            print("Clicked 'Finish my page' button")
                        except:
                            # Try JavaScript click
                            driver.execute_script("arguments[0].click();", btn)
                            print("Clicked 'Finish my page' button using JavaScript")
                        
                        finish_button_found = True
                        time.sleep(3)
                        break
                if finish_button_found:
                    break
            except:
                continue
        
        # Method 2: If button not found, look for any modal/popup and try to close it
        if not finish_button_found:
            print("\n'Finish my page' button not found with direct selectors. Looking for modals...")
            
            # Look for modal containers
            modal_selectors = [
                "//div[contains(@class, 'modal')]",
                "//div[contains(@class, 'popup')]",
                "//div[contains(@class, 'dialog')]",
                "//div[contains(@class, 'overlay')]",
                "//div[contains(@class, 'sc-') and contains(@class, 'Modal')]",
                "//div[contains(@class, 'sc-') and contains(@class, 'Dialog')]"
            ]
            
            for modal_selector in modal_selectors:
                try:
                    modals = driver.find_elements(By.XPATH, modal_selector)
                    for modal in modals:
                        if modal.is_displayed():
                            print(f"Found modal with selector: {modal_selector}")
                            
                            # Look for buttons inside the modal
                            modal_buttons = modal.find_elements(By.TAG_NAME, "button")
                            for btn in modal_buttons:
                                if btn.is_displayed():
                                    btn_text = btn.text.lower()
                                    print(f"Found button in modal with text: {btn.text}")
                                    
                                    # Check if it's a finish button
                                    if 'finish' in btn_text or 'continue' in btn_text or 'start' in btn_text:
                                        try:
                                            btn.click()
                                            print(f"Clicked modal button: {btn.text}")
                                            finish_button_found = True
                                            time.sleep(3)
                                            break
                                        except:
                                            pass
                                    # If no finish button, try close button
                                    elif 'close' in btn_text or 'x' in btn.text.lower():
                                        try:
                                            btn.click()
                                            print("Clicked close button on modal")
                                            time.sleep(2)
                                            break
                                        except:
                                            pass
                            
                            if finish_button_found:
                                break
                except:
                    continue
        
        # Method 3: Try clicking any visible "Finish" or "Continue" button
        if not finish_button_found:
            print("\nTrying to find any 'Finish' or 'Continue' button on page...")
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                try:
                    if btn.is_displayed():
                        btn_text = btn.text.lower()
                        if 'finish' in btn_text or 'continue' in btn_text or 'get started' in btn_text:
                            print(f"Found button with text: {btn.text}")
                            btn.click()
                            print(f"Clicked button: {btn.text}")
                            finish_button_found = True
                            time.sleep(3)
                            break
                except:
                    continue
        
        if finish_button_found:
            print("\nSuccessfully handled the popup!")
        else:
            print("\nCould not find 'Finish my page' popup. Continuing...")
        
        # STEP 3: Navigate to creator page (only if not already there)
        print("\nStep 3: Navigating to creator page...")
        creator_urls = [
            "https://www.patreon.com/creator/home",
            "https://www.patreon.com/creator-home",
            "https://www.patreon.com/create"
        ]
        if not _on_creator_area(driver):
            for url in creator_urls:
                try:
                    driver.get(url)
                    print(f"Navigated to: {url}")
                    time.sleep(5)
                    if _on_creator_area(driver):
                        print("Successfully on creator page!")
                        break
                except:
                    continue
        
        if not _on_creator_area(driver):
            print("\nStep 4: Switching to Creator role...")
            time.sleep(2)
            try:
                _switch_role(driver, 'Creator')
            except:
                pass
            try:
                driver.get("https://www.patreon.com/creator/home")
                time.sleep(4)
            except:
                pass
        
        if not _on_creator_area(driver):
            print("\nStep 5: Clicking on Creator...")
            time.sleep(2)
            creator_found = False
            try:
                if _click_text(driver, "Creator"):
                    print("Clicked Creator")
                    creator_found = True
                    time.sleep(5)
                else:
                    for selector in [
                        "//footer//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator')]",
                        "//div[contains(@class, 'sidebar')]//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator')]",
                        "//a[contains(@href, '/creator')]",
                        "//nav//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator')]",
                        "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'creator') and @href]"
                    ]:
                        try:
                            links = driver.find_elements(By.XPATH, selector)
                            for link in links:
                                if link.is_displayed() and link.is_enabled():
                                    try:
                                        link.click()
                                    except:
                                        driver.execute_script("arguments[0].click();", link)
                                    print("Clicked Creator")
                                    creator_found = True
                                    time.sleep(5)
                                    break
                            if creator_found:
                                break
                        except:
                            continue
            except:
                pass
            if not creator_found:
                print("Creator link not found. Trying direct navigation...")
                driver.get("https://www.patreon.com/creator/home")
                time.sleep(5)
        try:
            _dismiss_popups(driver, wait, attempts=6)
        except:
            pass
        
        # STEP 6: Click Create button
        print("\nStep 6: Looking for Create button...")
        time.sleep(3)
        
        create_selectors = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create post')]",
            "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create post')]",
            "//button[@aria-label and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create') and not(contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'account'))]",
            "//a[contains(@href, '/post/new')]",
            "//a[contains(@href, '/creator/posts/create')]",
            "//aside//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')]",
            "//nav//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')]",
            "//*[contains(@data-test-id,'create')]",
            "//button[.//span[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create')]]"
        ]
        
        create_clicked = False
        for selector in create_selectors:
            try:
                create_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, selector)))
                for btn in create_buttons:
                    if btn.is_displayed():
                        btn.click()
                        print("Clicked Create button")
                        create_clicked = True
                        time.sleep(5)
                        break
                if create_clicked:
                    break
            except:
                continue
        
        if not create_clicked:
            print("Create button not found. Trying alternative...")
            try:
                driver.get("https://www.patreon.com/create")
                time.sleep(5)
                if _is_404(driver):
                    driver.get("https://www.patreon.com/creator/home")
                    time.sleep(5)
                for selector in create_selectors:
                    try:
                        btns = driver.find_elements(By.XPATH, selector)
                        for b in btns:
                            if b.is_displayed() and b.is_enabled():
                                b.click()
                                create_clicked = True
                                time.sleep(5)
                                break
                        if create_clicked:
                            break
                    except:
                        continue
            except:
                pass
        
        # STEP 7: Create post with title and body from blog.txt
        print("\nStep 7: Creating post...")
        time.sleep(3)
        
        # Dismiss popups on editor page
        try:
            _dismiss_popups(driver, wait, attempts=5)
            try:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass
        except:
            pass
        
        # Read blog content from file
        try:
            content_file = "body.txt" if os.path.exists("body.txt") else "blog.txt"
            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.strip().split('\n')
                title = lines[0] if lines else "Test Post"
                body = '\n'.join(lines[1:]) if len(lines) > 1 else "Test content"
                print(f"Read content from {content_file} - Title: {title[:50]}...")
        except:
            title = "Test Post Title"
            body = "This is a test post created by automation."
            print("Using default content as body.txt/blog.txt not found")
        
        # Enter title
        print("Entering title...")
        title_selectors = [
            "//textarea[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'title')]",
            "//input[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'title')]",
            "//textarea[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'title')]",
            "//input[@name='title']",
            "//textarea[@name='title']"
        ]
        
        for selector in title_selectors:
            try:
                title_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, selector)))
                if title_field.is_displayed():
                    title_field.clear()
                    title_field.send_keys(title)
                    print("Title entered")
                    time.sleep(2)
                    break
            except:
                continue
        
        # Enter body
        print("Entering body content...")
        body_selectors = [
            "//div[@contenteditable='true']",
            "//div[@role='textbox']",
            "//div[contains(@class, 'editor') and @contenteditable='true']",
            "//div[contains(@class, 'editor-content')]",
            "//div[contains(@class, 'post-content')]"
        ]
        
        for selector in body_selectors:
            try:
                body_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, selector)))
                body_field.click()
                time.sleep(1)
                
                body_field.send_keys(Keys.CONTROL + "a")
                body_field.send_keys(Keys.DELETE)
                time.sleep(1)
                parts = re.split(r'(\{.*?\})', body or "")
                just_pasted_image = False
                for part in parts:
                    if not part:
                        continue
                    m = re.match(r'^\{(.*)\}$', part)
                    if m:
                        rawp = m.group(1).strip()
                        resolved = _resolve_image_path(rawp)
                        if resolved and _copy_image_to_clipboard(resolved):
                            try:
                                target = body_field
                            except Exception:
                                target = body_field
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                            except Exception:
                                pass
                            try:
                                driver.execute_script("""
                                    try {
                                        var el = arguments[0];
                                        el.focus();
                                        var sel = window.getSelection();
                                        var range = document.createRange();
                                        range.selectNodeContents(el);
                                        range.collapse(false);
                                        sel.removeAllRanges();
                                        sel.addRange(range);
                                    } catch(e){}
                                """, target)
                            except Exception:
                                pass
                            ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(1.0)
                            try:
                                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                                time.sleep(0.1)
                                ActionChains(driver).send_keys(Keys.ENTER).perform()
                            except:
                                pass
                            time.sleep(0.2)
                            just_pasted_image = True
                        else:
                            if just_pasted_image:
                                part = part.lstrip('\n')
                                just_pasted_image = False
                            if part:
                                _type_text_with_links(driver, body_field, part)
                    else:
                        if just_pasted_image:
                            part = part.lstrip('\n')
                            just_pasted_image = False
                        if part:
                            _type_text_with_links(driver, body_field, part)
                print("Body content entered")
                time.sleep(2)
                break
            except:
                continue
        
        # STEP 8: Click Publish button (upper right side)
        print("\nStep 8: Looking for Publish button...")
        time.sleep(2)
        
        publish_selectors = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'publish')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'publish post')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'update')]",
            "//button[@type='submit' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'publish')]",
            "//button[@aria-label and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'publish')]"
        ]
        
        publish_clicked = False
        for selector in publish_selectors:
            try:
                publish_buttons = driver.find_elements(By.XPATH, selector)
                for btn in publish_buttons:
                    if btn.is_displayed():
                        btn.click()
                        print("Clicked Publish button")
                        publish_clicked = True
                        time.sleep(5)
                        break
                if publish_clicked:
                    break
            except:
                continue
        
        if publish_clicked:
            try:
                _confirm_publish(driver)
            except:
                pass
        if publish_clicked and _verify_published(driver, title):
            print("\n" + "="*50)
            print("SUCCESS: Post published and verified")
            print("="*50)
            try:
                screenshot_path = f"patreon_post_published_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved: {screenshot_path}")
            except:
                pass
        else:
            print("\nERROR: Publish not verified")
        
        try:
            driver.get("https://www.patreon.com/home")
            time.sleep(3)
            try:
                _close_non_patreon_windows(driver)
            except:
                pass
        except:
            pass
        
        if wait_for_enter:
            try:
                input("\nPress Enter to close the browser...")
            except:
                pass
    
    except Exception as e:
        print(f"\nERROR: {e}")
        try:
            driver.save_screenshot("patreon_error.png")
            print("Saved error screenshot as patreon_error.png")
        except:
            pass
    finally:
        driver.quit()

# Run the automation
if __name__ == "__main__":
    print("Patreon Automation Script")
    print("="*30)
    
    # Get credentials
    email = input("Enter your Patreon email: ").strip()
    password = input("Enter your Patreon password: ").strip()
    
    # Optional: If you have a vanity URL
    vanity_url = input("Enter your vanity URL (optional, press Enter to skip): ").strip()
    if not vanity_url:
        vanity_url = None
    use_profile_ans = input("Use existing Chrome profile to stay logged in? (y/N): ").strip().lower()
    use_profile = use_profile_ans == "y"
    profile_path = None
    profile_dir = "Default"
    if use_profile:
        auto_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
        print(f"Auto-detected profile dir: {auto_path}")
        p = input("Enter profile directory path (or press Enter to use auto-detected): ").strip()
        if p:
            profile_path = p
        else:
            profile_path = auto_path
        d = input("Enter profile directory name (Default/Profile 1/etc.) [Default]: ").strip()
        if d:
            profile_dir = d
    print("\nStarting automation...")
    hold_ans = input("Hold the browser open until you press Enter? (y/N): ").strip().lower()
    wait_for_enter = hold_ans == "y"
    automate_patreon(email, password, vanity_url, use_profile=use_profile, profile_path=profile_path, profile_dir=profile_dir, wait_for_enter=wait_for_enter)
