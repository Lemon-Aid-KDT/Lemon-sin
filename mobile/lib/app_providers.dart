import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_controller.dart';
import 'core/api/api_client.dart';
import 'core/config/app_config.dart';
import 'core/storage/local_prefs.dart';
import 'features/ai_coaching/ai_coaching_repository.dart';
import 'features/auth/token_session.dart';
import 'features/chat/chat_repository.dart';
import 'features/supplements/supplement_repository.dart';

/// Runtime configuration provider.
final Provider<AppConfig> appConfigProvider = Provider<AppConfig>((Ref ref) {
  return AppConfig.fromEnvironment();
});

/// Local persistence wrapper provider (shared_preferences).
///
/// Loads once on first watch. Consumers read `.value` and degrade gracefully to
/// in-memory behavior while the future is still resolving or if it fails.
final FutureProvider<LocalPrefs> localPrefsProvider =
    FutureProvider<LocalPrefs>((Ref ref) {
      return LocalPrefs.create();
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

/// Chatbot repository provider for the chat tab.
final Provider<ChatRepository> chatRepositoryProvider =
    Provider<ChatRepository>((Ref ref) {
      return ChatRepository(apiClient: ref.watch(apiClientProvider));
    });

/// Daily-coaching repository provider for the analysis tab.
final Provider<AiCoachingRepository> aiCoachingRepositoryProvider =
    Provider<AiCoachingRepository>((Ref ref) {
      return AiCoachingRepository(apiClient: ref.watch(apiClientProvider));
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
