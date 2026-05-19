// screens/auth/signup_flow_screen.dart — 회원가입 10-step Flow (v2)
//
// 2026-05-18 갱신:
//   - 배경 무조건 흰색 (#FFFFFF), 카드는 흰 + 1px border (포인트 액센트만)
//   - 좌우 패딩 AppSpace.page (20) 통일
//   - PageView 안전성 (initialPage / keep alive)
//   - 마스코트 character-cutout.png + errorBuilder (실패 시 fallback)
//   - 메시지: "사진 한 장으로 끝" → "영양제·식단 사진으로 5종 분석"
//             "병원 기록을 기억하는 Agent" → "내 만성질환·복약·검사값을 함께 봐드려요"
//             "AI는 거드는 손길" → "AI는 보여드리고, 결정은 당신이"
//   - 진행 바 + 뒤로 + step 표시 위치 정렬
//
// 구성: Claude Design v1 의 10-step (Welcome / Profile / Purpose / Concerns /
//       Body / Healthkit / MealTimes / Review / Dashboard / Terms)
// 디자인: design_tokens_v2 (Lemon Yellow brand + 흰 + 검정 텍스트)

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../../services/token_storage.dart';
import '../../utils/design_tokens_v2.dart';
import '../../utils/router.dart';

// ─── 데이터 모델 ─────────────────────────────
class SignupData {
  // 이메일 가입자만 사용 (OAuth 는 자동 검증 → 비움)
  String? email;
  String? password;
  bool emailVerified = false;

  String? name;
  DateTime? birthDate;
  String? sex; // M / F
  Set<String> purposes = {};
  Set<String> concerns = {};
  int? heightCm;
  double? weightKg;
  double? targetWeightKg;
  bool healthkitConsent = false;        // 전체 (legacy)
  bool healthSteps = false;             // 걸음수
  bool healthWorkout = false;           // 운동
  bool healthActivity = false;          // 활동량
  bool termsAgree = false;
}

const _CONCERNS = [
  ('fatigue', '피로감', Icons.battery_charging_full, '추천'),
  ('chronic', '만성질환', Icons.favorite, null),
  ('liver', '간 건강', Icons.eco, null),
  ('chol', '콜레스테롤', Icons.water_drop_outlined, null),
  ('eye', '눈 건강', Icons.visibility_outlined, null),
  ('muscle', '운동·근육', Icons.fitness_center, null),
  ('bp', '혈압', Icons.show_chart, null),
  ('sleep', '수면·스트레스', Icons.nightlight_round, null),
  ('immune', '면역', Icons.shield_outlined, null),
];

const _PURPOSES = [
  ('chronic', '만성질환 관리', Icons.favorite),
  ('supplement', '영양제 관리', Icons.medication),
  ('diet', '식단·다이어트', Icons.restaurant),
  ('blood', '혈당 관리', Icons.water_drop),
];

const _TOTAL_STEPS = 9; // 2026-05-19: MealTimes 제거

class SignupFlowScreen extends ConsumerStatefulWidget {
  /// OAuth(카카오/구글) 신규 사용자 진입 시 true
  /// → 이메일·비번·인증 단계 건너뜀 (이미 OAuth 측에서 검증됨)
  final bool oauthMode;
  /// 회원가입 진입 직전 약관 모달에서 사전 동의함 → step 10 약관 스킵
  final bool preConsented;
  /// 사전 동의 시 마케팅 동의 여부
  final bool marketingAgreed;
  /// OAuth 로 받은 이름 (있으면 SignupData.name 미리 채움)
  final String? prefillName;
  /// OAuth 로 받은 이메일 (있으면 SignupData.email 미리 채움)
  final String? prefillEmail;

  const SignupFlowScreen({
    super.key,
    this.oauthMode = false,
    this.preConsented = false,
    this.marketingAgreed = false,
    this.prefillName,
    this.prefillEmail,
  });

  @override
  ConsumerState<SignupFlowScreen> createState() => _SignupFlowScreenState();
}

class _SignupFlowScreenState extends ConsumerState<SignupFlowScreen> {
  int _step = 1;
  final _data = SignupData();
  late final PageController _pageCtrl;

  @override
  void initState() {
    super.initState();
    _pageCtrl = PageController(initialPage: 0, keepPage: true);
    // OAuth 진입 시 받은 이름/이메일 미리 채워넣기
    if (widget.prefillName != null && widget.prefillName!.isNotEmpty) {
      _data.name = widget.prefillName;
    }
    if (widget.prefillEmail != null && widget.prefillEmail!.isNotEmpty) {
      _data.email = widget.prefillEmail;
      // OAuth 측에서 이미 이메일 인증된 상태로 간주
      if (widget.oauthMode) {
        _data.emailVerified = true;
      }
    }
    // 회원가입 진입 직전 약관 모달에서 사전 동의 → step 10 약관 스킵
    if (widget.preConsented) {
      _data.termsAgree = true;
    }
  }

  /// 총 step 수 동적 계산
  ///   기본 10 (Welcome / Profile / Purpose / Concerns / Body / Healthkit / MealTimes / Review / Dashboard / Terms)
  ///   + 1 (Email — 이메일 가입자 전용, OAuth 모드면 제외)
  ///   - 1 (약관 — preConsented 시 제외)
  int get _totalSteps {
    var n = _TOTAL_STEPS;
    if (!widget.oauthMode) n += 1;       // Email 추가
    if (widget.preConsented) n -= 1;     // Terms 제외
    return n;
  }

  @override
  void dispose() {
    _pageCtrl.dispose();
    super.dispose();
  }

  void _next() {
    if (!_canNext()) return;
    if (_step < _totalSteps) {
      setState(() => _step++);
      // PageView 안전 호출 — hasClients 체크 (페이지 넘김 에러 방지)
      if (_pageCtrl.hasClients) {
        _pageCtrl.animateToPage(
          _step - 1,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOutCubic,
        );
      }
    } else {
      _finish();
    }
  }

  void _back() {
    if (_step > 1) {
      setState(() => _step--);
      if (_pageCtrl.hasClients) {
        _pageCtrl.animateToPage(
          _step - 1,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOutCubic,
        );
      }
    } else {
      if (context.canPop()) {
        context.pop();
      } else {
        context.go(AppRoute.login);
      }
    }
  }

  Future<void> _finish() async {
    // 회원가입 완료 플래그 박음 — 다음 로그인부터 signup_flow 건너뜀
    try {
      await TokenStorage().markSignupComplete();
    } catch (_) {/* 무시 */}
    // "메인 화면에서 로그인해주세요" 흐름 — 자동 로그인 X
    // 로그인 화면으로 이동, 사용자가 직접 로그인 시 → shell 로 진입
    if (mounted) context.go(AppRoute.login);
  }

  /// PageView 의 실제 children 순서 (OAuth 모드에 따라 Email 포함/제외)
  /// step 번호(1-base) → semantic key 매핑
  String _stepKey(int step) {
    final pages = <String>[
      'welcome',
      'profile',
      if (!widget.oauthMode) 'email',
      'purpose',
      'concerns',
      'body',
      'healthkit',
      'review',
      'dashboard',
      if (!widget.preConsented) 'terms',
    ];
    final idx = step - 1;
    if (idx < 0 || idx >= pages.length) return 'unknown';
    return pages[idx];
  }

  bool _canNext() {
    switch (_stepKey(_step)) {
      case 'welcome':
        return true;
      case 'profile':
        return _data.name?.trim().isNotEmpty == true &&
               _data.birthDate != null &&
               _data.sex != null;
      case 'email':
        // 임시 — 인증 우회 (UI 수정 중)
        // TODO: 복원 시 emailVerified 검증 다시 추가
        return true;
      case 'purpose':   return _data.purposes.isNotEmpty;
      case 'concerns':  return _data.concerns.isNotEmpty;
      case 'body':      return _data.heightCm != null && _data.weightKg != null;
      case 'healthkit':
      case 'review':
      case 'dashboard': return true;
      case 'terms':     return _data.termsAgree;
      default:          return false;
    }
  }

