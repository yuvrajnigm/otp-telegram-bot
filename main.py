# dgroup_login.py
# Requirements:
#   pip install requests beautifulsoup4

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://d-group.stats.direct"
LOGIN_PAGE = urljoin(BASE, "/user-management/auth/login")

# ====== Fill your credentials here ======
USERNAME = "Yuvraj2008"
PASSWORD = "Yuvraj2008"
# =========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def get_login_form_data(session):
    r = session.get(LOGIN_PAGE, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form", {"id": "login-form"}) or soup.find("form")
    if not form:
        raise RuntimeError("Login form not found on page.")
    data = {}
    # collect all inputs (including hidden CSRF)
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        # take existing value or empty string
        data[name] = inp.get("value", "")
    # fill username/password
    # note: page uses names LoginForm[username] and LoginForm[password]
    # keep existing keys, but override with our credentials
    # try both common possibilities, but based on provided source:
    uname_key = None
    pwd_key = None
    for key in data.keys():
        if "user" in key.lower() and "pass" not in key.lower():
            uname_key = key
        if "pass" in key.lower():
            pwd_key = key
    # fallback to known names from the source
    if not uname_key:
        uname_key = "LoginForm[username]"
    if not pwd_key:
        pwd_key = "LoginForm[password]"

    data[uname_key] = USERNAME
    data[pwd_key] = PASSWORD

    # Ensure rememberMe exists; default to 0 (unchecked) if not present
    if "LoginForm[rememberMe]" not in data:
        data["LoginForm[rememberMe]"] = "0"

    # form action (relative or absolute)
    action = form.get("action") or LOGIN_PAGE
    post_url = urljoin(LOGIN_PAGE, action)
    method = (form.get("method") or "post").lower()
    return post_url, method, data

def main():
    sess = requests.Session()
    try:
        post_url, method, payload = get_login_form_data(sess)
    except Exception as e:
        print("Error while preparing login form:", e)
        return

    print("Submitting", method.upper(), "to", post_url)
    # include referer header (some sites require it)
    headers = HEADERS.copy()
    headers["Referer"] = LOGIN_PAGE

    if method == "post":
        resp = sess.post(post_url, data=payload, headers=headers, allow_redirects=True, timeout=20)
    else:
        resp = sess.get(post_url, params=payload, headers=headers, allow_redirects=True, timeout=20)

    # show redirect history if any
    if resp.history:
        print("Redirect history (earliest -> latest):")
        for i, h in enumerate(resp.history, 1):
            loc = h.headers.get("Location", "(no Location header)")
            print(f" {i}. {h.status_code} -> {loc}")
    else:
        print("No HTTP redirect history (server returned final page directly).")

    print("\nFinal URL after login / redirect:")
    print(resp.url)

    # small debug snippet (optional)
    print("\n--- Page snippet (first 800 chars) ---")
    snippet = resp.text[:800].replace("\n", " ")
    print(snippet)
    print("--- end snippet ---")

if __name__ == "__main__":
    main()
