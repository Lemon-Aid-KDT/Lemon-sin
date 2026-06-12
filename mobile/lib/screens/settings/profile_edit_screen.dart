// screens/settings/profile_edit_screen.dart — 프로필 편집 (figma 957:24)
//
// 가이드 08 (a) step 9. 이름(로컬), 생년, 성별 세그먼트, 키/몸무게 숫자 입력.
// 저장 시 POST /health/profile-snapshots. 이름은 백엔드 공백이라 로컬 저장만.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app_providers.dart';
import '../../core/api/api_error.dart';
import '../../core/storage/local_prefs.dart';
import '../../features/profile/profile_models.dart';
import '../../features/profile/profile_repository.dart';
import '../../utils/design_tokens_v2.dart';

/// 신체 정보 편집 화면.
class ProfileEditScreen extends ConsumerStatefulWidget {
  /// 화면을 생성한다.
  const ProfileEditScreen({super.key});

  @override
  ConsumerState<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends ConsumerState<ProfileEditScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _birthYearController = TextEditingController();
  final TextEditingController _heightController = TextEditingController();
  final TextEditingController _weightController = TextEditingController();

  ProfileSex? _sex;
  bool _loading = true;
  bool _saving = false;
  bool _notReady = false;
  String? _formError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _nameController.dispose();
    _birthYearController.dispose();
    _heightController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    // localPrefs 가 아직 로딩 중일 수 있으므로 future 를 직접 await 한다.
    final LocalPrefs? prefs = await ref.read(localPrefsProvider.future);
    _nameController.text = prefs?.profileDisplayName() ?? '';
    final ProfileRepository repo = ref.read(profileRepositoryProvider);
    try {
      final BodyProfileSnapshot? snapshot = await repo.fetchLatest();
      if (!mounted) return;
      setState(() {
        _notReady = snapshot == null;
        if (snapshot != null) {
          _sex = snapshot.sex;
          if (snapshot.birthYear != null) {
            _birthYearController.text = snapshot.birthYear.toString();
          }
          if (snapshot.heightCm != null) {
            _heightController.text = _trim(snapshot.heightCm!);
          }
          if (snapshot.weightKg != null) {
            _weightController.text = _trim(snapshot.weightKg!);
          }
        }
        _loading = false;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _formError = error.message;
        _loading = false;
      });
    }
  }

  static String _trim(double value) {
    if (value == value.roundToDouble()) return value.toStringAsFixed(0);
    return value.toStringAsFixed(1);
  }

  String? _validate() {
    final String birthRaw = _birthYearController.text.trim();
    if (birthRaw.isNotEmpty) {
      final int? year = int.tryParse(birthRaw);
      if (year == null || year < 1900 || year > 2100) {
        return '출생 연도는 1900~2100 사이로 입력해주세요.';
      }
    }
    final String heightRaw = _heightController.text.trim();
    if (heightRaw.isNotEmpty) {
      final double? height = double.tryParse(heightRaw);
      if (height == null || height < 30 || height > 260) {
        return '키는 30~260cm 사이로 입력해주세요.';
      }
    }
    final String weightRaw = _weightController.text.trim();
    if (weightRaw.isNotEmpty) {
      final double? weight = double.tryParse(weightRaw);
      if (weight == null || weight < 1 || weight > 500) {
        return '몸무게는 1~500kg 사이로 입력해주세요.';
      }
    }
    return null;
  }

  Future<void> _save() async {
    final String? error = _validate();
    if (error != null) {
      setState(() => _formError = error);
      return;
    }
    setState(() {
      _saving = true;
      _formError = null;
    });

    // 이름은 백엔드 공백 — 로컬에만 저장.
    final LocalPrefs? prefs = await ref.read(localPrefsProvider.future);
    await prefs?.setProfileDisplayName(_nameController.text);

    final BodyProfileSnapshot snapshot = BodyProfileSnapshot(
      sex: _sex,
      birthYear: int.tryParse(_birthYearController.text.trim()),
      heightCm: double.tryParse(_heightController.text.trim()),
      weightKg: double.tryParse(_weightController.text.trim()),
    );

    if (!snapshot.hasAnyValue) {
      // 신체 값이 하나도 없으면 서버 저장은 건너뛰고 이름만 반영.
      if (!mounted) return;
      _finishSaved();
      return;
    }

    try {
      await ref.read(profileRepositoryProvider).save(snapshot);
      if (!mounted) return;
      _finishSaved();
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _formError = error.message;
      });
    }
  }

  void _finishSaved() {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(const SnackBar(content: Text('저장했어요')));
    Navigator.of(context).maybePop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      appBar: AppBar(
        backgroundColor: AppColor.section,
        elevation: 0,
        title: const Text(
          '프로필 편집',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            color: AppColor.ink,
          ),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: Column(
                children: <Widget>[
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.all(AppSpace.page),
                      children: <Widget>[
                        if (_notReady)
                          Padding(
                            padding: const EdgeInsets.only(bottom: AppSpace.lg),
                            child: Text(
                              '신체 정보를 입력하면 분석이 더 정확해져요',
                              style: AppText.caption.copyWith(
                                color: AppColor.inkSecondary,
                              ),
                            ),
                          ),
                        AppTextField(
                          controller: _nameController,
                          label: '이름',
                          hint: '닉네임을 입력해주세요',
                        ),
                        const SizedBox(height: AppSpace.lg),
                        AppTextField(
                          controller: _birthYearController,
                          label: '출생 연도',
                          hint: '예: 1985',
                          keyboardType: TextInputType.number,
                        ),
                        const SizedBox(height: AppSpace.lg),
                        _SexSegment(
                          value: _sex,
                          onChanged: (ProfileSex sex) =>
                              setState(() => _sex = sex),
                        ),
                        const SizedBox(height: AppSpace.lg),
                        AppTextField(
                          controller: _heightController,
                          label: '키 (cm)',
                          hint: '예: 172',
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                        ),
                        const SizedBox(height: AppSpace.lg),
                        AppTextField(
                          controller: _weightController,
                          label: '몸무게 (kg)',
                          hint: '예: 68',
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                        ),
                        if (_formError != null) ...<Widget>[
                          const SizedBox(height: AppSpace.md),
                          Text(
                            _formError!,
                            style: AppText.caption.copyWith(
                              color: AppColor.danger,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(AppSpace.page),
                    child: SizedBox(
                      height: 52,
                      child: AppPrimaryButton(
                        label: '저장하기',
                        loading: _saving,
                        onPressed: _saving ? null : _save,
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

/// 성별 세그먼트 (male/female).
class _SexSegment extends StatelessWidget {
  const _SexSegment({required this.value, required this.onChanged});

  final ProfileSex? value;
  final ValueChanged<ProfileSex> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 8),
          child: Text(
            '성별',
            style: AppText.caption.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColor.inkSecondary,
            ),
          ),
        ),
        Row(
          children: ProfileSex.values.map((ProfileSex sex) {
            final bool selected = sex == value;
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: sex == ProfileSex.male ? AppSpace.sm : 0,
                ),
                child: GestureDetector(
                  onTap: () => onChanged(sex),
                  child: Container(
                    height: 48,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: selected ? AppColor.brand : AppColor.surface,
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                      border: Border.all(
                        color: selected ? AppColor.brand : AppColor.border,
                      ),
                    ),
                    child: Text(
                      sex.label,
                      style: TextStyle(
                        fontFamily: 'Pretendard',
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: selected ? Colors.white : AppColor.ink,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
