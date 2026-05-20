// screens/health_profile_screen.dart — 만성질환·복약·목적·신체 통합
//
// 쿼리: ?tab=disease|drug|goal|body
//
// 디자인 (LADS v2):
//   - 상단 흰 헤더 (뒤로 + 제목)
//   - 4 탭 segment
//   - 각 탭: 칩 선택 + 자유 입력 + 저장
//
// 의료법 가드: "처방"·"진단"·"치료"·"효능"·"효과" 금지
//   → "기록 / 입력 / 도움" 표현으로
//
// 백엔드 연동: TODO (지금은 로컬 mock state)

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v2.dart';

enum _Tab { disease, drug, goal, body }

class HealthProfileScreen extends StatefulWidget {
  final String initialTab;
  const HealthProfileScreen({super.key, this.initialTab = 'disease'});

  @override
  State<HealthProfileScreen> createState() => _HealthProfileScreenState();
}

class _HealthProfileScreenState extends State<HealthProfileScreen> {
  late _Tab _tab;

  // 선택 상태 (mock — 추후 Riverpod state 연동)
  final Set<String> _diseases = {};
  final Set<String> _drugs = {};
  final Set<String> _goals = {};

  final _heightCtl = TextEditingController(text: '175');
  final _weightCtl = TextEditingController(text: '70');

  static const _diseaseOptions = [
    '당뇨', '고혈압', '고지혈증', '갑상선', '심혈관', '신장',
    '간', '소화기', '관절·근육', '알레르기', '수면 장애', '없음',
  ];
  static const _drugOptions = [
    '혈압약', '당뇨약', '항응고제', '갑상선약', '콜레스테롤약',
    '소화제', '진통제', '항히스타민', '수면제', '없음',
  ];
  static const _goalOptions = [
    '체중 관리', '혈당 안정', '혈압 관리', '근육 증가',
    '면역력', '수면 개선', '소화 개선', '에너지', '뼈·관절',
  ];

  @override
  void initState() {
    super.initState();
    _tab = _parseTab(widget.initialTab);
  }

