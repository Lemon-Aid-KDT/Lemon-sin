// features/records/records_models.dart — 캘린더(월 단위) 집계 모델
//
// 가이드 07 ②: 월 그리드 + 일자별 기록 점 + 일자 상세 카드.
//   - GET /meals (월 범위) 끼니 + GET /supplements (등록일 기준) 영양제를
//     로컬 타임존 날짜로 버킷팅한다.
//   - 끼니 점 = 그 날 끼니 기록 존재, 영양제 점 = 그 날 영양제 등록 존재.
//   - 일자 상세 카드는 [DayRecords] 의 끼니·영양제 행을 그대로 표시한다.
//
// 연산은 모두 백엔드. 모바일은 표시·날짜 버킷팅·합산만(알고리즘 아님).
//
// 파싱은 home_models 의 HomeMeal / HomeSupplement 를 그대로 재사용한다.

import '../dashboard/home_models.dart';

/// 한 달치 기록 — 일(day) → [DayRecords] 맵.
///
/// 키는 로컬 타임존 기준 `yyyy-MM-dd` 문자열. 빈 날은 맵에 없다.
class MonthRecords {
  /// 한 달치 기록을 생성한다.
  const MonthRecords({required this.monthKey, required this.days});

  /// 이 달의 식별 키 (`yyyy-MM`, 로컬).
  final String monthKey;

  /// 일자 키(`yyyy-MM-dd`) → 그 날의 기록.
  final Map<String, DayRecords> days;

  /// 빈 달.
  static const MonthRecords empty = MonthRecords(
    monthKey: '',
    days: <String, DayRecords>{},
  );

  /// 로컬 [month] 의 `yyyy-MM` 키.
  static String keyForMonth(DateTime month) {
    final String m = month.month.toString().padLeft(2, '0');
    return '${month.year}-$m';
  }

  /// 로컬 [day] 의 `yyyy-MM-dd` 키.
  static String keyForDay(DateTime day) {
    final String m = day.month.toString().padLeft(2, '0');
    final String d = day.day.toString().padLeft(2, '0');
    return '${day.year}-$m-$d';
  }

  /// 특정 [day] 의 기록 (없으면 빈 [DayRecords]).
  DayRecords forDay(DateTime day) {
    return days[keyForDay(day)] ?? DayRecords.empty;
  }

  /// [day] 에 끼니 기록이 있으면 true (식단 점).
  bool hasMeal(DateTime day) => forDay(day).meals.isNotEmpty;

  /// [day] 에 영양제 등록이 있으면 true (영양제 점).
  bool hasSupplement(DateTime day) => forDay(day).supplements.isNotEmpty;

  /// 끼니/영양제를 로컬 날짜로 버킷팅해 한 달치 맵을 만든다.
  ///
  /// Args:
  ///   month: 대상 달 (year·month 만 사용).
  ///   meals: 그 달 범위로 조회한 끼니 (eaten_at 로 버킷팅).
  ///   supplements: 등록 영양제 (user_confirmed_at → created_at 순으로 날짜 결정).
  factory MonthRecords.fromData({
    required DateTime month,
    required List<HomeMeal> meals,
    required List<HomeSupplement> supplements,
  }) {
    final Map<String, List<HomeMeal>> mealBuckets = <String, List<HomeMeal>>{};
    for (final HomeMeal meal in meals) {
      final DateTime? eatenAt = meal.eatenAt;
      if (eatenAt == null) continue;
      final DateTime local = eatenAt.toLocal();
      if (local.year != month.year || local.month != month.month) continue;
      (mealBuckets[keyForDay(local)] ??= <HomeMeal>[]).add(meal);
    }

    final Map<String, List<HomeSupplement>> supplementBuckets =
        <String, List<HomeSupplement>>{};
    for (final HomeSupplement supplement in supplements) {
      final DateTime? registeredAt = supplement.registeredAt;
      if (registeredAt == null) continue;
      final DateTime local = registeredAt.toLocal();
      if (local.year != month.year || local.month != month.month) continue;
      (supplementBuckets[keyForDay(local)] ??= <HomeSupplement>[])
          .add(supplement);
    }

    final Set<String> allKeys = <String>{
      ...mealBuckets.keys,
      ...supplementBuckets.keys,
    };
    final Map<String, DayRecords> days = <String, DayRecords>{};
    for (final String key in allKeys) {
      days[key] = DayRecords(
        meals: mealBuckets[key] ?? const <HomeMeal>[],
        supplements: supplementBuckets[key] ?? const <HomeSupplement>[],
      );
    }
    return MonthRecords(monthKey: keyForMonth(month), days: days);
  }
}

/// 하루치 끼니·영양제 기록.
class DayRecords {
  /// 하루치 기록을 생성한다.
  const DayRecords({required this.meals, required this.supplements});

  /// 그 날 끼니 목록.
  final List<HomeMeal> meals;

  /// 그 날 등록한 영양제 목록.
  final List<HomeSupplement> supplements;

  /// 빈 하루.
  static const DayRecords empty = DayRecords(
    meals: <HomeMeal>[],
    supplements: <HomeSupplement>[],
  );

  /// 기록 건수 (끼니 + 영양제).
  int get totalCount => meals.length + supplements.length;

  /// 그 날 끼니 kcal 합계 (nutrition_summary 누락은 0 처리).
  int get totalKcal {
    double sum = 0;
    for (final HomeMeal meal in meals) {
      sum += meal.nutrition.kcal;
    }
    return sum.round();
  }
}
