// services/mock_repository.dart — 백엔드 합치기 전 mock 데이터 단일 소스
//
// 참조: mobile/CLAUDE.md §6 + mobile/docs/integration_notes.md
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 백엔드 API 연결 시 — 이 클래스를 ApiRepository 로 교체.
// 인터페이스 (메서드 시그니처) 동일 유지. integration_notes.md 의
// 실제 API 경로 (yeong-Vision-Nutrition/backend/src/api/v1/*) / 응답 키 참고.
//
// 모든 메서드 `await Future.delayed(300ms)` — 네트워크 지연 시뮬레이션.

import '../models/analysis_result.dart';
import '../models/daily_score.dart';
import '../models/meal.dart';
import '../models/supplement.dart';
import '../utils/dev_mock_user.dart';

class MockRepository {
  MockRepository._();
  static final MockRepository instance = MockRepository._();

  static const Duration _latency = Duration(milliseconds: 300);

  /// 홈 한눈 — 오늘 점수 + 다음 행동 한 줄.
  Future<DailyScore> getTodayScore() async {
    await Future<void>.delayed(_latency);
    return DailyScore(
      userId: DevMockUser.id,
      date: DateTime.now(),
      totalScore: 82,
      nextActionHint: '저녁에 채소 한 줌만 더 챙겨볼까요?',
      deltaFromYesterday: 5,
      updatedAt: DateTime.now(),
      raw: const <String, dynamic>{},
    );
  }

  /// 오늘 출력 카드 — 5 종 가안 (nutrient / kdri / weight / activity / goal).
  /// integration_notes.md §2.1 — 백엔드 실제 분류는 3종 (activity_score / weight_prediction / nutrition_analysis).
  /// 합치기 시 kind 매핑만 수정.
  Future<List<AnalysisResult>> getTodayAnalyses() async {
    await Future<void>.delayed(_latency);
    final DateTime now = DateTime.now();
    return <AnalysisResult>[
      AnalysisResult(
        id: 'mock-nutrient-001',
        userId: DevMockUser.id,
        createdAt: now,
        kind: 'nutrient',
        headline: '오늘 단백질 18g 부족해요',
        detail: '점심 닭가슴살 한 조각이면 채워져요.',
        source: '농진청 식품 DB · 방금 전',
        confidence: 0.86,
        editableFields: const <String>['grams_input', 'serving_input'],
        fallbackText: '오늘 식사 기록이 적어서 정확도가 낮아요.',
        raw: const <String, dynamic>{},
      ),
      AnalysisResult(
        id: 'mock-kdri-002',
        userId: DevMockUser.id,
        createdAt: now,
        kind: 'kdri',
        headline: '비타민 D 섭취가 권장량보다 낮음',
        detail: '햇볕 산책 15분 또는 연어 한 토막 권장.',
        source: 'KDRIs 2020 · 30분 전',
        confidence: 0.71,
        editableFields: const <String>['target_amount'],
        raw: const <String, dynamic>{},
      ),
      AnalysisResult(
        id: 'mock-weight-003',
        userId: DevMockUser.id,
        createdAt: now,
        kind: 'weight',
        headline: '7일 후 예상 체중 67.8kg',
        detail: '현재 추세대로면 가벼움 유지.',
        source: '에너지 수지 모델 · 오늘 아침',
        confidence: 0.62,
        raw: const <String, dynamic>{},
      ),
      AnalysisResult(
        id: 'mock-activity-004',
        userId: DevMockUser.id,
        createdAt: now,
        kind: 'activity',
        headline: '오늘 활동 점수 78점',
        detail: '걸음수 7,200 · 목표 심박 구간 18분.',
        source: '활동점수 v4 · 1시간 전',
        confidence: 0.91,
        raw: const <String, dynamic>{},
      ),
      AnalysisResult(
        id: 'mock-goal-005',
        userId: DevMockUser.id,
        createdAt: now,
        kind: 'goal',
        headline: '주간 목표 4/5 달성',
        detail: '내일까지 한 끼 더 기록하면 완료.',
        source: '주간 목표 트래커',
        confidence: 0.55,
        raw: const <String, dynamic>{},
      ),
    ];
  }

  Future<List<Meal>> getRecentMeals({int limit = 5}) async {
    await Future<void>.delayed(_latency);
    final DateTime now = DateTime.now();
    final List<Meal> all = <Meal>[
      Meal(
        id: 'mock-meal-001',
        userId: DevMockUser.id,
        takenAt: now.subtract(const Duration(hours: 2)),
        photoUrl: null,
        candidates: const <FoodCandidate>[
          FoodCandidate(
            foodCode: 'KR_RICE_001',
            canonicalName: '잡곡밥',
            confidence: 0.92,
            source: 'yolo_v8',
          ),
          FoodCandidate(
            foodCode: 'KR_KIM_001',
            canonicalName: '배추김치',
            confidence: 0.81,
            source: 'google_vision',
          ),
        ],
        reviewFlag: false,
      ),
      Meal(
        id: 'mock-meal-002',
        userId: DevMockUser.id,
        takenAt: now.subtract(const Duration(hours: 5)),
        candidates: const <FoodCandidate>[
          FoodCandidate(
            canonicalName: '닭가슴살 샐러드',
            confidence: 0.74,
            source: 'yolo_v8',
          ),
        ],
        reviewFlag: true,
      ),
    ];
    return all.take(limit).toList();
  }

  Future<List<Supplement>> getRecentSupplements({int limit = 5}) async {
    await Future<void>.delayed(_latency);
    final DateTime now = DateTime.now();
    final List<Supplement> all = <Supplement>[
      Supplement(
        id: 'mock-supp-001',
        userId: DevMockUser.id,
        takenAt: now.subtract(const Duration(days: 1)),
        ocrText: '종합비타민 1정',
        ingredients: const <SupplementIngredient>[
          SupplementIngredient(
            name: '비타민 D',
            amount: 1000,
            unit: 'IU',
            confidence: 0.88,
          ),
          SupplementIngredient(
            name: '비타민 C',
            amount: 500,
            unit: 'mg',
            confidence: 0.93,
          ),
        ],
        previewApproved: true,
      ),
    ];
    return all.take(limit).toList();
  }
}