  String _ctaLabel() => _step == _totalSteps ? '메인으로' : '다음';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.bg,  // 무조건 흰색
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(step: _step, total: _totalSteps, onBack: _back),
            Expanded(
              child: PageView(
                controller: _pageCtrl,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _StepWelcome(),
                  _StepProfile(
                    data: _data,
                    onChange: () => setState(() {}),
                  ),
                  // 이메일 가입자 전용 step (OAuth 모드면 건너뜀)
                  if (!widget.oauthMode)
                    _StepEmail(
                      data: _data,
                      onChange: () => setState(() {}),
                      onProceed: _next,
                      onSendCode: (email) => ref
                          .read(authControllerProvider.notifier)
                          .sendEmailCode(email: email),
                      onVerifyCode: (email, code) => ref
                          .read(authControllerProvider.notifier)
                          .verifyEmailCode(email: email, code: code),
                    ),
                  _StepPurpose(data: _data, onChange: () => setState(() {})),
                  _StepConcerns(data: _data, onChange: () => setState(() {})),
                  _StepBody(data: _data, onChange: () => setState(() {})),
                  _StepHealthkit(data: _data, onChange: () => setState(() {})),
                  _StepReview(data: _data),
                  _StepDashboard(),
                  // preConsented (회원가입 진입 시 모달 동의) → step 10 약관 화면 스킵
                  if (!widget.preConsented)
                    _StepTerms(data: _data, onChange: () => setState(() {})),
                ],
              ),
            ),
            _BottomCta(
              label: _ctaLabel(),
              enabled: _canNext(),
              onPressed: _next,
            ),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 상단 바 — 정확 정렬 (좌 ←, 중앙 진행바, 우 step/total)
// ═══════════════════════════════════════════
class _TopBar extends StatelessWidget {
  final int step;
  final int total;
  final VoidCallback onBack;
  const _TopBar({required this.step, required this.total, required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      color: AppColor.bg,
      // 좌측 패딩 살짝 줄여서 전체 진행바·카운트 묶음 좌측으로 미세 이동
      padding: const EdgeInsets.fromLTRB(
        AppSpace.lg, 0, AppSpace.page, 0,
      ),
      child: Row(
        children: [
          // 뒤로 ← (ripple 동그라미 없음, 더 연한 색)
          GestureDetector(
            onTap: onBack,
            behavior: HitTestBehavior.opaque,
            child: SizedBox(
              width: 28, height: 28,
              child: Icon(
                Icons.arrow_back_ios_new,
                color: AppColor.inkSecondary,
                size: 18,
              ),
            ),
          ),
          const SizedBox(width: AppSpace.sm),

          // 진행바 (길이 원래대로, 위치만 왼쪽으로)
          // Expanded 로 가용 폭 다 차지 + 우측 끝에 step 카운터
          // 좌측 밀림은 ← 뒤 SizedBox(md) 줄이고 우측 카운트 폭 줄여서 확보
          Expanded(
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: step / total),
              duration: const Duration(milliseconds: 280),
              curve: Curves.easeOutCubic,
              builder: (ctx, v, _) => ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.full),
                child: LinearProgressIndicator(
                  value: v,
                  // 더 얇고 연하게 — 6 → 4
                  minHeight: 4,
                  // 배경: 매우 옅은 회색
                  backgroundColor: const Color(0xFFF1F3F6),
                  // 채움: brand 보다 한 톤 옅은 노랑 (brandSoft 정도)
                  valueColor: AlwaysStoppedAnimation(AppColor.brand.withOpacity(0.7)),
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          Text(
            '$step / $total',
            style: AppText.caption.copyWith(
              color: AppColor.inkTertiary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 하단 CTA — Login 화면과 통일 (AppPrimaryButton 사용, accent: true)
// 노랑 brand + 검정 텍스트, height/style 동일
// ═══════════════════════════════════════════
class _BottomCta extends StatelessWidget {
  final String label;
  final bool enabled;
  final VoidCallback onPressed;
  const _BottomCta({required this.label, required this.enabled, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    // 2026-05-18: 약관 모달 CTA 와 동일 위치 — SafeArea 바닥에서 xl(24)
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, 0, AppSpace.page, AppSpace.xl,
      ),
      child: AppPrimaryButton(
        label: label,
        enabled: enabled,
        accent: true,
        onPressed: enabled ? onPressed : null,
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 공통 — 흰 카드 + 1px 테두리 (포인트 액센트만)
// ═══════════════════════════════════════════
BoxDecoration _cardDeco({bool selected = false}) => BoxDecoration(
      color: AppColor.surface,  // 무조건 흰색
      borderRadius: BorderRadius.circular(AppRadius.md),
      border: Border.all(
        color: selected ? AppColor.brand : AppColor.border,
        width: selected ? 2 : 1,
      ),
    );

Widget _mascot({double height = 160}) {
  return Image.asset(
    'assets/mascot/character-cutout.png',
    height: height,
    fit: BoxFit.contain,
    errorBuilder: (ctx, err, st) {
      // 자산 누락 시 fallback — pubspec.yaml 등록 안 됐거나 깨졌을 때
      return Container(
        height: height, width: height,
        decoration: BoxDecoration(
          color: AppColor.brandSoft,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(Icons.emoji_food_beverage, size: height * 0.5, color: AppColor.brand),
      );
    },
  );
}

// ═══════════════════════════════════════════
// Step 1: 환영
// 순서: 타이틀 → 서브 → 캐릭터 → 1번 박스 → 2번 박스
// 1·2번 박스는 진입 후 순차적으로 fade + slide 등장 (320ms 간격)
// ═══════════════════════════════════════════
class _StepWelcome extends StatefulWidget {
  @override
  State<_StepWelcome> createState() => _StepWelcomeState();
}

class _StepWelcomeState extends State<_StepWelcome> {
  bool _showTitle = false;
  bool _showSub = false;
  bool _showBox1 = false;
  bool _showBox2 = false;

  @override
  void initState() {
    super.initState();
    // 진입 후 순차적 등장 — 토스 톤
    // 타이틀(80ms) → 서브(520ms) → 박스1(900ms) → 박스2(1350ms)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 80), () {
        if (mounted) setState(() => _showTitle = true);
      });
      Future.delayed(const Duration(milliseconds: 520), () {
        if (mounted) setState(() => _showSub = true);
      });
    });
    Future.delayed(const Duration(milliseconds: 900), () {
      if (mounted) setState(() => _showBox1 = true);
    });
    Future.delayed(const Duration(milliseconds: 1350), () {
      if (mounted) setState(() => _showBox2 = true);
    });
  }

  Widget _appearTitle(bool show, Widget child) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 700),
      curve: Curves.easeOutQuart,
      offset: show ? Offset.zero : const Offset(0, 0.32),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 700),
        curve: Curves.easeOutCubic,
        opacity: show ? 1 : 0,
        child: child,
      ),
    );
  }

  Widget _appearSub(bool show, Widget child) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOutCubic,
      offset: show ? Offset.zero : const Offset(0, 0.24),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        opacity: show ? 1 : 0,
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. 타이틀 — 토스 톤 동적 등장
          _appearTitle(_showTitle, Text('환영해요', style: AppText.display)),
          const SizedBox(height: AppSpace.xs + 4),
          // 2. 서브 타이틀 — 타이틀 뒤에 한 박자 늦게
          _appearSub(_showSub, Text(
            '만성질환을 함께 챙기는,\nAI 영양·복약 동반 앱이에요.',
            style: AppText.bodyLg.copyWith(color: AppColor.inkSecondary, height: 1.5),
          )),

          // 3. 캐릭터 (타이틀·서브 아래, 시각 중심 가운데)
          // 캐릭터 위 여백 살짝 키워서 아래로 — md(12) → lg(16)+xs(4)=20
          const SizedBox(height: AppSpace.lg + AppSpace.xs),
          Center(
            child: Transform.translate(
              // 캐릭터 살짝 더 아래로 (8 → 14), 가로 그대로
              offset: const Offset(0, 14),
              child: Image.asset(
                'assets/mascot/hello-mascot.png',
                // 200 → 216 미세 확대
                height: 216,
                fit: BoxFit.contain,
                errorBuilder: (ctx, err, st) => _mascot(height: 216),
              ),
            ),
          ),
          // 박스 묶음 미세하게 더 아래로 — sectionGap(28) + lg(16) = 44
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),

          // 4. 핵심 메시지 카드 — 순차 fade+slide 등장
          _AnimatedAppear(
            visible: _showBox1,
            child: _FeatureRow(
              num: '1',
              title: '영양제와 식단을 사진으로 기록해요',
              body: '약통이나 식사를 카메라로 찍으면 부족한 영양소, 과다 섭취, 주의해야 할 성분까지 한눈에 정리해드려요.',
            ),
          ),
          const SizedBox(height: AppSpace.md),
          _AnimatedAppear(
            visible: _showBox2,
            child: _FeatureRow(
              num: '2',
              title: '나의 만성질환과 복용 중인 약을 기억해요',
              body: '병원 기록과 복용 중인 약을 함께 살펴 영양제·식단이 안전한지 같이 확인해드려요.',
            ),
          ),
        ],
      ),
    );
  }
}

/// fade + slide(16px ↑) 적당한 페이스의 등장.
/// 500ms easeOutCubic.
class _AnimatedAppear extends StatelessWidget {
  final bool visible;
  final Widget child;
  const _AnimatedAppear({required this.visible, required this.child});

