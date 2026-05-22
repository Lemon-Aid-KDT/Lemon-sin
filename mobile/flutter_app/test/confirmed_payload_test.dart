import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_healthcare/features/ai_coaching/domain/ai_coaching_models.dart';
import 'package:lemon_healthcare/features/activity/domain/activity_models.dart';
import 'package:lemon_healthcare/features/food/domain/confirmed_food_entry.dart';
import 'package:lemon_healthcare/features/supplement/domain/supplement_analysis_preview.dart';
import 'package:lemon_healthcare/shared/dev/dev_confirmed_samples.dart';
import 'package:lemon_healthcare/shared/state/confirmed_entry_store.dart';

void main() {
  test('confirmed food entry does not invent nutrients', () {
    final ConfirmedFoodEntry entry = ConfirmedFoodEntry(
      name: 'rice bowl',
      mealType: 'lunch',
      servingLabel: '1 bowl',
      memo: 'manual entry',
      photoName: 'food-photo.jpg',
    );

    expect(entry.toAgentSourceJson()['source_type'], 'food_user_input');
    expect(entry.toAgentSourceJson()['user_confirmed'], isTrue);
    expect(entry.toAgentFoodJson().containsKey('nutrients'), isFalse);
  });

  test('daily coaching request uses confirmed food and supplement inputs', () {
    final ConfirmedFoodEntry food = ConfirmedFoodEntry(
      name: 'rice bowl',
      mealType: 'lunch',
      servingLabel: '1 bowl',
      memo: '',
      photoName: null,
    );
    final SupplementConfirmedInput supplement = SupplementConfirmedInput(
      analysisId: 'analysis-1',
      displayName: 'Vitamin D',
      manufacturer: '',
      ingredients: <SupplementConfirmedIngredientInput>[
        SupplementConfirmedIngredientInput(
          displayName: 'Vitamin D',
          nutrientCode: 'vitamin_d',
          amount: 10,
          unit: 'mcg',
        ),
      ],
      serving: SupplementServingInput(
        amount: 1,
        unit: 'tablet',
        dailyServings: 1,
      ),
      intakeSchedule: null,
    );

    final DailyCoachingRequest request =
        DailyCoachingRequest.fromConfirmedInputs(
      foods: <ConfirmedFoodEntry>[food],
      supplements: <SupplementConfirmedInput>[supplement],
    );
    final Map<String, dynamic> payload =
        request.toJson()['payload'] as Map<String, dynamic>;

    expect(payload['foods'], hasLength(1));
    expect(payload['supplements'], hasLength(1));
    expect(payload['supplements'].first['product_name'], 'Vitamin D');
    expect(payload['supplements'].first.containsKey('display_name'), isFalse);
    expect(payload['supplements'].first['times_per_day'], 1);
    expect(
      payload['supplements'].first['ingredients'].first['name'],
      'Vitamin D',
    );
    expect(payload.toString().contains('raw_ocr_text'), isFalse);
    expect(payload.toString().contains('user_confirmed: true'), isTrue);
  });

  test('daily coaching response parses recommendations and existing fields',
      () {
    final DailyCoachingResponse response = DailyCoachingResponse.fromJson(
      <String, dynamic>{
        'request_id': 'response-1',
        'status': 'completed',
        'approval_status': 'confirmed',
        'message': '오늘의 요약: 확인된 입력 기준입니다.',
        'provider': 'sglang',
        'used_tools': <String>['daily_health_agent', 'agent_memory'],
        'findings': <Map<String, dynamic>>[
          <String, dynamic>{
            'nutrient': 'vitamin d',
            'total_amount': 25,
            'unit': 'mcg',
            'level': 'high',
          },
        ],
        'recommendations': <Map<String, dynamic>>[
          <String, dynamic>{
            'category': 'reduce',
            'title': 'Reduce vitamin d',
            'rationale': 'vitamin d intake is above the target range.',
            'priority': 8,
          },
        ],
        'safety_warnings': <String>['현재 입력 기준입니다.'],
      },
    );

    expect(response.requestId, 'response-1');
    expect(response.provider, 'sglang');
    expect(response.usedAgentMemory, isTrue);
    expect(response.findings, hasLength(1));
    expect(response.recommendations, hasLength(1));
    expect(response.safetyWarnings, hasLength(1));
  });

  test('dev sample seeds confirmed entries without food nutrients', () {
    seedDevConfirmedEntries();

    final DailyCoachingRequest request =
        DailyCoachingRequest.fromConfirmedInputs(
      foods: ConfirmedEntryStore.instance.foods,
      supplements: ConfirmedEntryStore.instance.supplements,
    );
    final Map<String, dynamic> payload =
        request.toJson()['payload'] as Map<String, dynamic>;

    expect(payload['foods'], hasLength(1));
    expect(payload['supplements'], hasLength(1));
    expect(payload.toString().contains('nutrients'), isFalse);
    expect(payload.toString().contains('raw_ocr_text'), isFalse);
    ConfirmedEntryStore.instance.clear();
  });

  test('daily coaching request includes confirmed activity context only', () {
    final ConfirmedActivityEntry confirmed = ConfirmedActivityEntry(
      date: DateTime(2026, 5, 21),
      steps: 7200,
      activeMinutes: 34,
      activityEnergyKcal: 220,
      workoutType: 'walk',
      source: 'manual',
      userConfirmed: true,
    );
    final ConfirmedActivityEntry preview = ConfirmedActivityEntry(
      date: DateTime(2026, 5, 21),
      steps: 5000,
      activeMinutes: 20,
      activityEnergyKcal: 120,
      workoutType: 'run',
      source: 'health_connect_preview',
      userConfirmed: false,
    );

    final DailyCoachingRequest request =
        DailyCoachingRequest.fromConfirmedInputs(
      foods: <ConfirmedFoodEntry>[],
      supplements: <SupplementConfirmedInput>[],
      activities: <ConfirmedActivityEntry>[confirmed, preview],
    );
    final Map<String, dynamic> payload =
        request.toJson()['payload'] as Map<String, dynamic>;
    final List<dynamic> healthTrends = payload['health_trends'] as List<dynamic>;

    expect(healthTrends, hasLength(1));
    expect(healthTrends.first['metric'], 'activity_context');
    expect(healthTrends.first['steps'], 7200);
    expect(healthTrends.first['active_minutes'], 34);
    expect(healthTrends.first['activity_energy_kcal'], 220);
    expect(healthTrends.first['workout_type'], 'walk');
    expect(healthTrends.first['source'], 'manual');
    expect(healthTrends.first['user_confirmed'], isTrue);
    expect(payload.toString().contains('health_connect_preview'), isFalse);
    expect(payload.toString().contains('sleep'), isFalse);
    expect(payload.toString().contains('route'), isFalse);
    expect(payload.toString().contains('blood_glucose'), isFalse);
    expect(payload.toString().contains('blood_pressure'), isFalse);
  });
}
