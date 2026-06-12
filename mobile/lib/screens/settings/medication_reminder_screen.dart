// screens/settings/medication_reminder_screen.dart — 복약 알림 (figma 916:76)
//
// 가이드 08 (d) step 24. 시간 행(토글) 목록 + [시간 추가] → 시간 휠 + 요일 칩 7개.
// 저장 시 로컬 스케줄 재등록 + 서버(/notifications/reminders) 동기화.
// 로컬이 1차 소스 — 서버 실패 시 로컬은 유지하고 재시도 안내만 띄운다.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../features/reminders/medication_reminder_models.dart';
import '../../features/reminders/medication_reminder_store.dart';
import '../../features/reminders/medication_reminder_sync.dart';
import '../../shared/services/local_notification_service.dart';
import '../../utils/design_tokens_v2.dart';
import '../../widgets/common/time_wheel_sheet.dart';

/// 요일 칩 라벨 (1=월 … 7=일).
const List<String> _kWeekdayLabels = <String>['월', '화', '수', '목', '금', '토', '일'];

/// 복약 알림 설정 화면.
class MedicationReminderScreen extends ConsumerStatefulWidget {
  /// 화면을 생성한다.
  const MedicationReminderScreen({super.key});

  @override
  ConsumerState<MedicationReminderScreen> createState() =>
      _MedicationReminderScreenState();
}

class _MedicationReminderScreenState
    extends ConsumerState<MedicationReminderScreen> {
  List<MedicationReminder> _reminders = <MedicationReminder>[];
  bool _permissionDenied = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _reminders = ref.read(medicationReminderStoreProvider).load();
  }

  Future<void> _addReminder() async {
    final TimeOfDayResult? time = await showTimeWheelSheet(context);
    if (time == null || !mounted) return;
    setState(() {
      _reminders = <MedicationReminder>[
        ..._reminders,
        MedicationReminder(
          id: 'rem-${DateTime.now().microsecondsSinceEpoch}',
          hour: time.hour,
          minute: time.minute,
          weekdays: <int>{1, 2, 3, 4, 5, 6, 7},
        ),
      ];
    });
  }

  void _toggleEnabled(int index, bool value) {
    setState(() {
      _reminders = List<MedicationReminder>.of(_reminders)
        ..[index] = _reminders[index].copyWith(enabled: value);
    });
  }

  void _toggleWeekday(int index, int weekday) {
    setState(() {
      final MedicationReminder reminder = _reminders[index];
      final Set<int> next = Set<int>.of(reminder.weekdays);
      if (next.contains(weekday)) {
        next.remove(weekday);
      } else {
        next.add(weekday);
      }
      _reminders = List<MedicationReminder>.of(_reminders)
        ..[index] = reminder.copyWith(weekdays: next);
    });
  }

  void _removeReminder(int index) {
    setState(() {
      _reminders = List<MedicationReminder>.of(_reminders)..removeAt(index);
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);

    // 1) 로컬 영속.
    final MedicationReminderStore store = ref.read(
      medicationReminderStoreProvider,
    );
    await store.save(_reminders);

    // 2) 로컬 알림 권한 + 재스케줄 (1차 소스).
    final ReminderScheduler scheduler = ref.read(reminderSchedulerProvider);
    final bool granted = await scheduler.ensurePermissions();
    if (!granted) {
      if (!mounted) return;
      setState(() => _permissionDenied = true);
    }
    await scheduler.reschedule(_reminders);

    // 3) 서버 동기화 (동기화 사본 — 실패해도 로컬 유지).
    final MedicationReminderSync sync = ref.read(
      medicationReminderSyncProvider,
    );
    bool anyServerFailure = false;
    for (final MedicationReminder reminder in _reminders) {
      if (!reminder.enabled) continue;
      if (reminder.serverId != null) continue; // 이미 동기화됨.
      final ReminderSyncResult result = await sync.push(reminder);
      if (!result.synced) anyServerFailure = true;
    }

    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(
        SnackBar(
          content: Text(
            anyServerFailure
                ? '알림을 설정했어요. 서버 동기화는 잠시 후 다시 시도해주세요'
                : '알림을 설정했어요',
          ),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      appBar: AppBar(
        backgroundColor: AppColor.section,
        elevation: 0,
        title: const Text(
          '복약 알림',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
          ),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            if (_permissionDenied) const _PermissionBanner(),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(AppSpace.page),
                children: <Widget>[
                  for (int i = 0; i < _reminders.length; i += 1)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpace.md),
                      child: _ReminderCard(
                        reminder: _reminders[i],
                        onToggle: (bool v) => _toggleEnabled(i, v),
                        onWeekday: (int w) => _toggleWeekday(i, w),
                        onDelete: () => _removeReminder(i),
                      ),
                    ),
                  _AddTimeButton(onTap: _addReminder),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(AppSpace.page),
              child: SizedBox(
                height: 52,
                child: AppPrimaryButton(
                  label: '저장하기',
                  loading: _saving,
                  onPressed: _saving ? null : _save,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PermissionBanner extends StatelessWidget {
  const _PermissionBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColor.warningSoft,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.page,
        vertical: AppSpace.md,
      ),
      child: Text(
        '알림 권한을 허용해야 시간에 맞춰 알려드릴 수 있어요',
        style: AppText.caption.copyWith(
          color: AppColor.warning,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _ReminderCard extends StatelessWidget {
  const _ReminderCard({
    required this.reminder,
    required this.onToggle,
    required this.onWeekday,
    required this.onDelete,
  });

  final MedicationReminder reminder;
  final ValueChanged<bool> onToggle;
  final ValueChanged<int> onWeekday;
  final VoidCallback onDelete;

  String get _timeLabel {
    final int hour12 = reminder.hour % 12 == 0 ? 12 : reminder.hour % 12;
    final String ampm = reminder.hour < 12 ? '오전' : '오후';
    return '$ampm $hour12:${reminder.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                _timeLabel,
                style: AppText.subtitle.copyWith(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              IconButton(
                onPressed: onDelete,
                icon: const Icon(
                  Icons.delete_outline_rounded,
                  color: AppColor.inkTertiary,
                ),
              ),
              Switch(
                value: reminder.enabled,
                activeTrackColor: AppColor.brand,
                onChanged: onToggle,
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              for (int w = 1; w <= 7; w += 1)
                _WeekdayChip(
                  label: _kWeekdayLabels[w - 1],
                  selected: reminder.weekdays.contains(w),
                  onTap: () => onWeekday(w),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _WeekdayChip extends StatelessWidget {
  const _WeekdayChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? AppColor.brand : AppColor.surface,
          shape: BoxShape.circle,
          border: Border.all(
            color: selected ? AppColor.brand : AppColor.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: selected ? Colors.white : AppColor.inkSecondary,
          ),
        ),
      ),
    );
  }
}

class _AddTimeButton extends StatelessWidget {
  const _AddTimeButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AppColor.surface,
          borderRadius: BorderRadius.circular(AppRadius.xl),
          border: Border.all(color: AppColor.border),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            const Icon(Icons.add_rounded, color: AppColor.brandDeep),
            const SizedBox(width: AppSpace.sm),
            Text(
              '시간 추가',
              style: AppText.body.copyWith(
                fontWeight: FontWeight.w700,
                color: AppColor.brandDeep,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
