import json
import os
import re

SOURCE_FIELD_ORDER = [
    "name",
    "identifier",
    "sourceURL",
    "iconURL",
    "sourceIcon",
    "website",
    "news",
    "apps",
]

APP_FIELD_ORDER = [
    "name",
    "bundleIdentifier",
    "developerName",
    "version",
    "versionDate",
    "downloadURL",
    "iconURL",
    "localizedDescription",
    "size",
    "category",
]

DEFAULT_SOURCE = {
    "name": "iKiraPlus - IPA Store",
    "identifier": "com.ikiraplus.store",
    "sourceURL": "https://raw.githubusercontent.com/jacckop/source/main/ipastore",
    "iconURL": "https://raw.githubusercontent.com/ikira18/feather/main/images/kiraplus.png",
    "sourceIcon": "https://raw.githubusercontent.com/ikira18/feather/main/images/kiraplus.png",
    "website": "https://t.me/iKiraPlus",
    "news": [
        {
            "title": "كيرا بلس",
            "identifier": "com.ikiraplus.card",
            "caption": "قناة كيرا بلس للتطبيقات والشهادات",
            "date": "2026-05-11",
            "tintColor": "#7A7DFF",
            "imageURL": "https://raw.githubusercontent.com/ikira18/feather/main/images/kiraplus.png",
            "url": "https://t.me/iKiraPlus",
        }
    ],
    "apps": [],
}


def slugify(text):
    text = str(text).lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", text)


def size_to_bytes(size):
    if size is None:
        return 0

    if isinstance(size, int):
        return size

    if isinstance(size, float):
        return int(size)

    text = str(size).strip().lower().replace(",", "")

    if text.isdigit():
        return int(text)

    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return 0

    value = float(match.group(1))

    if any(unit in text for unit in ["gb", "gib", "جيجا", "غيغا"]):
        return int(value * 1024 * 1024 * 1024)

    if any(unit in text for unit in ["mb", "mib", "ميجا", "ميكا", "مب"]):
        return int(value * 1024 * 1024)

    if any(unit in text for unit in ["kb", "kib", "كيلو", "كب"]):
        return int(value * 1024)

    return int(value)


def normalize_version_date(value):
    """Return a valid Feather-friendly versionDate.

    Empty dates must be JSON null, not an empty string "".
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "nan"}:
        return None

    if "T" in text:
        text = text.split("T", 1)[0].strip()

    return text or None


def first_value(*values, default=""):
    for value in values:
        if value is not None and str(value).strip() != "":
            return value
    return default


def load_json_or_default(file_path):
    if not os.path.exists(file_path):
        return json.loads(json.dumps(DEFAULT_SOURCE, ensure_ascii=False))

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
    except Exception:
        pass

    return json.loads(json.dumps(DEFAULT_SOURCE, ensure_ascii=False))


def ordered_news_item(item):
    return {
        "title": item.get("title", "كيرا بلس"),
        "identifier": item.get("identifier", "com.ikiraplus.card"),
        "caption": item.get("caption", "قناة كيرا بلس للتطبيقات والشهادات"),
        "date": item.get("date", "2026-05-11"),
        "tintColor": item.get("tintColor", "#7A7DFF"),
        "imageURL": item.get("imageURL", DEFAULT_SOURCE["iconURL"]),
        "url": item.get("url", "https://t.me/iKiraPlus"),
    }


def ordered_app(app):
    return {
        "name": app.get("name", ""),
        "bundleIdentifier": app.get("bundleIdentifier", ""),
        "developerName": app.get("developerName", "iKiraPlus"),
        "version": app.get("version", ""),
        "versionDate": normalize_version_date(app.get("versionDate")),
        "downloadURL": app.get("downloadURL", ""),
        "iconURL": app.get("iconURL", ""),
        "localizedDescription": app.get("localizedDescription", ""),
        "size": size_to_bytes(app.get("size")),
        "category": app.get("category", "ألعاب"),
    }


def ordered_source(source):
    source.setdefault("name", DEFAULT_SOURCE["name"])
    source.setdefault("identifier", DEFAULT_SOURCE["identifier"])
    source.setdefault("sourceURL", DEFAULT_SOURCE["sourceURL"])
    source.setdefault("iconURL", DEFAULT_SOURCE["iconURL"])
    source.setdefault("sourceIcon", source.get("iconURL", DEFAULT_SOURCE["sourceIcon"]))
    source.setdefault("website", DEFAULT_SOURCE["website"])

    news = source.get("news")
    if not isinstance(news, list) or not news:
        news = DEFAULT_SOURCE["news"]
    source["news"] = [ordered_news_item(item if isinstance(item, dict) else {}) for item in news]

    apps = source.get("apps")
    if not isinstance(apps, list):
        apps = []
    source["apps"] = [ordered_app(app) for app in apps if isinstance(app, dict) and app.get("name")]

    ordered = {key: source[key] for key in SOURCE_FIELD_ORDER if key in source}
    for key, value in source.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


with open("jom.json", "r", encoding="utf-8") as f:
    new_source = json.load(f)

new_apps = new_source.get("apps", [])
files_to_update = ["old_repo/ipastore"]

for file_path in files_to_update:
    old_source = load_json_or_default(file_path)
    old_apps = old_source.get("apps", [])
    if not isinstance(old_apps, list):
        old_apps = []

    old_apps_map = {app.get("name"): app for app in old_apps if isinstance(app, dict) and app.get("name")}

    for n_app in new_apps:
        if not isinstance(n_app, dict):
            continue

        name = n_app.get("name")
        if not name:
            continue

        version_date = normalize_version_date(first_value(n_app.get("updatedAt"), n_app.get("versionDate"), default=None))
        app_size = size_to_bytes(n_app.get("size"))
        download_url = first_value(n_app.get("ipaUrl"), n_app.get("downloadURL"), default="")
        icon_url = first_value(n_app.get("icon"), n_app.get("iconURL"), default="")
        description = first_value(n_app.get("note"), n_app.get("localizedDescription"), default="")

        if name in old_apps_map:
            app = old_apps_map[name]
            app["version"] = n_app.get("version", app.get("version", ""))
            app["versionDate"] = version_date
            app["downloadURL"] = download_url
            app["iconURL"] = icon_url
            app["size"] = app_size
            app["localizedDescription"] = description
            app["category"] = n_app.get("category", app.get("category", "ألعاب"))
        else:
            old_apps.append(
                {
                    "name": name,
                    "bundleIdentifier": first_value(
                        n_app.get("bundleIdentifier"),
                        n_app.get("bundleId"),
                        default=f"com.ikiraplus.{slugify(name)}",
                    ),
                    "developerName": n_app.get("developerName", "iKiraPlus"),
                    "version": n_app.get("version", ""),
                    "versionDate": version_date,
                    "downloadURL": download_url,
                    "iconURL": icon_url,
                    "localizedDescription": description,
                    "size": app_size,
                    "category": n_app.get("category", "ألعاب"),
                }
            )

    old_source["apps"] = old_apps
    old_source = ordered_source(old_source)

    empty_dates = [app.get("name") for app in old_source["apps"] if app.get("versionDate") == ""]
    if empty_dates:
        raise ValueError(f"Found empty versionDate values after cleanup: {empty_dates[:10]}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(old_source, f, indent=2, ensure_ascii=False)

print("✅ ipastore updated successfully")
print("✅ empty versionDate values converted to null")
