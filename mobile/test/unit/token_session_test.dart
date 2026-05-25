import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/features/auth/token_session.dart';

void main() {
  test('uses debug dev bypass when no token is stored', () async {
    final TokenSessionController controller = TokenSessionController(
      store: MemoryBearerTokenStore(),
      releaseMode: false,
    );

    await controller.bootstrap();

    expect(controller.bootstrapped, isTrue);
    expect(controller.bearerToken, isNull);
    expect(controller.devBypassActive, isTrue);
    expect(controller.canEnterShell, isTrue);
  });

  test('requires a token in release mode', () async {
    final TokenSessionController controller = TokenSessionController(
      store: MemoryBearerTokenStore(),
      releaseMode: true,
    );

    await controller.bootstrap();

    expect(controller.devBypassActive, isFalse);
    expect(controller.canEnterShell, isFalse);
  });

  test('stores normalized externally issued bearer token', () async {
    final MemoryBearerTokenStore store = MemoryBearerTokenStore();
    final TokenSessionController controller = TokenSessionController(
      store: store,
      releaseMode: true,
    );

    await controller.saveBearerToken('Bearer jwt-access-token');

    expect(controller.bearerToken, 'jwt-access-token');
    expect(await store.readBearerToken(), 'jwt-access-token');
    expect(controller.canEnterShell, isTrue);
  });
}
