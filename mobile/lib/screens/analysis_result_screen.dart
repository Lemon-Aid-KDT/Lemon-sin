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
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/supplement_analysis.dart';
import '../models/supplement_comprehensive.dart';
import '../providers/analysis_provider.dart';
import '../utils/design_tokens_v2.dart';

class AnalysisResultScreen extends ConsumerWidget {
  final String mode; // 'supplement' | 'meal'
  const AnalysisResultScreen({super.key, this.mode = 'supplement'});

  bool get _isMeal => mode == 'meal';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(analysisProvider);
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
                  // 백엔드 분석 상태 카드 (로딩/에러/성공 분기)
                  _BackendAnalysisCard(
                    state: state,
                    onRetry: () => ref.read(analysisProvider.notifier).retry(),
                  ),
                  const SizedBox(height: AppSpace.md),
                  // 5종 카드 — 1번 카드만 백엔드 ingredient 로 동적 렌더링
                  state.result.when(
                    data: (preview) => _IngredientResultCard(preview: preview),
                    loading: () => _ResultCard(
                      color: const Color(0xFF22B07D),
                      icon: Icons.hourglass_top_rounded,
                      label: '부족 영양소',
                      value: '분석 중…',
                      desc: '백엔드에서 라벨을 읽고 있어요',
                    ),
                    error: (_, __) => _ResultCard(
                      color: const Color(0xFF22B07D),
                      icon: Icons.eco_rounded,
                      label: '부족 영양소',
                      value: '비타민 D · 마그네슘',
                      desc: '햇볕 시간이 부족하면 보충을 권장드려요',
                    ),
                  ),
                  const SizedBox(height: AppSpace.sm),
                  _ExcessiveResultCard(comprehensive: state.comprehensive),
                  const SizedBox(height: AppSpace.sm),
                  _CautionResultCard(comprehensive: state.comprehensive),
                  const SizedBox(height: AppSpace.sm),
                  _DietScoreCard(comprehensive: state.comprehensive, isMeal: _isMeal),
                  const SizedBox(height: AppSpace.sm),
                  _PurposeResultCard(comprehensive: state.comprehensive),
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

// ═══════════════════════════════════════════
// 백엔드 OCR 분석 상태 카드 (로딩/에러/성공)
// ═══════════════════════════════════════════
class _BackendAnalysisCard extends StatelessWidget {
  const _BackendAnalysisCard({required this.state, required this.onRetry});

  final AnalysisState state;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return state.result.when(
      data: (preview) => _buildSuccessOrIdle(context, preview),
      loading: () => _buildLoading(context),
      error: (e, _) => _buildError(context, e),
    );
  }