  @override
  Widget build(BuildContext context) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 500),
      curve: Curves.easeOutCubic,
      offset: visible ? Offset.zero : const Offset(0, 0.16),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeOutCubic,
        opacity: visible ? 1 : 0,
        child: child,
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  final String num;
  final String title;
  final String body;
  const _FeatureRow({required this.num, required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    // Flat 톤 — 메인 흰색 버튼 패턴 기반, 그림자 더 옅게
    //   - 흰 배경
    //   - 라운드: AppRadius.sm (12)
    //   - 그림자 한 겹만, 매우 옅게 (떠있는 느낌 최소화)
    //   - 테두리 X
    return Container(
      padding: const EdgeInsets.all(AppSpace.cardInside + 2),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(140, 155, 175, 0.20),
            blurRadius: 16,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 번호 배지 — 노랑 라운드 사각형 (flat 톤)
          Container(
            width: 28, height: 28,
            decoration: BoxDecoration(
              color: AppColor.brand,
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            alignment: Alignment.center,
            child: Text(
              num,
              style: AppText.subtitle.copyWith(
                color: AppColor.ink,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppText.subtitle),
                const SizedBox(height: AppSpace.xs),
                Text(
                  body,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkSecondary,
                    height: 1.55,
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
// Step 2: 프로필 (이름 + 생년월일 + 성별)
// 이메일/비번/인증은 _StepEmail (step 3) 에서 별도 처리
// ═══════════════════════════════════════════
class _StepProfile extends StatefulWidget {
  final SignupData data;
  final VoidCallback onChange;

  const _StepProfile({
    required this.data,
    required this.onChange,
  });

  @override
  State<_StepProfile> createState() => _StepProfileState();
}

class _StepProfileState extends State<_StepProfile> with AutomaticKeepAliveClientMixin {
  late final TextEditingController _name = TextEditingController(text: widget.data.name ?? '');

  @override
  bool get wantKeepAlive => true;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    // Cupertino 휠 스타일 (Pillyze 스타일, 시니어 친화)
    final initial = widget.data.birthDate ?? DateTime(1970, 1, 1);
    DateTime picked = initial;

    await showModalBottomSheet(
      context: context,
      backgroundColor: AppColor.surface,
      // consent_modal 과 핸들 패턴 통일 — Material 3 기본 핸들 OFF, 자체 핸들 사용
      showDragHandle: false,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Container(
            padding: const EdgeInsets.only(top: AppSpace.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // 핸들 (얇고 연하게)
                Container(
                  width: 36, height: 4,
                  decoration: BoxDecoration(
                    color: AppColor.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: AppSpace.lg),
                Text('생년월일 선택', style: AppText.subtitle),
                const SizedBox(height: AppSpace.md),
                // Cupertino 휠 datepicker
                // selectionOverlay 의 가로 회색선 2개 제거 → 깔끔한 화이트
                SizedBox(
                  height: 220,
                  child: CupertinoTheme(
                    data: CupertinoThemeData(
                      textTheme: CupertinoTextThemeData(
                        dateTimePickerTextStyle: AppText.subtitle.copyWith(color: AppColor.ink),
                      ),
                    ),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        CupertinoDatePicker(
                          mode: CupertinoDatePickerMode.date,
                          initialDateTime: initial,
                          minimumYear: 1930,
                          maximumYear: DateTime.now().year,
                          dateOrder: DatePickerDateOrder.ymd,
                          onDateTimeChanged: (v) {
                            picked = v;
                          },
                        ),
                        // 회색선 2개 가리기용 투명 IgnorePointer
                        // selectionOverlay 의 stroke 만 덮음 (선택 영역은 그대로)
                        IgnorePointer(
                          child: Container(
                            height: 36,
                            decoration: BoxDecoration(
                              border: Border.symmetric(
                                horizontal: BorderSide(color: AppColor.surface, width: 1),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: AppSpace.md),
                // 확인 버튼
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpace.page),
                  child: AppPrimaryButton(
                    label: '확인',
                    accent: true,
                    onPressed: () => Navigator.of(ctx).pop(),
                  ),
                ),
                const SizedBox(height: AppSpace.lg),
              ],
            ),
          ),
        );
      },
    );

    widget.data.birthDate = picked;
    widget.onChange();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '어떻게 불러드릴까요?',
            subtitle: '정확한 분석을 위해 기본 정보가 필요해요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),

          // 콘텐츠 — 헤더 애니메이션 후 stagger 등장
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 130),
            children: [
              _FloatingField(
                label: '이름',
                controller: _name,
                hasValue: (widget.data.name?.isNotEmpty ?? false),
                onChanged: (v) {
                  widget.data.name = v;
                  widget.onChange();
                  setState(() {});
                },
              ),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 220),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeOutCubic,
                transitionBuilder: (child, anim) => FadeTransition(
                  opacity: anim,
                  child: SizeTransition(
                    sizeFactor: anim,
                    axisAlignment: -1,
                    child: child,
                  ),
                ),
                child: (widget.data.name?.trim().isNotEmpty ?? false)
                    ? Padding(
                        key: const ValueKey('name-hint'),
                        padding: const EdgeInsets.only(top: AppSpace.sm),
                        child: Text(
                          '권장 칼로리, 영양 성분 섭취량은\n성별과 만 나이에 따라 달라질 수 있어요.',
                          style: AppText.body.copyWith(
                            color: AppColor.inkTertiary.withOpacity(0.7),
                            height: 1.5,
                          ),
                        ),
                      )
                    : const SizedBox.shrink(key: ValueKey('name-hint-empty')),
              ),
              const SizedBox(height: AppSpace.sectionGap + AppSpace.sm),
              _FloatingField(
                label: '생년월일',
                hasValue: widget.data.birthDate != null,
                readOnly: true,
                onTap: _pickDate,
                valueText: widget.data.birthDate != null
                    ? '${widget.data.birthDate!.year}.${widget.data.birthDate!.month.toString().padLeft(2, '0')}.${widget.data.birthDate!.day.toString().padLeft(2, '0')}'
                    : '',
                trailing: Icon(
                  Icons.calendar_today_outlined,
                  size: 20,
                  color: AppColor.inkTertiary,
                ),
              ),
              const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
              _StaticFloatingLabel(
                label: '성별',
                floated: widget.data.sex != null,
                child: Row(
                  children: [
                    Expanded(child: _SexChip(label: '여성', value: 'F',
                      selected: widget.data.sex == 'F',
                      onTap: () { widget.data.sex = 'F'; widget.onChange(); setState(() {}); })),
                    const SizedBox(width: AppSpace.md),
                    Expanded(child: _SexChip(label: '남성', value: 'M',
                      selected: widget.data.sex == 'M',
                      onTap: () { widget.data.sex = 'M'; widget.onChange(); setState(() {}); })),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 3: 이메일 가입자 — 이메일 + 인증 + 비밀번호
// (OAuth 모드면 PageView 에서 건너뜀)
// ═══════════════════════════════════════════
class _StepEmail extends StatefulWidget {
  final SignupData data;
  final VoidCallback onChange;
  final VoidCallback onProceed; // 임시: 인증코드 받기 누르면 바로 다음 step
  final Future<String> Function(String email) onSendCode;
  final Future<String> Function(String email, String code) onVerifyCode;
  const _StepEmail({
    required this.data,
    required this.onChange,
    required this.onProceed,
    required this.onSendCode,
    required this.onVerifyCode,
  });

  @override
  State<_StepEmail> createState() => _StepEmailState();
}

class _StepEmailState extends State<_StepEmail> with AutomaticKeepAliveClientMixin {
  late final TextEditingController _email = TextEditingController(text: widget.data.email ?? '');
  late final TextEditingController _password = TextEditingController(text: widget.data.password ?? '');
  final TextEditingController _code = TextEditingController();

  bool _codeSent = false;
  bool _sending = false;
  bool _verifying = false;
  String? _emailError;
  String? _codeMessage;

  @override
  bool get wantKeepAlive => true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _code.dispose();
    super.dispose();
  }

  bool _isValidEmail(String v) {
    final re = RegExp(r'^[\w\.\-]+@[\w\-]+\.[\w\.\-]+$');
    return re.hasMatch(v);
  }

  Future<void> _sendCode() async {
    // 임시 — 인증 우회 모드: 이메일 형식만 맞으면 바로 다음 step
    // TODO: 복원 시 백엔드 호출 + 인증코드 입력 화면으로 전환
    final email = widget.data.email ?? '';
    if (!_isValidEmail(email)) {
      setState(() => _emailError = '올바른 이메일을 입력해주세요');
      return;
    }
    widget.data.emailVerified = true;
    widget.onChange();
    widget.onProceed();
  }

  Future<void> _verifyCode() async {
    final email = widget.data.email ?? '';
    final code = _code.text.trim();
    if (code.length < 4) {
      setState(() => _codeMessage = '인증코드를 정확히 입력해주세요');
      return;
    }
    setState(() {
      _verifying = true;
      _codeMessage = null;
    });
    try {
      final msg = await widget.onVerifyCode(email, code);
      if (!mounted) return;
      setState(() {
        widget.data.emailVerified = true;
        _codeMessage = msg;
      });
      widget.onChange();
    } on AuthFailure catch (e) {
      if (!mounted) return;
      setState(() => _codeMessage = e.message);
    } catch (_) {
      if (!mounted) return;
      setState(() => _codeMessage = '인증에 실패했어요');
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '계정을 만들어요',
            subtitle: '이메일과 비밀번호로 로그인할 수 있어요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),

          // 콘텐츠 — 헤더 후 stagger 등장
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 130),
            children: [
              _FloatingField(
                label: '이메일',
                controller: _email,
                hasValue: (widget.data.email?.isNotEmpty ?? false),
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                onChanged: (v) {
                  widget.data.email = v.trim();
                  if (_emailError != null) {
                    setState(() => _emailError = null);
                  } else {
                    setState(() {});
                  }
                },
              ),
              if (_emailError != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.sm),
                  child: Text(_emailError!,
                    style: AppText.caption.copyWith(color: AppColor.danger)),
                ),
              if (!widget.data.emailVerified)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.md),
                  child: SizedBox(
                    width: double.infinity,
                    child: _CodeActionButton(
                      label: _codeSent ? '인증코드 재전송' : '인증코드 받기',
                      loading: _sending,
                      enabled: !_sending && _isValidEmail(widget.data.email ?? ''),
                      onPressed: _sendCode,
                    ),
                  ),
                ),
            ],
          ),

          if (_codeSent && !widget.data.emailVerified) ...[
            const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
            _FloatingField(
              label: '인증코드',
              controller: _code,
              hasValue: _code.text.isNotEmpty,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: AppSpace.md),
            SizedBox(
              width: double.infinity,
              child: _CodeActionButton(
                label: '인증 확인',
                loading: _verifying,
                enabled: !_verifying && _code.text.trim().length >= 4,
                onPressed: _verifyCode,
              ),
            ),
          ],

          if (_codeMessage != null) ...[
            const SizedBox(height: AppSpace.sm),
            Text(_codeMessage!,
              style: AppText.caption.copyWith(
                color: widget.data.emailVerified ? AppColor.brandDeep : AppColor.inkSecondary,
              )),
          ],

          if (widget.data.emailVerified) ...[
            const SizedBox(height: AppSpace.sm),
            Row(
              children: [
                Icon(Icons.check_circle, color: AppColor.brandDeep, size: 16),
                const SizedBox(width: 6),
                Text('이메일 인증 완료',
                  style: AppText.caption.copyWith(
                    color: AppColor.brandDeep, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
            _FloatingField(
              label: '비밀번호 (8자 이상)',
              controller: _password,
              hasValue: (widget.data.password?.isNotEmpty ?? false),
              obscureText: true,
              onChanged: (v) {
                widget.data.password = v;
                widget.onChange();
                setState(() {});
              },
            ),
          ],
        ],
      ),
    );
  }
}

/// 동적 floating label 필드 (TextField 아닌 탭 영역용 — 생년월일 등)
/// 값이 없으면 라벨이 큰 글자로 입력 영역 안, 값 있으면 위로 작게 + brand 색
class _DynamicLabelField extends StatelessWidget {
  final String label;
  final String? value;       // null = 빈 상태
  final Widget? trailing;
  final VoidCallback onTap;
  const _DynamicLabelField({
    required this.label,
    required this.value,
    required this.onTap,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final hasValue = value != null && value!.isNotEmpty;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        // 높이는 라벨(위) + 값(아래) 공간 위해 고정 — TextField 와 호흡 맞춤
        height: 60,
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColor.border, width: 1)),
        ),
        child: Stack(
          children: [
            // 라벨 — 빈 상태 가운데, 값 있으면 위로 슬라이드 + 축소
            AnimatedPositioned(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOutCubic,
              left: 0,
              top: hasValue ? 4 : 22,
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOutCubic,
                style: hasValue
                    ? AppText.body.copyWith(
                        color: AppColor.brandDeep,
                        fontWeight: FontWeight.w400,
                        letterSpacing: -0.2,
                      )
                    : AppText.bodyLg.copyWith(
                        color: AppColor.inkTertiary,
                        fontWeight: FontWeight.w500,
                      ),
                child: Text(label),
              ),
            ),
            // 값 + trailing
            if (hasValue)
              Positioned(
                left: 0, right: 0, bottom: 8,
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        value!,
                        style: AppText.bodyLg.copyWith(color: AppColor.ink),
                      ),
                    ),
                    if (trailing != null) trailing!,
                  ],
                ),
              )
            else if (trailing != null)
              Positioned(
                right: 0, top: 22,
                child: trailing!,
              ),
          ],
        ),
      ),
    );
  }
}

