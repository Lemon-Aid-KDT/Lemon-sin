// screens/auth/signup_screen.dart — S-03 Signup (Flat 2.0)
//
// 디자인 시스템 v2.0 (UX_DIARY §14.10) 적용. Toss/여기어때 톤.
// AppTextField + AppPrimaryButton (design_tokens_v2.dart) 공용 사용.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../utils/router.dart';
import '../../utils/design_tokens_v2.dart';
import '../../widgets/common/app_modals.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _email = TextEditingController();
  final _pw = TextEditingController();
  final _pw2 = TextEditingController();
  final _name = TextEditingController();

  final _emailFocus = FocusNode();
  final _pwFocus = FocusNode();
  final _pw2Focus = FocusNode();
  final _nameFocus = FocusNode();

  bool _showPw = false;
  bool _showPw2 = false;
  bool _submitting = false;

  String? _emailErr;
  String? _pwErr;
  String? _pw2Err;
  String? _nameErr;

  @override
  void initState() {
    super.initState();
    _email.addListener(_validate);
    _pw.addListener(_validate);
    _pw2.addListener(_validate);
    _name.addListener(_validate);
  }

  @override
  void dispose() {
    _email.dispose(); _pw.dispose(); _pw2.dispose(); _name.dispose();
    _emailFocus.dispose(); _pwFocus.dispose(); _pw2Focus.dispose(); _nameFocus.dispose();
    super.dispose();
  }

  void _validate() {
    setState(() {
      final email = _email.text.trim();
      _emailErr = email.isEmpty ? null
          : !RegExp(r'^[\w\.-]+@[\w\.-]+\.\w+$').hasMatch(email) ? '이메일 형식이 아니에요'
          : null;
      final pw = _pw.text;
      _pwErr = pw.isEmpty ? null
          : (pw.length < 8 || !RegExp(r'[A-Za-z]').hasMatch(pw) || !RegExp(r'\d').hasMatch(pw))
              ? '8자 이상, 영문+숫자를 섞어주세요'
              : null;
      final pw2 = _pw2.text;
      _pw2Err = pw2.isEmpty ? null : pw2 != pw ? '비밀번호가 일치하지 않아요' : null;
      final name = _name.text.trim();
      _nameErr = name.isEmpty ? null
          : (name.length < 2 || name.length > 10) ? '2~10자로 입력해주세요'
          : null;
    });
  }

  bool get _allOk =>
      _email.text.isNotEmpty && _emailErr == null &&
      _pw.text.isNotEmpty && _pwErr == null &&
      _pw2.text.isNotEmpty && _pw2Err == null &&
      _name.text.isNotEmpty && _nameErr == null;

  void _submit() async {
    if (!_allOk || _submitting) return;
    setState(() => _submitting = true);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;
    setState(() => _submitting = false);
    context.push(AppRoute.verifyEmail);
  }

  Future<bool> _confirmDiscard() async {
    final hasInput = _email.text.isNotEmpty || _pw.text.isNotEmpty ||
                     _pw2.text.isNotEmpty || _name.text.isNotEmpty;
    if (!hasInput) return true;
    // Soft Hybrid 다이얼로그 (Claude 시안 02)
    // Primary "계속 작성" (true 반환 시 머무름), Secondary "나가기" (false 반환 = 나감)
    // 그래서 반환 의미를 뒤집어 사용 — 우리 메서드는 "나갈까?" 에 true 면 나감.
    final stay = await showAppDialog(
      context,
      title: '나가시겠어요?',
      body: '작성 중인 정보가 사라져요.\n계속 작성하면 그대로 이어갈 수 있어요.',
      primaryLabel: '계속 작성',
      secondaryLabel: '나가기',
      dangerSecondary: true,
    );
    // stay == true 이면 머무름. false (Secondary 누름) 또는 null (barrier) 이면 나감.
    return stay == false;
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: AppColor.bg,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: PopScope(
        canPop: false,
        onPopInvokedWithResult: (didPop, _) async {
          if (didPop) return;
          if (await _confirmDiscard() && mounted) context.pop();
        },
        child: Scaffold(
          backgroundColor: AppColor.bg,
          body: SafeArea(
            child: Column(
              children: [
                // 상단 바 — 평면 백 + 스텝
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
                  child: Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.arrow_back, size: 24),
                        color: AppColor.inkTertiary,
                        splashRadius: 22,
                        onPressed: () async {
                          if (await _confirmDiscard() && mounted) context.pop();
                        },
                      ),
                      const Spacer(),
                      Text('1 / 1',
                        style: AppText.caption.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColor.inkTertiary,
                        ),
                      ),
                      const SizedBox(width: 12),
                    ],
                  ),
                ),

                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(AppSpace.xl, 32, AppSpace.xl, AppSpace.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('환영해요',
                          style: AppText.display.copyWith(
                            fontSize: 32,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -1.2,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text('이메일로 시작할게요',
                          style: AppText.bodyLg.copyWith(color: AppColor.inkSecondary),
                        ),
                        const SizedBox(height: 64),

                        AppTextField(
                          controller: _email,
                          focusNode: _emailFocus,
                          label: '이메일',
                          hint: 'example@email.com',
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          onSubmitted: (_) => _pwFocus.requestFocus(),
                          error: _emailErr,
                          ok: _email.text.isNotEmpty && _emailErr == null,
                        ),
                        const SizedBox(height: AppSpace.xl),

                        AppTextField(
                          controller: _pw,
                          focusNode: _pwFocus,
                          label: '비밀번호',
                          hint: '8자 이상, 영문+숫자',
                          obscure: !_showPw,
                          textInputAction: TextInputAction.next,
                          onSubmitted: (_) => _pw2Focus.requestFocus(),
                          error: _pwErr,
                          ok: _pw.text.isNotEmpty && _pwErr == null,
                          helper: _pw.text.isEmpty ? '8자 이상, 영문+숫자' : null,
                          suffix: IconButton(
                            icon: Icon(_showPw ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                              color: AppColor.inkTertiary, size: 22),
                            onPressed: () => setState(() => _showPw = !_showPw),
                          ),
                        ),
                        const SizedBox(height: AppSpace.xl),

                        AppTextField(
                          controller: _pw2,
                          focusNode: _pw2Focus,
                          label: '비밀번호 확인',
                          hint: '한 번 더 입력해주세요',
                          obscure: !_showPw2,
                          textInputAction: TextInputAction.next,
                          onSubmitted: (_) => _nameFocus.requestFocus(),
                          error: _pw2Err,
                          ok: _pw2.text.isNotEmpty && _pw2Err == null,
                          suffix: IconButton(
                            icon: Icon(_showPw2 ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                              color: AppColor.inkTertiary, size: 22),
                            onPressed: () => setState(() => _showPw2 = !_showPw2),
                          ),
                        ),
                        const SizedBox(height: AppSpace.xl),

                        AppTextField(
                          controller: _name,
                          focusNode: _nameFocus,
                          label: '닉네임',
                          hint: '2~10자',
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _submit(),
                          error: _nameErr,
                          ok: _name.text.isNotEmpty && _nameErr == null,
                        ),

                        const SizedBox(height: AppSpace.xxl),

                        AppPrimaryButton(
                          label: _submitting ? '가입 중...' : '다음',
                          enabled: _allOk,
                          loading: _submitting,
                          accent: true,
                          onPressed: _submit,
                        ),

                        const SizedBox(height: AppSpace.md),

                        Center(
                          child: Text(
                            '다음 단계에서 이용약관에 동의해야 가입이 완료돼요',
                            style: AppText.micro,
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
