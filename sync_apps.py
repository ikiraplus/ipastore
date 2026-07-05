#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter

START_APP_NAME = "ريكرام"
BUNDLE_PREFIX = "com.ikiraplus.apps"

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
    "id",
    "name",
    "bundleIdentifier",
    "bundleId",
    "developerName",
    "version",
    "versionDate",
    "downloadURL",
    "ipaUrl",
    "iconURL",
    "icon",
    "localizedDescription",
    "note",
    "size",
    "category",
    "addedAt",
    "updatedAt",
    "hidden",
]

DEFAULT_SOURCE_META = {
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
}

CERTIFICATE_ID_NEEDLES = (
    "shahada-free",
    "shahadda-free",
    "shahada",
    "shahadda",
)
CERTIFICATE_NAME_NEEDLES = (
    "شهاده مجاني",
    "شهاده",
)


def clean_text(value):
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u2060]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_arabic(value):
    text = clean_text(value)
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")
    return text.casefold()


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "null", "none", "nan"}:
        return True
    return False


def first_non_empty(*values):
    for value in values:
        if not is_empty(value):
            return value
    return None


def is_certificate_app(app):
    if not isinstance(app, dict):
        return False

    name_key = normalize_arabic(app.get("name"))
    id_key = clean_text(app.get("id")).casefold()
    bundle_key = clean_text(app.get("bundleIdentifier") or app.get("bundleId")).casefold()
    url_key = clean_text(app.get("downloadURL") or app.get("ipaUrl")).casefold()
    blob = f"{id_key} {bundle_key} {url_key}"

    if any(needle in name_key for needle in CERTIFICATE_NAME_NEEDLES):
        return True
    if any(needle in blob for needle in CERTIFICATE_ID_NEEDLES):
        return True
    return False


def size_to_bytes(size):
    if size is None:
        return 0
    if isinstance(size, bool):
        return int(size)
    if isinstance(size, int):
        return size
    if isinstance(size, float):
        return int(size)

    text = str(size).strip().lower().replace(",", "")
    if not text:
        return 0
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
    value = first_non_empty(value)
    if value is None:
        return None
    text = str(value).strip()
    if "T" in text:
        text = text.split("T", 1)[0].strip()
    return text or None


def slugify(text):
    text = clean_text(text).casefold()
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:42].strip("-") or "app"


def stable_hash(*parts):
    raw = "|".join(clean_text(part) for part in parts if not is_empty(part))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def make_bundle(app, used_bundles):
    existing = first_non_empty(app.get("bundleIdentifier"), app.get("bundleId"))
    existing_key = clean_text(existing).casefold()
    if existing_key and existing_key not in used_bundles:
        used_bundles.add(existing_key)
        return clean_text(existing)

    base = (
        f"{BUNDLE_PREFIX}."
        f"{slugify(first_non_empty(app.get('name'), app.get('id'), 'app'))}."
        f"{stable_hash(app.get('id'), app.get('name'), app.get('ipaUrl'), app.get('downloadURL'))}"
    )
    candidate = base
    counter = 2
    while candidate.casefold() in used_bundles:
        candidate = f"{base}.{counter}"
        counter += 1

    used_bundles.add(candidate.casefold())
    return candidate


def order_dict(data, preferred_order):
    ordered = {key: data[key] for key in preferred_order if key in data}
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if not isinstance(data.get("apps"), list):
        raise ValueError(f"{path} must contain an apps array")
    return data


def get_apps(source):
    return [app for app in source.get("apps", []) if isinstance(app, dict)]


def find_start_index(apps):
    target = normalize_arabic(START_APP_NAME)
    for index, app in enumerate(apps):
        if normalize_arabic(app.get("name")) == target:
            return index
    names_preview = [clean_text(app.get("name")) for app in apps[:30]]
    raise ValueError(f"Start app '{START_APP_NAME}' was not found. First apps: {names_preview}")


def normalize_app(app, used_bundles):
    fixed = copy.deepcopy(app)

    if "name" in fixed:
        fixed["name"] = clean_text(fixed.get("name"))

    fixed["size"] = size_to_bytes(fixed.get("size"))
    fixed["versionDate"] = normalize_version_date(
        first_non_empty(fixed.get("versionDate"), fixed.get("updatedAt"), fixed.get("addedAt"))
    )

    if is_empty(fixed.get("downloadURL")) and not is_empty(fixed.get("ipaUrl")):
        fixed["downloadURL"] = fixed.get("ipaUrl")
    if is_empty(fixed.get("iconURL")) and not is_empty(fixed.get("icon")):
        fixed["iconURL"] = fixed.get("icon")
    if is_empty(fixed.get("localizedDescription")) and not is_empty(fixed.get("note")):
        fixed["localizedDescription"] = fixed.get("note")

    fixed["bundleIdentifier"] = make_bundle(fixed, used_bundles)
    return order_dict(fixed, APP_FIELD_ORDER)


