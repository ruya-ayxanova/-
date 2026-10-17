import 'dart:math' as m;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

const names = ['صبح اذانی', 'گون دوغومو', 'ناهار اذانی', 'ایکیندی اذانی', 'گون باتومی', 'آخشام اذانی', 'گجه اذانی', 'گجه یاریسی'];
const adhanIdx = [0, 2, 3, 5, 6]; // ezan çalınacak vakitler
final plugin = FlutterLocalNotificationsPlugin();
const details = NotificationDetails(
  android: AndroidNotificationDetails('azan', 'Ezan',
      channelDescription: 'Ezan vakitleri',
      importance: Importance.max,
      priority: Priority.high,
      playSound: true,
      sound: RawResourceAndroidNotificationSound('azan'),
      audioAttributesUsage: AudioAttributesUsage.alarm),
);

class City {
  final String group, name;
  final double lat, lng;
  City(this.group, this.name, this.lat, this.lng);
}

double fix(double a, double b) => a - b * (a / b).floorToDouble();
double rad(double d) => d * m.pi / 180;
double deg(double r) => r * 180 / m.pi;

// Tahran Üniversitesi yöntemi: sabah 17,7°, akşam 4,5°, yatsı 14°
List<double> calc(DateTime date, double lat, double lng) {
  final off = DateTime(date.year, date.month, date.day, 12).timeZoneOffset.inMinutes / 60;
  final d = DateTime.utc(date.year, date.month, date.day, 12).millisecondsSinceEpoch / 86400000.0 + 2440587.5 - 2451545;
  final g = fix(357.529 + .98560028 * d, 360), q = fix(280.459 + .98564736 * d, 360);
  final l = fix(q + 1.915 * m.sin(rad(g)) + .02 * m.sin(rad(2 * g)), 360), e = 23.439 - 3.6e-7 * d;
  final ra = fix(deg(m.atan2(m.cos(rad(e)) * m.sin(rad(l)), m.cos(rad(l)))) / 15, 24);
  final dec = deg(m.asin(m.sin(rad(e)) * m.sin(rad(l))));
  final eq = fix(q / 15 - ra + 12, 24) - 12, noon = 12 + off - lng / 15 - eq;
  double t(double a) => deg(m.acos((-m.sin(rad(a)) - m.sin(rad(dec)) * m.sin(rad(lat))) / (m.cos(rad(dec)) * m.cos(rad(lat))))) / 15;
  final asr = -deg(m.atan(1 / (1 + m.tan(rad((lat - dec).abs())))));
  final f = noon - t(17.7), ss = noon + t(.833);
  return [f, noon - t(.833), noon, noon + t(asr), ss, noon + t(4.5), noon + t(14), ss + (f + 24 - ss) / 2];
}

String fmt(double h) {
  if (h.isNaN) return '--:--';
  final mm = (fix(h, 24) * 60).round() % 1440;
  return '${(mm ~/ 60).toString().padLeft(2, '0')}:${(mm % 60).toString().padLeft(2, '0')}';
}

String err = '';

Future<void> sched(int id, String title, tz.TZDateTime t) async {
  try {
    await plugin.zonedSchedule(id, title, '', t, details,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime);
  } catch (_) {
    await plugin.zonedSchedule(id, title, '', t, details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime);
  }
}

Future<void> schedule(City c) async {
  await plugin.cancelAll();
  final now = DateTime.now();
  var id = 0;
  for (var k = 0; k < 14; k++) {
    final day = DateTime(now.year, now.month, now.day + k);
    final tm = calc(day, c.lat, c.lng);
    for (final i in adhanIdx) {
      if (tm[i].isNaN) continue;
      final at = day.add(Duration(minutes: (tm[i] * 60).round()));
      if (!at.isAfter(now)) continue;
      await sched(id++, names[i], tz.TZDateTime.from(at, tz.local));
    }
  }
}

Future<void> setup() async {
  try {
    tzdata.initializeTimeZones();
    var name = 'UTC';
    try {
      name = await FlutterTimezone.getLocalTimezone();
    } catch (e) {
      err += 'saat dilimi: $e\n';
    }
    try {
      tz.setLocalLocation(tz.getLocation(name));
    } catch (e) {
      err += 'saat dilimi ($name): $e\n';
    }
    await plugin.initialize(const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')));
    final a = plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    try {
      await a?.requestNotificationsPermission();
    } catch (e) {
      err += 'bildirim izni: $e\n';
    }
    try {
      await a?.requestExactAlarmsPermission();
    } catch (e) {
      err += 'alarm izni: $e\n';
    }
  } catch (e) {
    err += 'başlatma: $e\n';
  }
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(MaterialApp(
      title: 'تورک تقویمی و اذانی',
      theme: ThemeData(colorSchemeSeed: const Color(0xFF17302B), useMaterial3: true),
      home: const Home()));
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  List<City> cities = [];
  City? city;
  String msg = '';

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    await setup();
    try {
      final raw = await rootBundle.loadString('cities.txt');
      cities = raw.trim().split('\n').map((l) {
        final a = l.split('|');
        return City(a[0], a[1], double.parse(a[2]), double.parse(a[3]));
      }).toList();
    } catch (e) {
      err += 'şehir listesi: $e\n';
    }
    if (cities.isEmpty) {
      setState(() {});
      return;
    }
    var c = cities.first;
    try {
      final p = await SharedPreferences.getInstance();
      final n = p.getString('city');
      c = cities.firstWhere((x) => x.name == n,
          orElse: () => cities.firstWhere((x) => x.name == 'İstanbul', orElse: () => cities.first));
    } catch (e) {
      err += 'kayıt: $e\n';
    }
    setState(() => city = c);
    try {
      await schedule(c);
      setState(() => msg = 'Ezan 14 gün için kuruldu');
    } catch (e) {
      setState(() => err += 'alarm kurma: $e\n');
    }
  }

  Future<void> test() async {
    try {
      await sched(9999, 'Deneme', tz.TZDateTime.now(tz.local).add(const Duration(seconds: 10)));
      setState(() => msg = '10 saniye sonra ezan çalmalı');
    } catch (e) {
      setState(() => err += 'deneme: $e\n');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (city == null) {
      return Scaffold(
          body: Center(
              child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: err.isEmpty ? const CircularProgressIndicator() : SelectableText(err))));
    }
    final tm = calc(DateTime.now(), city!.lat, city!.lng);
    return Scaffold(
      appBar: AppBar(title: const Text('تورک تقویمی و اذانی')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        DropdownButton<City>(
          isExpanded: true,
          value: city,
          items: [for (final x in cities) DropdownMenuItem(value: x, child: Text('${x.group}  ${x.name}'))],
          onChanged: (x) async {
            try {
              final p = await SharedPreferences.getInstance();
              await p.setString('city', x!.name);
              await schedule(x);
              setState(() {
                city = x;
                msg = 'Ezan 14 gün için kuruldu';
              });
            } catch (e) {
              setState(() {
                city = x;
                err += 'şehir değiştirme: $e\n';
              });
            }
          },
        ),
        for (var i = 0; i < 8; i++)
          ListTile(title: Text(names[i]), trailing: Text(fmt(tm[i]), style: const TextStyle(fontSize: 20))),
        const SizedBox(height: 12),
        FilledButton(onPressed: test, child: const Text('Ezanı 10 saniye sonra dene')),
        Padding(padding: const EdgeInsets.only(top: 12), child: Text(msg)),
        if (err.isNotEmpty) SelectableText(err, style: const TextStyle(color: Colors.red)),
      ]),
    );
  }
}
