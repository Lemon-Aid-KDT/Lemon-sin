// utils/brand_palette.dart — Lemon Aid 4색 브랜드 테마 팔레트
//
// SoT v1.1 §9.5: 사용자가 설정에서 선택할 수 있는 4색 브랜드 테마 정의.
// 기본값: yellow (#FFC700, design_tokens_v2 AppColor.brand 와 일치).
// brandThemeNotifier → AppColors.brand 동적 반영 구상.

import 'package:flutter/material.dart';

/// 사용자가 선택 가능한 브랜드 테마 색상 4종.
enum BrandTheme {
  /// 기본 레몬 옐로우 — design_tokens_v2 AppColor.brand 와 동일.
  yellow,

  /// 퍼플
  purple,

  /// 그린
  green,

  /// 블루
  blue,
}

/// 각 BrandTheme 에 대응하는 색상 값.
extension BrandThemeColor on BrandTheme {
  /// 메인 브랜드 색상.
  Color get color {
    switch (this) {
      case BrandTheme.yellow:
        return const Color(0xFFFFC700);
      case BrandTheme.purple:
        return const Color(0xFF8B7EE8);
      case BrandTheme.green:
        return const Color(0xFF5FBF7A);
      case BrandTheme.blue:
        return const Color(0xFF4D9CFF);
    }
  }

  /// 눌림 상태 (약간 어두운 톤).
  Color get pressedColor {
    switch (this) {
      case BrandTheme.yellow:
        return const Color(0xFFE5B300);
      case BrandTheme.purple:
        return const Color(0xFF7B6ED4);
      case BrandTheme.green:
        return const Color(0xFF4FA869);
      case BrandTheme.blue:
        return const Color(0xFF3A88EE);
    }
  }

  /// 옅은 소프트 배경 (chip, badge 등).
  Color get softColor {
    switch (this) {
      case BrandTheme.yellow:
        return const Color(0xFFFFF6CC);
      case BrandTheme.purple:
        return const Color(0xFFF0EEFF);
      case BrandTheme.green:
        return const Color(0xFFE8F7ED);
      case BrandTheme.blue:
        return const Color(0xFFE3F0FF);
    }
  }

  /// 화면에 표시할 한국어 레이블.
  String get label {
    switch (this) {
      case BrandTheme.yellow:
        return '옐로우';
      case BrandTheme.purple:
        return '퍼플';
      case BrandTheme.green:
        return '그린';
      case BrandTheme.blue:
        return '블루';
    }
  }
}
