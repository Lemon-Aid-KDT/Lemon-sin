// widgets/common/food_candidate_list.dart — 음식 후보 선택 리스트 (figma 852:23)
//
// 카메라 음식 분석 후 백엔드 후보(MealFoodCandidate[])를 카드로 보여주고
// 하나를 단일 선택(라디오)하게 한다.
//   - 후보 카드: 썸네일 자리 + 음식명 + 일치 등급 칩(ConfidenceGradeChip, % 비노출)
//                + 예상 영양 요약(kcal·탄단지 — null 필드는 숨김)
//   - 선택 상태: brand 테두리 + 라디오 채움
//   - 섭취량: 선택된 카드에 현재 섭취량 칩 노출 + [섭취량 조절] 탭 → 호출부에서 시트 표시
//
// 표시만 담당 — 선택/섭취량 변경 콜백은 호출부 책임.
// 신뢰도 %·금칙어(진단/처방/치료/효능) 노출 없음.

import 'package:flutter/material.dart';

import '../../features/supplements/supplement_models.dart';
import '../../utils/design_tokens_v2.dart';
import 'confidence_grade_chip.dart';
import 'portion_sheet.dart';

/// 음식 후보 단일 선택 리스트.
class FoodCandidateList extends StatelessWidget {
  /// 후보 선택 리스트를 만든다.
  const FoodCandidateList({
    super.key,
    required this.candidates,
    required this.selectedIndex,
    required this.onSelect,
    required this.portionAmount,
    required this.onAdjustPortion,
  });

  /// 백엔드가 돌려준 음식 후보 목록.
  final List<MealFoodCandidate> candidates;

  /// 현재 선택된 후보 인덱스 (없으면 null).
  final int? selectedIndex;

  /// 후보 선택 콜백.
  final ValueChanged<int> onSelect;

  /// 선택된 후보의 현재 섭취량 (인분).
  final double portionAmount;

  /// 섭취량 조절 탭 콜백.
  final VoidCallback onAdjustPortion;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          '어떤 음식이 맞나요?',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 18,
            fontWeight: FontWeight.w900,
            color: AppColor.ink,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '가장 비슷한 음식을 하나 골라 주세요.',
          style: AppText.caption.copyWith(color: AppColor.inkTertiary),
        ),
        const SizedBox(height: AppSpace.md),
        for (int index = 0; index < candidates.length; index++) ...<Widget>[
          _FoodCandidateCard(
            candidate: candidates[index],
            selected: selectedIndex == index,
            portionAmount: portionAmount,
            onTap: () => onSelect(index),
            onAdjustPortion: onAdjustPortion,
          ),
          if (index != candidates.length - 1)
            const SizedBox(height: AppSpace.sm),
        ],
      ],
    );
  }
}

class _FoodCandidateCard extends StatelessWidget {
  const _FoodCandidateCard({
    required this.candidate,
    required this.selected,
    required this.portionAmount,
    required this.onTap,
    required this.onAdjustPortion,
  });

  final MealFoodCandidate candidate;
  final bool selected;
  final double portionAmount;
  final VoidCallback onTap;
  final VoidCallback onAdjustPortion;

  @override
  Widget build(BuildContext context) {
    final String? nutritionSummary = _nutritionSummary(candidate);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Container(
          padding: const EdgeInsets.all(AppSpace.md),
          decoration: BoxDecoration(
            color: selected ? AppColor.brandSoft : AppColor.surface,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(
              color: selected ? AppColor.brand : AppColor.border,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // 썸네일 자리 (백엔드 후보 이미지 미노출 — placeholder).
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: AppColor.sunken,
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(
                      Icons.restaurant_rounded,
                      size: 22,
                      color: AppColor.inkTertiary,
                    ),
                  ),
                  const SizedBox(width: AppSpace.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          candidate.displayName,
                          style: const TextStyle(
                            fontFamily: 'Pretendard',
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: AppColor.ink,
                            letterSpacing: 0,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: ConfidenceGradeChip(
                            confidence: candidate.confidence,
                            compact: true,
                          ),
                        ),
                        if (nutritionSummary != null) ...<Widget>[
                          const SizedBox(height: 6),
                          Text(
                            nutritionSummary,
                            style: AppText.caption.copyWith(
                              color: AppColor.inkSecondary,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  // 단일 선택 라디오.
                  Icon(
                    selected
                        ? Icons.radio_button_checked_rounded
                        : Icons.radio_button_unchecked_rounded,
                    size: 24,
                    color: selected ? AppColor.brand : AppColor.inkDisabled,
                  ),
                ],
              ),
              // 선택된 후보에만 섭취량 조절 행 노출.
              if (selected) ...<Widget>[
                const SizedBox(height: AppSpace.md),
                _PortionRow(
                  portionAmount: portionAmount,
                  onTap: onAdjustPortion,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _PortionRow extends StatelessWidget {
  const _PortionRow({required this.portionAmount, required this.onTap});

  final double portionAmount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpace.md,
            vertical: AppSpace.md,
          ),
          decoration: BoxDecoration(
            color: AppColor.surface,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColor.border),
          ),
          child: Row(
            children: <Widget>[
              const Icon(
                Icons.rice_bowl_rounded,
                size: 18,
                color: AppColor.brandDeep,
              ),
              const SizedBox(width: AppSpace.sm),
              Text(
                '섭취량',
                style: AppText.caption.copyWith(
                  color: AppColor.inkSecondary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              Text(
                formatPortionLabel(portionAmount),
                key: const ValueKey<String>('candidate-portion-label'),
                style: const TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: AppColor.ink,
                  letterSpacing: 0,
                ),
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.tune_rounded,
                size: 18,
                color: AppColor.inkTertiary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 후보의 예상 영양을 한 줄 요약으로 만든다 (null 필드는 생략).
///
/// 모두 null 이면 null 을 돌려준다(요약 행 숨김).
String? _nutritionSummary(MealFoodCandidate candidate) {
  final List<String> parts = <String>[
    if (candidate.kcal != null) '${_round(candidate.kcal!)}kcal',
    if (candidate.carbG != null) '탄 ${_round(candidate.carbG!)}g',
    if (candidate.proteinG != null) '단 ${_round(candidate.proteinG!)}g',
    if (candidate.fatG != null) '지 ${_round(candidate.fatG!)}g',
  ];
  if (parts.isEmpty) return null;
  return parts.join(' · ');
}

String _round(double value) => value.round().toString();
