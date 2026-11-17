import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:eva_desktop/main.dart';

void main() {
  testWidgets('EVA Desktop Shell smoke test', (WidgetTester tester) async {
    // Configure simulated desktop monitor resolution
    tester.view.physicalSize = const Size(1440, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const EvaOSApp());
    await tester.pumpAndSettle();

    // If sidebar is collapsed (persisted from user settings), expand it for test assertions
    final expandBtn = find.byIcon(Icons.keyboard_double_arrow_right_rounded);
    if (expandBtn.evaluate().isNotEmpty) {
      await tester.tap(expandBtn);
      await tester.pumpAndSettle();
    }

    // Verify EVA branding is rendered
    expect(find.text('EVA AI OS'), findsWidgets);
    expect(find.text('Home'), findsWidgets);
    expect(find.text('EVA Assistant'), findsWidgets);
    expect(find.text('Applications'), findsWidgets);
    expect(find.text('File Explorer'), findsWidgets);
    expect(find.text('Memory'), findsWidgets);
    expect(find.text('Task Manager'), findsWidgets);
    expect(find.text('System Monitor'), findsWidgets);
    expect(find.text('Settings'), findsWidgets);
  });
}
