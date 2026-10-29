#!/usr/bin/env python3
"""
Kai-tier FOTA URL manager for Jio JMSB200A / AirFiber builds.

Path taxonomy (tokenized, non-enumerable):
    http://fota.slv.kai.jiophone.net/<CATEGORY>/<DEVICE_ID>/<BUILD_ID>/<TOKEN>.<ext>

WARNING: <TOKEN> is a 10-char pseudo-random hash. It cannot be guessed or
brute-forced (Akamai returns 403/404 on directory listings and unknown paths).
Valid tokens must be obtained from ACS Download RPCs, live traffic captures,
or decompiled APK catalog strings. This script only manages KNOWN tokens
already extracted from this repository.
"""

import json
import sys
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = "http://fota.slv.kai.jiophone.net"

# Known tokenized URLs extracted from this repository.
# Source: jio_infrastructure/ENDPOINTS_REFERENCE.json, 03_FOTA_AND_FIRMWARE_DISTRIBUTION.md §3.1, OTA_ANALYSIS.md
KNOWN_URLS = [
    # Current JMSB200A 4K STB (build SA002_19 / Android 11 / 25.1.9)
    "http://fota.slv.kai.jiophone.net/BHTS/DIN1009/SA002_19/loOOGaJIPm.zip",

    # Legacy / prototype device catalog (DIN* matrix)
    "http://fota.slv.kai.jiophone.net/BHTS/DIN59/D002D_11/zMbiKlmKfm.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN62/S002B_011/AfblteoWZe.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN62/SA002_011/tiOwCGBFDU.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN292/D002D_020/UAtWTevgwZ.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN292/S002B_020/sAydtUZsOC.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN292/S002C_020/TOKNrjMKby.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN293/D002D_120/WVnkJkfyBQ.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN293/S002C_202/VSyIqnTPqD.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_-99/YZocoPAaBG.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_75-E/wyNnasHigE.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_81/xU5GtWOLMH.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_910/zwdhLxbvHJ.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN353/S002C_9-H/CKEv2odf5n.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN368/D002D_211/KDYRLwwQsGQ.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN372/S002C_211/IvNbOICw7t.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN380/S002B_211/qE4WT6Ezy1.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN387/D002D_13-H/AyIwu7D7AB.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN390/BA002_114/ks6fkIEJJV.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN422/S002B_13-H/CdksdojCmi.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN431/D002D_228/RchIhUhqEW.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN431/S002B_228/QwDZLBwrRM.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN431/S002C_228/SmTXZD3vuY.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN442/SA002_109/yFT88iUnII.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN445/BA002_109/Is6fkIEJJV.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN445/SA002_109/HOwJatziuX.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN537/BA002_111/JOwJatziuX.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN537/SA002_111/kArxcKXoHi.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN551/D002D_248/VchIhUhqEW.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN551/S002B_248/tU831C61cr.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN551/S002C_248/UmTXZD3vuY.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN666/D002D_280/MchIhUhqEW.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN667/S002B_280/PKLg53bXlX.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN667/S002C_280/OWcaMhIc1i.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN730/D002D_294/KchIhUhqEW.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN733/S002C_294/OBcaMhIc1i.zip",
    "http://fota.slv.kai.jiophone.net/BHTS/DIN738/S002B_294/LU831C61cr.zip",
]


def build_url(category, device_id, build_id, token, ext="zip"):
    """Construct a tokenized kai-tier FOTA URL from its components."""
    path = f"{category}/{device_id}/{build_id}/{token}.{ext}"
    return urljoin(BASE + "/", path)


def list_known():
    """Print all known tokenized URLs with parsed components."""
    print(f"{'#':>3}  CATEGORY   DEVICE    BUILD        TOKEN         EXT  URL")
    print("-" * 110)
    for i, url in enumerate(KNOWN_URLS, 1):
        # strip scheme+host
        rest = url.replace("http://fota.slv.kai.jiophone.net/", "")
        parts = rest.split("/")
        category, device_id, build_id, fname = parts[0], parts[1], parts[2], parts[3]
        token, ext = fname.rsplit(".", 1)
        print(f"{i:>3}  {category:<10} {device_id:<9} {build_id:<12} {token:<13} {ext:<4} {url}")
    print(f"\nTotal known tokenized URLs: {len(KNOWN_URLS)}")


def check_url(url, timeout=8):
    """HEAD-check whether a known URL is still live (does not download payload)."""
    req = Request(url, method="HEAD", headers={"User-Agent": "Android"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Length"), resp.headers.get("Last-Modified")
    except HTTPError as e:
        return e.code, None, None
    except URLError as e:
        return f"ERR:{e.reason}", None, None


def check_all():
    """HEAD-check every known URL for liveness."""
    print(f"{'#':>3}  STATUS  CONTENT-LENGTH  LAST-MODIFIED          URL")
    print("-" * 115)
    for i, url in enumerate(KNOWN_URLS, 1):
        status, clen, lm = check_url(url)
        print(f"{i:>3}  {str(status):<7} {str(clen):<15} {str(lm):<24} {url}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python kai_fota_urls.py list          # list all known tokenized URLs")
        print("  python kai_fota_urls.py check         # HEAD-check all known URLs for liveness")
        print("  python kai_fota_urls.py build <cat> <dev> <build> <token> [ext]  # construct a URL")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        list_known()
    elif cmd == "check":
        check_all()
    elif cmd == "build":
        if len(sys.argv) < 6:
            print("Usage: build <category> <device_id> <build_id> <token> [ext]")
            return
        ext = sys.argv[6] if len(sys.argv) > 6 else "zip"
        print(build_url(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], ext))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
