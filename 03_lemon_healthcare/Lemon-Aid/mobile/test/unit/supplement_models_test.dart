import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';

void main() {
  test('parses supplement preview and serializes registration payload', () {
    final SupplementAnalysisPreview preview =
        SupplementAnalysisPreview.fromJson(<String, dynamic>{
          'analysis_id': '00000000-0000-0000-0000-000000000001',
          'status': 'requires_confirmation',
          'parsed_product': <String, dynamic>{
            'product_name': 'Vitamin D',
            'manufacturer': 'Lemon Labs',
            'serving_size': '1 capsule',
            'daily_servings': 1,
          },
          'ingredient_candidates': <Map<String, dynamic>>[
            <String, dynamic>{
              'display_name': 'Vitamin D',
              'nutrient_code': 'vitamin_d',
              'amount': 25,
              'unit': 'ug',
              'confidence': 0.8,
              'source': 'ocr_llm_preview',
            },
          ],
          'layout_available': true,
          'label_sections': <Map<String, dynamic>>[
            <String, dynamic>{
              'section_id': 'section-001',
              'section_type': 'ingredients',
              'heading_text': 'Supplement Facts',
              'text_bundle': 'Vitamin D 25 ug',
              'confidence': 0.8,
              'requires_review': false,
              'evidence_refs': <String>['span-001'],
            },
          ],
          'intake_method': <String, dynamic>{
            'text': 'Take 1 capsule daily.',
            'structured': <String, dynamic>{
              'frequency': 'daily',
              'times_per_day': 1,
              'amount_per_time': 1,
              'amount_unit': 'capsule',
              'time_of_day': <String>['morning'],
              'with_food': 'unknown',
            },
            'confidence': 0.82,
            'requires_review': false,
            'evidence_refs': <String>['span-002'],
          },
          'precautions': <Map<String, dynamic>>[
            <String, dynamic>{
              'text': 'Consult a professional if pregnant.',
              'category': 'pregnancy',
              'severity': 'label_caution',
              'confidence': 0.9,
              'requires_review': false,
              'evidence_refs': <String>['span-003'],
            },
          ],
          'functional_claims': <Map<String, dynamic>>[
            <String, dynamic>{
              'text': 'Supports normal bone health.',
              'claim_type': 'label_claim',
              'confidence': 0.85,
              'requires_review': false,
              'evidence_refs': <String>['span-004'],
            },
          ],
          'evidence_spans': <Map<String, dynamic>>[
            <String, dynamic>{
              'span_id': 'span-001',
              'source_type': 'label_layout',
              'section_type': 'ingredients',
              'text_excerpt': 'Vitamin D 25 ug',
              'page_index': 0,
              'cell_ref': 'section-001:r0:c0',
              'confidence': 0.8,
            },
          ],
          'provider_observations': <Map<String, dynamic>>[
            <String, dynamic>{
              'provider': 'paddleocr_local',
              'stage': 'primary',
              'status': 'completed',
              'latency_ms': 123,
              'text_non_empty': true,
              'parser_success': true,
              'error_code': null,
              'warning_codes': <String>[],
              'raw_ocr_text_stored': false,
              'raw_provider_payload_stored': false,
            },
          ],
          'image_quality_report': <String, dynamic>{
            'status': 'retake_recommended',
            'issues': <Map<String, dynamic>>[
              <String, dynamic>{
                'reason_code': 'cover_only',
                'severity': 'retake',
                'message': 'Only the front label is visible.',
                'evidence': <String, dynamic>{'label': 'brand_front_label'},
              },
            ],
            'metrics': <String, dynamic>{
              'image_width': 400,
              'image_height': 300,
            },
            'detected_rois': <Map<String, dynamic>>[
              <String, dynamic>{
                'label': 'brand_front_label',
                'x': 10,
                'y': 20,
                'width': 180,
                'height': 220,
                'confidence': 0.94,
                'area_ratio': 0.33,
              },
            ],
            'retake_reasons': <String>['cover_only'],
          },
          'analysis_scope': 'identity_only',
          'action_required': 'additional_label_image_required',
          'detected_product_regions': <Map<String, dynamic>>[
            <String, dynamic>{
              'region_id': 'roi-001',
              'label': 'brand_front_label',
              'x': 10,
              'y': 20,
              'width': 180,
              'height': 220,
              'confidence': 0.94,
              'area_ratio': 0.33,
              'selected': true,
            },
          ],
          'selected_region_id': 'roi-001',
          'missing_required_sections': <String>['supplement_facts'],
          'image_role': 'front_label',
          'multi_image_group_id': null,
          'source_type': 'uploaded_image',
          'identity_conflict': <String, dynamic>{
            'conflict_type': 'barcode_product_mismatch',
            'severity': 'review',
            'message': 'Confirm product identity.',
            'evidence': <String, dynamic>{
              'barcode_candidate_count': 1,
              'parsed_product_present': true,
            },
          },
          'matched_product_candidates': <Object>[],
          'low_confidence_fields': <String>['manufacturer'],
          'warnings': <String>['User confirmation required.'],
          'algorithm_version': 'test',
          'source_manifest_version': null,
          'expires_at': '2026-05-15T00:00:00Z',
        });

    expect(preview.parsedProduct.productName, 'Vitamin D');
    expect(preview.ingredientCandidates.single.amount, 25);
    expect(preview.layoutAvailable, isTrue);
    expect(preview.labelSections.single.textBundle, 'Vitamin D 25 ug');
    expect(preview.intakeMethod.structured.timesPerDay, 1);
    expect(preview.precautions.single.category, 'pregnancy');
    expect(preview.functionalClaims.single.claimType, 'label_claim');
    expect(preview.evidenceSpans.single.textExcerpt, 'Vitamin D 25 ug');
    expect(preview.providerObservations.single.provider, 'paddleocr_local');
    expect(preview.providerObservations.single.rawOcrTextStored, isFalse);
    expect(preview.imageQualityReport?.issues.single.reasonCode, 'cover_only');
    expect(preview.actionRequired, 'additional_label_image_required');
    expect(preview.blocksRegistrationForImageRisk, isTrue);
    expect(preview.detectedProductRegions.single.regionId, 'roi-001');
    expect(preview.missingRequiredSections.single, 'supplement_facts');
    expect(preview.identityConflict?.conflictType, 'barcode_product_mismatch');

    final UserSupplementCreate request = UserSupplementCreate(
      analysisId: preview.analysisId,
      displayName: 'Vitamin D',
      manufacturer: 'Lemon Labs',
      ingredients: const <UserSupplementIngredientInput>[
        UserSupplementIngredientInput(
          displayName: 'Vitamin D',
          nutrientCode: 'vitamin_d',
          amount: 25,
          unit: 'ug',
          confidence: 0.8,
          source: 'ocr_llm_preview',
        ),
      ],
      serving: const SupplementServing(
        amount: 1,
        unit: 'capsule',
        dailyServings: 1,
      ),
      intakeSchedule: const SupplementIntakeSchedule(
        frequency: 'daily',
        timeOfDay: <String>['morning'],
      ),
    );

    expect(request.toJson()['user_confirmed'], true);
    expect(request.toJson()['analysis_id'], preview.analysisId);
  });

  test('parses supplement impact preview response', () {
    final SupplementImpactPreviewResponse response =
        SupplementImpactPreviewResponse.fromJson(<String, dynamic>{
          'calculation_version': 'supplement-impact-v1.0.0',
          'reference_version': '2025',
          'source_manifest_version': null,
          'data_status': 'partial',
          'current_supplement_contributions': <Map<String, dynamic>>[
            <String, dynamic>{
              'nutrient_code': 'vitamin_d_ug',
              'nutrient_name': 'Vitamin D',
              'reference_unit': 'ug',
              'total_daily_amount': 25,
              'original_unit_totals': <String, dynamic>{'ug': 25},
              'contribution_count': 1,
              'supplement_ids': <String>[],
              'items': <Object>[],
              'warnings': <String>[],
            },
          ],
          'deficiency_support_candidates': <Map<String, dynamic>>[],
          'excess_or_duplicate_risks': <Map<String, dynamic>>[
            <String, dynamic>{
              'nutrient_code': 'vitamin_d_ug',
              'nutrient_name': 'Vitamin D',
              'action_label': 'avoid_duplicate',
              'reason_code': 'duplicate_supplement_source',
              'current_food_or_recorded_amount': null,
              'supplement_daily_amount': 25,
              'estimated_total_amount': null,
              'reference_amount': null,
              'reference_unit': 'ug',
              'ul_amount': null,
              'contributing_supplements': <String>[],
              'evidence': <Object>[],
              'user_message': 'Check duplicate supplement sources.',
            },
          ],
          'missing_profile_fields': <String>['age'],
          'safe_user_message': 'Review current supplement intake.',
          'clinical_disclaimer': 'Reference information only.',
          'warnings': <String>['partial_profile'],
          'requires_user_confirmation': true,
        });

    expect(response.dataStatus, 'partial');
    expect(response.currentSupplementContributions.single.totalDailyAmount, 25);
    expect(
      response.excessOrDuplicateRisks.single.actionLabel,
      'avoid_duplicate',
    );
    expect(
      response.toJson()['calculation_version'],
      'supplement-impact-v1.0.0',
    );
  });
}
