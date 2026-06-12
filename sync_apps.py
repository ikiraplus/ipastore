import json
import os
import re

def slugify(text):
    text = text.lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9-]', '', text)

# تحميل الملفات
with open('jom.json', 'r', encoding='utf-8') as f:
    new_source = json.load(f)

# نفتح ملف السورس القديم (الموجود في المجلد المستنسخ)
with open('old_repo/source', 'r', encoding='utf-8') as f:
    old_source = json.load(f)

new_apps = new_source.get('apps', [])
old_apps = old_source.get('apps', [])

# تحويل السورس القديم لقاموس للبحث السريع
old_apps_map = {app['name']: app for app in old_apps}

for n_app in new_apps:
    name = n_app.get('name')
    
    # تحديث البيانات (أو إضافة تطبيق جديد)
    if name in old_apps_map:
        app = old_apps_map[name]
        app['version'] = n_app.get('version')
        app['versionDate'] = n_app.get('updatedAt', '').split('T')[0] if 'T' in n_app.get('updatedAt', '') else n_app.get('updatedAt')
        app['downloadURL'] = n_app.get('ipaUrl')
        app['iconURL'] = n_app.get('icon')
        app['size'] = n_app.get('size')
        app['localizedDescription'] = n_app.get('note', '')
        app['category'] = n_app.get('category', 'ألعاب')
    else:
        # إضافة تطبيق جديد كلياً
        new_entry = {
            "name": name,
            "bundleIdentifier": f"com.ikiraplus.{slugify(name)}",
            "developerName": "iKiraPlus",
            "version": n_app.get('version'),
            "versionDate": n_app.get('updatedAt', '').split('T')[0] if 'T' in n_app.get('updatedAt', '') else n_app.get('updatedAt'),
            "downloadURL": n_app.get('ipaUrl'),
            "iconURL": n_app.get('icon'),
            "localizedDescription": n_app.get('note', ''),
            "size": n_app.get('size'),
            "category": n_app.get('category', 'ألعاب')
        }
        old_apps.append(new_entry)

# حفظ الملف القديم المحدث
with open('old_repo/source', 'w', encoding='utf-8') as f:
    json.dump(old_source, f, indent=2, ensure_ascii=False)
