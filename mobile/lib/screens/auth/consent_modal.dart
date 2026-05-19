// screens/auth/consent_modal.dart — 회원가입 진입 직전 약관 동의 모달
//
// 흐름: /login 회원가입 버튼 → showConsentModal() → 동의 시 /signup 으로 push
//       동의 안 하면 /login 그대로 유지
//
// 디자인: bottom sheet 형태 (Pillyze/토스 패턴),
//        흰 배경 + 라운드 상단, 핸들 + 타이틀 + 약관 4종 + CTA 2개

import 'package:flutter/material.dart';
import '../../utils/design_tokens_v2.dart';

/// 약관 동의 결과 — 필수 3종 동의 / 선택 1종 동의 / 취소
class ConsentResult {
  const ConsentResult({
    required this.agreed,
    required this.service,
    required this.privacy,
    required this.medical,
    required this.marketing,
  });
  final bool agreed;          // 필수 3종 모두 OK 이면 true
  final bool service;
  final bool privacy;
  final bool medical;
  final bool marketing;
}

/// 회원가입 진입 직전 약관 동의 bottom sheet.
/// 동의 → ConsentResult(agreed=true, ...) 반환
/// 닫기/취소 → null 반환
Future<ConsentResult?> showConsentModal(BuildContext context) {
  return showModalBottomSheet<ConsentResult>(
    context: context,
    backgroundColor: AppColor.surface,
    isScrollControlled: true,
    // Material 3 기본 drag handle 끔 — 자체 핸들과 중복돼 두 줄로 보임
    showDragHandle: false,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
    ),
    builder: (ctx) => const _ConsentSheet(),
  );
}

class _ConsentSheet extends StatefulWidget {
  const _ConsentSheet();
  @override
  State<_ConsentSheet> createState() => _ConsentSheetState();
}

class _ConsentSheetState extends State<_ConsentSheet> {
  bool _all = false;
  bool _service = false;
  bool _privacy = false;
  bool _medical = false;
  bool _marketing = false;

  bool get _requiredOk => _service && _privacy && _medical;

  void _toggleAll(bool v) {
    setState(() {
      _all = v;
      _service = v;
      _privacy = v;
      _medical = v;
      _marketing = v;
    });
  }

  void _onRowTap(VoidCallback set) {
    setState(() {
      set();
      _all = _service && _privacy && _medical && _marketing;
    });
  }

  void _confirm() {
    if (!_requiredOk) return;
    Navigator.of(context).pop(ConsentResult(
      agreed: true,
      service: _service,
      privacy: _privacy,
      medical: _medical,
      marketing: _marketing,
    ));
  }

