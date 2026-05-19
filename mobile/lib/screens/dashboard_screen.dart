// screens/dashboard_screen.dart — 홈 (5종 출력 카드)
//
// 참조:
//   - PROJECT_GUIDE.md §3.5 주요 화면 / §8 5종 출력 메타스펙
//   - mobile/CLAUDE.md §3.4 결과 카드 4 요소 약속
//   - docs/UX_DIARY.md §5.6 Dashboard
//
// 구조 (2026-05-14 결정):
//   - 세로 스크롤 스택 (시니어 친화)
//   - 카드 5개:
//     1. 부족 영양소 추천
//     2. 권장 섭취량 (KDRIs)
//     3. 체중 예측
//     4. 활동 권고 (v4)
//     5. 목적별 분석 (눈/간/피로)
//   - 각 카드 = OutputCard 위젯 (label / headline / detail / source / confidence)
//   - 데이터: Mock (백엔드 /dashboard 엔드포인트 합의 후 교체)
//
// FAB: 카메라 진입 (사진 촬영 → AI 분석)

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../utils/design_tokens_v2.dart';
import '../utils/router.dart';
import '../widgets/common/output_card.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.bg,
      appBar: AppBar(
        backgroundColor: AppColor.bg,
        elevation: 0,
        title: const Text(
          '오늘의 건강',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
            letterSpacing: -0.5,
          ),
        ),
        centerTitle: false,
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.xl,
            AppSpace.md,
            AppSpace.xl,
            AppSpace.xxxl + 64, // FAB 가리지 않게 하단 여백
          ),
          children: const [
            _DateGreeting(),
            SizedBox(height: AppSpace.lg),
            _NutrientShortageCard(),
            SizedBox(height: AppSpace.md),
            _KdriIntakeCard(),
            SizedBox(height: AppSpace.md),
            _WeightPredictionCard(),
            SizedBox(height: AppSpace.md),
            _ActivityAdviceCard(),
            SizedBox(height: AppSpace.md),
            _PurposeAnalysisCard(),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push(AppRoute.camera),
        backgroundColor: AppColor.brand,
        foregroundColor: Colors.white,
        elevation: 2,
        label: const Text(
          '사진 찍기',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w700,
          ),
        ),
        icon: const Icon(Icons.photo_camera_rounded),
      ),
    );
  }
}

// ─── 상단 인사말 + 날짜 ───
class _DateGreeting extends StatelessWidget {
  const _DateGreeting();
  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final weekday = ['월', '화', '수', '목', '금', '토', '일'][now.weekday - 1];
    final dateText = '${now.month}월 ${now.day}일 ($weekday)';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          dateText,
          style: AppText.caption.copyWith(
            color: AppColor.inkTertiary,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '오늘 챙겨야 할 5가지예요',
          style: AppText.bodyLg.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColor.ink,
          ),
        ),
      ],
    );
  }
}

// ─── 1. 부족 영양소 ───
// AI 가 최근 식사 기록 분석해 부족한 영양소 추천. 신뢰도 모델 출력.
class _NutrientShortageCard extends StatelessWidget {
  const _NutrientShortageCard();
  @override
  Widget build(BuildContext context) {
    return OutputCard(
      label: '부족한 영양소',
      icon: Icons.eco_rounded,
      iconBg: AppColor.successSoft,
      iconFg: AppColor.success,
      headline: '비타민 D 부족',
      detail: '최근 7일 식사에서 비타민 D 권장량의 38%만 섭취했어요.',
      source: 'KDRIs 2020 · AI 분석',
      confidence: 0.84,
      onTap: () {
        // TODO: 영양소 상세 화면
      },
    );
  }
}

// ─── 2. 권장 섭취량 (KDRIs) ───
class _KdriIntakeCard extends StatelessWidget {
  const _KdriIntakeCard();
  @override
  Widget build(BuildContext context) {
    return OutputCard(
      label: '오늘 권장 섭취량',
      icon: Icons.restaurant_rounded,
      iconBg: AppColor.brandSoft,
      iconFg: AppColor.brand,
      headline: '칼로리 1,840 kcal',
      detail: '단백질 72g · 탄수화물 230g · 지방 60g',
      source: 'KDRIs 2020 · 50대 남성 기준',
      confidence: 0.95,
      onTap: () {
        // TODO: KDRIs 상세
      },
    );
  }
}

// ─── 3. 체중 예측 ───
class _WeightPredictionCard extends StatelessWidget {
  const _WeightPredictionCard();
  @override
  Widget build(BuildContext context) {
    return OutputCard(
      label: '체중 예측',
      icon: Icons.trending_down_rounded,
      iconBg: AppColor.yellowSoft,
      iconFg: AppColor.warning,
      headline: '4주 후 -1.2 kg',
      detail: '현재 식단·활동 유지 시 예상치예요.',
      source: '자체 모델 v0.3',
      confidence: 0.62,
      onTap: () {
        // TODO: 체중 그래프
      },
    );
  }
}

// ─── 4. 활동 권고 ───
class _ActivityAdviceCard extends StatelessWidget {
  const _ActivityAdviceCard();
  @override
  Widget build(BuildContext context) {
    return OutputCard(
      label: '오늘 활동 권고',
      icon: Icons.directions_walk_rounded,
      iconBg: AppColor.brandSoft,
      iconFg: AppColor.brand,
      headline: '걷기 30분',
      detail: '저녁 식사 후 가볍게 — 혈당 상승 완화에 도움.',
      source: 'WHO 가이드 · 활동 권고 v4',
      confidence: 0.78,
      onTap: () {
        // TODO: 활동 상세
      },
    );
  }
}

// ─── 5. 목적별 분석 (눈/간/피로) ───
class _PurposeAnalysisCard extends StatelessWidget {
  const _PurposeAnalysisCard();
  @override
  Widget build(BuildContext context) {
    return OutputCard(
      label: '목적별 분석 — 피로',
      icon: Icons.battery_charging_full_rounded,
      iconBg: AppColor.dangerSoft,
      iconFg: AppColor.danger,
      headline: '비타민 B군 보충 권장',
      detail: '최근 피로 기록 + 식사 패턴 분석 결과예요.',
      source: '자체 모델 · 사용자 일지',
      confidence: 0.55,
      onTap: () {
        // TODO: 목적별 상세
      },
    );
  }
}
