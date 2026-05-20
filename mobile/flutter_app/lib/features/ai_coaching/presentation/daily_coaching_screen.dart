import 'package:flutter/material.dart';

import '../../../shared/state/confirmed_entry_store.dart';
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

  Future<void> _runConfirmedFlow() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      await _repository.grantSensitiveHealthAnalysisConsent();
      final DailyCoachingResponse response = await _repository.runDailyCoaching(
        DailyCoachingRequest.fromConfirmedInputs(
          foods: ConfirmedEntryStore.instance.foods,
          supplements: ConfirmedEntryStore.instance.supplements,
        ),
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
            'Daily coaching',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          const Text('AI Agent coaching uses confirmed food and supplement entries only.'),
          const SizedBox(height: 8),
          Text('Confirmed foods: ${ConfirmedEntryStore.instance.foods.length}'),
          Text('Confirmed supplements: ${ConfirmedEntryStore.instance.supplements.length}'),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _isLoading ? null : _runConfirmedFlow,
            child: Text(_isLoading ? 'Requesting...' : 'Request coaching'),
          ),
          const SizedBox(height: 16),
          if (_error != null) const _ErrorPanel(),
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
    final String memoryLabel = response.usedAgentMemory ? 'yes' : 'no';

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
            Text('Status: ${response.status}'),
            Text('Provider: ${response.provider}'),
            Text('Memory used: $memoryLabel'),
            const SizedBox(height: 12),
            Text(response.message),
            if (response.findings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              Text('Findings: ${response.findings.length}'),
            ],
          ],
        ),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel();

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
          'The request did not complete. Check the server connection and authentication state.',
          style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
        ),
      ),
    );
  }
}
