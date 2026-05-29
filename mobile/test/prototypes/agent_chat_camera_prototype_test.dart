import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid/prototypes/agent_chat_camera_prototype.dart';

void main() {
  testWidgets('Agent tab starts with three full-width dashboard cards',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    expect(find.text('오늘의 Agent'), findsOneWidget);
    expect(find.text('식단'), findsOneWidget);
    expect(find.text('영양제'), findsOneWidget);
    expect(find.text('분석'), findsOneWidget);
    expect(find.text('약속'), findsNothing);

    await tester.scrollUntilVisible(
      find.text('오늘 하루 약속'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(find.text('오늘 하루 약속'), findsOneWidget);
    expect(find.text('아침 루틴'), findsNothing);
  });

  testWidgets('Diet detail has meal slots, photo sheet, and custom meal name',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-diet')));
    await tester.pumpAndSettle();

    expect(find.text('식단 기록'), findsOneWidget);
    expect(find.text('아침'), findsWidgets);
    expect(find.text('점심'), findsWidgets);
    expect(find.text('저녁'), findsWidgets);

    await tester.tap(find.byKey(const Key('diet-photo-morning')));
    await tester.pumpAndSettle();

    expect(find.text('카메라로 찍기'), findsOneWidget);
    expect(find.text('사진 업로드'), findsOneWidget);

    await tester.tap(find.text('사진 업로드'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('그 외 식사 추가하기'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('그 외 식사 추가하기'), findsOneWidget);

    await tester.tap(find.text('그 외 식사 추가하기'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('custom-entry-name')), '야식');
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();

    expect(find.text('야식'), findsOneWidget);
  });

  testWidgets('Diet cards can rename and delete default and custom entries',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-diet')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('diet-edit-morning')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('entry-edit-name')), '아침 식사');
    await tester.tap(find.text('수정'));
    await tester.pumpAndSettle();

    expect(find.text('아침 식사'), findsOneWidget);
    expect(find.text('아침'), findsNothing);

    await tester.tap(find.byKey(const Key('diet-delete-lunch')));
    await tester.pumpAndSettle();

    expect(find.text('점심'), findsNothing);
    expect(find.text('아침 식사'), findsOneWidget);
    expect(find.text('저녁'), findsOneWidget);

    await tester.tap(find.text('그 외 식사 추가하기'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('custom-entry-name')), '야식');
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('diet-edit-custom-0')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('entry-edit-name')), '운동 후 식사');
    await tester.tap(find.text('수정'));
    await tester.pumpAndSettle();

    expect(find.text('운동 후 식사'), findsOneWidget);
    expect(find.text('야식'), findsNothing);

    await tester.tap(find.byKey(const Key('diet-delete-custom-0')));
    await tester.pumpAndSettle();

    expect(find.text('운동 후 식사'), findsNothing);
  });

  testWidgets('Supplement registration previews upload and applies to groups',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-supplement')));
    await tester.pumpAndSettle();

    expect(find.text('영양제 기록'), findsOneWidget);
    expect(
      find.text('복용 중인 영양제를 등록해두고 시간대별로 관리합니다.'),
      findsOneWidget,
    );
    expect(find.text('영양제 등록하기'), findsOneWidget);
    expect(find.text('아침'), findsOneWidget);
    expect(find.text('점심'), findsOneWidget);
    expect(find.text('혈압약 B'), findsOneWidget);
    expect(find.text('오메가-3'), findsOneWidget);
    expect(find.text('당뇨약 A'), findsOneWidget);
    expect(find.text('비타민 D'), findsOneWidget);
    expect(find.text('복용약'), findsWidgets);
    expect(find.text('영양제'), findsWidgets);
    expect(find.text('아직 등록된 영양제가 없습니다.'), findsNothing);

    await tester.scrollUntilVisible(
      find.text('저녁'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(find.text('저녁'), findsOneWidget);
    expect(find.text('마그네슘'), findsOneWidget);
    expect(find.text('프로바이오틱스'), findsOneWidget);
    expect(find.text('그 외 영양제 추가하기'), findsNothing);
    expect(find.text('아침 루틴'), findsNothing);

    await tester.drag(find.byType(ListView), const Offset(0, 900));
    await tester.pumpAndSettle();

    await tester.tap(find.text('영양제 등록하기'));
    await tester.pumpAndSettle();

    expect(find.text('카메라로 찍기'), findsOneWidget);
    expect(find.text('사진 업로드'), findsOneWidget);

    await tester.tap(find.text('사진 업로드'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('supplement-mock-preview')), findsOneWidget);
    expect(find.byKey(const Key('supplement-name-input')), findsOneWidget);
    expect(find.text('업로드한 멀티비타민'), findsOneWidget);
    expect(find.byKey(const Key('target-group-아침')), findsOneWidget);
    expect(find.byKey(const Key('target-group-점심')), findsOneWidget);
    expect(find.text('복용약'), findsWidgets);
    expect(find.text('영양제'), findsWidgets);

    await tester.tap(find.byKey(const Key('target-group-아침')));
    await tester.enterText(find.byKey(const Key('new-group-input')), '운동 후');
    await tester.tap(find.byKey(const Key('add-target-group')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('target-group-운동 후')), findsOneWidget);

    await tester.tap(find.byKey(const Key('target-group-운동 후')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('apply-supplement-registration')));
    await tester.pumpAndSettle();

    expect(find.text('업로드한 멀티비타민'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('운동 후'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(find.text('운동 후'), findsOneWidget);
    expect(find.text('업로드한 멀티비타민'), findsWidgets);
  });

  testWidgets(
      'Supplement cards can rename and delete routine and registered entries',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-supplement')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('supplement-edit-morning-omega3')));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const Key('entry-edit-name')), '알티지 오메가-3');
    await tester.tap(find.text('수정'));
    await tester.pumpAndSettle();

    expect(find.text('알티지 오메가-3'), findsOneWidget);
    expect(find.text('오메가-3'), findsNothing);

    await tester.tap(
      find.byKey(const Key('supplement-delete-morning-pressure-med')),
    );
    await tester.pumpAndSettle();

    expect(find.text('혈압약 B'), findsNothing);
    expect(find.text('알티지 오메가-3'), findsOneWidget);

    await tester.tap(find.text('영양제 등록하기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('사진 업로드'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('target-group-아침')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('apply-supplement-registration')));
    await tester.pumpAndSettle();

    expect(find.text('업로드한 멀티비타민'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const Key('supplement-edit-registered-0')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('supplement-edit-registered-0')));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const Key('entry-edit-name')), '저녁 멀티비타민');
    await tester.tap(find.text('수정'));
    await tester.pumpAndSettle();

    expect(find.text('저녁 멀티비타민'), findsOneWidget);
    expect(find.text('업로드한 멀티비타민'), findsNothing);

    await tester.tap(find.byKey(const Key('supplement-delete-registered-0')));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView), const Offset(0, 900));
    await tester.pumpAndSettle();

    expect(find.text('저녁 멀티비타민'), findsNothing);
    expect(find.text('알티지 오메가-3'), findsOneWidget);
  });

  testWidgets('Supplement registration disables apply without target group',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-supplement')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('영양제 등록하기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('카메라로 찍기'));
    await tester.pumpAndSettle();

    final button = tester.widget<ElevatedButton>(
      find.byKey(const Key('apply-supplement-registration')),
    );

    expect(button.onPressed, isNull);
  });

  testWidgets('Diet check updates card status and analysis basis',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-diet')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('diet-toggle-morning')));
    await tester.pumpAndSettle();

    expect(find.text('먹었어요'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView), const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('오늘 진행 기준: 아침 식사 기록을 기준으로 분석합니다.'),
      findsOneWidget,
    );
    expect(find.textContaining('누적 메모리 기준:'), findsOneWidget);
  });

  testWidgets('Supplement check updates card status and analysis basis',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-supplement')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('supplement-toggle-morning-omega3')));
    await tester.pumpAndSettle();

    expect(find.text('복용 완료'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView), const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('오늘 진행 기준: 아침 영양제 기록을 기준으로 분석합니다.'),
      findsOneWidget,
    );
  });

  testWidgets('Combined analysis follows checked breakfast and supplement only',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.byKey(const Key('agent-card-diet')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('diet-toggle-morning')));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('agent-card-supplement')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('supplement-toggle-morning-omega3')));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView), const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('오늘 진행 기준: 아침 식사와 아침 영양제 기록을 기준으로 분석합니다.'),
      findsOneWidget,
    );
    expect(find.textContaining('점심 식사와 저녁 식사 기록'), findsNothing);
  });

  testWidgets('Analysis cumulative score uses gauge stage labels',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView), const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();

    expect(find.text('누적 점수'), findsOneWidget);
    expect(find.textContaining('주의'), findsWidgets);
    expect(find.textContaining('점검'), findsWidgets);
    expect(find.textContaining('보통'), findsWidgets);
    expect(find.textContaining('좋음'), findsWidgets);
    expect(find.textContaining('안정'), findsWidgets);
    expect(find.textContaining('0-19'), findsWidgets);
    expect(find.textContaining('20-39'), findsWidgets);
    expect(find.textContaining('40-59'), findsWidgets);
    expect(find.textContaining('60-79'), findsWidgets);
    expect(find.textContaining('80-100'), findsWidgets);
    expect(find.text('최근 7회'), findsNothing);
  });

  testWidgets('Analysis detail can move result to chat and add promise',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();

    expect(find.text('오늘 분석 점수'), findsOneWidget);
    expect(find.text('누적 점수'), findsOneWidget);
    expect(find.text('분석 결과'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const Key('analysis-add-promise')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('analysis-add-promise')));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView), const Offset(0, 900));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('분석 제안 약속'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('분석 제안 약속'), findsOneWidget);

    await tester.tap(find.byKey(const Key('promise-toggle-analysis-0')));
    await tester.pumpAndSettle();
    expect(find.byIcon(Icons.check_rounded), findsWidgets);

    await tester.scrollUntilVisible(
      find.byKey(const Key('agent-card-analysis')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agent-card-analysis')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('analysis-question-combined')),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('analysis-question-combined')));
    await tester.pumpAndSettle();

    expect(find.text('대화와 질문 사진만 관리합니다'), findsOneWidget);
    expect(find.textContaining('통합 분석'), findsWidgets);
  });

  testWidgets('Chat tab opens attachment sheet and shows temporary preview',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AgentChatCameraPrototype()),
    );

    await tester.tap(find.text('챗봇').last);
    await tester.pumpAndSettle();

    expect(find.text('대화와 질문 사진만 관리합니다'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.add_rounded));
    await tester.pumpAndSettle();

    expect(find.text('카메라로 찍기'), findsOneWidget);
    expect(find.text('사진 업로드'), findsOneWidget);

    await tester.tap(find.text('카메라로 찍기'));
    await tester.pumpAndSettle();

    expect(find.text('카메라 사진'), findsOneWidget);
    expect(find.text('질문에 첨부된 임시 사진'), findsOneWidget);
  });
}
