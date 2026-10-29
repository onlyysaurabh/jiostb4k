#!/usr/bin/env python3
"""
Jio FOTA Server Firmware & Signature Probe Tool
Checks availability of STB and Router firmware binaries without downloading full payloads.
"""

import sys
import urllib.request
import urllib.error
import concurrent.futures

BASE_FXD = "http://fota.slv.fxd.jiophone.net"
BASE_KAI = "http://fota.slv.kai.jiophone.net"

def check_url(url):
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            cl = resp.headers.get("Content-Length", "unknown")
            lm = resp.headers.get("Last-Modified", "unknown")
            return (url, resp.status, cl, lm)
    except urllib.error.HTTPError as e:
        return (url, e.code, None, None)
    except Exception as e:
        return (url, str(e), None, None)

def main():
    print("=" * 70)
    print(" Reliance Jio FOTA Endpoint Verification Tool")
    print("=" * 70)

    paths_to_test = []

    # 1. Droidlogic JHSD200 STB versions
    for major in range(5, 8):
        for minor in range(0, 10):
            for patch in range(0, 10):
                ver = f"{major}.{minor}.{patch}"
                paths_to_test.append(f"{BASE_FXD}/STB/Droidlogic/JHSD200/STB-JHSD200-{ver}.zip")

    # 2. Router models & prefixes
    routers = [
        ("Arcadyan", "JCOW411", "ARCNTF1_JCOW411_R"),
        ("Sercomm", "JCOW414", "SRCMTF1_JCOW414_R"),
        ("Skyworth", "JCOW407", "SKYWTF1_JCOW407_R"),
        ("Sercomm", "JCOW404", "SRCMTF1_JCOW404_R"),
    ]

    for mfg, model, prefix in routers:
        for major in (1, 2):
            for minor in range(0, 55):
                for ver in [f"{major}.{minor}", f"{major}.{minor}.1"]:
                    paths_to_test.append(f"{BASE_FXD}/ONT/{mfg}/{model}/{prefix}{ver}.img")
                    paths_to_test.append(f"{BASE_FXD}/ONT/{mfg}/{model}/{prefix}{ver}.sig")

    print(f"[*] Probing {len(paths_to_test)} candidate paths across FOTA endpoints...")

    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(check_url, u): u for u in paths_to_test}
        for fut in concurrent.futures.as_completed(futures):
            url, status, cl, lm = fut.result()
            if status == 200:
                print(f"[FOUND 200] {url} ({cl} bytes | {lm})")
                found.append((url, cl, lm))

    print("\n" + "=" * 70)
    print(f" Total Active Firmwares / Signatures Discovered: {len(found)}")
    print("=" * 70)
    for u, cl, lm in sorted(found):
        print(f"• {u} ({cl} bytes)")

if __name__ == "__main__":
    main()