/// 인증 발송 / 코드 확인 버튼 — 우측 작은 액션 버튼 (언더라인 입력 옆)
/// ═══════════════════════════════════════════
/// 페이지 진입 stagger 애니메이션 시스템 (토스/필라이즈 표준)
///
/// 사용:
///   _StaggeredColumn(
///     children: [
///       Text('타이틀'),
///       Text('서브'),
///       _SomeField(...),
///       _AnotherField(...),
///     ],
///   )
///
/// 자동 동작:
///   - 진입 후 80ms 부터 시작
///   - 자식마다 120ms 간격으로 순차 fade + slide 18px↑
///   - duration 600ms easeOutCubic
/// ═══════════════════════════════════════════
class _StaggeredColumn extends StatefulWidget {
  final List<Widget> children;
  final CrossAxisAlignment crossAxisAlignment;
  final Duration initialDelay;
  final Duration stagger;
  final Duration itemDuration;
  final double slideOffset;
  const _StaggeredColumn({
    required this.children,
    this.crossAxisAlignment = CrossAxisAlignment.start,
    this.initialDelay = const Duration(milliseconds: 80),
    this.stagger = const Duration(milliseconds: 120),
    this.itemDuration = const Duration(milliseconds: 600),
    this.slideOffset = 0.18,
  });

  @override
  State<_StaggeredColumn> createState() => _StaggeredColumnState();
}

class _StaggeredColumnState extends State<_StaggeredColumn> {
  late final List<bool> _shown = List.filled(widget.children.length, false);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      for (var i = 0; i < widget.children.length; i++) {
        final delay = widget.initialDelay + widget.stagger * i;
        Future.delayed(delay, () {
          if (mounted) setState(() => _shown[i] = true);
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: widget.crossAxisAlignment,
      children: [
        for (var i = 0; i < widget.children.length; i++)
          AnimatedSlide(
            duration: widget.itemDuration,
            curve: Curves.easeOutCubic,
            offset: _shown[i] ? Offset.zero : Offset(0, widget.slideOffset),
            child: AnimatedOpacity(
              duration: widget.itemDuration,
              curve: Curves.easeOutCubic,
              opacity: _shown[i] ? 1 : 0,
              child: widget.children[i],
            ),
          ),
      ],
    );
  }
}

/// 토스 느낌 동적 헤더 — 진입 시 부드러운 fade + slide
/// 타이틀은 display 톤(좀 더 크게), 서브는 bodyLg
class _StepHeader extends StatefulWidget {
  final String title;
  final String subtitle;
  const _StepHeader({required this.title, required this.subtitle});

  @override
  State<_StepHeader> createState() => _StepHeaderState();
}

class _StepHeaderState extends State<_StepHeader> {
  bool _showTitle = false;
  bool _showSub = false;

  @override
  void initState() {
    super.initState();
    // 첫 프레임은 invisible 상태로 그리고, 살짝 뒤에 visible 트리거
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future.delayed(const Duration(milliseconds: 80), () {
        if (mounted) setState(() => _showTitle = true);
      });
      Future.delayed(const Duration(milliseconds: 520), () {
        if (mounted) setState(() => _showSub = true);
      });
    });
  }

  /// 타이틀용 등장 — 더 멀리서, 더 길게, easeOutQuart 로 끝맺음 강조
  Widget _appearTitle(bool show, Widget child) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 700),
      curve: Curves.easeOutQuart,
      offset: show ? Offset.zero : const Offset(0, 0.32),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 700),
        curve: Curves.easeOutCubic,
        opacity: show ? 1 : 0,
        child: child,
      ),
    );
  }

  /// 서브타이틀용 등장 — 살짝 약하게 (타이틀 강조)
  Widget _appearSub(bool show, Widget child) {
    return AnimatedSlide(
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOutCubic,
      offset: show ? Offset.zero : const Offset(0, 0.24),
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        opacity: show ? 1 : 0,
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _appearTitle(_showTitle, Text(
          widget.title,
          style: AppText.title.copyWith(
            fontSize: (AppText.title.fontSize ?? 22) + 3,
            letterSpacing: -0.5,
            height: 1.3,
            fontWeight: FontWeight.w800,
          ),
        )),
        const SizedBox(height: AppSpace.xs + 4),
        _appearSub(_showSub, Text(
          widget.subtitle,
          style: AppText.bodyLg.copyWith(
            color: AppColor.inkSecondary,
            height: 1.5,
          ),
        )),
      ],
    );
  }
}

