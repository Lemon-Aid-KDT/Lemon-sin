import 'package:flutter/material.dart';

import '../../core/storage/local_prefs.dart';
import '../../utils/design_tokens_v2.dart' as ds2;

/// 선택 옵션 정의 — 안정적인 id ↔ 한국어 라벨.
class _Option {
  const _Option(this.id, this.label);

  /// 로컬 저장에 쓰는 안정적인 옵션 id.
  final String id;

  /// 화면에 표시하는 한국어 라벨.
  final String label;
}

// 라벨은 디자인 시스템 온보딩(onboarding.jsx PURPOSES / HEALTH_CONCERNS)이 권위.
// '혈당 관리' 목적은 제품 스코프 제외(2026-06-10 redesign plan: 혈당 기능 제외)라
// 의도적으로 뺐다 — 라벨 날조가 아니라 권위 목록에서 스코프 항목만 제거.
const List<_Option> _purposeOptions = <_Option>[
  _Option('chronic', '만성질환 관리'),
  _Option('supplement', '영양제 섭취 관리'),
  _Option('diet', '식단 관리 & 다이어트'),
];

const List<_Option> _concernOptions = <_Option>[
  _Option('fatigue', '피로감'),
  _Option('chronic', '만성질환 관리'),
  _Option('liver', '간 건강'),
  _Option('chol', '혈중 콜레스테롤'),
  _Option('eye', '눈 건강'),
  _Option('muscle', '운동 능력 & 근육량'),
  _Option('bp', '혈압'),
  _Option('sleep', '수면 & 스트레스'),
  _Option('immune', '면역'),
];

/// 가입 목적 / 건강 관심사 선택 화면 — 가이드 01 2단계(로컬 전용).
///
/// 백엔드에 목적/관심사 필드가 없어 선택값은 [LocalPrefs]에만 저장한다(날조 금지).
/// 설정의 "관심사" 진입점으로 사용하며, 진입 시 기존 선택을 프리필한다.
class ProfileInterestsScreen extends StatefulWidget {
  /// 로컬 저장소를 주입받아 화면을 만든다.
  const ProfileInterestsScreen({required this.prefs, super.key});

  /// 목적/관심사를 영속하는 로컬 저장소.
  final LocalPrefs prefs;

  @override
  State<ProfileInterestsScreen> createState() => _ProfileInterestsScreenState();
}

class _ProfileInterestsScreenState extends State<ProfileInterestsScreen> {
  late final Set<String> _purposes;
  late final Set<String> _concerns;
  bool _saving = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _purposes = widget.prefs.profilePurposes().toSet();
    _concerns = widget.prefs.profileConcerns().toSet();
  }

  void _toggle(Set<String> target, String id) {
    setState(() {
      if (target.contains(id)) {
        target.remove(id);
      } else {
        target.add(id);
      }
      _saved = false;
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    await widget.prefs.setProfilePurposes(_purposes.toList(growable: false));
    await widget.prefs.setProfileConcerns(_concerns.toList(growable: false));
    if (!mounted) return;
    setState(() {
      _saving = false;
      _saved = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ds2.AppColor.bg,
      appBar: AppBar(
        backgroundColor: ds2.AppColor.bg,
        elevation: 0,
        title: Text('관심사', style: ds2.AppText.subtitle),
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  ds2.AppSpace.page,
                  ds2.AppSpace.lg,
                  ds2.AppSpace.page,
                  ds2.AppSpace.lg,
                ),
                children: <Widget>[
                  Text('무엇을 위해 찾아주셨나요?', style: ds2.AppText.title),
                  const SizedBox(height: ds2.AppSpace.sm),
                  Text(
                    '고른 항목에 맞춰 분석을 보여드려요. 여러 개를 골라도 괜찮아요.',
                    style: ds2.AppText.body.copyWith(
                      color: ds2.AppColor.inkSecondary,
                    ),
                  ),
                  const SizedBox(height: ds2.AppSpace.xl),
                  const _SectionTitle('가입 목적'),
                  const SizedBox(height: ds2.AppSpace.md),
                  _ChipWrap(
                    options: _purposeOptions,
                    selected: _purposes,
                    onToggle: (String id) => _toggle(_purposes, id),
                  ),
                  const SizedBox(height: ds2.AppSpace.xl),
                  const _SectionTitle('건강 고민'),
                  const SizedBox(height: ds2.AppSpace.md),
                  _ChipWrap(
                    options: _concernOptions,
                    selected: _concerns,
                    onToggle: (String id) => _toggle(_concerns, id),
                  ),
                ],
              ),
            ),
            if (_saved)
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: ds2.AppSpace.page,
                ),
                child: Row(
                  children: <Widget>[
                    const Icon(
                      Icons.check_circle_rounded,
                      color: ds2.AppColor.success,
                      size: 18,
                    ),
                    const SizedBox(width: ds2.AppSpace.xs),
                    Text(
                      '관심사를 저장했어요',
                      style: ds2.AppText.caption.copyWith(
                        color: ds2.AppColor.success,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                ds2.AppSpace.page,
                ds2.AppSpace.md,
                ds2.AppSpace.page,
                ds2.AppSpace.pageBottom,
              ),
              child: ds2.AppPrimaryButton(
                label: '저장하기',
                accent: true,
                loading: _saving,
                onPressed: _save,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: ds2.AppText.bodyLg.copyWith(fontWeight: FontWeight.w700),
    );
  }
}

class _ChipWrap extends StatelessWidget {
  const _ChipWrap({
    required this.options,
    required this.selected,
    required this.onToggle,
  });

  final List<_Option> options;
  final Set<String> selected;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: ds2.AppSpace.sm,
      runSpacing: ds2.AppSpace.sm,
      children: <Widget>[
        for (final _Option option in options)
          _SelectChip(
            label: option.label,
            selected: selected.contains(option.id),
            onTap: () => onToggle(option.id),
          ),
      ],
    );
  }
}

class _SelectChip extends StatelessWidget {
  const _SelectChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? ds2.AppColor.brandSoft : ds2.AppColor.sunken,
      borderRadius: BorderRadius.circular(ds2.AppRadius.full),
      child: InkWell(
        borderRadius: BorderRadius.circular(ds2.AppRadius.full),
        onTap: onTap,
        child: Container(
          height: 48,
          padding: const EdgeInsets.symmetric(horizontal: ds2.AppSpace.lg),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(ds2.AppRadius.full),
            border: Border.all(
              color: selected ? ds2.AppColor.brand : ds2.AppColor.border,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Text(
            label,
            style: ds2.AppText.body.copyWith(
              color: selected ? ds2.AppColor.brandDeep : ds2.AppColor.ink,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}
