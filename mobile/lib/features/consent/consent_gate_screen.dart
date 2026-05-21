import 'package:flutter/material.dart';

import '../../app_controller.dart';
import 'consent_models.dart';

/// Consent screen for OCR image processing and sensitive health analysis.
class ConsentGateScreen extends StatelessWidget {
  /// Creates the consent screen.
  const ConsentGateScreen({required this.controller, super.key});

  /// App flow controller.
  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final ConsentState? consentState = controller.consentState;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        Text(
          'Required demo consents',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        const Text(
          'The mobile demo calls the same backend consent gates as production APIs.',
        ),
        const SizedBox(height: 16),
        _ConsentRow(
          label: 'OCR image processing',
          granted: consentState?.isGranted(AppController.ocrConsent) ?? false,
        ),
        _ConsentRow(
          label: 'Sensitive health analysis',
          granted:
              consentState?.isGranted(AppController.healthConsent) ?? false,
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: controller.busy ? null : controller.grantMinimumConsents,
          icon: const Icon(Icons.verified_user),
          label: const Text('Grant required consents'),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: controller.busy ? null : controller.bootstrap,
          icon: const Icon(Icons.sync),
          label: const Text('Reload consent state'),
        ),
      ],
    );
  }
}

class _ConsentRow extends StatelessWidget {
  const _ConsentRow({required this.label, required this.granted});

  final String label;
  final bool granted;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(
          granted ? Icons.check_circle : Icons.radio_button_unchecked,
        ),
        title: Text(label),
        trailing: Text(granted ? 'Granted' : 'Required'),
      ),
    );
  }
}
