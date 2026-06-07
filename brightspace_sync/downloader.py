import os
import re
import sys
import io
import urllib.parse
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Reconfigure standard output streams to handle Unicode characters safely on Windows console
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


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

async def download_topic(request_context, course_id, topic, course_dir):
    """
    Downloads a single file topic from Brightspace.
    """
    topic_id = topic.get("TopicId")
    topic_title = topic.get("Title", f"topic_{topic_id}")
    topic_url = topic.get("Url", "")
    
    # constructed API endpoint to fetch the topic file
    download_url = f"/d2l/api/le/1.26/{course_id}/content/topics/{topic_id}/file"
    
    try:
        # Perform GET request to download the file
        response = await request_context.get(download_url)
        if response.status != 200:
            print(f"  [Failed] HTTP {response.status} for topic: {topic_title}")
            return
            
        # Determine the filename
        # 1. Try Content-Disposition header
        cd_header = response.headers.get("content-disposition")
        filename = parse_content_disposition(cd_header)
        
        # 2. Fall back to topic Title + extension from Url
        if not filename:
            ext = get_extension_from_url(topic_url)
            # If no extension in URL, try mapping Content-Type
            if not ext:
                content_type = response.headers.get("content-type", "").lower()
                if "pdf" in content_type:
                    ext = ".pdf"
                elif "msword" in content_type or "officedocument.word" in content_type:
                    ext = ".docx"
                elif "powerpoint" in content_type or "officedocument.presentation" in content_type:
                    ext = ".pptx"
                elif "excel" in content_type or "officedocument.spreadsheet" in content_type:
                    ext = ".xlsx"
                elif "zip" in content_type:
                    ext = ".zip"
                elif "html" in content_type:
                    ext = ".html"
            
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
                return
                
        # Write/Overwrite file
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)
            
        print(f"  [Downloaded] {filename} ({content_size / 1024:.1f} KB)")
        
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
