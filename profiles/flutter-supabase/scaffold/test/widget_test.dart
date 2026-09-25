import 'package:flutter_test/flutter_test.dart';
import 'package:{{SLUG_SNAKE}}/app/app.dart';

void main() {
  testWidgets('يبني التطبيق دون أخطاء', (tester) async {
    await tester.pumpWidget(const {{CLASS_NAME}}App());
    expect(find.byType({{CLASS_NAME}}App), findsOneWidget);
  });
}
