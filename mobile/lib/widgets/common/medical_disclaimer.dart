// widgets/common/medical_disclaimer.dart
//
// §14 의료 컴플라이언스 의무 — 모든 추천 화면 하단에 포함
// 매니페스토 §13 LADS + §16 차별화 준수

import 'package:flutter/material.dart';
import '../../utils/design_tokens_v3.dart';

class MedicalDisclaimer extends StatelessWidget {
  /// 표준 / 컴팩트 / 카드 인라인 변형
  final DisclaimerVariant variant;

  const MedicalDisclaimer({
    super.key,
    this.variant = DisclaimerVariant.standard,
  });

  @override
  Widget build(BuildContext context) {
    switch (variant) {
      case DisclaimerVariant.standard:
        return _standard();
      case DisclaimerVariant.compact:
        return _compact();
      case DisclaimerVariant.inline:
        return _inline();
    }
  }

  Widget _standard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s16),
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s16,
        vertical: AppSpacing.s24,
      ),
      decoration: BoxDecoration(
        color: AppColor.reviewSoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColor.ink100),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: AppColor.review, size: 20),
          const SizedBox(width: AppSpacing.s12),
          Expanded(
            child: Text(
              AppIdentity.medicalDisclaimer,
              style: AppText.caption.copyWith(
                color: AppColor.ink700,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _compact() {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s16,
        vertical: AppSpacing.s8,
      ),
      child: Text(
        "* 참고용 정보입니다. 전문가 상담을 권유드려요.",
        style: AppText.caption.copyWith(color: AppColor.ink500),
        textAlign: TextAlign.center,
      ),
    );
  }

  Widget _inline() {
    return Text(
      "참고용",
      style: AppText.label.copyWith(
        color: AppColor.review,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

enum DisclaimerVariant {
  /// 화면 하단 표준 면책 박스 (가장 자주 사용)
  standard,

  /// 화면 하단 작은 한 줄
  compact,

  /// 카드 안 인라인 라벨
  inline,
}
