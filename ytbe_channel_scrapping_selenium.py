from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import pandas as pd
from datetime import datetime

from selenium.webdriver.chrome.options import Options

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--start-maximized')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

# Add undetected characteristics
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

channel_url = "https://www.youtube.com/@MrBeast/"
driver.get(channel_url)

# Wait for initial page load
time.sleep(5)

# Initialize variables
channel_name = "Unknown Channel"
sub_count = "Unknown Subscribers"

try:
    print("=== ATTEMPTING TO EXTRACT CHANNEL INFORMATION ===")
    
    # METHOD 1: Try multiple selectors for channel name
    channel_selectors = [
        "#text.ytd-channel-name",
        "yt-formatted-string#channel-name",
        "#channel-name yt-formatted-string",
        "ytd-channel-name yt-formatted-string",
        # Alternative selectors
        "ytd-c4-tabbed-header-renderer #channel-name",
        "#inner-header-container yt-formatted-string",
        "yt-formatted-string[has-link-only_]:not([is-empty])"
    ]
    
    for selector in channel_selectors:
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            # Wait for element to have text content
            WebDriverWait(driver, 5).until(
                lambda driver: element.text.strip() != ""
            )
            if element.text.strip():
                channel_name = element.text.strip()
                print(f"✓ CHANNEL NAME FOUND: {channel_name} (using: {selector})")
                break
        except:
            continue
    
    # METHOD 2: If still not found, extract from video metadata
    if channel_name == "Unknown Channel":
        print("Trying to extract channel name from video metadata...")
        try:
            videos = driver.find_elements(By.CSS_SELECTOR, "ytd-rich-grid-media")[:3]
            for video in videos:
                try:
                    channel_element = video.find_element(By.CSS_SELECTOR, "ytd-channel-name yt-formatted-string")
                    if channel_element.text.strip():
                        channel_name = channel_element.text.strip()
                        print(f"✓ CHANNEL NAME FROM VIDEO: {channel_name}")
                        break
                except:
                    continue
        except:
            pass
    
    # METHOD 3: Extract from page title or URL as last resort
    if channel_name == "Unknown Channel":
        page_title = driver.title
        if " - YouTube" in page_title:
            channel_name = page_title.split(" - YouTube")[0]
            print(f"✓ CHANNEL NAME FROM PAGE TITLE: {channel_name}")
        else:
            # Extract from URL
            channel_name = channel_url.split("@")[-1].split("/")[0]
            print(f"✓ CHANNEL NAME FROM URL: {channel_name}")

    # METHOD 4: Multiple approaches for subscriber count
    sub_selectors = [
        "yt-formatted-string#subscriber-count",
        "#subscriber-count",
        "[id*='subscriber']",
        "ytd-c4-tabbed-header-renderer yt-formatted-string",
        # YouTube often uses these patterns
        "span#subscriber-count",
        ".ytd-c4-tabbed-header-renderer yt-formatted-string",
        "[aria-label*='subscriber']"
    ]
    
    for selector in sub_selectors:
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if element.text.strip():
                sub_count = element.text.strip()
                print(f"✓ SUBSCRIBER COUNT FOUND: {sub_count} (using: {selector})")
                break
        except:
            continue
    
    # METHOD 5: If subscriber count not found, try searching in all text elements
    if sub_count == "Unknown Subscribers":
        print("Searching for subscriber count in all text elements...")
        try:
            all_elements = driver.find_elements(By.TAG_NAME, "yt-formatted-string")
            for element in all_elements:
                text = element.text.strip()
                if "subscriber" in text.lower() and any(char.isdigit() for char in text):
                    sub_count = text
                    print(f"✓ SUBSCRIBER COUNT FOUND IN TEXT: {sub_count}")
                    break
        except:
            pass

except Exception as e:
    print(f"Error extracting channel information: {str(e)}")

print(f"\n=== FINAL CHANNEL INFORMATION ===")
print(f"Channel: {channel_name}")
print(f"Subscribers: {sub_count}")

# Continue with video extraction (your existing code)
print("\n=== EXTRACTING VIDEO DATA ===")

# Scroll to bottom of page to load all videos
print("Scrolling to load all videos...")
last_height = driver.execute_script("return document.documentElement.scrollHeight")
scroll_attempts = 0
max_scroll_attempts = 10

while scroll_attempts < max_scroll_attempts:
    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
    time.sleep(2)
    new_height = driver.execute_script("return document.documentElement.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height
    scroll_attempts += 1

print(f"Scrolling completed after {scroll_attempts} attempts")

# Create a list to store video data
video_data = []

try:
    # Get video data with updated selector
    videos = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-rich-grid-media"))
    )
    print(f"Found {len(videos)} videos")
    
    for i, video in enumerate(videos):
        try:
            # Get title
            title_element = video.find_element(By.ID, "video-title")
            title = title_element.text
            
            # Get metadata (views, upload date)
            metadata = video.find_elements(By.CSS_SELECTOR, "#metadata-line span")
            if len(metadata) >= 2:
                view_count = metadata[0].text.split(' ')[0]  # First span contains views
                upload_date = metadata[1].text  # Second span contains upload date
            else:
                view_count = "N/A"
                upload_date = "N/A"
            
            # Get video URL - improved method
            video_url = title_element.get_attribute("href")
            if not video_url:
                # Alternative method to get URL
                try:
                    video_url = video.find_element(By.CSS_SELECTOR, "a#thumbnail").get_attribute("href")
                except:
                    video_url = "N/A"
            
            # Store data
            video_data.append({
                'title': title,
                'views': view_count,
                'upload_date': upload_date,
                'url': video_url
            })
            
            print(f"Video {i+1}: {title}")
            print(f"Views: {view_count}")
            print(f"Upload Date: {upload_date}")
            print(f"URL: {video_url}")
            print("-" * 50)
            
        except (NoSuchElementException, IndexError) as e:
            print(f"Error extracting video {i+1}: {str(e)}")
            continue

except Exception as e:
    print(f"Error in video extraction: {str(e)}")

# Save data to CSV
try:
    if video_data:
        df = pd.DataFrame(video_data)
        # Clean channel name for filename
        clean_channel_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_data_{clean_channel_name}_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"\nData saved to {filename}")
        print(f"Total videos extracted: {len(video_data)}")
    else:
        print("No video data to save")
except Exception as e:
    print(f"Error saving data: {str(e)}")

driver.quit()