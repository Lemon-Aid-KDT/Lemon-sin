import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_healthcare/app.dart';

void main() {
  testWidgets('dashboard opens chatbot screen', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: LemonAidApp()));
    await tester.pumpAndSettle();

    expect(find.text('Lemon Aid'), findsOneWidget);
    expect(find.text('챗봇'), findsOneWidget);

    await tester.tap(find.text('챗봇'));
    await tester.pumpAndSettle();

    expect(find.text('확정한 기록에 대해 물어보기'), findsOneWidget);
    expect(
      find.text('오늘 확정한 음식, 영양제 기록을 기준으로 확인할 점을 물어보세요.'),
      findsOneWidget,
    );
  });
}
