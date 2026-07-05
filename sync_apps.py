import hashlib
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

# Every app written to the target source will get a stable, unique bundle id.
# This avoids stores treating multiple apps as the same item because of duplicate bundles.
FORCE_GENERATED_UNIQUE_BUNDLES = True
BUNDLE_PREFIX = "com.ikiraplus.apps"

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


def clean_text(value):
    """Normalize text for comparison without changing the displayed value."""
    if value is None:
        return ""

    text = str(value)
    # Remove invisible chars that often cause duplicate app names in JSON sources.
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def name_key(value):
    return clean_text(value).casefold()


def bundle_key(value):
    return clean_text(value).casefold()


def slugify(text):
    text = clean_text(text).casefold()
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return (slug[:42].strip("-") or "app")


def stable_hash(text):
    return hashlib.sha1(name_key(text).encode("utf-8")).hexdigest()[:8]


def make_unique_bundle(name, used_bundles):
    base = f"{BUNDLE_PREFIX}.{slugify(name)}.{stable_hash(name)}"
    candidate = base
    counter = 2

    while candidate in used_bundles:
        candidate = f"{base}.{counter}"
        counter += 1

    used_bundles.add(candidate)
    return candidate


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


def set_if_present(app, field, value, allow_none=False):
    if value is None:
        if allow_none:
            app[field] = None
        return

    if isinstance(value, str) and value.strip() == "":
        return

    app[field] = value


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
        "name": clean_text(app.get("name", "")),
        "bundleIdentifier": clean_text(app.get("bundleIdentifier", "")),
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


def app_bundle_from_input(app):
    return first_value(
        app.get("bundleIdentifier"),
        app.get("bundleId"),
        app.get("identifier"),
        default="",
    )


def merge_non_empty(target, source):
    """Merge duplicate old entries. Later non-empty values win."""
    for key, value in source.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        target[key] = value


def dedupe_old_apps(apps):
    """Remove duplicates already created by older workflow runs.

    The identity is the normalized app name first, because downloadURL/iconURL can change
    and must never create a second app.
    """
    result = []
    seen_by_name = {}

    for app in apps:
        if not isinstance(app, dict) or not app.get("name"):
            continue

        key = name_key(app.get("name"))
        if key in seen_by_name:
            merge_non_empty(seen_by_name[key], app)
            continue

        seen_by_name[key] = app
        result.append(app)

    return result


def build_lookup_maps(apps):
    by_name = {}
    by_bundle = {}

    for app in apps:
        n_key = name_key(app.get("name"))
        b_key = bundle_key(app.get("bundleIdentifier"))

        if n_key and n_key not in by_name:
            by_name[n_key] = app
        if b_key and b_key not in by_bundle:
            by_bundle[b_key] = app

    return by_name, by_bundle


def find_existing_app(new_app, by_name, by_bundle):
    """Find the old app without using downloadURL/iconURL as identity."""
    incoming_bundle = bundle_key(app_bundle_from_input(new_app))
    incoming_name = name_key(new_app.get("name"))

    if incoming_bundle and incoming_bundle in by_bundle:
        return by_bundle[incoming_bundle]

    if incoming_name and incoming_name in by_name:
        return by_name[incoming_name]

    return None


def update_app_from_jom(app, n_app):
    name = clean_text(n_app.get("name"))
    version_date = normalize_version_date(first_value(n_app.get("updatedAt"), n_app.get("versionDate"), default=None))
    app_size = size_to_bytes(n_app.get("size"))
    download_url = first_value(n_app.get("ipaUrl"), n_app.get("downloadURL"), default="")
    icon_url = first_value(n_app.get("icon"), n_app.get("iconURL"), default="")
    description = first_value(n_app.get("note"), n_app.get("localizedDescription"), default="")

    # Keep name stable when the same normalized name matched. If a bundle matched and name changed,
    # this allows the displayed name to be updated intentionally.
    set_if_present(app, "name", name)
    set_if_present(app, "developerName", n_app.get("developerName", "iKiraPlus"))
    set_if_present(app, "version", n_app.get("version", app.get("version", "")))
    app["versionDate"] = version_date
    set_if_present(app, "downloadURL", download_url)
    set_if_present(app, "iconURL", icon_url)
    set_if_present(app, "localizedDescription", description)
    app["size"] = app_size
    set_if_present(app, "category", n_app.get("category", app.get("category", "ألعاب")))


