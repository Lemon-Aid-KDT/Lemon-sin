import 'package:flutter/material.dart';

class MedicalDisclaimer extends StatelessWidget {
  const MedicalDisclaimer({super.key});

  static const String copy =
      '본 서비스의 정보는 건강 관리를 위한 참고 자료이며, 의사 또는 약사의 진단과 처방을 대체하지 않습니다.';

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: const Padding(
        padding: EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(Icons.info_outline, size: 20),
            SizedBox(width: 8),
            Expanded(child: Text(copy)),
          ],
        ),
      ),
    );
  }
}
