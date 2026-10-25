import re, os, shutil
mf = 'android/app/src/main/AndroidManifest.xml'
s = open(mf, encoding='utf-8').read()
perms = '''<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS"/>
<uses-permission android:name="android.permission.WAKE_LOCK"/>
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
import subprocess, sys

def get_ffmpeg():
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--break-system-packages', 'imageio-ffmpeg'])
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print('ffmpeg bulunamadı:', e)
        return None

FF = get_ffmpeg()
# Internetten ezan sesleri: ezan_listesi.txt icindeki "Ad|Baglanti" satirlarini indir
import urllib.request
if os.path.exists('ezan_listesi.txt'):
    for line in open('ezan_listesi.txt', encoding='utf-8').read().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '|' not in line:
            continue
        name, url = [x.strip() for x in line.split('|', 1)]
        safe = re.sub(r'[^A-Za-z0-9_\-]', '_', name) or 'ezan'
        tmp = 'indirilen_' + safe + '.bin'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=120).read()
            if len(data) < 5000 or len(data) > 40000000:
                raise RuntimeError('dosya boyutu gecersiz: %d' % len(data))
            if not FF:
                raise RuntimeError('ffmpeg yok')
            open(tmp, 'wb').write(data)
            subprocess.run([FF, '-y', '-loglevel', 'error', '-i', tmp, '-vn', '-b:a', '128k', safe + '.mp3'], check=True)
            print('EZAN SESI indirildi:', name)
        except Exception as e:
            print('EZAN SESI indirilemedi:', name, e)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

res_list = []
for f in sorted(os.listdir('.')):
    if f.lower().endswith('.mp3'):
        base = f[:-4]
        res = re.sub(r'[^a-z0-9_]', '_', base.lower())
        if not re.match(r'[a-z]', res):
            res = 'm_' + res
        shutil.copy(f, 'android/app/src/main/res/raw/' + res + '.mp3')
        for lv in (25, 50, 75, 150):
            out = 'android/app/src/main/res/raw/%s_v%d.mp3' % (res, lv)
            flt = 'volume=%s' % (lv / 100.0) + (',alimiter=limit=0.95' if lv > 100 else '')
            try:
                if not FF:
                    raise RuntimeError('ffmpeg yok')
                subprocess.run([FF, '-y', '-loglevel', 'error', '-i', f, '-filter:a', flt, out], check=True)
            except Exception as e:
                print('Ses seviyesi dosyası üretilemedi, orijinal kopyalandı:', e)
                shutil.copy(f, out)
        res_list.append(res + '|' + base.replace('_', ' '))
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
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.reflect.TypeToken { *; }
-keep class * extends com.google.gson.reflect.TypeToken
''')

# Uygulama simgesi: icon.png varsa tüm boyutlara çevir
SIZES = [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]
if not os.path.exists('icon.png'):
    print('UYARI: icon.png reponun ana klasorunde bulunamadi, varsayilan Flutter simgesi kalacak')
else:
    for dname, sz in SIZES:
        os.makedirs('android/app/src/main/res/mipmap-%s' % dname, exist_ok=True)
    done = False
    try:
        try:
            from PIL import Image
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--break-system-packages', 'pillow'])
            from PIL import Image
        im = Image.open('icon.png').convert('RGBA')
        for dname, sz in SIZES:
            im.resize((sz, sz), Image.LANCZOS).save('android/app/src/main/res/mipmap-%s/ic_launcher.png' % dname)
        done = True
    except Exception as e:
        print('Pillow ile simge uretilemedi:', e)
    if not done and FF:
        try:
            for dname, sz in SIZES:
                subprocess.run([FF, '-y', '-loglevel', 'error', '-i', 'icon.png', '-vf', 'scale=%d:%d' % (sz, sz),
                                'android/app/src/main/res/mipmap-%s/ic_launcher.png' % dname], check=True)
            done = True
        except Exception as e:
            print('ffmpeg ile simge uretilemedi:', e)
    # Android 8+ uyarlanabilir simge varsa PNG'nin onune gecer: kaldir
    ad = 'android/app/src/main/res/mipmap-anydpi-v26'
    if os.path.isdir(ad):
        shutil.rmtree(ad)
    print('SIMGE URETILDI' if done else 'UYARI: simge uretilemedi')

