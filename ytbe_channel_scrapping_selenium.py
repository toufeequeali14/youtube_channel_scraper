from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import pandas as pd
from datetime import datetime
import re

from selenium.webdriver.chrome.options import Options

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

# Add undetected characteristics
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# =============================================================================
# CONFIGURATION - CHANGE THIS URL TO SCRAPE DIFFERENT CHANNELS
# =============================================================================
channel_url = "https://www.youtube.com/@MrBeast"
# =============================================================================

print("="*70)
print("YOUTUBE CHANNEL SCRAPER")
print("="*70)
print(f"Target Channel: {channel_url}")
print("="*70)

# Extract channel handle from URL
channel_handle = channel_url.rstrip('/').split('/')[-1]
print(f"Channel Handle: {channel_handle}\n")

# Initialize variables
channel_name = "Unknown Channel"
sub_count = "Unknown Subscribers"
channel_description = "No description available"
video_count = "Unknown"

def clean_text(text):
    """Clean and normalize text"""
    return ' '.join(text.split()).strip()

def extract_subscriber_count(text):
    """Extract subscriber count from text"""
    if not text or text == "Unknown Subscribers":
        return text
    # Remove any extra text and keep just the number + unit
    text = text.lower()
    match = re.search(r'([\d.]+\s*[kmb]?)\s*subscriber', text)
    if match:
        return match.group(1).strip()
    return text

# =============================================================================
# STEP 1: EXTRACT CHANNEL INFORMATION FROM ABOUT PAGE
# =============================================================================
print("\n" + "="*70)
print("STEP 1: EXTRACTING CHANNEL INFORMATION")
print("="*70)

try:
    # Navigate to About page
    about_url = f"https://www.youtube.com/{channel_handle}/about"
    print(f"Navigating to: {about_url}")
    driver.get(about_url)
    time.sleep(5)
    
    # Extract Channel Name from page title first
    page_title = driver.title
    if " - YouTube" in page_title:
        channel_name = page_title.replace(" - YouTube", "").strip()
        print(f"✓ Channel Name: {channel_name}")
    
    # Try to get channel name from header
    try:
        name_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-channel-name yt-formatted-string, #channel-name yt-formatted-string"))
        )
        if name_element.text.strip():
            channel_name = clean_text(name_element.text)
            print(f"✓ Channel Name (verified): {channel_name}")
    except:
        pass
    
    # Extract Subscriber Count
    print("\nSearching for subscriber count...")
    try:
        # Method 1: Look for subscriber count element
        sub_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#subscriber-count"))
        )
        sub_text = clean_text(sub_element.text)
        if sub_text:
            sub_count = extract_subscriber_count(sub_text)
            print(f"✓ Subscribers: {sub_count}")
    except:
        # Method 2: Search all text elements
        try:
            all_elements = driver.find_elements(By.TAG_NAME, "yt-formatted-string")
            for element in all_elements:
                text = clean_text(element.text)
                if "subscriber" in text.lower():
                    sub_count = extract_subscriber_count(text)
                    print(f"✓ Subscribers: {sub_count}")
                    break
        except:
            print("⚠ Could not find subscriber count")
    
    # Extract Channel Description
    print("\nSearching for channel description...")
    try:
        desc_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#description-container"))
        )
        desc_text = clean_text(desc_element.text)
        if desc_text and len(desc_text) > 10:
            channel_description = desc_text
            print(f"✓ Description: {channel_description[:100]}...")
    except:
        print("⚠ Could not find channel description")
    
    # Extract Statistics (videos, views, joined date)
    print("\nSearching for channel statistics...")
    try:
        # Look for the stats table
        stats_elements = driver.find_elements(By.CSS_SELECTOR, "#right-column yt-formatted-string")
        for element in stats_elements:
            text = clean_text(element.text)
            # Look for video count
            if "video" in text.lower() and not video_count.isdigit():
                match = re.search(r'([\d,]+)\s*video', text, re.IGNORECASE)
                if match:
                    video_count = match.group(1).replace(',', '')
                    print(f"✓ Total Videos: {video_count}")
    except:
        print("⚠ Could not find video count from About page")

except Exception as e:
    print(f"⚠ Error extracting channel information: {str(e)}")

# =============================================================================
# STEP 2: EXTRACT VIDEO DATA FROM VIDEOS TAB
# =============================================================================
print("\n" + "="*70)
print("STEP 2: EXTRACTING VIDEO DATA")
print("="*70)

