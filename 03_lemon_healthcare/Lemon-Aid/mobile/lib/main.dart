import 'package:flutter/material.dart';

import 'app.dart';
import 'core/api/api_client.dart';
import 'core/config/app_config.dart';
import 'features/supplements/supplement_repository.dart';

void main() {
  final AppConfig config = AppConfig.fromEnvironment();
  final ApiClient apiClient = ApiClient(
    baseUrl: config.apiBaseUrl,
    bearerToken: config.apiToken,
  );

  runApp(
    LemonAidApp(repository: BackendLemonAidRepository(apiClient: apiClient)),
  );
}