/// 인증 발송 / 코드 확인 버튼 — Flat 2.0 + Soft UI 회색 톤
/// 메인 흰 버튼과 동일한 그림자 시스템, 배경은 연한 회색
class _CodeActionButton extends StatelessWidget {
  final String label;
  final bool loading;
  final bool enabled;
  final VoidCallback onPressed;
  const _CodeActionButton({
    required this.label,
    required this.loading,
    required this.enabled,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final on = enabled && !loading;
    return GestureDetector(
      onTap: on ? onPressed : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        height: 52,
        decoration: BoxDecoration(
          color: on ? AppColor.section : const Color(0xFFF7F8FA),
          borderRadius: BorderRadius.circular(AppRadius.sm),
          boxShadow: on
              ? const [
                  BoxShadow(
                    color: Color.fromRGBO(140, 155, 175, 0.20),
                    blurRadius: 16,
                    offset: Offset(0, 5),
                  ),
                ]
              : null,
        ),
        alignment: Alignment.center,
        child: loading
            ? const SizedBox(
                width: 18, height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.black45,
                ),
              )
            : Text(
                label,
                style: AppText.body.copyWith(
                  color: on ? AppColor.ink : AppColor.inkTertiary,
                  fontWeight: FontWeight.w600,
                ),
              ),
      ),
    );
  }
}