  Widget _buildLoading(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Row(
        children: [
          const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2.5),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Text(
              '백엔드 OCR 분석 중이에요…',
              style: AppText.body.copyWith(
                color: AppColor.ink,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, Object error) {
    final message = error is SupplementAnalyzeException
        ? error.userMessage
        : '분석 중 문제가 발생했어요';
    return Container(
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF1F0),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: const Color(0xFFFFB1A8), width: 1),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, color: Color(0xFFEF4452)),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  message,
                  style: AppText.body.copyWith(
                    color: AppColor.ink,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: AppSpace.xs),
                Text(
                  '잠시 후 다시 시도하거나 다른 사진을 사용해주세요.',
                  style: AppText.caption.copyWith(color: AppColor.inkSecondary),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: onRetry,
            child: const Text('다시 시도'),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessOrIdle(BuildContext context, SupplementAnalysisPreview? preview) {
    if (preview == null) {
      // idle — 분석 호출 전 (camera 화면에서 아직 push 안 한 상태)
      return const SizedBox.shrink();
    }
    final product = preview.parsedProduct;
    final productName = product.productName?.trim().isNotEmpty == true
        ? product.productName!
        : '제품명 인식 중';
    final serving = product.servingSize ?? '복용량 미인식';
    return Container(
      padding: const EdgeInsets.all(AppSpace.lg),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.qr_code_scanner_rounded, color: AppColor.brand),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: Text(
                  productName,
                  style: AppText.bodyLg.copyWith(
                    fontWeight: FontWeight.w800,
                    color: AppColor.ink,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.xs),
          Text(
            serving,
            style: AppText.caption.copyWith(color: AppColor.inkSecondary),
          ),
          if (preview.warnings.isNotEmpty) ...[
            const SizedBox(height: AppSpace.sm),
            Wrap(
              spacing: AppSpace.xs,
              runSpacing: AppSpace.xs,
              children: preview.warnings.take(3).map((w) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpace.sm,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF8DC),
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    w,
                    style: AppText.micro.copyWith(color: AppColor.ink),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Ingredient → "부족 영양소" 카드 (1번 카드 동적 버전)
// ═══════════════════════════════════════════
class _IngredientResultCard extends StatelessWidget {
  const _IngredientResultCard({required this.preview});

  final SupplementAnalysisPreview? preview;

  @override
  Widget build(BuildContext context) {
    final ings = preview?.ingredientCandidates ?? const [];
    if (preview == null) {
      // idle — 기존 더미 표시
      return _ResultCard(
        color: const Color(0xFF22B07D),
        icon: Icons.eco_rounded,
        label: '부족 영양소',
        value: '비타민 D · 마그네슘',
        desc: '햇볕 시간이 부족하면 보충을 권장드려요',
      );
    }
    if (ings.isEmpty) {
      return _ResultCard(
        color: const Color(0xFF22B07D),
        icon: Icons.eco_rounded,
        label: '추출된 영양소',
        value: '인식된 성분이 없어요',
        desc: '라벨이 잘 보이는 다른 사진으로 다시 시도해주세요',
      );
    }
    final topThree = ings.take(3).map((i) {
      final amountText = (i.amount != null && i.unit != null)
          ? ' ${i.amount} ${i.unit}'
          : '';
      return '${i.displayName}$amountText';
    }).join(' · ');
    final lowConf = ings.where((i) => i.confidence < 0.6).length;
    return _ResultCard(
      color: const Color(0xFF22B07D),
      icon: Icons.eco_rounded,
      label: '추출된 영양소 (${ings.length}개)',
      value: topThree,
      desc: lowConf > 0
          ? '검토 권장 $lowConf개 — 라벨을 다시 확인해주세요'
          : '백엔드가 라벨에서 인식한 성분이에요',
    );
  }
}

// ═══════════════════════════════════════════
// 카드 2: 과다 섭취 (KDRIs UL 초과)
// ═══════════════════════════════════════════
class _ExcessiveResultCard extends StatelessWidget {
  const _ExcessiveResultCard({required this.comprehensive});
  final AsyncValue<SupplementComprehensiveAnalysis?> comprehensive;

  @override
  Widget build(BuildContext context) {
    return comprehensive.when(
      data: (data) {
        if (data == null) {
          return _ResultCard(
            color: const Color(0xFFFF9500),
            icon: Icons.warning_amber_rounded,
            label: '과다 섭취',
            value: '확인 중…',
            desc: '분석을 시작하면 KDRIs 상한과 비교해 알려드릴게요',
          );
        }
        if (data.excessiveNutrients.isEmpty) {
          return _ResultCard(
            color: const Color(0xFF22B07D),
            icon: Icons.check_circle_outline_rounded,
            label: '과다 섭취',
            value: '상한 내 안전',
            desc: '모든 영양소가 KDRIs 상한 안에 있어요',
          );
        }
        final top = data.excessiveNutrients.take(3).map((e) {
          return '${e.displayName} ${e.excessRatio}배';
        }).join(' · ');
        return _ResultCard(
          color: const Color(0xFFFF9500),
          icon: Icons.warning_amber_rounded,
          label: '과다 섭취 (${data.excessiveNutrients.length}개)',
          value: top,
          desc: 'KDRIs 상한 초과 — 다른 보충제와 함께 드시기 전 의료진과 상의해주세요',
        );
      },
      loading: () => _ResultCard(
        color: const Color(0xFFFF9500),
        icon: Icons.hourglass_top_rounded,
        label: '과다 섭취',
        value: '분석 중…',
        desc: 'KDRIs 상한과 비교하고 있어요',
      ),
      error: (_, __) => _ResultCard(
        color: const Color(0xFFFF9500),
        icon: Icons.warning_amber_rounded,
        label: '과다 섭취',
        value: '계산 실패',
        desc: '잠시 후 다시 시도해주세요',
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 카드 3: 주의 성분 (약물 상호작용 등)
// ═══════════════════════════════════════════
class _CautionResultCard extends StatelessWidget {
  const _CautionResultCard({required this.comprehensive});
  final AsyncValue<SupplementComprehensiveAnalysis?> comprehensive;

  @override
  Widget build(BuildContext context) {
    return comprehensive.when(
      data: (data) {
        if (data == null) {
          return _ResultCard(
            color: const Color(0xFFFF6B6B),
            icon: Icons.shield_outlined,
            label: '주의 성분',
            value: '확인 중…',
            desc: '분석을 시작하면 의약품 상호작용을 알려드릴게요',
          );
        }
        if (data.cautionaryComponents.isEmpty) {
          return _ResultCard(
            color: const Color(0xFF22B07D),
            icon: Icons.shield_outlined,
            label: '주의 성분',
            value: '특별한 주의사항 없음',
            desc: '확인된 약물 상호작용은 없어요. 복용 중인 약이 있다면 의료진과 상담을 권해드려요.',
          );
        }
        // 최우선: high → medium → low 순으로 정렬
        final sorted = List.of(data.cautionaryComponents)
          ..sort((a, b) {
            const order = {'high': 0, 'medium': 1, 'low': 2};
            return (order[a.severity] ?? 3).compareTo(order[b.severity] ?? 3);
          });
        final top = sorted.first;
        final extras = sorted.length > 1 ? ' (+${sorted.length - 1}개)' : '';
        final color = top.severity == 'high'
            ? const Color(0xFFFF6B6B)
            : top.severity == 'medium'
                ? const Color(0xFFFF9500)
                : const Color(0xFF4D7BFF);
        return _ResultCard(
          color: color,
          icon: Icons.shield_outlined,
          label: '주의 성분$extras',
          value: top.component,
          desc: top.message,
        );
      },
      loading: () => _ResultCard(
        color: const Color(0xFFFF6B6B),
        icon: Icons.hourglass_top_rounded,
        label: '주의 성분',
        value: '확인 중…',
        desc: '약물 상호작용과 만성질환 회피군을 확인하고 있어요',
      ),
      error: (_, __) => _ResultCard(
        color: const Color(0xFFFF6B6B),
        icon: Icons.shield_outlined,
        label: '주의 성분',
        value: '계산 실패',
        desc: '복용 중인 약이 있다면 의료진과 상담해주세요',
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 카드 4: 식단 점수 (diet_score)
// ═══════════════════════════════════════════
class _DietScoreCard extends StatelessWidget {
  const _DietScoreCard({required this.comprehensive, required this.isMeal});
  final AsyncValue<SupplementComprehensiveAnalysis?> comprehensive;
  final bool isMeal;

  @override
  Widget build(BuildContext context) {
    return comprehensive.when(
      data: (data) {
        if (data == null) {
          return _ResultCard(
            color: AppColor.brand,
            icon: Icons.workspace_premium_rounded,
            label: isMeal ? '오늘 식단 점수' : '영양제 균형 점수',
            value: '–',
            desc: '분석을 시작하면 0~100 점으로 알려드릴게요',
            big: true,
          );
        }
        // 라벨에 따른 색상
        final color = switch (data.dietScoreLabel) {
          'excellent' => const Color(0xFF22B07D),
          'good' => AppColor.brand,
          'moderate' => const Color(0xFFFF9500),
          'warning' => const Color(0xFFFF6B6B),
          'critical' => const Color(0xFFD32F2F),
          _ => AppColor.brand,
        };
        return _ResultCard(
          color: color,
          icon: Icons.workspace_premium_rounded,
          label: isMeal ? '오늘 식단 점수' : '영양제 균형 점수',
          value: '${data.dietScore}점',
          desc: data.dietScoreMessage,
          big: true,
        );
      },
      loading: () => _ResultCard(
        color: AppColor.brand,
        icon: Icons.hourglass_top_rounded,
        label: isMeal ? '오늘 식단 점수' : '영양제 균형 점수',
        value: '계산 중…',
        desc: 'KDRIs + 만성질환 매트릭스를 종합 비교 중',
        big: true,
      ),
      error: (_, __) => _ResultCard(
        color: AppColor.brand,
        icon: Icons.workspace_premium_rounded,
        label: isMeal ? '오늘 식단 점수' : '영양제 균형 점수',
        value: '–',
        desc: '잠시 후 다시 시도해주세요',
        big: true,
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 카드 5: 목적별 / 만성질환 (B-persona 차별화 핵심)
// ═══════════════════════════════════════════
class _PurposeResultCard extends StatelessWidget {
  const _PurposeResultCard({required this.comprehensive});
  final AsyncValue<SupplementComprehensiveAnalysis?> comprehensive;

  @override
  Widget build(BuildContext context) {
    return comprehensive.when(
      data: (data) {
        if (data == null) {
          return _ResultCard(
            color: const Color(0xFF4D7BFF),
            icon: Icons.flag_rounded,
            label: '목적별 (만성질환)',
            value: '확인 중…',
            desc: '분석을 시작하면 만성질환별 적합도를 알려드릴게요',
          );
        }
        if (data.purposeTargets.isEmpty) {
          return _ResultCard(
            color: const Color(0xFF4D7BFF),
            icon: Icons.flag_rounded,
            label: '목적별 (만성질환)',
            value: '특별한 인디케이션 없음',
            desc: '본 영양제는 일반 건강 관리용으로 보여요',
          );
        }
        final top = data.purposeTargets.first;
        final extras = data.purposeTargets.length > 1
            ? ' (+${data.purposeTargets.length - 1}개)'
            : '';
        return _ResultCard(
          color: const Color(0xFF4D7BFF),
          icon: Icons.flag_rounded,
          label: '목적별 (만성질환)$extras',
          value: _conditionLabel(top.condition),
          desc: top.message,
        );
      },
      loading: () => _ResultCard(
        color: const Color(0xFF4D7BFF),
        icon: Icons.hourglass_top_rounded,
        label: '목적별 (만성질환)',
        value: '분석 중…',
        desc: '만성질환 매트릭스 매핑 진행 중',
      ),
      error: (_, __) => _ResultCard(
        color: const Color(0xFF4D7BFF),
        icon: Icons.flag_rounded,
        label: '목적별 (만성질환)',
        value: '–',
        desc: '잠시 후 다시 시도해주세요',
      ),
    );
  }

  String _conditionLabel(String condition) {
    const labels = <String, String>{
      'cardiovascular': '심혈관 건강',
      'dyslipidemia': '이상지질혈증 관리',
      'diabetes': '당뇨 관리',
      'hypertension': '고혈압 관리',
      'osteoporosis': '골다공증·뼈 건강',
      'chronic_kidney_disease': '신장 기능',
      'liver_disease': '간 건강',
      'cognitive_decline': '인지·기억',
    };
    return labels[condition] ?? condition;
  }
}