def create_app_from_jom(n_app):
    name = clean_text(n_app.get("name"))
    version_date = normalize_version_date(first_value(n_app.get("updatedAt"), n_app.get("versionDate"), default=None))
    download_url = first_value(n_app.get("ipaUrl"), n_app.get("downloadURL"), default="")
    icon_url = first_value(n_app.get("icon"), n_app.get("iconURL"), default="")
    description = first_value(n_app.get("note"), n_app.get("localizedDescription"), default="")

    return {
        "name": name,
        "bundleIdentifier": app_bundle_from_input(n_app),
        "developerName": n_app.get("developerName", "iKiraPlus"),
        "version": n_app.get("version", ""),
        "versionDate": version_date,
        "downloadURL": download_url,
        "iconURL": icon_url,
        "localizedDescription": description,
        "size": size_to_bytes(n_app.get("size")),
        "category": n_app.get("category", "ألعاب"),
    }


def ensure_unique_bundle_identifiers(apps):
    used_bundles = set()

    for app in apps:
        if FORCE_GENERATED_UNIQUE_BUNDLES:
            app["bundleIdentifier"] = make_unique_bundle(app.get("name", "app"), used_bundles)
            continue

        current = bundle_key(app.get("bundleIdentifier"))
        if not current or current in used_bundles:
            app["bundleIdentifier"] = make_unique_bundle(app.get("name", "app"), used_bundles)
        else:
            used_bundles.add(current)


def validate_source(source):
    apps = source.get("apps", [])
    empty_dates = [app.get("name") for app in apps if app.get("versionDate") == ""]
    empty_urls = [app.get("name") for app in apps if not app.get("downloadURL")]

    bundles = [app.get("bundleIdentifier") for app in apps if app.get("bundleIdentifier")]
    duplicate_bundles = sorted({bundle for bundle in bundles if bundles.count(bundle) > 1})

    if empty_dates:
        raise ValueError(f"Found empty versionDate values after cleanup: {empty_dates[:10]}")
    if empty_urls:
        raise ValueError(f"Found empty downloadURL values after cleanup: {empty_urls[:10]}")
    if duplicate_bundles:
        raise ValueError(f"Found duplicate bundleIdentifier values after cleanup: {duplicate_bundles[:10]}")


with open("jom.json", "r", encoding="utf-8") as f:
    new_source = json.load(f)

new_apps = new_source.get("apps", [])
files_to_update = ["old_repo/ipastore"]

for file_path in files_to_update:
    old_source = load_json_or_default(file_path)
    old_apps = old_source.get("apps", [])
    if not isinstance(old_apps, list):
        old_apps = []

    old_apps = dedupe_old_apps(old_apps)
    by_name, by_bundle = build_lookup_maps(old_apps)

    added_count = 0
    updated_count = 0

    for n_app in new_apps:
        if not isinstance(n_app, dict):
            continue

        name = clean_text(n_app.get("name"))
        if not name:
            continue

        existing_app = find_existing_app(n_app, by_name, by_bundle)

        if existing_app is not None:
            old_name_key = name_key(existing_app.get("name"))
            update_app_from_jom(existing_app, n_app)
            new_name_key = name_key(existing_app.get("name"))

            # If a displayed name changed, keep the lookup table accurate during the same run.
            if old_name_key != new_name_key:
                by_name.pop(old_name_key, None)
                by_name[new_name_key] = existing_app

            updated_count += 1
        else:
            app = create_app_from_jom(n_app)
            old_apps.append(app)
            by_name[name_key(app.get("name"))] = app

            incoming_bundle = bundle_key(app_bundle_from_input(n_app))
            if incoming_bundle:
                by_bundle[incoming_bundle] = app

            added_count += 1

    ensure_unique_bundle_identifiers(old_apps)
    old_source["apps"] = old_apps
    old_source = ordered_source(old_source)

    validate_source(old_source)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(old_source, f, indent=2, ensure_ascii=False)

print("✅ ipastore updated successfully")
print("✅ existing apps are matched by normalized name/bundle, not by downloadURL/iconURL")
print("✅ duplicate old apps were merged before syncing")
print("✅ bundleIdentifier values are unique")
print(f"✅ updated apps: {updated_count}")
print(f"✅ added apps: {added_count}")
