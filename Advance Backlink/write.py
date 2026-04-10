from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import os
import time
from datetime import datetime

def run(driver, website, email, username, password):
    try:
        driver.maximize_window()
        def is_login_error():
            try:
                return len(driver.find_elements(By.XPATH, "//*[contains(translate(normalize-space(string(.)),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'error logging in')]")) > 0
            except Exception:
                return False
        def is_logged_in():
            try:
                return len(driver.find_elements(By.XPATH, "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')] | //a[contains(@href,'logout')]")) > 0
            except Exception:
                return False
        def attempt_login(login_value):
            try:
                # Find form and submit button
                try:
                    submit_el = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='submit' and (@value='Login' or @value='Log In')]"))
                    )
                    form_el = submit_el.find_element(By.XPATH, "./ancestor::form")
                except TimeoutException:
                    form_el = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//form[.//input[@type='password']]"))
                    )
                    try:
                        submit_el = form_el.find_element(By.XPATH, ".//input[@type='submit' or self::button]")
                    except Exception:
                        submit_el = None
                user_el = form_el.find_element(By.XPATH, ".//input[@type='text' or @type='email']")
                pass_el = form_el.find_element(By.XPATH, ".//input[@type='password']")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", user_el)
                try: user_el.clear()
                except: pass
                user_el.send_keys(login_value)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pass_el)
                try: pass_el.clear()
                except: pass
                pass_el.send_keys(password)
                # Click submit
                if submit_el:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_el)
                    try:
                        submit_el.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", submit_el)
                else:
                    # Fallback: press Enter in password field
                    pass_el.send_keys(Keys.ENTER)
                # Wait for either success or error
                try:
                    WebDriverWait(driver, 10).until(lambda d: is_logged_in() or is_login_error())
                except Exception:
                    pass
                if is_logged_in():
                    return True
                return False
            except Exception:
                return False
        if not website:
            website = "https://www.writerscafe.org/login"
        if "writerscafe.org" not in website.lower():
            website = "https://www.writerscafe.org/login"
        print("Navigating to login page...")
        driver.get(website)
        print("Logging in...")
        # Attempt login with username first, then email if error shown
        login_primary = (username or "").strip() or (email or "").strip()
        login_secondary = (email or "").strip() if login_primary != (email or "").strip() else ""
        ok_login = attempt_login(login_primary)
        if not ok_login and is_login_error() and login_secondary:
            print("Retrying login with email...")
            ok_login = attempt_login(login_secondary)
        if not ok_login:
            print("Login failed.")
            raise Exception("WritersCafe login failed")
        print("Navigating to blog creation page...")
        uname = (username or (email.split('@')[0] if email else '')).strip()
        driver.get(f"https://www.writerscafe.org/{uname}/blogs/new/")
        time.sleep(3)
        print("Reading data from blog.txt...")
        blog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog.txt")
        try:
            with open(blog_path, 'r', encoding='utf-8') as file:
                blog_content = file.read()
        except Exception:
            blog_content = "Automated Blog\nHello from automation."
        lines = blog_content.strip().split('\n')
        blog_title = lines[0] if len(lines) > 0 else "New Blog"
        blog_body = '\n'.join(lines[1:]) if len(lines) > 1 else blog_content
        print("Filling title...")
        try:
            form = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.XPATH, "//form[.//input[@type='submit' and contains(@value,'Save')]]"))
            )
        except TimeoutException:
            form = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.XPATH, "//form"))
            )
        try:
            title_field = form.find_element(By.XPATH, ".//label[normalize-space()='Title']/following::*[self::input or self::textarea][1]")
        except Exception:
            inputs = form.find_elements(By.XPATH, ".//input[@type='text' and not(@disabled)]")
            if inputs:
                title_field = inputs[0]
            else:
                title_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@name,'title') or contains(@id,'title')]"))
                )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_field)
        title_field.click()
        try:
            title_field.clear()
        except Exception:
            pass
        title_field.send_keys(Keys.CONTROL, "a")
        title_field.send_keys(Keys.DELETE)
        title_field.send_keys(blog_title)
        try:
            driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", title_field, blog_title)
        except Exception:
            pass
        print("Filling content...")
        try:
            content_field = form.find_element(By.XPATH, ".//label[normalize-space()='Text']/following::textarea[1]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content_field)
            try:
                content_field.clear()
            except Exception:
                pass
            content_field.send_keys(Keys.CONTROL, "a")
            content_field.send_keys(Keys.DELETE)
            content_field.send_keys(blog_body)
            try:
                driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", content_field, blog_body)
            except Exception:
                pass
        except Exception:
            try:
                content_field = form.find_element(By.XPATH, ".//textarea[not(@disabled)]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content_field)
                try:
                    content_field.clear()
                except Exception:
                    pass
                content_field.send_keys(Keys.CONTROL, "a")
                content_field.send_keys(Keys.DELETE)
                content_field.send_keys(blog_body)
                try:
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", content_field, blog_body)
                except Exception:
                    pass
            except Exception:
                iframes = form.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    driver.switch_to.frame(iframes[0])
                    try:
                        editable = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.XPATH, "//*[@contenteditable='true' or self::body]"))
                        )
                        editable.click()
                        editable.send_keys(Keys.CONTROL, "a")
                        editable.send_keys(Keys.DELETE)
                        editable.send_keys(blog_body)
                    finally:
                        driver.switch_to.default_content()
                else:
                    driver.execute_script("document.querySelector('textarea')?.value = arguments[0];", blog_body)
        print("Adding tags...")
        try:
            tags_field = driver.find_element(By.ID, "tags")
            tags_field.send_keys("Writing, Blogging, Journals, Notebooks")
        except Exception:
            try:
                tags_field = driver.find_element(By.NAME, "blog[tags]")
                tags_field.send_keys("Writing, Blogging, Journals, Notebooks")
            except Exception:
                print("Tags field not found, skipping...")
        print("Saving blog...")
        try:
            save_button = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//label[normalize-space()='Photo']/following::*[self::input or self::button][contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')][1]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", save_button)
            save_button.click()
        except TimeoutException:
            try:
                save_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and contains(@value,'Save')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView();", save_button)
                save_button.click()
            except TimeoutException:
                try:
                    save_button = driver.find_element(By.XPATH, "//button[normalize-space()='Save' or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]")
                    driver.execute_script("arguments[0].scrollIntoView();", save_button)
                    save_button.click()
                except Exception:
                    driver.execute_script("document.querySelector('input[type=\"submit\"]')?.click();")
        time.sleep(5)
        try:
            WebDriverWait(driver, 20).until(lambda d: "blogs" in d.current_url and "new" not in d.current_url)
            print("Blog posted successfully!")
            return True
        except TimeoutException:
            print("Blog submission may not have completed.")
            return False
    except Exception as e:
        print(f"Error occurred: {e}")
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
            os.makedirs(base_dir, exist_ok=True)
            path = os.path.join(base_dir, f"writerscafe_error_{ts}.png")
            driver.save_screenshot(path)
            print(f"Saved screenshot to {path}")
        except Exception as se:
            print(f"Failed to save screenshot: {se}")
        return False
