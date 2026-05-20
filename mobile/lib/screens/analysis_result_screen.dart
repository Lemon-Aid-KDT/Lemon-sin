// screens/analysis_result_screen.dart — 분석 결과 5종 출력
//
// 입력: ?mode=supplement|meal
// 출력 (LADS §13 / TODO 5종):
//   1. 부족 영양소
//   2. 과다 섭취
//   3. 주의 성분 (만성질환·복약 교차 점검)
//   4. 식단 점수 (mode=meal 일 때 강조)
//   5. 목적별 분석
//
// 디자인:
//   - 상단: 닫기 + 모드 라벨 + 면책 inline
//   - 헤더 카드: 종합 한 줄 ("오늘은 충분히 균형잡힌 식사예요" 같은)
//   - 5개 카드 세로 스택 (각 카드: 아이콘 + 라벨 + 핵심 값 + 한 줄 설명)
//   - 하단 면책 박스 (의료법 §27)
//
// 의료법 가드: 진단·처방·치료·효능·효과 금칙
//   → 안내/권장/도움/관리 표현으로 대체

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v2.dart';

class AnalysisResultScreen extends StatelessWidget {
  final String mode; // 'supplement' | 'meal'
  const AnalysisResultScreen({super.key, this.mode = 'supplement'});

  bool get _isMeal => mode == 'meal';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _ResultTopBar(isMeal: _isMeal),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl + 80,
                ),
                children: [
                  _SummaryCard(isMeal: _isMeal),
                  const SizedBox(height: AppSpace.md),
                  // 5종 카드
                  _ResultCard(
                    color: const Color(0xFF22B07D),
                    icon: Icons.eco_rounded,
                    label: '부족 영양소',
                    value: '비타민 D · 마그네슘',
                    desc: '햇볕 시간이 부족하면 보충을 권장드려요',
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _ResultCard(
                    color: const Color(0xFFFF9500),
                    icon: Icons.warning_amber_rounded,
                    label: '과다 섭취',
                    value: '나트륨 1.8배 · 당류 1.2배',
                    desc: '오후 식사는 싱겁게 가는 게 어때요',
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _ResultCard(
                    color: const Color(0xFFFF6B6B),
                    icon: Icons.shield_outlined,
                    label: '주의 성분',
                    value: '비타민 K · 자몽',
                    desc: '복용 중인 약과 함께 드시기 전 의료진과 상의해주세요',
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _ResultCard(
                    color: AppColor.brand,
                    icon: Icons.workspace_premium_rounded,
                    label: '오늘 식단 점수',
                    value: _isMeal ? '82점' : '78점',
                    desc: _isMeal ? '균형 잘 잡혔어요. 채소 한 줌만 더!' : '비타민·미네랄을 조금만 보완해보세요',
                    big: true,
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _ResultCard(
                    color: const Color(0xFF4D7BFF),
                    icon: Icons.flag_rounded,
                    label: '목적별 (당뇨)',
                    value: '오늘 GI 평균 56 · 안정',
                    desc: '저녁엔 흰밥 대신 잡곡 1/2 공기 권장',
                  ),
                  const SizedBox(height: AppSpace.lg),
                  const _MedicalNote(),
                ],
              ),
            ),
          ],
        ),
      ),
      // 하단 고정 CTA
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page, AppSpace.sm, AppSpace.page, AppSpace.md,
          ),
          child: _SaveButton(
            onTap: () {
              HapticFeedback.mediumImpact();
              // 저장 후 홈으로
              context.go('/shell/home');
            },
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 상단 바
// ═══════════════════════════════════════════
class _ResultTopBar extends StatelessWidget {
  final bool isMeal;
  const _ResultTopBar({required this.isMeal});

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
                : context.go('/shell/home'),
            child: Container(
              width: 40, height: 40,
              alignment: Alignment.center,
              child: const Icon(Icons.close_rounded,
                  color: AppColor.ink, size: 24),
            ),
          ),
          const Spacer(),
          Text(
            isMeal ? '식단 분석' : '영양제 분석',
            style: const TextStyle(
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
// 헤더 — 종합 한 줄
// ═══════════════════════════════════════════
class _SummaryCard extends StatelessWidget {
  final bool isMeal;
  const _SummaryCard({required this.isMeal});

  @override
  Widget build(BuildContext context) {
    final headline = isMeal
        ? '오늘 식사는 균형이 잘 잡혔어요'
        : '이 영양제는 부족한 부분을 잘 채워줄 거예요';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.cardInside, AppSpace.lg,
        AppSpace.cardInside, AppSpace.lg,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [const Color(0xFFFFE07A), AppColor.brand],
        ),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: [
          BoxShadow(
            color: AppColor.brand.withOpacity(0.32),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 56, height: 56,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.40),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              isMeal ? Icons.restaurant_rounded : Icons.medication_rounded,
              color: AppColor.ink,
              size: 28,
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '분석이 끝났어요',
                  style: TextStyle(
                    color: AppColor.ink.withOpacity(0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  headline,
                  style: const TextStyle(
                    color: AppColor.ink,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.4,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 결과 카드 (공통)
// ═══════════════════════════════════════════
class _ResultCard extends StatelessWidget {
  final Color color;
  final IconData icon;
  final String label;
  final String value;
  final String desc;
  final bool big;
  const _ResultCard({
    required this.color,
    required this.icon,
    required this.label,
    required this.value,
    required this.desc,
    this.big = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.18),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(
              color: color.withOpacity(0.14),
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            alignment: Alignment.center,
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: AppColor.inkTertiary,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: TextStyle(
                    color: AppColor.ink,
                    fontSize: big ? 20 : 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  desc,
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 의료 면책
// ═══════════════════════════════════════════
class _MedicalNote extends StatelessWidget {
  const _MedicalNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.brandSoft,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded, color: AppColor.brandDeep, size: 18),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              '이 결과는 건강 관리를 도와드리는 참고 정보예요.\n의사·약사·영양사의 진단을 대신하지 않아요.',
              style: TextStyle(
                color: AppColor.ink,
                fontSize: 12.5,
                height: 1.5,
                letterSpacing: -0.2,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 하단 CTA
// ═══════════════════════════════════════════
class _SaveButton extends StatelessWidget {
  final VoidCallback onTap;
  const _SaveButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
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
          '기록에 저장',
          style: TextStyle(
            color: AppColor.ink,
            fontSize: 16,
            fontWeight: FontWeight.w800,
            letterSpacing: -0.3,
          ),
        ),
      ),
    );
  }
}