class _SexChip extends StatelessWidget {
  final String label;
  final String value;
  final bool selected;
  final VoidCallback onTap;
  const _SexChip({required this.label, required this.value, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        decoration: _cardDeco(selected: selected),
        alignment: Alignment.center,
        child: Text(label, style: AppText.subtitle.copyWith(
          color: selected ? AppColor.brandDeep : AppColor.ink,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
        )),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 3: 목적
// ═══════════════════════════════════════════
class _StepPurpose extends StatelessWidget {
  final SignupData data;
  final VoidCallback onChange;
  const _StepPurpose({required this.data, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '어떤 도움이 필요하세요?',
            subtitle: '중복 선택 가능해요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 90),
            children: _PURPOSES.map((p) {
            final selected = data.purposes.contains(p.$1);
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpace.md),
              child: GestureDetector(
                onTap: () {
                  if (selected) data.purposes.remove(p.$1);
                  else data.purposes.add(p.$1);
                  onChange();
                },
                child: Container(
                  padding: const EdgeInsets.all(AppSpace.cardInside),
                  decoration: _cardDeco(selected: selected),
                  child: Row(
                    children: [
                      Container(
                        width: 48, height: 48,
                        decoration: BoxDecoration(
                          color: selected ? AppColor.brand : AppColor.section,
                          shape: BoxShape.circle,
                        ),
                        alignment: Alignment.center,
                        child: Icon(p.$3,
                          color: selected ? AppColor.ink : AppColor.inkSecondary,
                          size: 24),
                      ),
                      const SizedBox(width: AppSpace.lg),
                      Expanded(child: Text(p.$2, style: AppText.subtitle)),
                      Icon(
                        selected ? Icons.check_circle : Icons.circle_outlined,
                        color: selected ? AppColor.brand : AppColor.inkTertiary,
                      ),
                    ],
                  ),
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

// ═══════════════════════════════════════════
// Step 4: 건강 고민 (9-grid)
// ═══════════════════════════════════════════
class _StepConcerns extends StatelessWidget {
  final SignupData data;
  final VoidCallback onChange;
  const _StepConcerns({required this.data, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '신경 쓰이는 부분이 있어요?',
            subtitle: '관심사를 알면 더 정확한 정보를 드릴 수 있어요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 0),
            children: [GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 3,
            mainAxisSpacing: AppSpace.md,
            crossAxisSpacing: AppSpace.md,
            childAspectRatio: 0.95,
            children: _CONCERNS.map((c) {
              final selected = data.concerns.contains(c.$1);
              return GestureDetector(
                onTap: () {
                  if (selected) data.concerns.remove(c.$1);
                  else data.concerns.add(c.$1);
                  onChange();
                },
                child: Container(
                  padding: const EdgeInsets.all(AppSpace.md),
                  decoration: _cardDeco(selected: selected),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(c.$3,
                        color: selected ? AppColor.brandDeep : AppColor.inkSecondary,
                        size: 28),
                      const SizedBox(height: AppSpace.xs),
                      Text(c.$2,
                        style: AppText.caption.copyWith(
                          color: AppColor.ink,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                        ),
                        textAlign: TextAlign.center,
                        maxLines: 2,
                      ),
                      if (c.$4 != null) ...[
                        const SizedBox(height: AppSpace.xs),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColor.brand,
                            borderRadius: BorderRadius.circular(AppRadius.xs),
                          ),
                          child: Text(c.$4!,
                            style: AppText.micro.copyWith(color: AppColor.ink, fontWeight: FontWeight.w700),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }).toList(),
          )],
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 5: 신체
// ═══════════════════════════════════════════
class _StepBody extends StatefulWidget {
  final SignupData data;
  final VoidCallback onChange;
  const _StepBody({required this.data, required this.onChange});
  @override
  State<_StepBody> createState() => _StepBodyState();
}

class _StepBodyState extends State<_StepBody> with AutomaticKeepAliveClientMixin {
  late final _h = TextEditingController(text: widget.data.heightCm?.toString());
  late final _w = TextEditingController(text: widget.data.weightKg?.toString());
  late final _t = TextEditingController(text: widget.data.targetWeightKg?.toString());

  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '신체 정보를 알려주세요',
            subtitle: 'BMI 와 권장 섭취량 계산에 사용해요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 130),
            children: [
              _FloatingField(
                label: '키',
                controller: _h,
                hasValue: widget.data.heightCm != null,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                suffixText: 'cm',
                onChanged: (v) {
                  widget.data.heightCm = int.tryParse(v);
                  widget.onChange();
                  setState(() {});
                },
              ),
              const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
              _FloatingField(
                label: '몸무게',
                controller: _w,
                hasValue: widget.data.weightKg != null,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                suffixText: 'kg',
                onChanged: (v) {
                  widget.data.weightKg = double.tryParse(v);
                  widget.onChange();
                  setState(() {});
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 6: 건강 연동
// ═══════════════════════════════════════════
class _StepHealthkit extends StatelessWidget {
  final SignupData data;
  final VoidCallback onChange;
  const _StepHealthkit({required this.data, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '걸음수·운동 데이터도\n연동하시겠어요?',
            subtitle: '활동량까지 함께 보면 더 정확해져요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 110),
            children: [
              Container(
                padding: const EdgeInsets.all(AppSpace.cardInside),
                decoration: _softCardDeco(),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, color: AppColor.brandDeep, size: 20),
                    const SizedBox(width: AppSpace.md),
                    Expanded(
                      child: Text(
                        '지금 안해도 괜찮아요.\n설정에서 언제든 바꿀 수 있어요.',
                        style: AppText.body.copyWith(color: AppColor.inkSecondary, height: 1.5),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpace.lg),
              _ToggleRow(
                label: '걸음수',
                value: data.healthSteps,
                onChange: (v) {
                  data.healthSteps = v;
                  data.healthkitConsent = data.healthSteps || data.healthWorkout || data.healthActivity;
                  onChange();
                },
              ),
              const SizedBox(height: AppSpace.md),
              _ToggleRow(
                label: '운동',
                value: data.healthWorkout,
                onChange: (v) {
                  data.healthWorkout = v;
                  data.healthkitConsent = data.healthSteps || data.healthWorkout || data.healthActivity;
                  onChange();
                },
              ),
              const SizedBox(height: AppSpace.md),
              _ToggleRow(
                label: '활동량',
                value: data.healthActivity,
                onChange: (v) {
                  data.healthActivity = v;
                  data.healthkitConsent = data.healthSteps || data.healthWorkout || data.healthActivity;
                  onChange();
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Flat 2.0 + Soft UI 토글 행
/// - 카드: 흰 배경 + soft shadow (회원가입 박스/메인 흰 버튼 통일)
/// - 스위치: 파란색 기본 X, brand 노랑 + 흰 thumb, 테두리 X
class _ToggleRow extends StatelessWidget {
  final String label;
  final bool value;
  final ValueChanged<bool> onChange;
  const _ToggleRow({required this.label, required this.value, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onChange(!value),
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.lg,
          vertical: AppSpace.md + 2,
        ),
        decoration: _softCardDeco(),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: AppText.bodyLg.copyWith(
                  color: AppColor.ink,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            _BrandToggle(value: value, onChange: onChange),
          ],
        ),
      ),
    );
  }
}

/// 커스텀 토글 — 파란색 Material Switch 대체
/// 비활성: 연한 회색 트랙 + 흰 thumb
/// 활성: brand 노랑 트랙 + 흰 thumb
class _BrandToggle extends StatelessWidget {
  final bool value;
  final ValueChanged<bool> onChange;
  const _BrandToggle({required this.value, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onChange(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        width: 48,
        height: 28,
        padding: const EdgeInsets.all(2),
        decoration: BoxDecoration(
          color: value ? AppColor.brand : const Color(0xFFE5E8EB),
          borderRadius: BorderRadius.circular(28),
        ),
        child: AnimatedAlign(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          alignment: value ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            width: 24, height: 24,
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: const [
                BoxShadow(
                  color: Color.fromRGBO(0, 0, 0, 0.10),
                  blurRadius: 4,
                  offset: Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Flat 2.0 + Soft UI 카드 — 흰 배경, 테두리 X, 옅은 그림자
/// 회원가입 박스/메인 흰 버튼과 동일 톤
BoxDecoration _softCardDeco() => BoxDecoration(
      color: AppColor.surface,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      boxShadow: const [
        BoxShadow(
          color: Color.fromRGBO(140, 155, 175, 0.20),
          blurRadius: 16,
          offset: Offset(0, 5),
        ),
      ],
    );

// ═══════════════════════════════════════════
// Step 7: 식사 시간
// ═══════════════════════════════════════════
class _StepMealTimes extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '평소 식사 시간을 알려주세요',
            subtitle: '영양제 복용 알림 시간 추천에 사용해요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _MealRow(label: '아침', defaultTime: '08:00'),
          const SizedBox(height: AppSpace.md),
          _MealRow(label: '점심', defaultTime: '12:30'),
          const SizedBox(height: AppSpace.md),
          _MealRow(label: '저녁', defaultTime: '19:00'),
        ],
      ),
    );
  }
}

class _MealRow extends StatelessWidget {
  final String label;
  final String defaultTime;
  const _MealRow({required this.label, required this.defaultTime});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.lg, vertical: AppSpace.lg),
      decoration: _cardDeco(),
      child: Row(
        children: [
          SizedBox(width: 60, child: Text(label, style: AppText.subtitle)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.lg, vertical: AppSpace.sm),
            decoration: BoxDecoration(
              color: AppColor.brand,
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            child: Text(defaultTime, style: AppText.subtitle.copyWith(color: AppColor.ink)),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 8: 확인
// ═══════════════════════════════════════════
class _StepReview extends StatelessWidget {
  final SignupData data;
  const _StepReview({required this.data});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '입력하신 정보를\n확인해주세요',
            subtitle: '잘못된 부분이 있다면 뒤로 돌아가 수정할 수 있어요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 80),
            children: [
              _ReviewRow(label: '이름', value: data.name ?? '-'),
              _ReviewRow(label: '생년월일',
                value: data.birthDate != null
                  ? '${data.birthDate!.year}.${data.birthDate!.month.toString().padLeft(2, '0')}.${data.birthDate!.day.toString().padLeft(2, '0')}'
                  : '-'),
              _ReviewRow(label: '성별', value: data.sex == 'F' ? '여성' : data.sex == 'M' ? '남성' : '-'),
              _ReviewRow(label: '키', value: data.heightCm != null ? '${data.heightCm} cm' : '-'),
              _ReviewRow(label: '몸무게', value: data.weightKg != null ? '${data.weightKg} kg' : '-'),
              _ReviewRow(
                label: '목적',
                value: data.purposes.isNotEmpty
                    ? _PURPOSES
                        .where((p) => data.purposes.contains(p.$1))
                        .map((p) => p.$2)
                        .join(', ')
                    : '-',
              ),
              _ReviewRow(
                label: '관심사',
                value: data.concerns.isNotEmpty
                    ? _CONCERNS
                        .where((c) => data.concerns.contains(c.$1))
                        .map((c) => c.$2)
                        .join(', ')
                    : '-',
              ),
              _ReviewRow(
                label: '연동 데이터',
                value: () {
                  final items = <String>[];
                  if (data.healthSteps) items.add('걸음수');
                  if (data.healthWorkout) items.add('운동');
                  if (data.healthActivity) items.add('활동량');
                  return items.isEmpty ? '없음' : items.join(', ');
                }(),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  final String label;
  final String value;
  const _ReviewRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.lg),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColor.border)),
      ),
      child: Row(
        children: [
          SizedBox(width: 90, child: Text(label, style: AppText.body.copyWith(color: AppColor.inkSecondary))),
          Expanded(child: Text(value, style: AppText.bodyLg, textAlign: TextAlign.end)),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 9: 가입 완료 안내 (축하 톤 동적 등장)
// ═══════════════════════════════════════════
class _StepDashboard extends StatefulWidget {
  @override
  State<_StepDashboard> createState() => _StepDashboardState();
}

class _StepDashboardState extends State<_StepDashboard>
    with SingleTickerProviderStateMixin {
  bool _showMascot = false;
  bool _showTitle = false;
  bool _showSub = false;
  late AnimationController _bounce;

  @override
  void initState() {
    super.initState();
    // 캐릭터 살짝 통통 튀는 축하 모션
    _bounce = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      // 캐릭터(80ms) → 타이틀(420ms) → 서브(900ms) 순차 등장
      Future.delayed(const Duration(milliseconds: 80), () {
        if (mounted) setState(() => _showMascot = true);
      });
      Future.delayed(const Duration(milliseconds: 420), () {
        if (mounted) setState(() => _showTitle = true);
      });
      Future.delayed(const Duration(milliseconds: 900), () {
        if (mounted) setState(() => _showSub = true);
      });
    });
  }

  @override
  void dispose() {
    _bounce.dispose();
    super.dispose();
  }

  Widget _appear(bool show, Widget child, {Duration dur = const Duration(milliseconds: 600), double slide = 0.22}) {
    return AnimatedSlide(
      duration: dur,
      curve: Curves.easeOutCubic,
      offset: show ? Offset.zero : Offset(0, slide),
      child: AnimatedOpacity(
        duration: dur,
        curve: Curves.easeOutCubic,
        opacity: show ? 1 : 0,
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // 캐릭터 — 페이드인 + 통통 튀는 축하 모션 (continuous)
          AnimatedOpacity(
            duration: const Duration(milliseconds: 600),
            opacity: _showMascot ? 1 : 0,
            child: AnimatedBuilder(
              animation: _bounce,
              builder: (ctx, child) {
                final t = Curves.easeInOut.transform(_bounce.value);
                return Transform.translate(
                  offset: Offset(0, -t * 6),
                  child: child,
                );
              },
              child: Image.asset(
                'assets/mascot/hello-mascot.png',
                height: 200,
                fit: BoxFit.contain,
                errorBuilder: (ctx, err, st) => _mascot(height: 200),
              ),
            ),
          ),
          const SizedBox(height: AppSpace.xl),
          // 타이틀 — bounce-in (톡톡 튀는 등장)
          AnimatedScale(
            duration: const Duration(milliseconds: 700),
            curve: Curves.elasticOut,
            scale: _showTitle ? 1.0 : 0.6,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeOutCubic,
              opacity: _showTitle ? 1 : 0,
              child: Text(
                '가입이 완료되었어요',
                style: AppText.title.copyWith(
                  fontSize: (AppText.title.fontSize ?? 22) + 6,
                  letterSpacing: -0.5,
                  height: 1.3,
                  fontWeight: FontWeight.w800,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
          const SizedBox(height: AppSpace.md),
          // 서브 — 늦게 등장
          _appear(
            _showSub,
            Text(
              '메인 화면에서 로그인해주세요.',
              style: AppText.bodyLg.copyWith(
                color: AppColor.inkSecondary,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════
// Step 10: 약관
// ═══════════════════════════════════════════
class _StepTerms extends StatefulWidget {
  final SignupData data;
  final VoidCallback onChange;
  const _StepTerms({required this.data, required this.onChange});
  @override
  State<_StepTerms> createState() => _StepTermsState();
}

class _StepTermsState extends State<_StepTerms> with AutomaticKeepAliveClientMixin {
  bool _all = false;
  bool _service = false;
  bool _privacy = false;
  bool _medical = false;
  bool _marketing = false;

  @override
  bool get wantKeepAlive => true;

  void _toggleAll(bool v) {
    setState(() {
      _all = v;
      _service = v;
      _privacy = v;
      _medical = v;
      _marketing = v;
      widget.data.termsAgree = v && _required();
      widget.onChange();
    });
  }

  bool _required() => _service && _privacy && _medical;

  void _check(VoidCallback set) {
    setState(() {
      set();
      _all = _service && _privacy && _medical && _marketing;
      widget.data.termsAgree = _required();
      widget.onChange();
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page, AppSpace.pageTop, AppSpace.page, AppSpace.pageBottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _StepHeader(
            title: '약관에 동의해주세요',
            subtitle: '서비스 이용을 위해 필수 항목 동의가 필요해요.',
          ),
          const SizedBox(height: AppSpace.sectionGap + AppSpace.lg),
          _StaggeredColumn(
            initialDelay: const Duration(milliseconds: 900),
            stagger: const Duration(milliseconds: 90),
            children: [
              GestureDetector(
                onTap: () => _toggleAll(!_all),
                child: Container(
                  padding: const EdgeInsets.all(AppSpace.cardInside),
                  decoration: _cardDeco(selected: _all),
                  child: Row(
                    children: [
                      Icon(_all ? Icons.check_circle : Icons.circle_outlined,
                        color: _all ? AppColor.brand : AppColor.inkTertiary, size: 24),
                      const SizedBox(width: AppSpace.md),
                      Expanded(child: Text('전체 동의', style: AppText.subtitle)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: AppSpace.lg),
              _TermRow(label: '서비스 이용 약관', required: true, value: _service,
                onTap: () => _check(() => _service = !_service)),
              _TermRow(label: '개인정보 처리방침', required: true, value: _privacy,
                onTap: () => _check(() => _privacy = !_privacy)),
              _TermRow(label: '민감정보(만성질환·복용약) 수집 동의', required: true, value: _medical,
                onTap: () => _check(() => _medical = !_medical)),
              _TermRow(label: '마케팅 정보 수신 (선택)', required: false, value: _marketing,
                onTap: () => _check(() => _marketing = !_marketing)),
              const SizedBox(height: AppSpace.xl),
              Container(
                padding: const EdgeInsets.all(AppSpace.cardInside),
                decoration: _cardDeco(),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, color: AppColor.review, size: 20),
                    const SizedBox(width: AppSpace.md),
                    Expanded(
                      child: Text(
                        '본 서비스의 정보는 일반적인 건강 관리를 위한 참고 자료이며, 의사·약사·영양사의 전문적 진단이나 처방을 대체하지 않습니다.',
                        style: AppText.caption.copyWith(color: AppColor.ink, height: 1.5),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TermRow extends StatelessWidget {
  final String label;
  final bool required;
  final bool value;
  final VoidCallback onTap;
  const _TermRow({required this.label, required this.required, required this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
        child: Row(
          children: [
            Icon(value ? Icons.check_circle : Icons.circle_outlined,
              color: value ? AppColor.brand : AppColor.inkTertiary, size: 22),
            const SizedBox(width: AppSpace.md),
            Expanded(
              child: RichText(
                text: TextSpan(
                  style: AppText.body.copyWith(color: AppColor.ink),
                  children: [
                    if (required)
                      TextSpan(
                        text: '[필수] ',
                        style: AppText.body.copyWith(
                          color: AppColor.brandDeep,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    TextSpan(text: label),
                  ],
                ),
              ),
            ),
            Icon(Icons.chevron_right, color: AppColor.inkTertiary, size: 20),
          ],
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 공통 헬퍼
// ═══════════════════════════════════════════
class _FieldLabel extends StatelessWidget {
  final String text;
  const _FieldLabel(this.text);
  @override
  Widget build(BuildContext context) =>
      Text(text, style: AppText.caption.copyWith(color: AppColor.inkSecondary, fontWeight: FontWeight.w600));
}

/// 입력 텍스트(실제 값) 스타일
const TextStyle _inputTextStyle = TextStyle(
  fontFamily: 'Pretendard',
  fontSize: 17,
  height: 1.5,
  color: AppColor.ink,
  fontWeight: FontWeight.w500,
  letterSpacing: -0.2,
);

/// _FloatingField 와 동일한 라벨 동작이 필요한 비-TextField 위젯용
/// (chip, button group 등)
class _StaticFloatingLabel extends StatelessWidget {
  final String label;
  final Widget child;
  final bool floated;
  const _StaticFloatingLabel({
    required this.label,
    required this.child,
    required this.floated,
  });

  @override
  Widget build(BuildContext context) {
    const motion = Duration(milliseconds: 200);
    const curve = Curves.easeOutCubic;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 라벨 — _FloatingField 와 같은 톤
        AnimatedDefaultTextStyle(
          duration: motion,
          curve: curve,
          style: floated
              ? const TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 13,
                  height: 1.0,
                  color: AppColor.brandDeep,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                )
              : const TextStyle(
                  fontFamily: 'Pretendard',
                  fontSize: 17,
                  height: 1.0,
                  color: AppColor.inkTertiary,
                  fontWeight: FontWeight.w500,
                  letterSpacing: -0.2,
                ),
          child: Text(label),
        ),
        const SizedBox(height: 14),
        child,
      ],
    );
  }
}

/// 토스 스타일 floating label 직접 구현
/// 빈 상태: 라벨이 입력값과 정확히 같은 baseline 위치에 표시
/// 포커스/값입력: 라벨이 부드럽게 위로 슬라이드 + 작아짐 + brand 색
class _FloatingField extends StatefulWidget {
  final String label;
  final TextEditingController? controller;
  final bool hasValue;
  final bool readOnly;
  final VoidCallback? onTap;
  final String? valueText;
  final Widget? trailing;
  final ValueChanged<String>? onChanged;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final bool autocorrect;
  final String? suffixText;   // 단위 표기 (cm, kg 등)
  const _FloatingField({
    required this.label,
    required this.hasValue,
    this.controller,
    this.readOnly = false,
    this.onTap,
    this.valueText,
    this.trailing,
    this.onChanged,
    this.keyboardType,
    this.inputFormatters,
    this.obscureText = false,
    this.autocorrect = true,
    this.suffixText,
  });

  @override
  State<_FloatingField> createState() => _FloatingFieldState();
}

class _FloatingFieldState extends State<_FloatingField> {
  final FocusNode _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    _focus.addListener(() => setState(() {}));
    widget.controller?.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  bool get _hasText => (widget.controller?.text.isNotEmpty ?? false);
  bool get _floated => _focus.hasFocus || widget.hasValue || _hasText;

  @override
  Widget build(BuildContext context) {
    const motion = Duration(milliseconds: 200);
    const curve = Curves.easeOutCubic;
    const fieldHeight = 56.0;        // 전체 입력 영역 높이
    const baselineFromTop = 30.0;    // 입력 텍스트 baseline 위치 (= 빈 상태 라벨 위치)
    const floatedTop = 0.0;          // 떠올랐을 때 라벨 위치

    // 값 있거나 포커스 시 brand 색 밑줄
    final isHighlighted = _focus.hasFocus || widget.hasValue || _hasText;
    final inputColor = isHighlighted ? AppColor.brand : AppColor.border;
    final inputWidth = isHighlighted ? 2.5 : 1.0;

    return GestureDetector(
      onTap: widget.readOnly
          ? widget.onTap
          : () => _focus.requestFocus(),
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        height: fieldHeight,
        child: Stack(
          children: [
            // 밑줄
            Positioned(
              left: 0, right: 0, bottom: 0,
              child: Container(
                height: inputWidth,
                color: inputColor,
              ),
            ),
            // 입력 영역 — 라벨보다 먼저 그려서 라벨이 위에 오게
            Positioned(
              left: 0, right: 0, top: 22, bottom: 6,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: widget.readOnly
                        ? Text(
                            widget.valueText ?? '',
                            style: _inputTextStyle,
                          )
                        : TextField(
                            controller: widget.controller,
                            focusNode: _focus,
                            style: _inputTextStyle,
                            onChanged: widget.onChanged,
                            keyboardType: widget.keyboardType,
                            inputFormatters: widget.inputFormatters,
                            obscureText: widget.obscureText,
                            autocorrect: widget.autocorrect,
                            textAlignVertical: TextAlignVertical.center,
                            decoration: InputDecoration(
                              isDense: true,
                              isCollapsed: true,
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              contentPadding: EdgeInsets.zero,
                              suffixText: widget.suffixText,
                              suffixStyle: AppText.body.copyWith(
                                color: AppColor.inkSecondary,
                              ),
                            ),
                          ),
                  ),
                  if (widget.trailing != null) widget.trailing!,
                ],
              ),
            ),
            // 라벨 — 입력 영역 위에 띄움, 빈 상태에서는 IgnorePointer 로
            //        탭이 입력 필드까지 가게 (라벨이 입력 위 덮어도 OK)
            AnimatedPositioned(
              duration: motion,
              curve: curve,
              left: 0,
              top: _floated ? floatedTop : baselineFromTop,
              child: IgnorePointer(
                child: AnimatedDefaultTextStyle(
                  duration: motion,
                  curve: curve,
                  style: _floated
                      ? TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 13,
                          height: 1.0,
                          color: AppColor.brandDeep,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.2,
                        )
                      : const TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 17,
                          height: 1.0,
                          color: AppColor.inkTertiary,
                          fontWeight: FontWeight.w500,
                          letterSpacing: -0.2,
                        ),
                  child: Text(widget.label),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 라벨이 입력 위에 상시 표시되는 필드 (필라이즈/토스 일부 패턴)
/// 라벨 ↔ 입력 사이 여백을 직접 제어 (Material InputDecoration 한계 회피)
/// isActive: 입력값 있거나 포커스 시 라벨 색을 brand 로 (시각 피드백)
class _StackedField extends StatelessWidget {
  final String label;
  final Widget child;
  final bool isActive;
  const _StackedField({
    required this.label,
    required this.child,
    this.isActive = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AnimatedDefaultTextStyle(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 13,
            height: 1.2,
            color: isActive ? AppColor.brandDeep : AppColor.inkTertiary,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
            letterSpacing: -0.2,
          ),
          child: Text(label),
        ),
        const SizedBox(height: 10),  // ← 라벨 ↔ 입력 사이 여백
        child,
      ],
    );
  }
}

/// 토스 스타일 동적 floating label 입력 위젯
/// - 빈 상태: 라벨이 입력 위치(=텍스트 들어가는 자리)에 큰 글자로
/// - 포커스/입력 시: 라벨이 부드럽게 위로 슬라이드 + 작아짐 + brand 색
class FloatingLabelField extends StatefulWidget {
  final TextEditingController controller;
  final FocusNode? focusNode;
  final String label;
  final bool readOnly;
  final VoidCallback? onTap;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final bool autocorrect;
  final bool enabled;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final Widget? trailing;

  const FloatingLabelField({
    super.key,
    required this.controller,
    required this.label,
    this.focusNode,
    this.readOnly = false,
    this.onTap,
    this.keyboardType,
    this.inputFormatters,
    this.obscureText = false,
    this.autocorrect = true,
    this.enabled = true,
    this.textInputAction,
    this.onChanged,
    this.onSubmitted,
    this.trailing,
  });

  @override
  State<FloatingLabelField> createState() => _FloatingLabelFieldState();
}

class _FloatingLabelFieldState extends State<FloatingLabelField> {
  late FocusNode _focusNode;
  bool _ownsFocusNode = false;

  @override
  void initState() {
    super.initState();
    _focusNode = widget.focusNode ?? FocusNode();
    _ownsFocusNode = widget.focusNode == null;
    _focusNode.addListener(_onFocusChange);
    widget.controller.addListener(_onTextChange);
  }

  @override
  void dispose() {
    _focusNode.removeListener(_onFocusChange);
    widget.controller.removeListener(_onTextChange);
    if (_ownsFocusNode) _focusNode.dispose();
    super.dispose();
  }

  void _onFocusChange() => setState(() {});
  void _onTextChange() => setState(() {});

  bool get _floated => _focusNode.hasFocus || widget.controller.text.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    const motion = Duration(milliseconds: 220);
    const curve = Curves.easeOutCubic;

    final field = TextField(
      controller: widget.controller,
      focusNode: _focusNode,
      readOnly: widget.readOnly,
      onTap: widget.onTap,
      keyboardType: widget.keyboardType,
      inputFormatters: widget.inputFormatters,
      obscureText: widget.obscureText,
      autocorrect: widget.autocorrect,
      enabled: widget.enabled,
      textInputAction: widget.textInputAction,
      onChanged: widget.onChanged,
      onSubmitted: widget.onSubmitted,
      style: _inputTextStyle,
      decoration: const InputDecoration(
        isDense: true,
        isCollapsed: true,
        border: InputBorder.none,
        enabledBorder: InputBorder.none,
        focusedBorder: InputBorder.none,
      ),
    );

    return GestureDetector(
      onTap: widget.readOnly
          ? widget.onTap
          : () => _focusNode.requestFocus(),
      behavior: HitTestBehavior.opaque,
      child: Container(
        // 전체 높이 = 라벨떠올랐을자리(20) + 입력영역(24) + 여백(8) + 밑줄(2) = ~54
        height: 60,
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: _focusNode.hasFocus ? AppColor.brand : AppColor.border,
              width: _focusNode.hasFocus ? 2.5 : 1,
            ),
          ),
        ),
        child: Stack(
          children: [
            // 라벨 — Animated 로 부드럽게 위치/크기/색 transition
            AnimatedPositioned(
              duration: motion,
              curve: curve,
              left: 0,
              top: _floated ? 0 : 22,   // 빈 상태: 입력 위치, 포커스시: 위
              child: AnimatedDefaultTextStyle(
                duration: motion,
                curve: curve,
                style: _floated
                    ? TextStyle(
                        fontFamily: 'Pretendard',
                        fontSize: 13,
                        height: 1.0,
                        color: AppColor.brandDeep,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.2,
                      )
                    : const TextStyle(
                        fontFamily: 'Pretendard',
                        fontSize: 17,
                        height: 1.0,
                        color: AppColor.inkTertiary,
                        fontWeight: FontWeight.w500,
                        letterSpacing: -0.2,
                      ),
                child: Text(widget.label),
              ),
            ),
            // 입력 영역 + trailing
            Positioned(
              left: 0, right: 0, bottom: 12, top: 22,
              child: Row(
                children: [
                  Expanded(child: Align(
                    alignment: Alignment.centerLeft,
                    child: field,
                  )),
                  if (widget.trailing != null) widget.trailing!,
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Toss / Pillyze 풍 동적 언더라인 입력
// - 빈 상태: 라벨이 필드 안 큰 글자 (bodyLg, inkTertiary)
// - 포커스/값 있음: 라벨이 위로 부드럽게 슬라이드 + 작아짐 + brandDeep 색
// - 밑줄: idle 1px border → focus 2.5px brand
// - 텍스트 transition 은 Flutter 가 floatingLabelBehavior 로 자동
InputDecoration _inputDeco({
  String? label,
  String? hint,
  String? suffixText,
  Widget? suffix,
}) => InputDecoration(
      // label 만 사용 (hint 안 씀 — label 이 그 역할)
      labelText: label,
      // 빈 상태 라벨 = placeholder 역할
      // height 를 입력 텍스트(_inputTextStyle)와 동일하게 두면 위치 일치
      labelStyle: const TextStyle(
        fontFamily: 'Pretendard',
        fontSize: 17,
        height: 1.5,
        color: AppColor.inkTertiary,
        fontWeight: FontWeight.w500,
        letterSpacing: -0.2,
      ),
      // 떠오른 후 — Material 0.75 배 감안. 지정 18 → 표시 ~13.5
      floatingLabelStyle: const TextStyle(
        fontFamily: 'Pretendard',
        fontSize: 18,
        height: 1.0,
        color: AppColor.brandDeep,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
      ),
      floatingLabelBehavior: FloatingLabelBehavior.auto,
      alignLabelWithHint: false,
      filled: false,
      isCollapsed: false,
      isDense: false,
      // top 32 = 떠오른 라벨과 입력값 사이 여백 확보 (라벨~14 + 여백 ~10)
      // bottom 14 = 입력값 ↔ 밑줄 여백
      contentPadding: const EdgeInsets.fromLTRB(0, 32, 0, 14),
      suffixText: suffixText,
      suffixStyle: AppText.body.copyWith(color: AppColor.inkSecondary),
      suffix: suffix,
      // 밑줄
      border: UnderlineInputBorder(
        borderSide: BorderSide(color: AppColor.border, width: 1),
      ),
      enabledBorder: UnderlineInputBorder(
        borderSide: BorderSide(color: AppColor.border, width: 1),
      ),
      focusedBorder: UnderlineInputBorder(
        borderSide: BorderSide(color: AppColor.brand, width: 2.5),
      ),
      errorBorder: UnderlineInputBorder(
        borderSide: BorderSide(color: AppColor.danger, width: 2),
      ),
      focusedErrorBorder: UnderlineInputBorder(
        borderSide: BorderSide(color: AppColor.danger, width: 2.5),
      ),
    );
