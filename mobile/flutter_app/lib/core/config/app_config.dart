class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.authToken,
  });

  factory AppConfig.fromEnvironment() {
    return const AppConfig(
      apiBaseUrl: String.fromEnvironment(
        'LEMON_API_BASE_URL',
        defaultValue: 'http://127.0.0.1:18080',
      ),
      authToken: String.fromEnvironment('LEMON_AUTH_TOKEN'),
    );
  }

  final String apiBaseUrl;
  final String authToken;

  bool get hasAuthToken => authToken.isNotEmpty;
}
