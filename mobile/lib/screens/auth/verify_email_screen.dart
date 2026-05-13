// screens/auth/verify_email_screen.dart — S-04 Verify Email
//
// 디자인 시스템 v2.1 (UX_DIARY §14.10) — Flat 2.0 + 액센트.
// 명세: §14.7 S-05 Verify Email (이메일 6자리 OTP)
// 데이터: PG.md §11.1 EmailVerification (token / expires_at / verified_at)

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/design_tokens_v2.dart';
import '../../widgets/common/app_modals.dart';

class VerifyEmailScreen extends StatefulWidget {
  const VerifyEmailScreen({super.key});

  @override
  State<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen> {
  static const int _codeLength = 6;
  static const Duration _expireAfter = Duration(minutes: 5);
  static const Duration _resendCooldown = Duration(seconds: 10);

  late List<TextEditingController> _ctrls;
  late List<FocusNode> _focs;

  // mock — 실제는 Signup 에서 라우트 파라미터로 전달
  String _email = 'example@email.com';

  Duration _remaining = _expireAfter;
  Timer? _timer;

  bool _verifying = false;
  bool _expired = false;
  String? _errorMsg;

  int _resendCount = 0; // 24h 누적 (PG: max 5)
  Duration _resendCooldownLeft = Duration.zero;
  Timer? _cooldownTimer;

  // shake animation
  final ValueNotifier<int> _shakeKey = ValueNotifier(0);

  @override
  void initState() {
    super.initState();
    _ctrls = List.generate(_codeLength, (_) => TextEditingController());
    _focs = List.generate(_codeLength, (_) => FocusNode());
    _startTimer();
    _startCooldown(); // 진입 직후 10초 비활성
  }

  @override
  void dispose() {
    _timer?.cancel();
    _cooldownTimer?.cancel();
    for (final c in _ctrls) c.dispose();
    for (final f in _focs) f.dispose();
    super.dispose();
  }

  void _startTimer() {
    _remaining = _expireAfter;
    _expired = false;
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      setState(() {
        _remaining -= const Duration(seconds: 1);
        if (_remaining <= Duration.zero) {
          _remaining = Duration.zero;
          _expired = true;
          _timer?.cancel();
        }
      });
    });
  }

  void _startCooldown() {
    _resendCooldownLeft = _resendCooldown;
    _cooldownTimer?.cancel();
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      setState(() {
        _resendCooldownLeft -= const Duration(seconds: 1);
        if (_resendCooldownLeft <= Duration.zero) {
          _resendCooldownLeft = Duration.zero;
          _cooldownTimer?.cancel();
        }
      });
    });
  }

  String _formatRemaining() {
    final m = _remaining.inMinutes.toString().padLeft(2, '0');
    final s = (_remaining.inSeconds % 60).toString().padLeft(2, '0');
    return '$m : $s';
  }

  String get _code => _ctrls.map((c) => c.text).join();

  void _onChanged(int i, String v) {
    setState(() => _errorMsg = null);
    // 한 칸 이상 붙여넣기 처리 (autofill / paste)
    if (v.length > 1) {
      final clean = v.replaceAll(RegExp(r'\D'), '');
      for (int k = 0; k < _codeLength; k++) {
        _ctrls[k].text = k < clean.length ? clean[k] : '';
      }
      final lastIdx = (clean.length).clamp(0, _codeLength - 1);
      FocusScope.of(context).requestFocus(_focs[lastIdx]);
      if (_code.length == _codeLength) _submit();
      return;
    }
    if (v.isNotEmpty) {
      // 다음 칸으로
      if (i < _codeLength - 1) {
        FocusScope.of(context).requestFocus(_focs[i + 1]);
      } else {
        FocusScope.of(context).unfocus();
        _submit();
      }
    }
  }

  void _onBackspace(int i) {
    if (_ctrls[i].text.isEmpty && i > 0) {
      FocusScope.of(context).requestFocus(_focs[i - 1]);
      _ctrls[i - 1].text = '';
    }
  }

  Future<void> _submit() async {
    if (_verifying || _expired) return;
    if (_code.length != _codeLength) return;
    setState(() => _verifying = true);
    HapticFeedback.lightImpact();

    // TODO(D2): POST /auth/verify-email {token}
    await Future<void>.delayed(const Duration(milliseconds: 800));

    if (!mounted) return;
    // mock: '000000' 만 통과 (개발용)
    final ok = _code == '000000' || _code.length == 6; // 임시 통과
    if (ok) {
      HapticFeedback.mediumImpact();
      setState(() => _verifying = false);
      context.go(AppRoute.consent);
    } else {
      _onWrongCode();
    }
  }

  void _onWrongCode() {
    setState(() {
      _verifying = false;
      _errorMsg = '코드가 일치하지 않아요. 다시 입력해주세요';
      for (final c in _ctrls) c.clear();
    });
    HapticFeedback.heavyImpact();
    _shakeKey.value++;
    FocusScope.of(context).requestFocus(_focs[0]);
  }

  Future<void> _resend() async {
    if (_resendCooldownLeft > Duration.zero) return;
    if (_resendCount >= 5) {
      _showFallbackSheet();
      return;
    }
    // TODO(D2): POST /auth/resend-verification
    setState(() {
      _resendCount += 1;
      for (final c in _ctrls) c.clear();
      _errorMsg = null;
    });
    _startTimer();
    _startCooldown();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('새 코드를 보냈어요 ($_resendCount/5)'),
        backgroundColor: AppColor.ink,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
    FocusScope.of(context).requestFocus(_focs[0]);
  }

  void _showFallbackSheet() {
    // Claude 시안 04 — BottomSheet 옵션 리스트
    showAppBottomSheet(
      context,
      title: '이메일이 안 와요',
      subtitle: '아래 방법 중 하나를 시도해보세요',
      items: [
        AppBottomSheetItem(
          icon: Icons.refresh_rounded,
          title: '인증 메일 다시 보내기',
          subtitle: '같은 주소로 한 번 더 보낼게요',
          onTap: _resend,
        ),
        AppBottomSheetItem(
          icon: Icons.edit_outlined,
          title: '이메일 주소 수정',
          subtitle: '오타가 있었다면 바꿔주세요',
          onTap: () => context.pop(),
        ),
        AppBottomSheetItem(
          icon: Icons.inbox_outlined,
          title: '스팸함 확인 안내',
          subtitle: '메일이 스팸함에 있을 수 있어요',
        ),
        AppBottomSheetItem(
          icon: Icons.chat_bubble_outline,
          title: '문의하기',
          subtitle: '도움이 더 필요하면 알려주세요',
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final complete = _code.length == _codeLength;
    final timeLow = _remaining.inSeconds < 30;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: AppColor.bg,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: AppColor.bg,
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back, size: 24),
                      color: AppColor.inkTertiary,
                      onPressed: () => context.pop(),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 16, 24, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('이메일 확인',
                        style: AppText.display.copyWith(
                          fontSize: 32, fontWeight: FontWeight.w800, letterSpacing: -1.2,
                        ),
                      ),
                      const SizedBox(height: 12),
                      RichText(
                        text: TextSpan(
                          style: AppText.bodyLg.copyWith(color: AppColor.inkSecondary),
                          children: [
                            TextSpan(
                              text: _email,
                              style: AppText.bodyLg.copyWith(
                                color: AppColor.brand,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const TextSpan(text: ' 으로\n6자리 코드를 보냈어요'),
                          ],
                        ),
                      ),
                      const SizedBox(height: 40),

                      // ─── OTP 6칸 (shake 애니메이션) ───
                      _ShakeAnimator(
                        triggerKey: _shakeKey,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: List.generate(_codeLength, (i) {
                            final filled = _ctrls[i].text.isNotEmpty;
                            final hasError = _errorMsg != null;
                            return Padding(
                              padding: EdgeInsets.symmetric(horizontal: i == 2 ? 8 : 4),
                              child: SizedBox(
                                width: 44, height: 56,
                                child: KeyboardListener(
                                  focusNode: FocusNode(skipTraversal: true),
                                  onKeyEvent: (e) {
                                    if (e is KeyDownEvent &&
                                        e.logicalKey == LogicalKeyboardKey.backspace) {
                                      _onBackspace(i);
                                    }
                                  },
                                  child: TextField(
                                    controller: _ctrls[i],
                                    focusNode: _focs[i],
                                    enabled: !_expired && !_verifying,
                                    keyboardType: TextInputType.number,
                                    textAlign: TextAlign.center,
                                    maxLength: 1,
                                    style: TextStyle(
                                      fontFamily: 'Pretendard',
                                      fontSize: 24, fontWeight: FontWeight.w800,
                                      color: AppColor.ink,
                                    ),
                                    decoration: InputDecoration(
                                      counterText: '',
                                      filled: true,
                                      fillColor: filled ? AppColor.surface : AppColor.sunken,
                                      contentPadding: EdgeInsets.zero,
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                          color: hasError ? AppColor.danger
                                              : filled ? AppColor.brand : AppColor.border,
                                          width: 1.5,
                                        ),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                          color: hasError ? AppColor.danger : AppColor.brand,
                                          width: 1.8,
                                        ),
                                      ),
                                      disabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: const BorderSide(
                                          color: AppColor.border, width: 1.5,
                                        ),
                                      ),
                                    ),
                                    onChanged: (v) => _onChanged(i, v),
                                  ),
                                ),
                              ),
                            );
                          }),
                        ),
                      ),

                      const SizedBox(height: 14),

                      // 타이머 / 에러
                      Center(
                        child: _errorMsg != null
                            ? Text(_errorMsg!,
                                style: AppText.caption.copyWith(
                                  color: AppColor.danger,
                                  fontWeight: FontWeight.w600,
                                ),
                              )
                            : _expired
                                ? Text('시간이 만료됐어요. 코드를 다시 받아주세요',
                                    style: AppText.caption.copyWith(
                                      color: AppColor.danger,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  )
                                : Text(
                                    '${_formatRemaining()} 남음',
                                    style: AppText.caption.copyWith(
                                      color: timeLow ? AppColor.danger : AppColor.inkTertiary,
                                      fontWeight: FontWeight.w600,
                                      fontFeatures: const [FontFeature.tabularFigures()],
                                    ),
                                  ),
                      ),

                      const SizedBox(height: 32),

                      AppPrimaryButton(
                        label: _verifying ? '확인 중...' : '확인',
                        enabled: complete && !_expired && !_verifying,
                        loading: _verifying,
                        accent: true,
                        onPressed: _submit,
                      ),

                      const SizedBox(height: 16),

                      // 재발송 + 이메일 안 와요
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          TextButton(
                            onPressed: _resendCooldownLeft > Duration.zero ? null : _resend,
                            style: TextButton.styleFrom(
                              foregroundColor: AppColor.brand,
                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                            ),
                            child: Text(
                              _resendCooldownLeft > Duration.zero
                                  ? '재발송 (${_resendCooldownLeft.inSeconds}초)'
                                  : '코드 재발송 ${_resendCount > 0 ? "($_resendCount/5)" : ""}',
                              style: AppText.body.copyWith(
                                color: _resendCooldownLeft > Duration.zero
                                    ? AppColor.inkDisabled
                                    : AppColor.brand,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          TextButton(
                            onPressed: _showFallbackSheet,
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                            ),
                            child: Text(
                              '이메일이 안 와요',
                              style: AppText.body.copyWith(
                                color: AppColor.inkSecondary,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Shake animation (코드 틀렸을 때) ───
class _ShakeAnimator extends StatefulWidget {
  final ValueNotifier<int> triggerKey;
  final Widget child;
  const _ShakeAnimator({required this.triggerKey, required this.child});

  @override
  State<_ShakeAnimator> createState() => _ShakeAnimatorState();
}

class _ShakeAnimatorState extends State<_ShakeAnimator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _a;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 360));
    _a = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: -10.0), weight: 1),
      TweenSequenceItem(tween: Tween(begin: -10.0, end: 10.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 10.0, end: -8.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: -8.0, end: 0.0), weight: 1),
    ]).animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
    widget.triggerKey.addListener(_onTrigger);
  }

  void _onTrigger() {
    _c.forward(from: 0);
  }

  @override
  void dispose() {
    widget.triggerKey.removeListener(_onTrigger);
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _a,
      builder: (_, child) => Transform.translate(offset: Offset(_a.value, 0), child: child),
      child: widget.child,
    );
  }
}

// ─── 폴백 항목 ───
// ignore: unused_element
class _FallbackItem extends StatelessWidget {
  final String num;
  final String text;
  const _FallbackItem({required this.num, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 26, height: 26,
            alignment: Alignment.center,
            decoration: const BoxDecoration(
              color: AppColor.brandSoft,
              shape: BoxShape.circle,
            ),
            child: Text(num,
              style: AppText.micro.copyWith(
                color: AppColor.brand,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(text,
              style: AppText.body.copyWith(
                color: AppColor.ink,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
