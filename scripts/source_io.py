"""Retrieve official releases and write a single validated browser edition."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent":"CoolCode.ca public records/1.0", "Accept":"*/*"}), timeout=100) as response:
                data = response.read()
                if response.status == 206:
                    bounds = re.fullmatch(r"bytes 0-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                    if not bounds or len(data) != int(bounds[2]):
                        raise ValueError("Partial source document")
                return data
        except (URLError, TimeoutError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def archives():
    return json.loads((ROOT / "sources" / "releases.json").read_text())

def archived(item):
    data = fetch(item["url"])
    if not data.startswith(b"%PDF") or hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError("Publisher file differs from the reviewed edition: " + item["title"])
    return data

def publish(data):
    if not data["count"] or not data["start"] or not data["end"]:
        raise ValueError("An empty edition cannot be published")
    data["retrieved"] = datetime.now(timezone.utc).date().isoformat()
    folder = ROOT / "web" / "data"
    folder.mkdir(exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=folder, delete=False, encoding="utf-8") as temp:
        json.dump(data,temp,ensure_ascii=False,separators=(",",":"))
        temp.write("\n")
    Path(temp.name).replace(folder / "edition.json")
    print(data["count"],data["coverage"],"retrieved",data["retrieved"])
