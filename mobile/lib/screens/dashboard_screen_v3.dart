// screens/dashboard_screen_v3.dart — v3 토큰 기반 Dashboard P0 (LADS §13)
//
// 상태: PREVIEW. Claude Design Export ZIP 도착 시 디테일만 교체.
// 진입: /dashboard-v3 (라우터 임시 경로 — hot-reload 검증용)
//
// 출처:
//   - .claude/inbox-design/20260518_DASHBOARD_FIRST_DESIGN.md (prompt)
//   - .claude/inbox-design/20260518_PAGE_BY_PAGE_WORKFLOW.md (워크플로우)
//   - mobile/lib/utils/design_tokens_v3.dart (단일 진실)
//
// 6 섹션 (위→아래):
//   1. _MascotGreetingSection — 마스코트 + 인사 + 날짜
//   2. _CameraQuickEntryCard — lemon CTA "사진으로 분석하기" + 할로 그림자
//   3. _NutritionSummaryCard — liquid-glass 큰 숫자 + 부족/충분 + leaf bar
//   4. _OutputGrid — 5종 출력 카드 그리드 (Pillyze 차용 + 만성질환 배지)
//   5. _RecentAnalysisList — 최근 분석 영양제 3개
//   6. MedicalDisclaimer.standard (§14 컴플라이언스 의무)
//
// 차별화 (§16):
//   - Pillyze 의 데이터 위주 → 마스코트 따뜻한 인사 추가
//   - Toss 의 minimal → liquid-glass + lemon halo
//   - "진단/처방/치료" 표현 절대 X — copywriter grep 통과
//
// 시니어 친화 (CLAUDE.md §0):
//   - 본문 17pt+ (AppFont.scaleBody17)
//   - 버튼 ≥48dp (AppA11y.minTouchTargetSenior)
//   - 대비 ≥4.5:1 (AppA11y.minContrastRatio)
//
// ⚠️ TODO (ZIP 도착 후):
//   - 마스코트 일러스트 위치/스케일
//   - liquid-glass blur 강도 미세 조정
//   - 5종 출력 카드 배치 (2x2 vs 1x5)
//   - 최근 분석 리스트 모양 (썸네일 유무)

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v3.dart';
import '../utils/router.dart';
import '../widgets/common/medical_disclaimer.dart';

