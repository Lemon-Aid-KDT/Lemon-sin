import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:lemon_aid_mobile/app_providers.dart';
import 'package:lemon_aid_mobile/core/api/api_client.dart';
import 'package:lemon_aid_mobile/core/storage/local_prefs.dart';
import 'package:lemon_aid_mobile/features/reminders/medication_reminder_models.dart';
import 'package:lemon_aid_mobile/features/reminders/medication_reminder_store.dart';
import 'package:lemon_aid_mobile/features/reminders/medication_reminder_sync.dart';
import 'package:lemon_aid_mobile/screens/settings/medication_reminder_screen.dart';
import 'package:lemon_aid_mobile/shared/services/local_notification_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 스케줄 호출만 기록하는 가짜 스케줄러 (실발송 없음 — 단위 검증용).
class _FakeScheduler implements ReminderScheduler {
  bool permissionGranted = true;
  int rescheduleCalls = 0;
  int cancelAllCalls = 0;
  List<MedicationReminder> lastReminders = <MedicationReminder>[];

  @override
  Future<bool> ensurePermissions() async => permissionGranted;

  @override
  Future<List<ScheduledNotification>> reschedule(
    List<MedicationReminder> reminders,
  ) async {
    rescheduleCalls += 1;
    lastReminders = reminders;
    return buildScheduleEntries(reminders);
  }

  @override
  Future<void> cancelAll() async {
    cancelAllCalls += 1;
  }
}

class _FakeClient extends http.BaseClient {
  _FakeClient(this.handler);

  final Future<http.StreamedResponse> Function(http.Request request) handler;
  final List<http.Request> requests = <http.Request>[];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final http.Request typed = request as http.Request;
    requests.add(typed);
    return handler(typed);
  }
}

http.StreamedResponse _json(Map<String, dynamic> body, int status) {
  return http.StreamedResponse(
    Stream<List<int>>.value(utf8.encode(jsonEncode(body))),
    status,
    headers: const <String, String>{'content-type': 'application/json'},
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pump(
    WidgetTester tester, {
    required _FakeScheduler scheduler,
    required _FakeClient client,
    required LocalPrefs prefs,
  }) async {
    tester.view.physicalSize = const Size(1200, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          reminderSchedulerProvider.overrideWithValue(scheduler),
          medicationReminderStoreProvider.overrideWithValue(
            MedicationReminderStore(prefs: prefs),
          ),
          medicationReminderSyncProvider.overrideWithValue(
            MedicationReminderSync(
              apiClient: ApiClient(
                baseUrl: 'https://api.example.com/api/v1',
                httpClient: client,
              ),
            ),
          ),
        ],
        child: const MaterialApp(home: MedicationReminderScreen()),
      ),
    );
    await tester.pump();
  }

  testWidgets('adding a time then saving reschedules and syncs to server',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final LocalPrefs prefs = await LocalPrefs.create();
    final _FakeScheduler scheduler = _FakeScheduler();
    final _FakeClient client = _FakeClient(
      (http.Request request) async => _json(<String, dynamic>{'id': 'srv-1'}, 201),
    );

    await pump(tester, scheduler: scheduler, client: client, prefs: prefs);

    // [시간 추가] → 시간 휠 → [확인].
    await tester.tap(find.text('시간 추가'));
    await tester.pumpAndSettle();
    expect(find.text('알림 시간'), findsOneWidget); // 휠 시트 제목
    await tester.tap(find.text('확인'));
    await tester.pumpAndSettle();

    // 한 개의 알림 카드가 추가됐다.
    expect(find.byType(Switch), findsWidgets);

    // 저장 → reschedule 1회 + 서버 POST.
    await tester.tap(find.text('저장하기'));
    await tester.pumpAndSettle();

    expect(scheduler.rescheduleCalls, 1);
    expect(scheduler.lastReminders, hasLength(1));
    expect(
      client.requests.single.url.path,
      '/api/v1/notifications/reminders',
    );
    final Map<String, dynamic> body =
        jsonDecode(client.requests.single.body) as Map<String, dynamic>;
    expect(body['category'], 'supplement_reminder');
    expect((body['message'] as String).contains('처방'), isFalse);
    // 저장이 영속됐다.
    expect(prefs.medicationReminders(), hasLength(1));
  });

  testWidgets('weekday chip toggle removes that day from the schedule',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'medication_reminders': jsonEncode(<Map<String, dynamic>>[
        const MedicationReminder(
          id: 'rem-1',
          hour: 8,
          minute: 0,
          weekdays: <int>{1, 2, 3, 4, 5, 6, 7},
        ).toJson(),
      ]),
    });
    final LocalPrefs prefs = await LocalPrefs.create();
    final _FakeScheduler scheduler = _FakeScheduler();
    final _FakeClient client = _FakeClient(
      (http.Request request) async => _json(<String, dynamic>{'id': 'srv-1'}, 201),
    );

    await pump(tester, scheduler: scheduler, client: client, prefs: prefs);

    // '일'(weekday 7) 칩을 해제.
    await tester.tap(find.text('일'));
    await tester.pump();
    await tester.tap(find.text('저장하기'));
    await tester.pumpAndSettle();

    expect(scheduler.lastReminders.single.weekdays.contains(7), isFalse);
    expect(scheduler.lastReminders.single.weekdays, hasLength(6));
  });
}
