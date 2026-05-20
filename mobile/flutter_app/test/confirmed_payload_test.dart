import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_healthcare/features/ai_coaching/domain/ai_coaching_models.dart';
import 'package:lemon_healthcare/features/food/domain/confirmed_food_entry.dart';
import 'package:lemon_healthcare/features/supplement/domain/supplement_analysis_preview.dart';

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

    final DailyCoachingRequest request = DailyCoachingRequest.fromConfirmedInputs(
      foods: <ConfirmedFoodEntry>[food],
      supplements: <SupplementConfirmedInput>[supplement],
    );
    final Map<String, dynamic> payload = request.toJson()['payload'] as Map<String, dynamic>;

    expect(payload['foods'], hasLength(1));
    expect(payload['supplements'], hasLength(1));
    expect(payload.toString().contains('raw_ocr_text'), isFalse);
    expect(payload.toString().contains('user_confirmed: true'), isTrue);
  });
}
