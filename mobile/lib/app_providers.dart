import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_controller.dart';
import 'core/api/api_client.dart';
import 'core/config/app_config.dart';
import 'features/auth/token_session.dart';
import 'features/supplements/supplement_repository.dart';

/// Runtime configuration provider.
final Provider<AppConfig> appConfigProvider = Provider<AppConfig>((Ref ref) {
  return AppConfig.fromEnvironment();
});

/// External bearer-token persistence provider.
final Provider<BearerTokenStore> bearerTokenStoreProvider =
    Provider<BearerTokenStore>((Ref ref) {
      return SecureBearerTokenStore();
    });

/// Local auth/session provider for dev bypass and externally issued JWTs.
final ChangeNotifierProvider<TokenSessionController> tokenSessionProvider =
    ChangeNotifierProvider<TokenSessionController>((Ref ref) {
      final TokenSessionController controller = TokenSessionController(
        store: ref.watch(bearerTokenStoreProvider),
      );
      controller.bootstrap();
      return controller;
    });

/// API client provider for the current `/api/v1` backend contract.
final Provider<ApiClient> apiClientProvider = Provider<ApiClient>((Ref ref) {
  final AppConfig config = ref.watch(appConfigProvider);
  final TokenSessionController session = ref.watch(tokenSessionProvider);
  final ApiClient client = ApiClient(
    baseUrl: config.apiBaseUrl,
    bearerToken: session.bearerToken ?? config.apiToken,
    devGatewayToken: config.devGatewayToken,
  );
  return client;
});

/// Backend repository provider.
final Provider<LemonAidRepository> lemonAidRepositoryProvider =
    Provider<LemonAidRepository>((Ref ref) {
      return BackendLemonAidRepository(apiClient: ref.watch(apiClientProvider));
    });

/// App controller provider that preserves the existing endpoint/data flow.
final ChangeNotifierProvider<AppController> appControllerProvider =
    ChangeNotifierProvider<AppController>((Ref ref) {
      final AppController controller = AppController(
        repository: ref.watch(lemonAidRepositoryProvider),
      );
      controller.bootstrap();
      return controller;
    });
