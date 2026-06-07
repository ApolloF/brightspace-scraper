import os
import re
import sys
import io
import urllib.parse
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Reconfigure standard output streams to handle Unicode characters safely on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# Load configuration
load_dotenv()
BRIGHTSPACE_BASE_URL = os.getenv("BRIGHTSPACE_BASE_URL", "https://brightspace.rug.nl").rstrip("/")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")
AUTH_STATE_PATH = "auth_state.json"

def sanitize_name(name):
    """
    Sanitizes file and folder names for Windows compatibility.
    """
    # Replace characters that are invalid in Windows paths: < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    # Strip leading/trailing spaces and dots
    sanitized = sanitized.strip().strip('.')
    # Fallback if empty
    return sanitized if sanitized else "unnamed"

def get_extension_from_url(url):
    """
    Extracts the file extension from a URL if possible.
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    _, ext = os.path.splitext(path)
    return ext.lower() if ext else ""

def get_extension_from_content_type(content_type):
    """
    Maps a MIME Content-Type to a file extension.
    """
    ct = content_type.lower()
    if "pdf" in ct:
        return ".pdf"
    elif "msword" in ct or "officedocument.word" in ct:
        return ".docx"
    elif "powerpoint" in ct or "officedocument.presentation" in ct or "ms-powerpoint" in ct:
        return ".pptx"
    elif "excel" in ct or "officedocument.spreadsheet" in ct or "ms-excel" in ct:
        return ".xlsx"
    elif "zip" in ct:
        return ".zip"
    elif "html" in ct:
        return ".html"
    return ""

def parse_content_disposition(header):
    """
    Parses the filename from the Content-Disposition header.
    Example: attachment; filename="lecture1.pdf"
    """
    if not header:
        return None
    
    # Try filename* (UTF-8 encoding)
    utf8_match = re.search(r"filename\*=UTF-8''([^;\n]+)", header, re.IGNORECASE)
    if utf8_match:
        val = urllib.parse.unquote(utf8_match.group(1))
        return sanitize_name(val)
        
    # Try normal filename
    normal_match = re.search(r'filename="?([^";\n]+)"?', header, re.IGNORECASE)
    if normal_match:
        return sanitize_name(normal_match.group(1))
        
    return None

async def scrape_and_download_html_links(request_context, html_content, dest_dir):
    """
    Extracts enforced-content and coursefile links from an HTML string,
    then downloads each discovered file to dest_dir.
    Handles both relative (/content/enforced/...) and absolute (https://...) URLs.
    """
    links = re.findall(r'href="([^"]+)"', html_content) + re.findall(r"href='([^']+)'", html_content)
    
    for link in links:
        # Normalize HTML entities
        normalized = link.replace("&amp;", "&")
        
        is_coursefile = "type=coursefile" in normalized
        is_enforced = "/content/enforced/" in normalized
        
        if not (is_coursefile or is_enforced):
            continue
        
        # Determine filename from the URL
        filename = None
        if is_coursefile:
            parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(normalized).query)
            file_ids = parsed_qs.get("fileId") or parsed_qs.get("fileid")
            if file_ids:
                # fileId may be a path like "Author/Week 1/filename.pdf" - take the basename
                raw_name = urllib.parse.unquote(file_ids[0])
                filename = sanitize_name(os.path.basename(raw_name))
        elif is_enforced:
            parsed_path = urllib.parse.urlparse(normalized).path
            raw_name = urllib.parse.unquote(parsed_path)
            filename = sanitize_name(os.path.basename(raw_name))
        
        if not filename or filename == "unnamed":
            continue
        
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            response = await request_context.get(normalized, timeout=600000)
            if response.status == 200:
                content = await response.body()
                content_size = len(content)
                
                # If filename has no extension, try to determine one from the response
                if not os.path.splitext(filename)[1]:
                    cd_header = response.headers.get("content-disposition", "")
                    cd_filename = parse_content_disposition(cd_header)
                    if cd_filename and os.path.splitext(cd_filename)[1]:
                        filename = cd_filename
                    else:
                        ext = get_extension_from_url(normalized)
                        if not ext:
                            ext = get_extension_from_content_type(response.headers.get("content-type", ""))
                        if ext:
                            filename = filename + ext
                    dest_path = os.path.join(dest_dir, filename)
                
                # Check if file exists and has same size
                if os.path.exists(dest_path) and os.path.getsize(dest_path) == content_size:
                    continue
                os.makedirs(dest_dir, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(content)
                print(f"  [Scraped Download] {filename} ({content_size / 1024:.1f} KB)")
            else:
                print(f"  [Warning] HTTP {response.status} for scraped link: {filename}")
        except Exception as e:
            print(f"  [Warning] Failed to download scraped link '{filename}': {e}")

async def download_topic(request_context, course_id, topic, course_dir):
    """
    Downloads a single file topic from Brightspace.
    If the topic is a small HTML redirect/wrapper page, also scrapes it for
    embedded enforced-content/coursefile links and downloads those files too.
    """
    topic_id = topic.get("TopicId")
    topic_title = topic.get("Title", f"topic_{topic_id}")
    topic_url = topic.get("Url", "")
    
    # constructed API endpoint to fetch the topic file
    download_url = f"/d2l/api/le/1.26/{course_id}/content/topics/{topic_id}/file"
    
    try:
        # Perform GET request to download the file (with 10-minute timeout for large files)
        response = await request_context.get(download_url, timeout=600000)
        if response.status != 200:
            print(f"  [Failed] HTTP {response.status} for topic: {topic_title}")
            return
            
        # Determine the filename
        # 1. Try Content-Disposition header
        cd_header = response.headers.get("content-disposition")
        filename = parse_content_disposition(cd_header)
        
        # 2. Fall back to topic Title + extension from Url or Content-Type
        if not filename:
            ext = get_extension_from_url(topic_url)
            if not ext:
                ext = get_extension_from_content_type(response.headers.get("content-type", ""))
            filename = sanitize_name(topic_title) + ext
            
        dest_path = os.path.join(course_dir, filename)
        
        # Read the file contents
        content = await response.body()
        content_size = len(content)
        
        # Check if file already exists locally and has the same size
        if os.path.exists(dest_path):
            local_size = os.path.getsize(dest_path)
            if local_size == content_size:
                # Same file size, skip download to optimize speed and network
                pass
            else:
                # Overwrite changed file
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(content)
                print(f"  [Downloaded] {filename} ({content_size / 1024:.1f} KB)")
        else:
            # Write new file
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(content)
            print(f"  [Downloaded] {filename} ({content_size / 1024:.1f} KB)")
        
        # If the topic is a small HTML redirect/wrapper page, also scrape it for
        # embedded links to actual course files (e.g. /content/enforced/ or coursefile links).
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type and content_size < 50000:
            html_text = content.decode("utf-8", errors="replace")
            await scrape_and_download_html_links(request_context, html_text, course_dir)
        
    except Exception as e:
        print(f"  [Error] Failed to download topic {topic_title} ({topic_id}): {e}")

async def walk_module(request_context, course_id, module, current_path):
    """
    Recursively walks the TOC module hierarchy and downloads file topics.
    """
    # Create the directory for the current module level
    os.makedirs(current_path, exist_ok=True)
    
    # 1. Download files directly in this module
    topics = module.get("Topics", [])
    for topic in topics:
        # TypeIdentifier "File" or ActivityType 1 represents a File topic (e.g. PDF, Word, PowerPoint)
        if topic.get("TypeIdentifier") == "File" or topic.get("ActivityType") == 1:
            await download_topic(request_context, course_id, topic, current_path)
            
    # 1.5. Scrape and download files linked in the module's description HTML
    # (e.g. quicklinks or /content/enforced/ paths embedded by instructors)
    desc_dict = module.get("Description")
    if desc_dict and desc_dict.get("Html"):
        await scrape_and_download_html_links(request_context, desc_dict.get("Html"), current_path)
            
    # 2. Traverse submodules recursively
    sub_modules = module.get("Modules", [])
    for sub_mod in sub_modules:
        sub_mod_title = sanitize_name(sub_mod.get("Title", "Untitled Module"))
        sub_path = os.path.join(current_path, sub_mod_title)
        await walk_module(request_context, course_id, sub_mod, sub_path)

async def sync_files():
    """
    Fetches all active courses and syncs their table of contents files to the local folder.
    """
    if not os.path.exists(AUTH_STATE_PATH):
        print(f"[ERROR] Session state file '{AUTH_STATE_PATH}' not found.")
        print("Please run `python sync.py login` first to log in and create this session.")
        return False
        
    print("Initializing sync process...")
    async with async_playwright() as p:
        try:
            # Create a request context with stored cookies
            request_context = await p.request.new_context(
                base_url=BRIGHTSPACE_BASE_URL,
                storage_state=AUTH_STATE_PATH
            )
            
            # 1. Fetch courses
            print("Fetching enrollments...")
            courses = []
            url = "/d2l/api/lp/1.26/enrollments/myenrollments/"
            
            while url:
                response = await request_context.get(url)
                if response.status != 200:
                    print(f"[ERROR] Failed to fetch enrollments (HTTP {response.status}). Session may have expired.")
                    print("Please run `python sync.py login` to refresh your login state.")
                    return False
                    
                data = await response.json()
                for item in data.get("Items", []):
                    org_unit = item.get("OrgUnit", {})
                    access = item.get("Access", {})
                    # Type ID 3 represents Course Offerings
                    if org_unit.get("Type", {}).get("Id") == 3 and access.get("CanAccess", True):
                        courses.append({
                            "id": org_unit.get("Id"),
                            "name": org_unit.get("Name"),
                            "code": org_unit.get("Code")
                        })
                
                # Check for next page of enrollments
                url = data.get("Next")
                if url and url.startswith(BRIGHTSPACE_BASE_URL):
                    url = url[len(BRIGHTSPACE_BASE_URL):]
            
            print(f"Found {len(courses)} active course(s). Starting content sync...")
            
            # Create root downloads directory
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            
            # 2. Sync each course
            for course in courses:
                course_id = course["id"]
                course_name = sanitize_name(course["name"])
                print(f"\nSyncing: {course['name']} ({course['code']})")
                
                course_dir = os.path.join(DOWNLOADS_DIR, course_name)
                
                # Fetch Table of Contents for this course
                toc_url = f"/d2l/api/le/1.26/{course_id}/content/toc"
                toc_response = await request_context.get(toc_url)
                
                if toc_response.status != 200:
                    print(f"  [Warning] Could not fetch Table of Contents (HTTP {toc_response.status})")
                    continue
                    
                toc_data = await toc_response.json()
                
                # Walk the TOC modules and download files
                modules = toc_data.get("Modules", [])
                for module in modules:
                    mod_title = sanitize_name(module.get("Title", "Untitled Module"))
                    mod_path = os.path.join(course_dir, mod_title)
                    await walk_module(request_context, course_id, module, mod_path)
                    
            print("\nFile sync complete!")
            return True
            
        except Exception as e:
            print(f"\n[ERROR] An error occurred during file sync: {e}")
            return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(sync_files())
