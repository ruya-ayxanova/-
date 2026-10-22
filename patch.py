import re, os, shutil
mf = 'android/app/src/main/AndroidManifest.xml'
s = open(mf, encoding='utf-8').read()
perms = '''<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
<uses-permission android:name="android.permission.VIBRATE"/>
'''
recv = '''<receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver"/>
<receiver android:exported="false" android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
<intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/><action android:name="android.intent.action.MY_PACKAGE_REPLACED"/><action android:name="android.intent.action.QUICKBOOT_POWERON"/><action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/></intent-filter>
</receiver>
'''
s = s.replace('<application', perms + '<application', 1).replace('</application>', recv + '</application>', 1)
s = re.sub(r'android:label="[^"]*"', 'android:label="تورک تقویمی و اذانی"', s, count=1)
open(mf, 'w', encoding='utf-8').write(s)
g = 'android/app/build.gradle'
b = open(g).read()
b = re.sub(r'compileOptions\s*\{', 'compileOptions {\n        coreLibraryDesugaringEnabled true', b, count=1)
b += "\ndependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.0.4'\n}\n"
open(g, 'w').write(b)
os.makedirs('android/app/src/main/res/raw', exist_ok=True)
res_list = []
for f in sorted(os.listdir('.')):
    if f.lower().endswith('.mp3'):
        base = f[:-4]
        res = re.sub(r'[^a-z0-9_]', '_', base.lower())
        if not re.match(r'[a-z]', res):
            res = 'm_' + res
        shutil.copy(f, 'android/app/src/main/res/raw/' + res + '.mp3')
        res_list.append(res + '|' + base)
open('muezzins.txt', 'w', encoding='utf-8').write('\n'.join(res_list) + '\n')
ps = open('pubspec.yaml', encoding='utf-8').read()
if 'muezzins.txt' not in ps:
    open('pubspec.yaml', 'w', encoding='utf-8').write(ps.replace('    - cities.txt', '    - cities.txt\n    - muezzins.txt'))
shutil.copy('main.dart', 'lib/main.dart')

# Release kodu küçültme (R8) bildirim eklentisini bozuyor: kapat ve kuralları ekle
b = open(g, encoding='utf-8').read()
b = re.sub(r'release\s*\{', "release {\n            minifyEnabled false\n            shrinkResources false\n            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'", b, count=1)
open(g, 'w', encoding='utf-8').write(b)
open('android/app/proguard-rules.pro', 'w').write('''-keep class com.dexterous.flutterlocalnotifications.** { *; }
