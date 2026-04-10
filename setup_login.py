import undetected_chromedriver as uc
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_login():
    print("=" * 60)
    print("🔐 TUMBLR LOGIN SETUP")
    print("=" * 60)
    print("This script opens the automation browser so you can log in manually.")
    print("Once logged in, your session will be saved for the main bot.")
    print("=" * 60)

    try:
        cwd = os.getcwd()
        profile_path = os.path.join(cwd, "automation_profile")
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
            
        logger.info(f"📁 Using automation profile: {profile_path}")
        
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument(f'--user-data-dir={profile_path}')
        
        print("\n🚀 Launching Chrome...")
        driver = uc.Chrome(options=options, use_subprocess=True, headless=False)
        
        print("\n🌐 Navigating to Tumblr...")
        driver.get("https://www.tumblr.com/login")
        
        print("\n" + "=" * 60)
        print("⚡ ACTION REQUIRED ⚡")
        print("Please log in to Tumblr in the opened Chrome window.")
        print("You have 120 seconds...")
        print("=" * 60)
        
        # Wait loop to check for login
        for i in range(120):
            try:
                if "dashboard" in driver.current_url or "home" in driver.current_url:
                    print("\n✅ LOGIN DETECTED! (Found 'dashboard' or 'home' in URL)")
                    print("Saving session...")
                    time.sleep(5) # Give time for cookies to settle
                    break
            except:
                pass
            time.sleep(1)
            if i % 10 == 0:
                print(f"Waiting... ({120-i}s left)")
        
        print("\n👋 Closing browser. You can now run the main script!")
        driver.quit()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        input("Press Enter to close...")

if __name__ == "__main__":
    setup_login()
