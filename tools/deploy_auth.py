#!/usr/bin/env python3
"""Deploy helper (GitHub Actions). Stdlib only.
  deploy_auth.py            configure Supabase Auth: site URL = the Worker URL, e-mail OTP code in the sign-in mail
  deploy_auth.py e2e-user   create/refresh the invited test user e2e.desk@proposal-desk.test (role desk) with E2E_TEST_PASSWORD
Env: SUPABASE_ACCESS_TOKEN, PROJECT_REF, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, SUPABASE_URL, SUPABASE_SERVICE_KEY."""
import json, os, sys, urllib.request, urllib.error

E2E_EMAIL = "e2e.desk@proposal-desk.test"


def call(method, url, body=None, headers=None):
    h = {"Content-Type": "application/json", "User-Agent": "proposal-desk-deploy"}
    h.update(headers or {})
    r = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            t = resp.read()
            return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url}: {e.code} {e.read().decode(errors='replace')[:400]}")


def worker_url():
    acc, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    d = call("GET", f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/subdomain", headers={"Authorization": f"Bearer {tok}"})
    sub = d["result"]["subdomain"]
    return f"https://proposal-desk.{sub}.workers.dev"


def auth_config():
    site = worker_url()
    ref, tok = os.environ["PROJECT_REF"], os.environ["SUPABASE_ACCESS_TOKEN"]
    body = {
        "site_url": site,
        "uri_allow_list": f"{site}/**",
        "external_email_enabled": True,
        "mailer_otp_exp": 600,
        "mailer_otp_length": 6,
        "mailer_subjects_magic_link": "प्रस्ताव कक्ष — लॉगिन कोड",
        "mailer_templates_magic_link_content": "<p>प्रस्ताव कक्ष लॉगिन कोड:</p><h2>{{ .Token }}</h2><p>10 मिनिटांत वापरा.</p>",
        "mailer_subjects_confirmation": "प्रस्ताव कक्ष — लॉगिन कोड",
        "mailer_templates_confirmation_content": "<p>प्रस्ताव कक्ष लॉगिन कोड:</p><h2>{{ .Token }}</h2><p>10 मिनिटांत वापरा.</p>",
    }
    call("PATCH", f"https://api.supabase.com/v1/projects/{ref}/config/auth", body, {"Authorization": f"Bearer {tok}"})
    print("auth configured; site:", site)
    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh:
        open(gh, "a").write(f"Dashboard URL: {site}\n")


def e2e_user():
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    pw = os.environ["E2E_TEST_PASSWORD"]
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    users = call("GET", f"{url}/auth/v1/admin/users?per_page=1000", headers=h)["users"]
    u = next((x for x in users if (x.get("email") or "").lower() == E2E_EMAIL), None)
    if u:
        call("PUT", f"{url}/auth/v1/admin/users/{u['id']}", {"password": pw}, h)
        print("e2e user password refreshed")
    else:
        call("POST", f"{url}/rest/v1/invites?on_conflict=email", {"email": E2E_EMAIL, "role": "desk"}, {**h, "Prefer": "resolution=merge-duplicates"})
        call("POST", f"{url}/auth/v1/admin/users", {"email": E2E_EMAIL, "password": pw, "email_confirm": True}, h)
        print("e2e user created (desk)")


if __name__ == "__main__":
    e2e_user() if sys.argv[1:] == ["e2e-user"] else auth_config()
