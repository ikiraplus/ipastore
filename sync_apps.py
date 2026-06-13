import json
import os
import re

def slugify(text):
    text = text.lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9-]', '', text)

# 1. تحميل بيانات السورس الجديد
with open('jom.json', 'r', encoding='utf-8') as f:
    new_source = json.load(f)
new_apps = new_source.get('apps', [])

# 2. تحديد الملفات المراد تحديثها في الريبو القديم (الملف القديم والملف الجديد sorse)
files_to_update = ['old_repo/source', 'old_repo/sorse']

for file_path in files_to_update:
    # التحقق من وجود الملف، إذا كان موجوداً نقرأه، وإذا لم يكن موجوداً ننشئ هيكل افتراضي له
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_source = json.load(f)
            except:
                old_source = {"name": "iKiraPlus Store", "apps": []}
    else:
        old_source = {
            "name": "iKiraPlus Store",
            "identifier": "com.ikiraplus.store",
            "apps": []
        }
        
    old_apps = old_source.get('apps', [])
    old_apps_map = {app['name']: app for app in old_apps}

    for n_app in new_apps:
        name = n_app.get('name')
        if not name:
            continue
            
        # إذا التطبيق موجود مسبقاً نقوم بتحديث بياناته وروابطه فقط
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
            # إذا كان التطبيق جديد كلياً نقوم بصياغته بالأسلوب القديم وضمه للقائمة
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

    old_source['apps'] = old_apps
    
    # حفظ الملف بعد التحديث والتنسيق
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(old_source, f, indent=2, ensure_ascii=False)

print("✅ تم تحديث ملفات source و sorse بنجاح ومطابقتها مع السورس الجديد!")
