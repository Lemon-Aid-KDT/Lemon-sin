import 'package:flutter/material.dart';

/// LADS v3 color tokens adapted from the UIUX branch.
///
/// Negative letter spacing and unavailable source-branch enforcement comments
/// were removed so the current Flutter app keeps stable, readable text.
final class AppColor {
  AppColor._();

  /// Warm white brand background.
  static const Color lemon50 = Color(0xFFFFFEF2);

  /// Primary container yellow.
  static const Color lemon100 = Color(0xFFFFF8C7);

  /// Shell highlight yellow.
  static const Color lemon200 = Color(0xFFFFEE7A);

  /// Midtone yellow.
  static const Color lemon300 = Color(0xFFFFDE3F);

  /// Primary Lemon Aid yellow.
  static const Color lemon400 = Color(0xFFFFCE00);

  /// Deep yellow.
  static const Color lemon500 = Color(0xFFF0B800);

  /// Text on yellow.
  static const Color lemon600 = Color(0xFFC99100);

  /// Soft leaf background.
  static const Color leaf50 = Color(0xFFECFBEE);

  /// Leaf container.
  static const Color leaf100 = Color(0xFFC9F2D0);

  /// Leaf midtone.
  static const Color leaf300 = Color(0xFF6FCB73);

  /// Leaf success.
  static const Color leaf600 = Color(0xFF1F8A4A);

  /// Data accent.
  static const Color sky500 = Color(0xFF2CA8E0);

  /// Primary warm text.
  static const Color ink900 = Color(0xFF1B1300);

  /// Body warm text.
  static const Color ink700 = Color(0xFF3C3526);

  /// Secondary warm text.
  static const Color ink500 = Color(0xFF6A6353);

  /// Placeholder text.
  static const Color ink300 = Color(0xFFABA590);

  /// Border.
  static const Color ink100 = Color(0xFFEBE6D4);

  /// Card surface.
  static const Color paper = Color(0xFFFFFDF6);

  /// Page surface.
  static const Color canvas = Color(0xFFFBF8EC);

  /// Danger state.
  static const Color danger = Color(0xFFD9342B);

  /// Review state.
  static const Color review = Color(0xFFB86A00);
}

/// Source display/body font names.
final class AppFont {
  AppFont._();

  /// Display family.
  static const String display = 'AtoZ';

  /// Body family.
  static const String body = 'Pretendard';

  /// Tabular fallback family.
  static const String mono = 'SF Mono';
}

/// LADS v3 text styles with non-negative letter spacing.
final class AppText {
  AppText._();

  /// Wordmark display.
  static const TextStyle wordmark = TextStyle(
    fontFamily: AppFont.display,
    fontWeight: FontWeight.w800,
    fontSize: 44,
    letterSpacing: 0,
    color: AppColor.ink900,
  );

  /// Large dashboard number.
  static const TextStyle numXl = TextStyle(
    fontFamily: AppFont.display,
    fontWeight: FontWeight.w800,
    fontSize: 56,
    letterSpacing: 0,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
    color: AppColor.ink900,
  );

  /// Section heading.
  static const TextStyle sectionHead = TextStyle(
    fontFamily: AppFont.display,
    fontWeight: FontWeight.w800,
    fontSize: 26,
    letterSpacing: 0,
    color: AppColor.ink900,
  );

  /// Body copy.
  static const TextStyle body = TextStyle(
    fontFamily: AppFont.body,
    fontWeight: FontWeight.w400,
    fontSize: 17,
    letterSpacing: 0,
    height: 1.5,
    color: AppColor.ink700,
  );

  /// Button copy.
  static const TextStyle button = TextStyle(
    fontFamily: AppFont.body,
    fontWeight: FontWeight.w700,
    fontSize: 17,
    letterSpacing: 0,
    color: AppColor.ink900,
  );
}

/// Shared v3 radius tokens.
final class AppRadius {
  AppRadius._();

  /// Small radius.
  static const double sm = 10;

  /// Medium radius.
  static const double md = 14;

  /// Card radius.
  static const double lg = 20;

  /// Large sheet radius.
  static const double xl = 28;

  /// Pill radius.
  static const double pill = 999;
}

/// Shared v3 spacing tokens.
final class AppSpacing {
  AppSpacing._();

  /// Four-point gap.
  static const double s4 = 4;

  /// Eight-point gap.
  static const double s8 = 8;

  /// Twelve-point gap.
  static const double s12 = 12;

  /// Sixteen-point gap.
  static const double s16 = 16;

  /// Twenty-four-point gap.
  static const double s24 = 24;
}
