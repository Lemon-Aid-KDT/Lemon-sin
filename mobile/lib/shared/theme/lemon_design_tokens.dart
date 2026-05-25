import 'package:flutter/material.dart';

/// Reusable design tokens imported from the Lemon Aid UIUX branch.
///
/// The tokens are intentionally small and framework-local so the current
/// backend-connected app can reuse UIUX assets without adopting the source
/// branch's router, auth, or state-management stack.
final class LemonColors {
  LemonColors._();

  /// Primary brand color for capture and call-to-action controls.
  static const Color lemon = Color(0xFFFFCE00);

  /// Deep lemon shade for text on pale yellow surfaces.
  static const Color lemonDeep = Color(0xFFC99100);

  /// Warm app canvas.
  static const Color canvas = Color(0xFFFBF8EC);

  /// Warm card surface.
  static const Color paper = Color(0xFFFFFDF6);

  /// Primary text color.
  static const Color ink = Color(0xFF1B1300);

  /// Secondary text color.
  static const Color inkSoft = Color(0xFF6A6353);

  /// Divider and border color.
  static const Color border = Color(0xFFEBE6D4);

  /// Success and growth accent.
  static const Color leaf = Color(0xFF1F8A4A);

  /// Data and trust accent.
  static const Color sky = Color(0xFF2CA8E0);

  /// Review state color.
  static const Color review = Color(0xFFB86A00);
}

/// Shared spacing constants.
final class LemonSpacing {
  LemonSpacing._();

  /// Compact spacing.
  static const double xs = 4;

  /// Small spacing.
  static const double sm = 8;

  /// Standard spacing.
  static const double md = 12;

  /// Page and card spacing.
  static const double lg = 16;

  /// Section spacing.
  static const double xl = 24;
}

/// Shared radius constants.
final class LemonRadius {
  LemonRadius._();

  /// Small control radius.
  static const double sm = 8;

  /// Standard control radius.
  static const double md = 14;

  /// Card radius.
  static const double lg = 20;

  /// Pill radius.
  static const double pill = 999;
}

/// Imported asset paths used by the current mobile app.
final class LemonAssets {
  LemonAssets._();

  /// Friendly mascot pose for dashboard and onboarding-like surfaces.
  static const String mascotHello = 'assets/mascot/poses/hello.png';

  /// Working mascot pose for OCR analysis surfaces.
  static const String mascotWorking = 'assets/mascot/poses/working.png';

  /// Fresh mascot pose for success states.
  static const String mascotFresh = 'assets/mascot/poses/fresh.png';
}

/// Builds the current app theme using the imported UIUX font and color assets.
///
/// Returns:
///   A Material 3 theme that preserves the existing app architecture.
ThemeData buildLemonAidTheme() {
  final ColorScheme colorScheme = ColorScheme.fromSeed(
    seedColor: LemonColors.leaf,
    primary: LemonColors.leaf,
    secondary: LemonColors.lemonDeep,
    surface: LemonColors.paper,
  );
  return ThemeData(
    colorScheme: colorScheme,
    scaffoldBackgroundColor: LemonColors.canvas,
    fontFamily: 'Pretendard',
    useMaterial3: true,
    appBarTheme: const AppBarTheme(
      backgroundColor: LemonColors.canvas,
      foregroundColor: LemonColors.ink,
      centerTitle: false,
      elevation: 0,
      titleTextStyle: TextStyle(
        color: LemonColors.ink,
        fontFamily: 'AtoZ',
        fontSize: 24,
        fontWeight: FontWeight.w800,
        letterSpacing: 0,
      ),
    ),
    cardTheme: CardThemeData(
      color: LemonColors.paper,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(LemonRadius.lg),
        side: const BorderSide(color: LemonColors.border),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: LemonColors.paper,
      indicatorColor: LemonColors.lemon.withValues(alpha: 0.28),
      labelTextStyle: WidgetStateProperty.resolveWith<TextStyle>((
        Set<WidgetState> states,
      ) {
        return TextStyle(
          color: states.contains(WidgetState.selected)
              ? LemonColors.ink
              : LemonColors.inkSoft,
          fontWeight: states.contains(WidgetState.selected)
              ? FontWeight.w700
              : FontWeight.w500,
          fontSize: 12,
          letterSpacing: 0,
        );
      }),
    ),
  );
}
