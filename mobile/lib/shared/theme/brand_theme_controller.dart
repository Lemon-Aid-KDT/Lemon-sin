// shared/theme/brand_theme_controller.dart — 브랜드 테마 Riverpod 컨트롤러
//
// SoT v1.1 §9.5: 사용자 선택 브랜드 테마를 상태로 관리한다.
// 선택값은 현재 in-memory 보관 (앱 재시작 시 초기화).
// TODO(persist): shared_preferences 를 pubspec.yaml 에 추가한 뒤
//   SharedPreferences.getInstance() 로 'brand_theme' 키를 읽고 저장.
//   의존성 추가 전까지 인메모리 유지 — 기능에는 영향 없음.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../utils/brand_palette.dart';

/// 현재 선택된 [BrandTheme] 을 관리하는 StateNotifier.
///
/// 사용법:
/// ```dart
/// final theme = ref.watch(brandThemeProvider);
/// ref.read(brandThemeProvider.notifier).select(BrandTheme.purple);
/// ```
class BrandThemeNotifier extends StateNotifier<BrandTheme> {
  BrandThemeNotifier() : super(BrandTheme.yellow);

  /// 브랜드 테마를 변경한다.
  ///
  /// TODO(persist): SharedPreferences 저장 로직을 여기에 추가.
  void select(BrandTheme theme) {
    state = theme;
  }
}

/// 앱 전역 브랜드 테마 Provider.
final StateNotifierProvider<BrandThemeNotifier, BrandTheme> brandThemeProvider =
    StateNotifierProvider<BrandThemeNotifier, BrandTheme>(
      (Ref ref) => BrandThemeNotifier(),
    );

/// 현재 선택된 브랜드 색상을 ThemeData 에 적용해 반환한다.
///
/// [brandTheme] 이 null 이면 기본 yellow 를 사용한다.
/// design_tokens_v2 의 정적 AppColor.brand 를 사용하는 화면들은
/// ThemeData.colorScheme.primary 로 점진 마이그레이션할 수 있다.
// TODO(migrate): 각 화면의 AppColor.brand 하드코딩을
//   Theme.of(context).colorScheme.primary 로 교체하면 동적 반영 완성.
ThemeData buildThemedLemonAidTheme(BrandTheme brandTheme) {
  final Color brandColor = brandTheme.color;
  // ink, bg 는 design_tokens_v2 AppColor 와 일치하는 고정값.
  const Color ink = Color(0xFF191F28);
  const Color bg = Color(0xFFFFFFFF);

  final ColorScheme colorScheme = ColorScheme.fromSeed(
    seedColor: brandColor,
    primary: brandColor,
    onPrimary: ink,
    surface: bg,
    onSurface: ink,
  );

  return ThemeData(
    colorScheme: colorScheme,
    scaffoldBackgroundColor: bg,
    fontFamily: 'Pretendard',
    useMaterial3: true,
    appBarTheme: AppBarTheme(
      backgroundColor: bg,
      foregroundColor: ink,
      centerTitle: false,
      elevation: 0,
      titleTextStyle: const TextStyle(
        color: ink,
        fontFamily: 'AtoZ',
        fontSize: 24,
        fontWeight: FontWeight.w800,
        letterSpacing: 0,
      ),
    ),
    cardTheme: CardThemeData(
      color: bg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: Color(0xFFEEF1F6)),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: bg,
      indicatorColor: brandColor.withValues(alpha: 0.28),
      labelTextStyle: WidgetStateProperty.resolveWith<TextStyle>(
        (Set<WidgetState> states) {
          return TextStyle(
            color: states.contains(WidgetState.selected)
                ? ink
                : const Color(0xFF4E5968),
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            fontSize: 12,
            letterSpacing: 0,
          );
        },
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: brandColor,
        foregroundColor: ink,
      ),
    ),
  );
}