def build_source_from_regram(jom_source):
    jom_apps = get_apps(jom_source)
    start_index = find_start_index(jom_apps)
    ignored_before_start = jom_apps[:start_index]

    used_bundles = set()
    clean_source = copy.deepcopy(DEFAULT_SOURCE_META)

    for key, value in jom_source.items():
        if key != "apps":
            clean_source[key] = copy.deepcopy(value)

    clean_source.setdefault("name", DEFAULT_SOURCE_META["name"])
    clean_source.setdefault("identifier", DEFAULT_SOURCE_META["identifier"])
    clean_source.setdefault("sourceURL", DEFAULT_SOURCE_META["sourceURL"])
    clean_source.setdefault("iconURL", DEFAULT_SOURCE_META["iconURL"])
    clean_source.setdefault("sourceIcon", clean_source.get("iconURL", DEFAULT_SOURCE_META["sourceIcon"]))
    clean_source.setdefault("website", DEFAULT_SOURCE_META["website"])
    if not isinstance(clean_source.get("news"), list) or not clean_source.get("news"):
        clean_source["news"] = copy.deepcopy(DEFAULT_SOURCE_META["news"])

    clean_apps = []
    skipped_certificates = []
    for app in jom_apps[start_index:]:
        if is_certificate_app(app):
            skipped_certificates.append(clean_text(app.get("name") or app.get("id")))
            continue
        fixed = normalize_app(app, used_bundles)
        if is_certificate_app(fixed):
            skipped_certificates.append(clean_text(fixed.get("name") or fixed.get("id")))
            continue
        clean_apps.append(fixed)

    clean_source["apps"] = clean_apps
    return order_dict(clean_source, SOURCE_FIELD_ORDER), ignored_before_start, skipped_certificates


def validate_output(jom_source, output_source, ignored_before_start):
    jom_apps = get_apps(jom_source)
    start_index = find_start_index(jom_apps)
    expected_names = [clean_text(app.get("name")) for app in jom_apps[start_index:] if not is_certificate_app(app)]
    output_apps = [app for app in output_source.get("apps", []) if isinstance(app, dict)]
    output_names = [clean_text(app.get("name")) for app in output_apps]

    if not output_apps:
        raise ValueError("Output has no apps")

    first_name = output_apps[0].get("name")
    if normalize_arabic(first_name) != normalize_arabic(START_APP_NAME):
        raise ValueError(f"First app must be '{START_APP_NAME}', got '{first_name}'")

    if output_names != expected_names:
        raise ValueError("Output apps do not exactly match jom.json from ريكرام onward")

    certificate_apps = [clean_text(app.get("name") or app.get("id")) for app in output_apps if is_certificate_app(app)]
    if certificate_apps:
        raise ValueError(f"Certificate apps leaked into output: {certificate_apps[:20]}")

    ignored_names = {clean_text(app.get("name")) for app in ignored_before_start if clean_text(app.get("name"))}
    leaked_before_start = [name for name in output_names if name in ignored_names]
    if leaked_before_start:
        raise ValueError(f"Apps before ريكرام leaked into output: {leaked_before_start[:20]}")

    empty_dates = [app.get("name") for app in output_apps if app.get("versionDate") == ""]
    if empty_dates:
        raise ValueError(f"Empty versionDate values found: {empty_dates[:20]}")

    bad_sizes = [app.get("name") for app in output_apps if not isinstance(app.get("size"), int)]
    if bad_sizes:
        raise ValueError(f"Size must be int bytes for: {bad_sizes[:20]}")

    missing_bundles = [app.get("name") for app in output_apps if is_empty(app.get("bundleIdentifier"))]
    if missing_bundles:
        raise ValueError(f"Missing bundleIdentifier values: {missing_bundles[:20]}")

    bundle_counts = Counter(app.get("bundleIdentifier") for app in output_apps if app.get("bundleIdentifier"))
    duplicate_bundles = [bundle for bundle, count in bundle_counts.items() if count > 1]
    if duplicate_bundles:
        raise ValueError(f"Duplicate bundleIdentifier values: {duplicate_bundles[:20]}")


def hard_write_json(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    try:
        if os.path.exists(path):
            os.chmod(path, 0o666)
            os.remove(path)
    except FileNotFoundError:
        pass

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    os.replace(tmp_path, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="jom.json", help="Path to jom.json")
    parser.add_argument("--target", default="old_repo/ipastore", help="Path to target ipastore file")
    args = parser.parse_args()

    jom_source = load_json_file(args.source)
    output_source, ignored_before_start, skipped_certificates = build_source_from_regram(jom_source)
    validate_output(jom_source, output_source, ignored_before_start)
    hard_write_json(args.target, output_source)

    written = load_json_file(args.target)
    validate_output(jom_source, written, ignored_before_start)

    apps = written["apps"]
    print("✅ HARD REBUILD OK")
    print(f"✅ target wiped and rewritten: {args.target}")
    print(f"✅ first app: {apps[0]['name']}")
    print(f"✅ ignored before ريكرام: {len(ignored_before_start)}")
    for app in ignored_before_start[:20]:
        print(f"   - ignored: {clean_text(app.get('name') or app.get('id'))}")
    print(f"✅ skipped certificate apps after ريكرام: {len(skipped_certificates)}")
    for name in skipped_certificates[:20]:
        print(f"   - skipped: {name}")
    print(f"✅ apps written: {len(apps)}")
    print("✅ no شهادة مجانية apps in output")
    print("✅ size is bytes/int")
    print("✅ versionDate is never empty string")
    print("✅ bundleIdentifier values are unique")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"❌ sync failed: {exc}", file=sys.stderr)
        sys.exit(1)
