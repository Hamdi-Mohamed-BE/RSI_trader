import re
import requests
from urllib.parse import unquote

BASE_URL = "https://my.bullwaves.global"
PROFILE_PAGE = f"{BASE_URL}/my-profile"
POST_URL = f"{BASE_URL}/api/profile"

# Paste your fresh browser Cookie header here from DevTools -> Network -> Request Headers
COOKIE_HEADER = r"""PASTE_FULL_COOKIE_HEADER_HERE"""

def cookie_header_to_dict(cookie_header: str) -> dict:
    cookies = {}
    for item in cookie_header.split(";"):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            cookies[key] = value
    return cookies

session = requests.Session()

session.headers.update({
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
})

session.cookies.update(cookie_header_to_dict(COOKIE_HEADER))

# 1) Load profile page first to get the fresh CSRF token
page = session.get(PROFILE_PAGE, timeout=30)

print("Profile page status:", page.status_code)

if page.status_code != 200:
    print(page.text[:1000])
    raise SystemExit("Could not load profile page. Your cookies are probably expired.")

html = page.text

csrf_token = None

# Try Laravel meta tag
match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html)
if match:
    csrf_token = match.group(1)

# Try hidden input
if not csrf_token:
    match = re.search(r'name="_token"\s+value="([^"]+)"', html)
    if match:
        csrf_token = match.group(1)

# Fallback: XSRF-TOKEN cookie
if not csrf_token and "XSRF-TOKEN" in session.cookies:
    csrf_token = unquote(session.cookies.get("XSRF-TOKEN"))

if not csrf_token:
    raise SystemExit("Could not find CSRF token in page.")

print("CSRF token found:", csrf_token[:20] + "...")

# 2) Submit profile update with the same session
headers = {
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": BASE_URL,
    "referer": PROFILE_PAGE,
    "x-csrf-token": csrf_token,
    "x-requested-with": "XMLHttpRequest",
}

data = {
    "name":"MOHAMED BEN ABDESSALEM TOUFIK BEN OMAR",
    "recoveryquestions": "What is your mother's maiden name?",
    "answer": "",
    "phone": "21693830957",
    "mobile": "0",
    "address": "lessouda",
    "city": "lessouda",
    "state": "lessouda",
    "country": "TN",
    "zip": "9171",
    "citizenship": "سيدي بوزيد",
    "dateofbirth2[day]": "16",
    "dateofbirth2[month]": "9",
    "dateofbirth2[year]": "1998",
    "_token": csrf_token,
}

response = session.post(
    POST_URL,
    headers=headers,
    data=data,
    timeout=30,
)

print("Status:", response.status_code)
print("Response:")
# print(response.text)