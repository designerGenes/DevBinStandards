#!/usr/bin/env python3
import time
import typer
import requests
import shlex
from rich import print
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = typer.Typer()

def _find_media_url_selenium(page_url: str):
    """Internal function to find media URL using Selenium."""
    print("[bold cyan]Setting up headless browser...[/bold cyan]")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        print(f"[cyan]Navigating to {page_url}...[/cyan]")
        driver.get(page_url)
        
        print("[cyan]Waiting for page to load and media to start playing (10s)...[/cyan]")
        time.sleep(10)
        
        print("[cyan]Inspecting network requests for media files...[/cyan]")
        performance_entries = driver.execute_script("return window.performance.getEntries()")
        
        media_urls = []
        for entry in performance_entries:
            # More robust check for media files
            initiator_type = entry.get('initiatorType', '')
            content_type = entry.get('contentType', '')
            name = entry.get('name', '')
            
            is_media = False
            if 'video' in content_type or 'audio' in content_type:
                is_media = True
            elif name.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv')):
                is_media = True
            elif initiator_type == 'fetch' and 'video' in name:
                is_media = True

            if is_media:
                media_urls.append(name)
        
        if media_urls:
            # Return the last one found, often the most relevant
            return media_urls[-1]

        print("[yellow]No media requests found. Falling back to video tags...[/yellow]")
        video_elements = driver.find_elements("tag name", "video")
        if video_elements:
            src = video_elements[0].get_attribute('src')
            if src:
                return src
        
        return None
            
    except Exception as e:
        print(f"[bold red]An error occurred: {e}[/bold red]")
        return None
    finally:
        if driver:
            driver.quit()
        print("[bold cyan]Browser session closed.[/bold cyan]")

def _download_file(url: str, headers: dict):
    """Internal function to download a file with optional headers."""
    if not url:
        print("[bold red]No URL provided.[/bold red]")
        return

    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        
        filename = url.split('/')[-1].split('?')[0] # Clean filename
        
        with open(filename, 'wb') as f, tqdm(
            total=total_size, unit='iB', unit_scale=True, desc=filename, colour="green"
        ) as pbar:
            for data in response.iter_content(block_size):
                f.write(data)
                pbar.update(len(data))
                
        print(f"[bold green]Downloaded {filename}[/bold green]")

    except requests.exceptions.RequestException as e:
        print(f"[bold red]An error occurred during download: {e}[/bold red]")

@app.command()
def find(page_url: str):
    """
    Finds and prints the media URL from a webpage.
    """
    media_url = _find_media_url_selenium(page_url)
    if media_url:
        print(f"[bold green]Found media URL:[/] {media_url}")
    else:
        print("[bold red]Could not find a media URL on the page.[/bold red]")

@app.command()
def download(media_url: str):
    """
    Downloads the media file from a URL.
    """
    _download_file(media_url, headers={})

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def curl(ctx: typer.Context):
    """
    Parses a raw cURL command and downloads the media.
    """
    import re
    print("[cyan]Parsing cURL command...[/cyan]")
    
    curl_command = " ".join(ctx.args)
    
    # Improved parsing logic using regular expressions
    # This is more robust to handle various quoting styles.
    
    url = None
    headers = {}

    # Extract URL first - it's typically the first non-option argument
    # This regex looks for 'curl' followed by an optional quoted string.
    url_match = re.search(r"curl\s+'([^']+)'", curl_command)
    if url_match:
        url = url_match.group(1)
    else:
        # Fallback for double quotes
        url_match = re.search(r'curl\s+"([^"]+)"', curl_command)
        if url_match:
            url = url_match.group(1)

    if not url:
        # Fallback for unquoted URL
        parts = shlex.split(curl_command)
        if len(parts) > 1 and parts[0] == 'curl':
            if parts[1].startswith('http'):
                url = parts[1]

    if not url:
        # Last resort: find the first http URL in the command
        url_match = re.search(r"https?://[^\s'\"_]+", curl_command)
        if url_match:
            url = url_match.group(0)

    if not url:
        print("[bold red]Could not extract URL from curl command.[/bold red]")
        return

    # Extract headers, supporting both single and double quotes
    header_matches = re.findall(r"-H\s+'([^']+)'", curl_command)
    for header in header_matches:
        if ': ' in header:
            key, value = header.split(': ', 1)
            headers[key.strip()] = value.strip()

    header_matches_double = re.findall(r'-H\s+"([^"]+)"', curl_command)
    for header in header_matches_double:
        if ': ' in header:
            key, value = header.split(': ', 1)
            headers[key.strip()] = value.strip()

    # Extract cookies from -b
    cookie_match = re.search(r"-b\s+'([^']+)'", curl_command)
    if cookie_match:
        headers['Cookie'] = cookie_match.group(1)
    else:
        cookie_match = re.search(r'-b\s+"([^"]+)"', curl_command)
        if cookie_match:
            headers['Cookie'] = cookie_match.group(1)
        
    # Remove range header to ensure we download the full file
    if 'range' in headers:
        headers.pop('range')
        print("[yellow]Removed 'range' header to download the full file.[/yellow]")

    print(f"[cyan]Extracted URL:[/] {url}")
    _download_file(url, headers=headers)

if __name__ == "__main__":
    app()