class DashboardScreenV3 extends StatelessWidget {
  const DashboardScreenV3({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.canvas,
      body: SafeArea(
        bottom: false,
        child: CustomScrollView(
          slivers: <Widget>[
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.s16,
                AppSpacing.s16,
                AppSpacing.s16,
                AppSpacing.s40,
              ),
              sliver: SliverList(
                delegate: SliverChildListDelegate(<Widget>[
                  const _MascotGreetingSection(userName: '태동'),
                  const SizedBox(height: AppSpacing.s24),
                  _CameraQuickEntryCard(
                    onTap: () => context.push(AppRoute.camera),
                  ),
                  const SizedBox(height: AppSpacing.s24),
                  const _NutritionSummaryCard(
                    shortageItems: <String>['비타민 D', '마그네슘'],
                    adequateItems: <String>['비타민 C', '오메가 3'],
                    coverageRatio: 0.62,
                  ),
                  const SizedBox(height: AppSpacing.s24),
                  const _SectionTitle(title: '오늘 챙겨야 할 5가지'),
                  const SizedBox(height: AppSpacing.s12),
                  const _OutputGrid(),
                  const SizedBox(height: AppSpacing.s24),
                  const _SectionTitle(title: '최근 분석한 영양제'),
                  const SizedBox(height: AppSpacing.s12),
                  const _RecentAnalysisList(),
                  const SizedBox(height: AppSpacing.s24),
                  const MedicalDisclaimer(variant: DisclaimerVariant.standard),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// 1. 마스코트 + 인사 + 날짜
// ============================================================================
class _MascotGreetingSection extends StatelessWidget {
  final String userName;
  const _MascotGreetingSection({required this.userName});

  @override
  Widget build(BuildContext context) {
    final DateTime now = DateTime.now();
    final List<String> weekdays = <String>['월', '화', '수', '목', '금', '토', '일'];
    final String dateText =
        '${now.month}월 ${now.day}일 (${weekdays[now.weekday - 1]})';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: <Widget>[
        // 마스코트 — 본 캐릭터 64×64
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          child: Image.asset(
            'assets/mascot/character-cutout.png',
            width: 64,
            height: 64,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppColor.lemon100,
                borderRadius: BorderRadius.circular(AppRadius.lg),
              ),
              child: const Icon(Icons.emoji_emotions_rounded,
                  color: AppColor.lemon500, size: 36),
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.s12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                dateText,
                style: AppText.label.copyWith(color: AppColor.ink500),
              ),
              const SizedBox(height: AppSpacing.s4),
              Text(
                '오늘도 좋은 하루예요, $userName 님',
                style: AppText.sectionHead.copyWith(
                  fontSize: AppFont.scaleHead20,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ============================================================================
// 2. 카메라 빠른 진입 CTA — lemon-400 + lemon halo
// ============================================================================
class _CameraQuickEntryCard extends StatelessWidget {
  final VoidCallback onTap;
  const _CameraQuickEntryCard({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        child: Ink(
          height: AppA11y.minTouchTargetSenior + 16,
          decoration: BoxDecoration(
            color: AppColor.lemon400,
            borderRadius: BorderRadius.circular(AppRadius.xl),
            boxShadow: AppShadow.lemonHalo,
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s20),
            child: Row(
              children: <Widget>[
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.35),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  child: const Icon(
                    Icons.photo_camera_rounded,
                    color: AppColor.ink900,
                    size: 24,
                  ),
                ),
                const SizedBox(width: AppSpacing.s16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: <Widget>[
                      Text(
                        '사진으로 분석하기',
                        style: AppText.button.copyWith(
                          color: AppColor.ink900,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '영양제·식단을 1초에 인식해요',
                        style: AppText.caption.copyWith(color: AppColor.ink700),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: AppColor.ink900,
                  size: 28,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 3. 영양 요약 카드 — liquid-glass + 큰 숫자 + 진행률 바
// ============================================================================
class _NutritionSummaryCard extends StatelessWidget {
  final List<String> shortageItems;
  final List<String> adequateItems;
  /// 0~1. 오늘 권장량 대비 충족 비율.
  final double coverageRatio;

  const _NutritionSummaryCard({
    required this.shortageItems,
    required this.adequateItems,
    required this.coverageRatio,
  });

  @override
  Widget build(BuildContext context) {
    final int coveragePercent = (coverageRatio.clamp(0.0, 1.0) * 100).round();

    return _GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.s20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('오늘 영양 충족률', style: AppText.label),
            const SizedBox(height: AppSpacing.s8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: <Widget>[
                Text(
                  '$coveragePercent',
                  style: AppText.numXl.copyWith(
                    fontSize: AppFont.scaleDisplay44,
                    color: AppColor.ink900,
                  ),
                ),
                const SizedBox(width: 2),
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    '%',
                    style: AppText.sectionHead.copyWith(
                      color: AppColor.ink500,
                      fontSize: AppFont.scaleHead20,
                    ),
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.s12,
                    vertical: AppSpacing.s4,
                  ),
                  decoration: BoxDecoration(
                    color: AppColor.successSoft,
                    borderRadius: BorderRadius.circular(AppRadius.pill),
                  ),
                  child: Text(
                    coverageRatio >= 0.7 ? '양호' : '보완 필요',
                    style: AppText.label.copyWith(
                      color: AppColor.success,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.s12),
            ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.pill),
              child: Stack(
                children: <Widget>[
                  Container(height: 10, color: AppColor.leaf50),
                  FractionallySizedBox(
                    widthFactor: coverageRatio.clamp(0.0, 1.0),
                    child: Container(height: 10, color: AppColor.leaf300),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.s16),
            _NutrientLine(
              label: '부족',
              items: shortageItems,
              color: AppColor.warning,
              softBg: AppColor.warningSoft,
            ),
            const SizedBox(height: AppSpacing.s8),
            _NutrientLine(
              label: '충분',
              items: adequateItems,
              color: AppColor.success,
              softBg: AppColor.successSoft,
            ),
          ],
        ),
      ),
    );
  }
}

class _NutrientLine extends StatelessWidget {
  final String label;
  final List<String> items;
  final Color color;
  final Color softBg;
  const _NutrientLine({
    required this.label,
    required this.items,
    required this.color,
    required this.softBg,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s8,
            vertical: 2,
          ),
          decoration: BoxDecoration(
            color: softBg,
            borderRadius: BorderRadius.circular(AppRadius.xs),
          ),
          child: Text(
            label,
            style: AppText.label.copyWith(color: color, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(width: AppSpacing.s8),
        Expanded(
          child: Text(
            items.join(' · '),
            style: AppText.body.copyWith(fontSize: AppFont.scaleBody15),
          ),
        ),
      ],
    );
  }
}

// ============================================================================
// 공통 — liquid-glass 카드 셸
// ============================================================================
class _GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final double radius;
  const _GlassCard({
    required this.child,
    this.padding,
    this.radius = AppRadius.xxl,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        boxShadow: AppShadow.glass,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: BackdropFilter(
          filter: AppGlass.blur(),
          child: Container(
            decoration: BoxDecoration(
              color: AppGlass.fill,
              borderRadius: BorderRadius.circular(radius),
              border: Border.all(
                color: const Color(0x40FFFFFF),
                width: 1,
              ),
            ),
            padding: padding ?? EdgeInsets.zero,
            child: child,
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 4. 5종 출력 그리드 (Pillyze 차용 + 만성질환 배지 차별화)
// ============================================================================
class _OutputGrid extends StatelessWidget {
  const _OutputGrid();

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: AppSpacing.s12,
      mainAxisSpacing: AppSpacing.s12,
      childAspectRatio: 1.05,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: const <Widget>[
        _OutputTile(
          icon: Icons.eco_rounded,
          label: '부족 영양소',
          value: '비타민 D',
          detail: '권장량 38%',
          bg: AppColor.lemon100,
          iconColor: AppColor.lemon600,
        ),
        _OutputTile(
          icon: Icons.warning_amber_rounded,
          label: '과다 섭취',
          value: '나트륨',
          detail: '권장 130%',
          bg: AppColor.warningSoft,
          iconColor: AppColor.warning,
        ),
        _OutputTile(
          icon: Icons.medical_information_rounded,
          label: '주의 성분',
          value: '와파린 충돌',
          detail: '비타민 K 함량',
          bg: AppColor.reviewSoft,
          iconColor: AppColor.review,
          chronicWarning: true,
        ),
        _OutputTile(
          icon: Icons.restaurant_menu_rounded,
          label: '식단 관리',
          value: '82점',
          detail: '7일 평균',
          bg: AppColor.leaf100,
          iconColor: AppColor.leaf600,
        ),
      ],
    );
  }
}

class _OutputTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String detail;
  final Color bg;
  final Color iconColor;

  /// 차별화 §16 — Pillyze 에는 없는 만성질환 경고 배지.
  final bool chronicWarning;

  const _OutputTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.detail,
    required this.bg,
    required this.iconColor,
    this.chronicWarning = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.level1,
      ),
      padding: const EdgeInsets.all(AppSpacing.s16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Icon(icon, color: iconColor, size: 24),
              if (chronicWarning)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.s8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: AppColor.danger,
                    borderRadius: BorderRadius.circular(AppRadius.pill),
                  ),
                  child: Text(
                    '만성질환',
                    style: AppText.label.copyWith(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),
          const Spacer(),
          Text(
            label,
            style: AppText.label.copyWith(color: AppColor.ink500),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: AppText.sectionHead.copyWith(fontSize: AppFont.scaleHead20),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            detail,
            style: AppText.caption.copyWith(color: AppColor.ink500),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// 5. 최근 분석 영양제 리스트 (3개)
// ============================================================================
class _RecentAnalysisList extends StatelessWidget {
  const _RecentAnalysisList();

  @override
  Widget build(BuildContext context) {
    final List<_RecentItem> items = <_RecentItem>[
      _RecentItem(
        name: '비타민 D 5000IU',
        brand: '나우푸드',
        date: '오늘',
        safe: true,
      ),
      _RecentItem(
        name: '오메가 3 1200',
        brand: '센트룸',
        date: '어제',
        safe: true,
      ),
      _RecentItem(
        name: '은행잎 추출물',
        brand: '솔가',
        date: '2일 전',
        safe: false,
      ),
    ];

    return Column(
      children: <Widget>[
        for (int i = 0; i < items.length; i++) ...<Widget>[
          _RecentRow(item: items[i]),
          if (i != items.length - 1) const SizedBox(height: AppSpacing.s8),
        ],
      ],
    );
  }
}

class _RecentItem {
  final String name;
  final String brand;
  final String date;
  final bool safe;
  _RecentItem({
    required this.name,
    required this.brand,
    required this.date,
    required this.safe,
  });
}

class _RecentRow extends StatelessWidget {
  final _RecentItem item;
  const _RecentRow({required this.item});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColor.paper,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.level1,
      ),
      padding: const EdgeInsets.all(AppSpacing.s16),
      child: Row(
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColor.canvas,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColor.ink100),
            ),
            child: const Icon(Icons.medication_rounded,
                color: AppColor.ink500, size: 22),
          ),
          const SizedBox(width: AppSpacing.s12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.name,
                  style: AppText.bodyBold.copyWith(
                    fontSize: AppFont.scaleBody17,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  '${item.brand} · ${item.date}',
                  style: AppText.caption,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.s8),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.s8,
              vertical: AppSpacing.s4,
            ),
            decoration: BoxDecoration(
              color: item.safe ? AppColor.successSoft : AppColor.dangerSoft,
              borderRadius: BorderRadius.circular(AppRadius.pill),
            ),
            child: Text(
              item.safe ? '안전' : '주의',
              style: AppText.label.copyWith(
                color: item.safe ? AppColor.success : AppColor.danger,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// 보조 — 섹션 타이틀
// ============================================================================
class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s4),
      child: Text(
        title,
        style: AppText.sectionHead.copyWith(fontSize: AppFont.scaleHead20),
      ),
    );
  }
}
