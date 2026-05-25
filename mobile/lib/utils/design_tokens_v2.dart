import 'package:flutter/material.dart';

/// Source-branch UIUX tokens adapted for the backend-connected app.
///
/// The original UIUX branch uses these names widely. This trimmed copy keeps
/// reusable visual values available without importing the source router, auth
/// services, mock repositories, or replacement native projects.
final class AppColor {
  AppColor._();

  /// Base app background.
  static const Color bg = Color(0xFFFFFFFF);

  /// Card and sheet surface.
  static const Color surface = Color(0xFFFFFFFF);

  /// Subtle recessed surface.
  static const Color sunken = Color(0xFFF7F8FA);

  /// Section divider background.
  static const Color section = Color(0xFFF2F4F6);

  /// Hairline border.
  static const Color border = Color(0xFFEEF1F6);

  /// Stronger border.
  static const Color borderStrong = Color(0xFFDEE2E8);

  /// Primary text.
  static const Color ink = Color(0xFF191F28);

  /// Secondary text.
  static const Color inkSecondary = Color(0xFF4E5968);

  /// Tertiary text.
  static const Color inkTertiary = Color(0xFF8B95A1);

  /// Disabled text.
  static const Color inkDisabled = Color(0xFFC5C8CE);

  /// Lemon Aid primary CTA.
  static const Color brand = Color(0xFFFFC700);

  /// Pressed CTA color.
  static const Color brandPressed = Color(0xFFE5B300);

  /// Deep text color for yellow surfaces.
  static const Color brandDeep = Color(0xFFC99100);

  /// Soft brand chip background.
  static const Color brandSoft = Color(0xFFFFF6CC);

  /// Success state.
  static const Color success = Color(0xFF22B07D);

  /// Soft success background.
  static const Color successSoft = Color(0xFFE6F5EE);

  /// Warning state.
  static const Color warning = Color(0xFFFF9500);

  /// Danger state.
  static const Color danger = Color(0xFFEF4452);

  /// Review-needed state.
  static const Color review = Color(0xFFB86A00);

  /// Data/trust accent.
  static const Color info = Color(0xFF2CA8E0);
}

/// Source-branch spacing scale normalized for current screens.
final class AppSpace {
  AppSpace._();

  /// Extra small gap.
  static const double xs = 4;

  /// Small gap.
  static const double sm = 8;

  /// Medium gap.
  static const double md = 12;

  /// Large gap.
  static const double lg = 16;

  /// Extra large gap.
  static const double xl = 24;

  /// Page horizontal padding.
  static const double page = 24;

  /// Card internal padding.
  static const double cardInside = 20;
}

/// Source-branch radius scale.
final class AppRadius {
  AppRadius._();

  /// Small controls.
  static const double sm = 12;

  /// Standard controls.
  static const double md = 16;

  /// Cards.
  static const double lg = 20;

  /// Large cards and sheets.
  static const double xl = 24;

  /// Fully rounded controls.
  static const double full = 999;
}

/// Text styles with source-branch weights and zero letter spacing.
final class AppText {
  AppText._();

  static const String _family = 'Pretendard';

  /// Display text.
  static const TextStyle display = TextStyle(
    fontFamily: _family,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
    height: 1.2,
    color: AppColor.ink,
  );

  /// Section title.
  static const TextStyle title = TextStyle(
    fontFamily: _family,
    fontSize: 24,
    fontWeight: FontWeight.w700,
    letterSpacing: 0,
    height: 1.3,
    color: AppColor.ink,
  );

  /// Body text.
  static const TextStyle body = TextStyle(
    fontFamily: _family,
    fontSize: 15,
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    height: 1.5,
    color: AppColor.ink,
  );

  /// Caption text.
  static const TextStyle caption = TextStyle(
    fontFamily: _family,
    fontSize: 13,
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    height: 1.4,
    color: AppColor.inkSecondary,
  );
}
