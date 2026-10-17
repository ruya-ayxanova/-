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
mp3 = [f for f in os.listdir('.') if f.lower().endswith('.mp3')][0]
shutil.copy(mp3, 'android/app/src/main/res/raw/azan.mp3')
shutil.copy('main.dart', 'lib/main.dart')
