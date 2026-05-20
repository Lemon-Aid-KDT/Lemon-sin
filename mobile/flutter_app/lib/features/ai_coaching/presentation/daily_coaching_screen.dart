import 'package:flutter/material.dart';

import '../../../shared/widgets/medical_disclaimer.dart';
import '../data/ai_coaching_repository.dart';
import '../domain/ai_coaching_models.dart';

class DailyCoachingScreen extends StatefulWidget {
  const DailyCoachingScreen({super.key});

  @override
  State<DailyCoachingScreen> createState() => _DailyCoachingScreenState();
}

class _DailyCoachingScreenState extends State<DailyCoachingScreen> {
  final AiCoachingRepository _repository = AiCoachingRepository();
  DailyCoachingResponse? _response;
  Object? _error;
  bool _isLoading = false;

  Future<void> _runSmokeFlow() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await _repository.grantSensitiveHealthAnalysisConsent();
      final DailyCoachingResponse response = await _repository.runDailyCoaching(
        DailyCoachingRequest.confirmedMealSample(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _response = response;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lemon Aid')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          Text(
            '오늘의 식단 코칭',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          const Text('확인된 식단 기록을 기반으로 AI Agent 코칭을 요청합니다.'),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _isLoading ? null : _runSmokeFlow,
            child: Text(_isLoading ? '요청 중' : '코칭 요청'),
          ),
          const SizedBox(height: 16),
          if (_error != null) _ErrorPanel(error: _error!),
          if (_response != null) _CoachingResult(response: _response!),
          const SizedBox(height: 24),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}

class _CoachingResult extends StatelessWidget {
  const _CoachingResult({required this.response});

  final DailyCoachingResponse response;

  @override
  Widget build(BuildContext context) {
    final String memoryLabel = response.usedAgentMemory ? '예' : '아니오';

    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('상태: ${response.status}'),
            Text('Provider: ${response.provider}'),
            Text('Memory 사용: $memoryLabel'),
            const SizedBox(height: 12),
            Text(response.message),
            if (response.findings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              Text('주요 결과 ${response.findings.length}건'),
            ],
          ],
        ),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Text(
          '요청을 완료하지 못했습니다. 서버 연결과 인증 상태를 확인해 주세요.',
          style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
        ),
      ),
    );
  }
}
