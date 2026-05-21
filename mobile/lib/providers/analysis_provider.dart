// providers/analysis_provider.dart — 영양제 라벨 OCR 분석 상태
//
// 담당: A 프론트 리드 + ML 팀 (백엔드 OCR endpoint 통합)
// 참조:
//   - 5종 출력 분석 결과 (UX_DIARY §8)
//   - 백엔드 endpoint: POST /api/v1/supplements/analyze (SupplementAnalysisPreview)
//
// 흐름:
//   1. CameraScreen 에서 takePicture / 갤러리 선택 → File 확보
//   2. analyzeImage(File) 호출 → AsyncValue.loading 상태로 전환
//   3. ApiClient.analyzeSupplementImage 호출 (multipart upload)
//   4. 응답 → AsyncValue.data(preview) 또는 AsyncValue.error
//   5. AnalysisResultScreen 이 ref.watch(analysisProvider) 로 동적 렌더링

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/supplement_analysis.dart';
import '../models/supplement_comprehensive.dart';
import '../services/api_client.dart';
import 'auth_provider.dart' show apiClientProvider;

/// 영양제 분석 결과 + 마지막 이미지 메타데이터.
@immutable
class AnalysisState {
  const AnalysisState({
    required this.result,
    this.comprehensive = const AsyncValue.data(null),
    this.lastImagePath,
  });

  /// OCR analyze 응답 (1단계).
  final AsyncValue<SupplementAnalysisPreview?> result;

  /// 5-card 종합 분석 응답 (2단계, B-persona 차별화 데이터 포함).
  final AsyncValue<SupplementComprehensiveAnalysis?> comprehensive;

  /// 마지막 분석 이미지 경로 (재시도 시 사용).
  final String? lastImagePath;

  /// 초기/idle 상태 — 아직 분석 호출 없음.
  static const AnalysisState idle = AnalysisState(result: AsyncValue.data(null));

  AnalysisState copyWith({
    AsyncValue<SupplementAnalysisPreview?>? result,
    AsyncValue<SupplementComprehensiveAnalysis?>? comprehensive,
    String? lastImagePath,
  }) {
    return AnalysisState(
      result: result ?? this.result,
      comprehensive: comprehensive ?? this.comprehensive,
      lastImagePath: lastImagePath ?? this.lastImagePath,
    );
  }
}

/// 영양제 OCR 분석 호출을 캡슐화하는 StateNotifier.
class AnalysisNotifier extends StateNotifier<AnalysisState> {
  AnalysisNotifier(this._apiClient) : super(AnalysisState.idle);

  final ApiClient _apiClient;

  /// 이미지 파일을 백엔드로 보내고 결과를 [state] 에 반영한다.
  ///
  /// 흐름:
  ///   1. `analyze` endpoint 호출 → `SupplementAnalysisPreview` 받음.
  ///   2. ingredient candidate → comprehensive payload 로 변환.
  ///   3. `analyze/comprehensive` 호출 → `SupplementComprehensiveAnalysis` 받음.
  ///   4. 두 응답을 state 에 분리 저장.
  ///
  /// Args:
  ///   imageFile: 촬영/선택된 라벨 이미지.
  ///   mode: 'supplement' / 'meal' (현재는 supplement endpoint 호출).
  ///   userProfile: KDRIs 룩업용 (없으면 기본값: 52세 남성 + cardiovascular).
  ///   persona: B-persona 기본 (만성질환자 가중치).
  Future<void> analyzeImage(
    File imageFile, {
    String mode = 'supplement',
    UserProfilePayload? userProfile,
    String persona = 'B',
  }) async {
    state = state.copyWith(
      result: const AsyncValue.loading(),
      comprehensive: const AsyncValue.data(null),
      lastImagePath: imageFile.path,
    );

    SupplementAnalysisPreview preview;
    try {
      final clientRequestId = await _generateIdempotencyKey(imageFile);
      preview = await _apiClient.analyzeSupplementImage(
        imageFile: imageFile,
        clientRequestId: clientRequestId,
      );
      state = state.copyWith(result: AsyncValue.data(preview));
    } catch (e, st) {
      state = state.copyWith(result: AsyncValue.error(e, st));
      return;
    }

    // 2단계: comprehensive 분석 자동 호출 (5-card 채우기)
    state = state.copyWith(comprehensive: const AsyncValue.loading());
    try {
      final ingredients = preview.ingredientCandidates
          .map(
            (i) => ComprehensiveIngredientPayload(
              displayName: i.displayName,
              nutrientCode: i.nutrientCode,
              amount: i.amount,
              unit: i.unit,
            ),
          )
          .toList(growable: false);
      final profile = userProfile ??
          const UserProfilePayload(
            age: 52,
            sex: 'male',
            chronicConditions: ['cardiovascular'],
          );
      final result = await _apiClient.analyzeComprehensive(
        analysisId: preview.analysisId,
        ingredients: ingredients,
        userProfile: profile,
        persona: persona,
      );
      state = state.copyWith(comprehensive: AsyncValue.data(result));
    } catch (e, st) {
      state = state.copyWith(comprehensive: AsyncValue.error(e, st));
    }
  }

  /// 마지막 이미지로 다시 분석 시도.
  Future<void> retry() async {
    final path = state.lastImagePath;
    if (path == null) return;
    final file = File(path);
    if (!await file.exists()) return;
    await analyzeImage(file);
  }

  /// 상태 초기화 (idle).
  void reset() {
    state = AnalysisState.idle;
  }

  /// 동일 이미지 중복 분석을 막기 위한 deterministic idempotency key.
  ///
  /// crypto 패키지 없이 dart core 만으로 구현. 파일 크기 + 수정 시각 + path hash
  /// 조합으로 같은 파일에서는 동일 key, 다른 파일에서는 다른 key 가 나오도록 한다.
  /// backend 의 80자 제한(`client_request_id`) 을 충족한다.
  Future<String> _generateIdempotencyKey(File imageFile) async {
    final stat = await imageFile.stat();
    final pathHash = imageFile.path.hashCode.toUnsigned(32).toRadixString(16);
    final modifiedMs = stat.modified.millisecondsSinceEpoch;
    return 'img_${stat.size}_${modifiedMs}_$pathHash';
  }
}

/// 전역 Provider (UI 에서 `ref.watch(analysisProvider)` 로 구독).
final analysisProvider = StateNotifierProvider<AnalysisNotifier, AnalysisState>(
  (ref) {
    final apiClient = ref.read(apiClientProvider);
    return AnalysisNotifier(apiClient);
  },
);
