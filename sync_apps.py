import json
import os
import re

def slugify(text):
    text = str(text).lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9-]', '', text)

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

    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if not match:
        return 0

    value = float(match.group(1))

    if any(unit in text for unit in ['gb', 'gib', 'جيجا', 'غيغا']):
        return int(value * 1024 * 1024 * 1024)

    if any(unit in text for unit in ['mb', 'mib', 'ميجا', 'ميكا', 'مب']):
        return int(value * 1024 * 1024)

    if any(unit in text for unit in ['kb', 'kib', 'كيلو', 'كب']):
        return int(value * 1024)

    return int(value)

with open('jom.json', 'r', encoding='utf-8') as f:
    new_source = json.load(f)

new_apps = new_source.get('apps', [])
files_to_update = ['old_repo/ipastore']

for file_path in files_to_update:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_source = json.load(f)
            except Exception:
                old_source = {
                    "name": "iKiraPlus Store",
                    "identifier": "com.ikiraplus.store",
                    "apps": []
                }
    else:
        old_source = {
            "name": "iKiraPlus Store",
            "identifier": "com.ikiraplus.store",
            "apps": []
        }

    old_apps = old_source.get('apps', [])

    old_apps_map = {
        app.get('name'): app
        for app in old_apps
        if app.get('name')
    }

    for n_app in new_apps:
        name = n_app.get('name')
        if not name:
            continue

        updated_at = n_app.get('updatedAt', '')
        version_date = updated_at.split('T')[0] if 'T' in updated_at else updated_at
        app_size = size_to_bytes(n_app.get('size'))

        if name in old_apps_map:
            app = old_apps_map[name]
            app['version'] = n_app.get('version')
            app['versionDate'] = version_date
            app['downloadURL'] = n_app.get('ipaUrl')
            app['iconURL'] = n_app.get('icon')
            app['size'] = app_size
            app['localizedDescription'] = n_app.get('note', '')
            app['category'] = n_app.get('category', 'ألعاب')
        else:
            old_apps.append({
                "name": name,
                "bundleIdentifier": f"com.ikiraplus.{slugify(name)}",
                "developerName": "iKiraPlus",
                "version": n_app.get('version'),
                "versionDate": version_date,
                "downloadURL": n_app.get('ipaUrl'),
                "iconURL": n_app.get('icon'),
                "localizedDescription": n_app.get('note', ''),
                "size": app_size,
                "category": n_app.get('category', 'ألعاب')
            })

    old_source['apps'] = old_apps

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(old_source, f, indent=2, ensure_ascii=False)

print("✅ ipastore updated successfully")