# Release derlemesinde kod küçültmeyi (R8) Flutter eklentisi de açabiliyor: derleme ayarı
# yüklendikten SONRA tekrar kapat ve koruma kurallarını ekle
b = open(g, encoding='utf-8').read()
b += """
afterEvaluate {
    android.buildTypes.release.minifyEnabled = false
    android.buildTypes.release.shrinkResources = false
    android.buildTypes.release.proguardFiles('proguard-rules.pro')
}
"""
open(g, 'w', encoding='utf-8').write(b)
print('----- build.gradle -----')
print(b)


# Kıble pusulası için gerekli paket
ps2 = open('pubspec.yaml', encoding='utf-8').read()
if 'flutter_compass' not in ps2:
    ps2 = ps2.replace('  shared_preferences: ^2.3.2', '  shared_preferences: ^2.3.2\n  flutter_compass: ^0.8.1')
    open('pubspec.yaml', 'w', encoding='utf-8').write(ps2)


# Sistem ayarlarını açmak için gerekli paket
ps3 = open('pubspec.yaml', encoding='utf-8').read()
if 'android_intent_plus' not in ps3:
    ps3 = ps3.replace('  shared_preferences: ^2.3.2', '  shared_preferences: ^2.3.2\n  android_intent_plus: ^5.1.0')
    open('pubspec.yaml', 'w', encoding='utf-8').write(ps3)


# Kalem (hat) yazı tipleri: internetten indir ve uygulamaya göm
import urllib.request
PENS = [
    ('Amiri', 'Nesih', 'https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf'),
    ('NotoNastaliqUrdu', 'Talik', 'https://raw.githubusercontent.com/google/fonts/main/ofl/notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf'),
    ('ArefRuqaa', "Rik'a", 'https://raw.githubusercontent.com/google/fonts/main/ofl/arefruqaa/ArefRuqaa-Regular.ttf'),
    ('ReemKufi', 'Kûfî', 'https://raw.githubusercontent.com/google/fonts/main/ofl/reemkufi/ReemKufi%5Bwght%5D.ttf'),
]
os.makedirs('fonts', exist_ok=True)
pen_lines = []
for fam, disp, url in PENS:
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
        if len(data) < 20000 or data[:4] not in (b'\x00\x01\x00\x00', b'OTTO', b'true', b'ttcf'):
            raise RuntimeError('gecersiz yazi tipi dosyasi')
        open('fonts/%s.ttf' % fam, 'wb').write(data)
        pen_lines.append(fam + '|' + disp)
        print('KALEM indirildi:', fam, len(data))
    except Exception as e:
        print('KALEM indirilemedi:', fam, e)
open('pens.txt', 'w', encoding='utf-8').write('\n'.join(pen_lines) + '\n')
ps4 = open('pubspec.yaml', encoding='utf-8').read()
if 'pens.txt' not in ps4:
    anchor = '    - muezzins.txt' if '    - muezzins.txt' in ps4 else '    - cities.txt'
    ps4 = ps4.replace(anchor, anchor + '\n    - pens.txt')
fy = ''.join('    - family: %s\n      fonts:\n        - asset: fonts/%s.ttf\n' % (l.split('|')[0], l.split('|')[0]) for l in pen_lines)
if fy and '  fonts:' not in ps4:
    ps4 = ps4.replace('  uses-material-design: true\n', '  uses-material-design: true\n  fonts:\n' + fy)
open('pubspec.yaml', 'w', encoding='utf-8').write(ps4)