  @override
  Widget build(BuildContext context) {
    // 통일된 섹션 간격 — 모든 큰 블록 사이 동일하게 sectionGap(28)
    const sectionGap = SizedBox(height: AppSpace.sectionGap);

    return SafeArea(
      child: Padding(
        // 2026-05-18: 회원가입 _BottomCta 와 시각 위치 매칭
        //   - bottom padding xl(24) → 모달 바닥에서 CTA 까지 거리 통일
        padding: const EdgeInsets.fromLTRB(
          AppSpace.page, AppSpace.lg, AppSpace.page, AppSpace.xl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 핸들
            Center(
              child: Container(
                width: 36, height: 4,
                decoration: BoxDecoration(
                  color: AppColor.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            sectionGap,

            // 타이틀
            Text('약관에 동의해주세요', style: AppText.title),
            const SizedBox(height: AppSpace.xs),
            // 서브타이틀 — 아래 동의 항목들과 동일 크기 (bodyLg - 1) + "보기" 와 같은 옅은 색
            Text(
              '서비스 이용을 위해 필수 항목 동의가 필요해요.',
              style: AppText.bodyLg.copyWith(
                fontSize: AppText.bodyLg.fontSize! - 1,
                color: AppColor.inkTertiary.withOpacity(0.6),
              ),
            ),
            sectionGap,

            // 전체 동의
            _RowItem(
              label: '전체 동의',
              required: false,
              value: _all,
              bold: true,
              onTap: () => _toggleAll(!_all),
            ),
            Divider(color: AppColor.border, height: AppSpace.lg),

            _RowItem(
              label: '서비스 이용 약관',
              required: true,
              value: _service,
              showViewLink: true,
              onTap: () => _onRowTap(() => _service = !_service),
              onViewTap: () {/* TODO: 약관 상세 화면 */},
            ),
            _RowItem(
              label: '개인정보 처리방침',
              required: true,
              value: _privacy,
              showViewLink: true,
              onTap: () => _onRowTap(() => _privacy = !_privacy),
              onViewTap: () {/* TODO */},
            ),
            _RowItem(
              label: '민감정보(만성질환·복용약) 수집 동의',
              required: true,
              value: _medical,
              showViewLink: true,
              onTap: () => _onRowTap(() => _medical = !_medical),
              onViewTap: () {/* TODO */},
            ),
            _RowItem(
              label: '마케팅 정보 수신 (선택)',
              required: false,
              value: _marketing,
              showViewLink: true,
              onTap: () => _onRowTap(() => _marketing = !_marketing),
              onViewTap: () {/* TODO */},
            ),

            sectionGap,

            // 의료 면책 — 작은 안내
            Container(
              padding: const EdgeInsets.all(AppSpace.cardInside),
              decoration: BoxDecoration(
                color: AppColor.brandSoft,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline, color: AppColor.brandDeep, size: 18),
                  const SizedBox(width: AppSpace.sm),
                  Expanded(
                    child: Text(
                      '레몬에이드는 건강 관리를 도와드리는 서비스로\n의사·약사·영양사의 진단을 대신하진 않아요.',
                      style: AppText.caption.copyWith(color: AppColor.ink, height: 1.5),
                    ),
                  ),
                ],
              ),
            ),

            sectionGap,

            // CTA — 취소 / 동의하고 시작
            Row(
              children: [
                Expanded(
                  child: AppSecondaryButton(
                    label: '취소',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
                const SizedBox(width: AppSpace.sm),
                Expanded(
                  flex: 2,
                  child: AppPrimaryButton(
                    label: '동의하고 시작',
                    accent: true,
                    enabled: _requiredOk,
                    onPressed: _requiredOk ? _confirm : null,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RowItem extends StatelessWidget {
  final String label;
  final bool required;
  final bool value;
  final bool bold;
  final bool showViewLink;        // 우측 "보기" 표시 여부 (전체동의는 X)
  final VoidCallback onTap;
  final VoidCallback? onViewTap;  // "보기" 클릭 시
  const _RowItem({
    required this.label,
    required this.required,
    required this.value,
    required this.onTap,
    this.bold = false,
    this.showViewLink = false,
    this.onViewTap,
  });

  @override
  Widget build(BuildContext context) {
    // 라벨 폰트 크기:
    //   - 전체 동의(bold=true): bodyLg + 1 → 살짝 더 큼
    //   - 개별 항목(bold=false): bodyLg - 1 → 아주 미세하게 줄임
    final base = bold
        ? AppText.bodyLg.copyWith(
            fontSize: AppText.bodyLg.fontSize! + 1,
            fontWeight: FontWeight.w700,
            color: AppColor.ink,
          )
        : AppText.bodyLg.copyWith(
            fontSize: AppText.bodyLg.fontSize! - 1,
            fontWeight: FontWeight.w500,
            color: AppColor.ink,
          );

    // 체크 원 — 모든 행 동일 크기, 글자 높이와 시각 정렬
    const iconSize = 18.0;

    return Padding(
      // 행간 일정 — vertical sm 으로 통일
      padding: const EdgeInsets.symmetric(vertical: AppSpace.sm),
      child: Row(
        children: [
          // 체크 + 라벨 영역만 토글 (탭 영역 분리)
          Expanded(
            child: GestureDetector(
              onTap: onTap,
              behavior: HitTestBehavior.opaque,
              child: Row(
                children: [
                  // 체크박스 — 미체크: 살짝 진한 회색 (#E5E8EB) / 체크: 브랜드 노랑
                  // 글자 baseline 과 시각 정렬 위해 더 아래로 (4px)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Container(
                      width: iconSize, height: iconSize,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: value ? AppColor.brand : const Color(0xFFE5E8EB),
                      ),
                      alignment: Alignment.center,
                      child: Icon(
                        Icons.check,
                        color: Colors.white,
                        size: iconSize * 0.62,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpace.md),
                  // 라벨
                  Expanded(
                    child: RichText(
                      text: TextSpan(
                        style: base,
                        children: [
                          if (required) TextSpan(text: '(필수) '),
                          TextSpan(text: label),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          // 우측 "보기" — 별도 탭, 옅은 회색
          if (showViewLink)
            GestureDetector(
              onTap: onViewTap ?? () {},
              behavior: HitTestBehavior.opaque,
              child: Padding(
                padding: const EdgeInsets.only(left: AppSpace.sm),
                child: Text(
                  '보기',
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary.withOpacity(0.6),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
