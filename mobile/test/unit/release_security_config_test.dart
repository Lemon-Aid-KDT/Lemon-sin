import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Android release manifest references network security config', () {
    final String manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();

    expect(
      manifest,
      contains('android:networkSecurityConfig="@xml/network_security_config"'),
    );
  });

  test('Android network security config blocks cleartext traffic', () {
    final String networkSecurityConfig = File(
      'android/app/src/main/res/xml/network_security_config.xml',
    ).readAsStringSync();

    expect(
      networkSecurityConfig,
      contains('<base-config cleartextTrafficPermitted="false">'),
    );
    expect(
      networkSecurityConfig,
      isNot(contains('cleartextTrafficPermitted="true"')),
    );
  });

  test('iOS ATS explicitly keeps arbitrary loads disabled', () {
    final String infoPlist = File('ios/Runner/Info.plist').readAsStringSync();
    final int atsIndex = infoPlist.indexOf('<key>NSAppTransportSecurity</key>');
    final int arbitraryLoadsIndex = infoPlist.indexOf(
      '<key>NSAllowsArbitraryLoads</key>',
    );
    final int falseIndex = infoPlist.indexOf('<false/>', arbitraryLoadsIndex);

    expect(atsIndex, isNonNegative);
    expect(arbitraryLoadsIndex, greaterThan(atsIndex));
    expect(falseIndex, greaterThan(arbitraryLoadsIndex));
  });
}
