import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/features/dashboard/home_models.dart';
import 'package:lemon_aid_mobile/features/records/records_models.dart';

HomeMeal _meal({
  required String id,
  required DateTime eatenAt,
  String name = '현미밥',
  double kcal = 520,
}) {
  return HomeMeal(
    id: id,
    status: 'confirmed',
    mealType: 'lunch',
    eatenAt: eatenAt,
    foodItems: <HomeFoodItem>[
      HomeFoodItem(
        displayName: name,
        kcal: kcal,
        carbG: 0,
        proteinG: 0,
        fatG: 0,
      ),
    ],
    nutrition: HomeMealNutrition(kcal: kcal, carbG: 0, proteinG: 0, fatG: 0),
  );
}

HomeSupplement _supplement({
  required String id,
  required DateTime registeredAt,
  String name = '오메가3',
}) {
  return HomeSupplement(
    id: id,
    displayName: name,
    manufacturer: null,
    schedule: null,
    registeredAt: registeredAt,
  );
}

void main() {
  group('MonthRecords aggregation', () {
    test('buckets meals and supplements by local day', () {
      final DateTime month = DateTime(2026, 6);
      final MonthRecords records = MonthRecords.fromData(
        month: month,
        meals: <HomeMeal>[
          _meal(id: 'm1', eatenAt: DateTime(2026, 6, 12, 8, 10)),
          _meal(id: 'm2', eatenAt: DateTime(2026, 6, 12, 19)),
          _meal(id: 'm3', eatenAt: DateTime(2026, 6, 5, 12)),
        ],
        supplements: <HomeSupplement>[
          _supplement(id: 's1', registeredAt: DateTime(2026, 6, 12, 9)),
          _supplement(id: 's2', registeredAt: DateTime(2026, 6, 20, 9)),
        ],
      );

      // 12일: 끼니 2 + 영양제 1.
      final DayRecords twelfth = records.forDay(DateTime(2026, 6, 12));
      expect(twelfth.meals.length, 2);
      expect(twelfth.supplements.length, 1);
      expect(twelfth.totalCount, 3);
      expect(twelfth.totalKcal, 1040);

      // record dot date set: 식단 점은 5·12, 영양제 점은 12·20.
      expect(records.hasMeal(DateTime(2026, 6, 5)), isTrue);
      expect(records.hasMeal(DateTime(2026, 6, 12)), isTrue);
      expect(records.hasSupplement(DateTime(2026, 6, 12)), isTrue);
      expect(records.hasSupplement(DateTime(2026, 6, 20)), isTrue);
      // 빈 날.
      expect(records.hasMeal(DateTime(2026, 6, 1)), isFalse);
      expect(records.hasSupplement(DateTime(2026, 6, 5)), isFalse);
    });

    test('excludes records from other months', () {
      final MonthRecords records = MonthRecords.fromData(
        month: DateTime(2026, 6),
        meals: <HomeMeal>[
          _meal(id: 'm1', eatenAt: DateTime(2026, 5, 31, 23, 59)),
          _meal(id: 'm2', eatenAt: DateTime(2026, 7, 1, 0, 1)),
          _meal(id: 'm3', eatenAt: DateTime(2026, 6, 30, 23, 59)),
        ],
        supplements: const <HomeSupplement>[],
      );

      expect(records.hasMeal(DateTime(2026, 6, 30)), isTrue);
      expect(records.days.length, 1);
      // 5월·7월 기록은 들어오지 않는다.
      expect(records.forDay(DateTime(2026, 5, 31)).meals, isEmpty);
      expect(records.forDay(DateTime(2026, 7, 1)).meals, isEmpty);
    });

    test('skips meals without an eaten_at and supplements without a date', () {
      final MonthRecords records = MonthRecords.fromData(
        month: DateTime(2026, 6),
        meals: <HomeMeal>[
          const HomeMeal(
            id: 'm-null',
            status: 'pending',
            mealType: 'unknown',
            eatenAt: null,
            foodItems: <HomeFoodItem>[],
            nutrition: HomeMealNutrition.zero,
          ),
        ],
        supplements: <HomeSupplement>[
          const HomeSupplement(
            id: 's-null',
            displayName: '비타민',
            manufacturer: null,
            schedule: null,
          ),
        ],
      );

      expect(records.days, isEmpty);
    });

    test('keyForMonth and keyForDay zero-pad', () {
      expect(MonthRecords.keyForMonth(DateTime(2026, 6)), '2026-06');
      expect(MonthRecords.keyForDay(DateTime(2026, 6, 1)), '2026-06-01');
    });
  });

  group('HomeSupplement.registeredAt parsing', () {
    test('prefers user_confirmed_at over created_at', () {
      final HomeSupplement supplement = HomeSupplement.fromJson(
        <String, dynamic>{
          'id': 's1',
          'display_name': '오메가3',
          'user_confirmed_at': '2026-06-12T09:00:00Z',
          'created_at': '2026-06-01T00:00:00Z',
        },
      );
      expect(supplement.registeredAt, DateTime.utc(2026, 6, 12, 9));
    });

    test('falls back to created_at when user_confirmed_at is missing', () {
      final HomeSupplement supplement = HomeSupplement.fromJson(
        <String, dynamic>{
          'id': 's1',
          'display_name': '오메가3',
          'created_at': '2026-06-01T00:00:00Z',
        },
      );
      expect(supplement.registeredAt, DateTime.utc(2026, 6, 1));
    });

    test('is null when no date fields are present', () {
      final HomeSupplement supplement = HomeSupplement.fromJson(
        <String, dynamic>{'id': 's1', 'display_name': '오메가3'},
      );
      expect(supplement.registeredAt, isNull);
    });
  });
}
