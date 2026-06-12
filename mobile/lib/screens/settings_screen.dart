import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../app_controller.dart';
import '../app_providers.dart';
import '../core/api/api_error.dart';
import '../core/storage/local_prefs.dart';
import '../features/auth/token_session.dart';
import '../features/consent/consent_models.dart';
import '../features/profile/profile_models.dart';
import '../shared/theme/brand_theme_controller.dart';
import '../utils/brand_palette.dart';
import '../utils/design_tokens_v2.dart';
import '../widgets/settings/settings_widgets.dart';

/// Source-style settings screen wired to the current auth and consent state.
class SettingsScreen extends ConsumerStatefulWidget {
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
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final TextEditingController _tokenController = TextEditingController();
  String? _tokenError;

  String? _displayName;
  String? _profileSummary;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadProfileHeader());
  }

  Future<void> _loadProfileHeader() async {
    final LocalPrefs? prefs = await ref.read(localPrefsProvider.future);
    final String? name = prefs?.profileDisplayName();
    try {
      final BodyProfileSnapshot? snapshot = await ref
          .read(profileRepositoryProvider)
          .fetchLatest();
      if (!mounted) return;
      setState(() {
        _displayName = name;
        _profileSummary = snapshot?.summaryLine();
      });
    } on ApiError {
      if (!mounted) return;
      setState(() => _displayName = name);
    }
  }

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
          _ProfileHeader(
            displayName: _displayName,
            summary: _profileSummary,
            onEdit: () => context.go('/shell/settings/profile-edit'),
          ),
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
                    const SectionLabel('내 건강'),
                    SettingsCard(
                      children: [
                        SettingsRow(
                          icon: Icons.medical_services_rounded,
                          iconBg: AppColor.successSoft,
                          iconColor: AppColor.success,
                          title: '만성질환·복약 정보',
                          subtitle: '복약 교차 점검에 쓰여요',
                          onTap: () =>
                              context.go('/shell/settings/health-profile'),
                        ),
                        const SettingsDivider(),
                        const SettingsRow(
                          icon: Icons.flag_rounded,
                          iconBg: Color(0xFFE8EDFF),
                          iconColor: Color(0xFF4D7BFF),
                          title: '관심 목적',
                          subtitle: '당뇨 · 혈압 · 체중 관리',
                        ),
                        const SettingsDivider(),
                        SettingsRow(
                          icon: Icons.straighten_rounded,
                          iconBg: AppColor.warningSoft,
                          iconColor: AppColor.warning,
                          title: '신체 정보',
                          subtitle: '키·몸무게·성별·나이',
                          onTap: () =>
                              context.go('/shell/settings/profile-edit'),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const SectionLabel('알림'),
                    SettingsCard(
                      children: [
                        SettingsRow(
                          icon: Icons.medication_rounded,
                          iconBg: AppColor.brandSoft,
                          iconColor: AppColor.brandDeep,
                          title: '복약 알림',
                          subtitle: '시간·요일을 맞춰 알려드려요',
                          onTap: () => context.go(
                            '/shell/settings/medication-reminders',
                          ),
                        ),
                        const SettingsDivider(),
                        SettingsRow(
                          icon: Icons.notifications_rounded,
                          iconBg: AppColor.brandSoft,
                          iconColor: AppColor.brandDeep,
                          title: '알림 설정',
                          subtitle: '복약 시간 · 평가 리포트',
                          onTap: () => context.go(
                            '/shell/settings/notification-settings',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const SectionLabel('계정'),
                    SettingsCard(
                      children: [
                        SettingsRow(
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
                        const SettingsDivider(),
                        SettingsRow(
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
                          onTap: () => context.go('/shell/settings/policies'),
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
                    const SectionLabel('OCR 테스트'),
                    const SettingsCard(
                      children: [
                        SettingsRow(
                          icon: Icons.camera_alt_rounded,
                          iconBg: AppColor.brandSoft,
                          iconColor: AppColor.brandDeep,
                          title: '촬영 환경',
                          subtitle: 'Android Studio AVD와 live flag 사용',
                        ),
                        SettingsDivider(),
                        SettingsRow(
                          icon: Icons.photo_library_rounded,
                          iconBg: AppColor.successSoft,
                          iconColor: AppColor.success,
                          title: '갤러리 입력',
                          subtitle: '선택 이미지는 앱 캐시에 복사 후 OCR 업로드',
                        ),
                        SettingsDivider(),
                        SettingsRow(
                          icon: Icons.psychology_rounded,
                          iconBg: AppColor.warningSoft,
                          iconColor: AppColor.warning,
                          title: '로컬 LLM 설명',
                          subtitle: 'Ollama 사용 여부는 백엔드 설정을 따름',
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const SectionLabel('안내'),
                    SettingsCard(
                      children: [
                        const SettingsRow(
                          icon: Icons.info_outline_rounded,
                          iconBg: Color(0xFFEDEFF3),
                          iconColor: AppColor.inkSecondary,
                          title: '서비스 정보',
                          subtitle: '의료 판단 전 전문 의료진 상담 필요',
                        ),
                        const SettingsDivider(),
                        SettingsRow(
                          icon: Icons.gavel_rounded,
                          iconBg: const Color(0xFFEDEFF3),
                          iconColor: AppColor.inkSecondary,
                          title: '약관 · 개인정보',
                          subtitle: '약관·정책과 동의 관리',
                          onTap: () => context.go('/shell/settings/policies'),
                        ),
                        const SettingsDivider(),
                        SettingsRow(
                          icon: Icons.person_off_rounded,
                          iconBg: AppColor.dangerSoft,
                          iconColor: AppColor.danger,
                          title: '회원 탈퇴',
                          subtitle: '계정과 데이터를 삭제해요',
                          onTap: () => context.go('/shell/settings/withdraw'),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.lg),
                    const SectionLabel('테마 색상'),
                    Consumer(
                      builder: (
                        BuildContext context,
                        WidgetRef ref,
                        Widget? child,
                      ) {
                        final BrandTheme current =
                            ref.watch(brandThemeProvider);
                        return SettingsCard(
                          children: [
                            _ThemeSwatchRow(
                              current: current,
                              onSelect: (BrandTheme t) =>
                                  ref
                                      .read(brandThemeProvider.notifier)
                                      .select(t),
                            ),
                          ],
                        );
                      },
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
  const _ProfileHeader({
    required this.displayName,
    required this.summary,
    required this.onEdit,
  });

  final String? displayName;
  final String? summary;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    final String name = (displayName == null || displayName!.isEmpty)
        ? '레몬 회원님'
        : '$displayName님';
    final String subtitle = summary ?? '신체 정보를 입력하면 분석이 더 정확해져요';
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
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: AppColor.ink,
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: const TextStyle(
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
                  onPressed: onEdit,
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

/// 4색 브랜드 테마 스와치 행 (Figma S-13).
///
/// 옐로/퍼플/그린/블루 스와치 4개를 가로로 나열한다.
/// 선택된 항목은 검정 외곽선 + 체크 아이콘으로 표시.
class _ThemeSwatchRow extends StatelessWidget {
  const _ThemeSwatchRow({
    required this.current,
    required this.onSelect,
  });

  final BrandTheme current;
  final ValueChanged<BrandTheme> onSelect;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '앱 색상 테마',
                  style: AppText.subtitle.copyWith(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  current.label,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
          Row(
            children: BrandTheme.values.map((BrandTheme t) {
              final bool selected = t == current;
              return Padding(
                padding: const EdgeInsets.only(left: AppSpace.sm),
                child: GestureDetector(
                  onTap: () => onSelect(t),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: t.color,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: selected
                            ? AppColor.ink
                            : Colors.transparent,
                        width: 2.5,
                      ),
                    ),
                    child: selected
                        ? const Icon(
                            Icons.check_rounded,
                            color: Colors.black,
                            size: 18,
                          )
                        : null,
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
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
