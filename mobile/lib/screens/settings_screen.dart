import 'package:flutter/material.dart';

import '../app_controller.dart';
import '../features/auth/token_session.dart';
import '../features/consent/consent_models.dart';
import '../utils/design_tokens_v2.dart';

/// Source-style settings screen wired to the current auth and consent state.
class SettingsScreen extends StatefulWidget {
  /// Creates the settings screen.
  ///
  /// Args:
  ///   controller: Current app controller for consent state.
  ///   session: Current token session controller for dev/JWT access.
  const SettingsScreen({
    required this.controller,
    required this.session,
    super.key,
  });

  /// App controller used by the existing consent flow.
  final AppController controller;

  /// Token session used by the existing backend auth contract.
  final TokenSessionController session;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _tokenController = TextEditingController();
  String? _tokenError;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool ocrConsentGranted =
        widget.controller.consentState?.isGranted(AppController.ocrConsent) ??
        false;
    final bool healthConsentGranted =
        widget.controller.consentState?.isGranted(
          AppController.healthConsent,
        ) ??
        false;

    return Scaffold(
      backgroundColor: AppColor.section,
      body: Column(
        children: [
          const _ProfileHeader(),
          Expanded(
            child: Transform.translate(
              offset: const Offset(0, -36),
              child: Container(
                decoration: const BoxDecoration(
                  color: AppColor.section,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(28),
                    topRight: Radius.circular(28),
                  ),
                ),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpace.page,
                    AppSpace.lg,
                    AppSpace.page,
                    AppSpace.xl + 80,
                  ),
                  children: [
                    const _SectionLabel('내 건강'),
                    const _SettingsCard(
                      children: [
                        _SettingsRow(
                          icon: Icons.medical_services_rounded,
                          iconBg: AppColor.successSoft,
                          iconColor: AppColor.success,
                          title: '만성질환·복약 정보',
                          subtitle: '복약 교차 점검에 쓰여요',
                        ),
                        _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.flag_rounded,
                          iconBg: Color(0xFFE8EDFF),
                          iconColor: Color(0xFF4D7BFF),
                          title: '관심 목적',
                          subtitle: '당뇨 · 혈압 · 체중 관리',
                        ),
                        _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.straighten_rounded,
                          iconBg: AppColor.warningSoft,
                          iconColor: AppColor.warning,
                          title: '신체 정보',
                          subtitle: '키·몸무게·성별·나이',
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const _SectionLabel('알림'),
                    const _SettingsCard(
                      children: [
                        _SettingsRow(
                          icon: Icons.notifications_rounded,
                          iconBg: AppColor.brandSoft,
                          iconColor: AppColor.brandDeep,
                          title: '알림 설정',
                          subtitle: '복약 시간 · 평가 리포트',
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const _SectionLabel('계정'),
                    _SettingsCard(
                      children: [
                        _SettingsRow(
                          icon: Icons.person_rounded,
                          iconBg: const Color(0xFFEDEFF3),
                          iconColor: AppColor.inkSecondary,
                          title: '내 정보',
                          subtitle: widget.session.devBypassActive
                              ? '로컬 dev bypass 사용 중'
                              : widget.session.bearerToken == null
                              ? '외부 JWT 토큰 미설정'
                              : '외부 JWT 토큰 저장됨',
                        ),
                        const _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.shield_rounded,
                          iconBg: ocrConsentGranted && healthConsentGranted
                              ? AppColor.successSoft
                              : AppColor.warningSoft,
                          iconColor: ocrConsentGranted && healthConsentGranted
                              ? AppColor.success
                              : AppColor.warning,
                          title: '동의 관리',
                          subtitle: ocrConsentGranted && healthConsentGranted
                              ? 'OCR 이미지 · 민감 건강 분석 동의 완료'
                              : 'OCR 이미지 · 민감 건강 분석 동의 필요',
                        ),
                        const SizedBox(height: AppSpace.md),
                        _ConsentStatusCard(
                          consentState: widget.controller.consentState,
                          busy: widget.controller.busy,
                          onGrant: widget.controller.grantMinimumConsents,
                          onReload: widget.controller.bootstrap,
                        ),
                        const SizedBox(height: AppSpace.md),
                        _TokenAccessCard(
                          controller: _tokenController,
                          errorText: _tokenError,
                          session: widget.session,
                          onSave: _saveToken,
                          onClear: widget.session.bearerToken == null
                              ? null
                              : widget.session.clearBearerToken,
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const _SectionLabel('OCR 테스트'),
                    const _SettingsCard(
                      children: [
                        _SettingsRow(
                          icon: Icons.camera_alt_rounded,
                          iconBg: AppColor.brandSoft,
                          iconColor: AppColor.brandDeep,
                          title: '촬영 환경',
                          subtitle: 'Android Studio AVD와 live flag 사용',
                        ),
                        _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.photo_library_rounded,
                          iconBg: AppColor.successSoft,
                          iconColor: AppColor.success,
                          title: '갤러리 입력',
                          subtitle: '선택 이미지는 앱 캐시에 복사 후 OCR 업로드',
                        ),
                        _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.psychology_rounded,
                          iconBg: AppColor.warningSoft,
                          iconColor: AppColor.warning,
                          title: '로컬 LLM 설명',
                          subtitle: 'Ollama 사용 여부는 백엔드 설정을 따름',
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const _SectionLabel('안내'),
                    const _SettingsCard(
                      children: [
                        _SettingsRow(
                          icon: Icons.info_outline_rounded,
                          iconBg: Color(0xFFEDEFF3),
                          iconColor: AppColor.inkSecondary,
                          title: '서비스 정보',
                          subtitle: '의료 판단 전 전문 의료진 상담 필요',
                        ),
                        _SettingsDivider(),
                        _SettingsRow(
                          icon: Icons.download_rounded,
                          iconBg: Color(0xFFEDEFF3),
                          iconColor: AppColor.inkSecondary,
                          title: '데이터 내보내기',
                          subtitle: '민감정보 export는 별도 승인 후 연결',
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    Center(
                      child: Text(
                        'v1.0.0 · Lemon Aid',
                        style: AppText.caption.copyWith(
                          color: AppColor.inkTertiary,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _saveToken() async {
    setState(() {
      _tokenError = null;
    });
    try {
      await widget.session.saveBearerToken(_tokenController.text);
      _tokenController.clear();
      if (mounted) FocusScope.of(context).unfocus();
    } on ArgumentError {
      setState(() {
        _tokenError = '토큰을 입력해주세요.';
      });
    }
  }
}

class _ConsentStatusCard extends StatelessWidget {
  const _ConsentStatusCard({
    required this.consentState,
    required this.busy,
    required this.onGrant,
    required this.onReload,
  });

  final ConsentState? consentState;
  final bool busy;
  final Future<void> Function() onGrant;
  final Future<void> Function() onReload;

  @override
  Widget build(BuildContext context) {
    final bool ocrGranted =
        consentState?.isGranted(AppController.ocrConsent) ?? false;
    final bool healthGranted =
        consentState?.isGranted(AppController.healthConsent) ?? false;
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '필수 동의 상태',
            style: AppText.caption.copyWith(
              color: AppColor.ink,
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          _ConsentPill(label: 'OCR 이미지 처리', granted: ocrGranted),
          const SizedBox(height: AppSpace.xs),
          _ConsentPill(label: '민감 건강 분석', granted: healthGranted),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: busy ? null : onGrant,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColor.brand,
                    foregroundColor: AppColor.ink,
                  ),
                  child: const Text('필수 동의 허용'),
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              OutlinedButton(
                onPressed: busy ? null : onReload,
                child: const Text('새로고침'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConsentPill extends StatelessWidget {
  const _ConsentPill({required this.label, required this.granted});

  final String label;
  final bool granted;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          granted
              ? Icons.check_circle_rounded
              : Icons.radio_button_unchecked_rounded,
          color: granted ? AppColor.success : AppColor.inkTertiary,
          size: 18,
        ),
        const SizedBox(width: AppSpace.xs),
        Expanded(
          child: Text(
            label,
            style: AppText.caption.copyWith(
              color: AppColor.ink,
              fontWeight: FontWeight.w700,
              letterSpacing: 0,
            ),
          ),
        ),
        Text(
          granted ? '허용됨' : '필요',
          style: AppText.micro.copyWith(
            color: granted ? AppColor.success : AppColor.inkTertiary,
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
        ),
      ],
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColor.brand,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page,
            AppSpace.xxl,
            AppSpace.page,
            AppSpace.xxl + 40,
          ),
          child: Row(
            children: [
              const CircleAvatar(
                radius: 42,
                backgroundColor: AppColor.brandTint,
                child: Icon(
                  Icons.person_rounded,
                  color: AppColor.ink,
                  size: 38,
                ),
              ),
              const SizedBox(width: AppSpace.lg),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '태동님',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                    SizedBox(height: 6),
                    Text(
                      '레몬에이드와 함께한 지 12일',
                      style: TextStyle(
                        color: AppColor.ink,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0,
                      ),
                    ),
                  ],
                ),
              ),
              DecoratedBox(
                decoration: const BoxDecoration(
                  color: AppColor.brandTint,
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.edit_rounded),
                  color: AppColor.ink,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 6, bottom: AppSpace.sm),
      child: Text(
        label,
        style: AppText.caption.copyWith(
          color: AppColor.inkTertiary,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.cardInside,
        vertical: AppSpace.md,
      ),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.14),
            blurRadius: 18,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(children: children),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({
    required this.icon,
    required this.iconBg,
    required this.iconColor,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final Color iconBg;
  final Color iconColor;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: iconBg,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Icon(icon, color: iconColor, size: 24),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppText.subtitle.copyWith(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded, color: AppColor.inkTertiary),
        ],
      ),
    );
  }
}

class _SettingsDivider extends StatelessWidget {
  const _SettingsDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(height: 1, color: AppColor.border);
  }
}

class _TokenAccessCard extends StatelessWidget {
  const _TokenAccessCard({
    required this.controller,
    required this.session,
    required this.onSave,
    required this.onClear,
    this.errorText,
  });

  final TextEditingController controller;
  final TokenSessionController session;
  final VoidCallback onSave;
  final VoidCallback? onClear;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'API access',
            style: AppText.caption.copyWith(
              color: AppColor.ink,
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          TextField(
            controller: controller,
            obscureText: true,
            decoration: InputDecoration(
              hintText: 'JWT bearer token',
              errorText: errorText,
              filled: true,
              fillColor: AppColor.surface,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: onSave,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColor.brand,
                    foregroundColor: AppColor.ink,
                  ),
                  child: const Text('저장'),
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              OutlinedButton(onPressed: onClear, child: const Text('삭제')),
            ],
          ),
        ],
      ),
    );
  }
}
