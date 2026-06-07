import os
import json
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load configuration
load_dotenv()
BRIGHTSPACE_BASE_URL = os.getenv("BRIGHTSPACE_BASE_URL", "https://brightspace.rug.nl").rstrip("/")
AUTH_STATE_PATH = "auth_state.json"

async def login():
    """
    Opens a headed browser window for the user to log in manually via SSO/MFA.
    Saves the authentication state once login is detected.
    """
    print("=" * 60)
    print("BRIGHTSPACE LOGIN INITIALIZATION")
    print("=" * 60)
    print("Starting a headed browser session...")
    print("Please enter your RUG credentials and complete the MFA challenge in the browser window.")
    print("Once you successfully log in and reach the home dashboard, this script will automatically")
    print("save your login session and close.")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch headed browser so the user can interact with the page
        browser = await p.chromium.launch(headless=False)
        # Create a new page context
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the Brightspace home page (redirects to SSO login page)
        print(f"Navigating to {BRIGHTSPACE_BASE_URL}...")
        await page.goto(BRIGHTSPACE_BASE_URL)
        
        # Wait until the user has successfully logged in and is redirected to /d2l/home
        try:
            # We wait up to 5 minutes (300,000 ms) for login to complete
            await page.wait_for_url("**/d2l/home*", timeout=300000)
            print("Login success detected! Saving session cookies...")
            
            # Save the storage state (cookies, localStorage, etc.)
            await context.storage_state(path=AUTH_STATE_PATH)
            print(f"Session cookies saved successfully to '{AUTH_STATE_PATH}'.")
            
        except asyncio.TimeoutError:
            print("\n[ERROR] Login timed out. Please complete the login process within 5 minutes.")
        except Exception as e:
            print(f"\n[ERROR] An error occurred during login: {e}")
        finally:
            await browser.close()

async def check_auth() -> bool:
    """
    Checks if there is a saved session and if it is still valid by hitting the whoami API endpoint.
    """
    if not os.path.exists(AUTH_STATE_PATH):
        return False
    
    async with async_playwright() as p:
        try:
            # Create an APIRequestContext using the saved cookies
            request_context = await p.request.new_context(
                base_url=BRIGHTSPACE_BASE_URL,
                storage_state=AUTH_STATE_PATH
            )
            
            # Hit the Valence API whoami endpoint
            response = await request_context.get("/d2l/api/lp/1.26/users/whoami")
            if response.status == 200:
                data = await response.json()
                if "Identifier" in data:
                    print(f"Authenticated as: {data.get('DisplayName', 'Unknown User')} ({data.get('UniqueName', 'Unknown')})")
                    return True
            return False
        except Exception as e:
            print(f"Auth check failed with error: {e}")
            return False

if __name__ == "__main__":
    # Test script directly
    asyncio.run(login())
