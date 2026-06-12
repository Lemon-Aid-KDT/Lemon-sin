// screens/settings/notification_settings_screen.dart — 알림 설정 (figma 957:63)
//
// 가이드 08 (d) step 25. 토글 5종(복약 시간 / 분석 완료 / 리포트 / 마케팅 /
// 야간 무음). 로컬 설정 키로 저장. 복약 토글 off 시 예약 알림 일괄 해제.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../core/storage/local_prefs.dart';
import '../../features/reminders/medication_reminder_store.dart';
import '../../shared/services/local_notification_service.dart';
import '../../utils/design_tokens_v2.dart';

/// 알림 토글 항목 정의.
class _ToggleSpec {
  const _ToggleSpec(this.key, this.title, this.subtitle, this.defaultOn);

  final String key;
  final String title;
  final String subtitle;
  final bool defaultOn;
}

const List<_ToggleSpec> _kToggles = <_ToggleSpec>[
  _ToggleSpec('medication', '복약 시간 알림', '설정한 시간에 알려드려요', true),
  _ToggleSpec('analysis', '분석 완료 알림', '분석이 끝나면 알려드려요', true),
  _ToggleSpec('report', '리포트 알림', '주간 리포트가 준비되면 알려드려요', true),
  _ToggleSpec('marketing', '마케팅 알림', '혜택·소식을 받아볼게요', false),
  _ToggleSpec('quiet_night', '야간 무음', '밤 시간에는 알림을 끌게요', false),
];

/// 알림 설정 화면.
class NotificationSettingsScreen extends ConsumerStatefulWidget {
  /// 화면을 생성한다.
  const NotificationSettingsScreen({super.key});

  @override
  ConsumerState<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends ConsumerState<NotificationSettingsScreen> {
  late Map<String, bool> _settings;

  @override
  void initState() {
    super.initState();
    final LocalPrefs? prefs = ref.read(localPrefsProvider).value;
    final Map<String, bool> saved = prefs?.notificationSettings() ?? <String, bool>{};
    _settings = <String, bool>{
      for (final _ToggleSpec spec in _kToggles)
        spec.key: saved[spec.key] ?? spec.defaultOn,
    };
  }

  Future<void> _set(String key, bool value) async {
    setState(() => _settings[key] = value);
    await ref.read(localPrefsProvider).value?.setNotificationSettings(_settings);

    // 복약 토글 off → 예약 알림 일괄 해제. on → 저장된 알림 재등록.
    if (key == 'medication') {
      final ReminderScheduler scheduler = ref.read(reminderSchedulerProvider);
      if (!value) {
        await scheduler.cancelAll();
      } else {
        final MedicationReminderStore store = ref.read(
          medicationReminderStoreProvider,
        );
        await scheduler.reschedule(store.load());
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      appBar: AppBar(
        backgroundColor: AppColor.section,
        elevation: 0,
        title: const Text(
          '알림 설정',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
          ),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpace.page),
          children: <Widget>[
            Container(
              decoration: BoxDecoration(
                color: AppColor.surface,
                borderRadius: BorderRadius.circular(AppRadius.xl),
                boxShadow: AppShadow.elev1,
              ),
              padding: const EdgeInsets.symmetric(horizontal: AppSpace.lg),
              child: Column(
                children: <Widget>[
                  for (int i = 0; i < _kToggles.length; i += 1) ...<Widget>[
                    _ToggleRow(
                      spec: _kToggles[i],
                      value: _settings[_kToggles[i].key] ?? false,
                      onChanged: (bool v) => _set(_kToggles[i].key, v),
                    ),
                    if (i < _kToggles.length - 1)
                      const Divider(height: 1, color: AppColor.border),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.spec,
    required this.value,
    required this.onChanged,
  });

  final _ToggleSpec spec;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  spec.title,
                  style: AppText.subtitle.copyWith(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  spec.subtitle,
                  style: AppText.caption.copyWith(color: AppColor.inkTertiary),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            activeTrackColor: AppColor.brand,
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}
