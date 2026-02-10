import requests
from bs4 import BeautifulSoup
from typing import List, Dict

def fetch_sec_url(url: str) -> str:
    """
    Fetches text content from an SEC.gov HTML page.
    (PDF handling can be added separately.)
    """
    headers = {
        "User-Agent": "Custody-Intelligence-Agent/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    return " ".join(text.split())


# Example run to test fetch_sec_url function
if __name__ == "__main__":
    # Test with a real SEC.gov URL (example: SEC Crypto Task Force page)
    test_url = "https://www.sec.gov/spotlight/cybersecurity"
    
    try:
        print(f"Fetching content from: {test_url}")
        print("-" * 80)
        
        content = fetch_sec_url(test_url)
        
        print(f"Successfully fetched content!")
        print(f"Content length: {len(content)} characters")
        print("-" * 80)
        print("First 500 characters:")
        print(content[:500])
        print("-" * 80)
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