  _Tab _parseTab(String s) {
    switch (s) {
      case 'drug': return _Tab.drug;
      case 'goal': return _Tab.goal;
      case 'body': return _Tab.body;
      default:     return _Tab.disease;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _TopBar(),
            _TabSegment(
              current: _tab,
              onChange: (t) {
                HapticFeedback.selectionClick();
                setState(() => _tab = t);
              },
            ),
            Expanded(
              child: _buildTab(),
            ),
            _SaveBar(onSave: () {
              HapticFeedback.mediumImpact();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: const Text('저장됐어요'),
                  backgroundColor: AppColor.brand,
                ),
              );
              if (context.canPop()) context.pop();
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildTab() {
    switch (_tab) {
      case _Tab.disease:
        return _ChipPicker(
          title: '앓고 있는 만성질환을 골라주세요',
          subtitle: '복약·식단 교차 점검에 쓰여요. 여러 개 선택할 수 있어요.',
          options: _diseaseOptions,
          selected: _diseases,
        );
      case _Tab.drug:
        return _ChipPicker(
          title: '드시는 약을 골라주세요',
          subtitle: '영양제와 함께 먹어도 되는지 확인하는 데 쓰여요.',
          options: _drugOptions,
          selected: _drugs,
        );
      case _Tab.goal:
        return _ChipPicker(
          title: '관심 있는 건강 목적을 골라주세요',
          subtitle: '맞춤 추천에 반영돼요. 여러 개 가능.',
          options: _goalOptions,
          selected: _goals,
        );
      case _Tab.body:
        return _BodyForm(
          heightCtl: _heightCtl,
          weightCtl: _weightCtl,
        );
    }
  }

  @override
  void dispose() {
    _heightCtl.dispose();
    _weightCtl.dispose();
    super.dispose();
  }
}

// ═══════════════════════════════════════════
// 상단 바
// ═══════════════════════════════════════════
class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.section,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.sm,
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => context.canPop()
                ? context.pop()
                : context.go('/shell/settings'),
            child: Container(
              width: 40, height: 40,
              alignment: Alignment.center,
              child: const Icon(Icons.arrow_back_rounded,
                  color: AppColor.ink, size: 22),
            ),
          ),
          const Spacer(),
          const Text(
            '내 건강 정보',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const Spacer(),
          const SizedBox(width: 40, height: 40),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 4탭 segment
// ═══════════════════════════════════════════
class _TabSegment extends StatelessWidget {
  final _Tab current;
  final ValueChanged<_Tab> onChange;
  const _TabSegment({required this.current, required this.onChange});

  @override
  Widget build(BuildContext context) {
    Widget item(_Tab t, String label) {
      final active = t == current;
      return Expanded(
        child: GestureDetector(
          onTap: () => onChange(t),
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            height: 40,
            decoration: BoxDecoration(
              color: active ? AppColor.brand : Colors.transparent,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: TextStyle(
                color: active ? AppColor.ink : AppColor.inkTertiary,
                fontSize: 13,
                fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                letterSpacing: -0.2,
              ),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.md,
      ),
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: AppColor.surface,
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: Border.all(color: AppColor.border, width: 1),
        ),
        child: Row(
          children: [
            item(_Tab.disease, '질환'),
            item(_Tab.drug, '약'),
            item(_Tab.goal, '목적'),
            item(_Tab.body, '신체'),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 칩 선택기 (질환·약·목적 공용)
// ═══════════════════════════════════════════
class _ChipPicker extends StatefulWidget {
  final String title;
  final String subtitle;
  final List<String> options;
  final Set<String> selected;
  const _ChipPicker({
    required this.title,
    required this.subtitle,
    required this.options,
    required this.selected,
  });

  @override
  State<_ChipPicker> createState() => _ChipPickerState();
}

class _ChipPickerState extends State<_ChipPicker> {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.xl,
      ),
      children: [
        Text(
          widget.title,
          style: const TextStyle(
            color: AppColor.ink,
            fontSize: 18,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.4,
            height: 1.3,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          widget.subtitle,
          style: const TextStyle(
            color: AppColor.inkSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w500,
            height: 1.45,
            letterSpacing: -0.2,
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        Wrap(
          spacing: AppSpace.sm,
          runSpacing: AppSpace.sm,
          children: [
            for (final o in widget.options)
              _Chip(
                label: o,
                active: widget.selected.contains(o),
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() {
                    if (widget.selected.contains(o)) {
                      widget.selected.remove(o);
                    } else {
                      widget.selected.add(o);
                    }
                  });
                },
              ),
          ],
        ),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _Chip({
    required this.label,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.md + 2, vertical: 10,
        ),
        decoration: BoxDecoration(
          color: active ? AppColor.brand : AppColor.surface,
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: Border.all(
            color: active ? AppColor.brand : AppColor.border,
            width: 1.5,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: AppColor.ink,
            fontSize: 13,
            fontWeight: active ? FontWeight.w800 : FontWeight.w600,
            letterSpacing: -0.2,
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 신체 폼
// ═══════════════════════════════════════════
class _BodyForm extends StatelessWidget {
  final TextEditingController heightCtl;
  final TextEditingController weightCtl;
  const _BodyForm({required this.heightCtl, required this.weightCtl});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.xl,
      ),
      children: [
        const Text(
          '신체 정보를 알려주세요',
          style: TextStyle(
            color: AppColor.ink,
            fontSize: 18,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.4,
            height: 1.3,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          '권장 칼로리·영양소 계산에 쓰여요.',
          style: TextStyle(
            color: AppColor.inkSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w500,
            letterSpacing: -0.2,
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        _NumberField(label: '키', unit: 'cm', controller: heightCtl),
        const SizedBox(height: AppSpace.md),
        _NumberField(label: '몸무게', unit: 'kg', controller: weightCtl),
      ],
    );
  }
}

class _NumberField extends StatelessWidget {
  final String label;
  final String unit;
  final TextEditingController controller;
  const _NumberField({
    required this.label,
    required this.unit,
    required this.controller,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.md + 2, vertical: 6,
      ),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColor.border, width: 1),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 64,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColor.inkSecondary,
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
          ),
          Expanded(
            child: TextField(
              controller: controller,
              keyboardType: TextInputType.number,
              style: const TextStyle(
                color: AppColor.ink,
                fontSize: 18,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.4,
              ),
              decoration: const InputDecoration(
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(vertical: 12),
                isCollapsed: true,
              ),
            ),
          ),
          Text(
            unit,
            style: const TextStyle(
              color: AppColor.inkTertiary,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 저장 바
// ═══════════════════════════════════════════
class _SaveBar extends StatelessWidget {
  final VoidCallback onSave;
  const _SaveBar({required this.onSave});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.md,
        ),
        child: GestureDetector(
          onTap: onSave,
          child: Container(
            height: 56,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFFFFD43A), AppColor.brand],
              ),
              borderRadius: BorderRadius.circular(AppRadius.md),
              boxShadow: [
                BoxShadow(
                  color: AppColor.brand.withOpacity(0.40),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            alignment: Alignment.center,
            child: const Text(
              '저장하기',
              style: TextStyle(
                color: AppColor.ink,
                fontSize: 16,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