try:
    # Navigate to Videos page
    videos_url = f"https://www.youtube.com/{channel_handle}/videos"
    print(f"Navigating to: {videos_url}")
    driver.get(videos_url)
    time.sleep(5)
    
    # Check if we're on the right page
    current_url = driver.current_url
    print(f"Current URL: {current_url}")
    
    if channel_handle not in current_url:
        print("⚠ Warning: Not on the expected channel page!")
    
    # Scroll to load videos
    print("\nScrolling to load videos...")
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    scroll_attempts = 0
    max_scroll_attempts = 20
    no_change_count = 0
    
    while scroll_attempts < max_scroll_attempts and no_change_count < 3:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(2.5)
        
        # Calculate new height
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        
        if new_height == last_height:
            no_change_count += 1
        else:
            no_change_count = 0
        
        last_height = new_height
        scroll_attempts += 1
        
        # Check how many videos are loaded so far
        try:
            current_videos = len(driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer"))
            print(f"Scroll {scroll_attempts}/{max_scroll_attempts} - Videos loaded: {current_videos}")
        except:
            print(f"Scroll {scroll_attempts}/{max_scroll_attempts}")
    
    print(f"✓ Scrolling complete!\n")
    
    # Extract video data
    video_data = []
    
    print("Extracting video information...")
    
    # Wait for videos to load
    video_elements = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-rich-item-renderer"))
    )
    
    print(f"Found {len(video_elements)} video elements\n")
    
    for i, video in enumerate(video_elements, 1):
        try:
            # Get title and URL
            title_element = video.find_element(By.CSS_SELECTOR, "#video-title-link, #video-title")
            title = clean_text(title_element.text)
            video_url = title_element.get_attribute("href")
            
            # Skip if no title
            if not title:
                continue
            
            # Get metadata (views and upload date)
            view_count = "N/A"
            upload_date = "N/A"
            
            try:
                metadata_elements = video.find_elements(By.CSS_SELECTOR, "#metadata-line span")
                if len(metadata_elements) >= 1:
                    view_count = clean_text(metadata_elements[0].text)
                if len(metadata_elements) >= 2:
                    upload_date = clean_text(metadata_elements[1].text)
            except:
                pass
            
            # Get duration
            duration = "N/A"
            try:
                duration_element = video.find_element(By.CSS_SELECTOR, "span.style-scope.ytd-thumbnail-overlay-time-status-renderer")
                duration = clean_text(duration_element.text)
            except:
                pass
            
            video_data.append({
                'channel_name': channel_name,
                'title': title,
                'views': view_count,
                'upload_date': upload_date,
                'duration': duration,
                'url': video_url
            })
            
            if i % 10 == 0:
                print(f"✓ Extracted {i} videos...")
        
        except Exception as e:
            continue
    
    print(f"\n✓ Total videos extracted: {len(video_data)}")

except Exception as e:
    print(f"⚠ Error extracting videos: {str(e)}")
    import traceback
    traceback.print_exc()

# Update video count if not found earlier
if video_count == "Unknown" and video_data:
    video_count = str(len(video_data))

# =============================================================================
# DISPLAY SUMMARY
# =============================================================================
print("\n" + "="*70)
print("CHANNEL SUMMARY")
print("="*70)
print(f"Channel Name:       {channel_name}")
print(f"Subscribers:        {sub_count}")
print(f"Total Videos:       {video_count}")
print(f"Videos Scraped:     {len(video_data)}")
print(f"Description Length: {len(channel_description)} characters")
print("="*70)

# =============================================================================
# SAVE DATA TO CSV FILES
# =============================================================================
print("\nSaving data...")

try:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_channel_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
    
    # Save video data
    if video_data:
        df = pd.DataFrame(video_data)
        video_filename = f"videos_{clean_channel_name}_{timestamp}.csv"
        df.to_csv(video_filename, index=False, encoding='utf-8-sig')
        print(f"✓ Video data saved: {video_filename}")
    else:
        print("⚠ No video data to save")
    
    # Save channel info
    channel_info = {
        'channel_name': [channel_name],
        'channel_handle': [channel_handle],
        'subscribers': [sub_count],
        'total_videos': [video_count],
        'videos_scraped': [len(video_data)],
        'description': [channel_description],
        'scraped_at': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'channel_url': [channel_url]
    }
    
    channel_df = pd.DataFrame(channel_info)
    channel_filename = f"channel_info_{clean_channel_name}_{timestamp}.csv"
    channel_df.to_csv(channel_filename, index=False, encoding='utf-8-sig')
    print(f"✓ Channel info saved: {channel_filename}")
    
except Exception as e:
    print(f"⚠ Error saving data: {str(e)}")
    import traceback
    traceback.print_exc()

# Close browser
driver.quit()
print("\n✓ Browser closed")
print("="*70)
print("SCRAPING COMPLETE!")
print("="*70)