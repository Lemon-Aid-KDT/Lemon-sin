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

  test(
    'Android manifest declares camera without broad gallery permissions',
    () {
      final String manifest = File(
        'android/app/src/main/AndroidManifest.xml',
      ).readAsStringSync();

      expect(manifest, contains('android:name="android.permission.CAMERA"'));
      expect(manifest, contains('android:name="android.hardware.camera"'));
      expect(manifest, contains('android:required="false"'));
      expect(
        manifest,
        isNot(contains('android.permission.READ_EXTERNAL_STORAGE')),
      );
      expect(manifest, isNot(contains('android.permission.READ_MEDIA_IMAGES')));
    },
  );

  test('Android release activity is not under com.example package', () {
    final String manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    final bool oldExampleActivity = File(
      'android/app/src/main/kotlin/com/example/lemon_aid_mobile/MainActivity.kt',
    ).existsSync();
    final bool productionActivity = File(
      'android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt',
    ).existsSync();

    expect(manifest, contains('com.lemonaid.mobile.MainActivity'));
    expect(oldExampleActivity, isFalse);
    expect(productionActivity, isTrue);
  });

  test('Android activity handles camera permission before picker intent', () {
    final String activity = File(
      'android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt',
    ).readAsStringSync();

    expect(activity, contains('com.lemonaid.mobile/camera_permission'));
    expect(activity, contains('requestCameraPermission'));
    expect(activity, contains('Manifest.permission.CAMERA'));
    expect(activity, contains('requestPermissions'));
    expect(activity, contains('onRequestPermissionsResult'));
  });

  test('Android activity verifies certificate pins before API traffic', () {
    final String activity = File(
      'android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt',
    ).readAsStringSync();

    expect(activity, contains('com.lemonaid.mobile/certificate_pins'));
    expect(activity, contains('verifyServerPins'));
    expect(activity, contains('SSLSocketFactory'));
    expect(activity, contains('HttpsURLConnection'));
    expect(activity, contains('getDefaultHostnameVerifier()'));
    expect(activity, contains('MessageDigest.getInstance("SHA-256")'));
    expect(activity, contains('X509Certificate'));
    expect(activity, contains('certificate_hostname_mismatch'));
    expect(activity, contains('certificate_pin_mismatch'));
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

  test('iOS declares camera and photo library OCR purpose strings', () {
    final String infoPlist = File('ios/Runner/Info.plist').readAsStringSync();

    expect(infoPlist, contains('<key>NSCameraUsageDescription</key>'));
    expect(infoPlist, contains('supplement label OCR previews'));
    expect(infoPlist, contains('<key>NSPhotoLibraryUsageDescription</key>'));
    expect(infoPlist, contains('selected supplement label images'));
  });

  test('iOS activity requests camera permission before picker flow', () {
    final String appDelegate = File(
      'ios/Runner/AppDelegate.swift',
    ).readAsStringSync();

    expect(appDelegate, contains('import AVFoundation'));
    expect(appDelegate, contains('com.lemonaid.mobile/camera_permission'));
    expect(appDelegate, contains('authorizationStatus(for: .video)'));
    expect(appDelegate, contains('requestAccess(for: .video)'));
    expect(appDelegate, contains('case .restricted'));
    expect(appDelegate, contains('case .denied'));
  });

  test('iOS app delegate verifies certificate pins before API traffic', () {
    final String appDelegate = File(
      'ios/Runner/AppDelegate.swift',
    ).readAsStringSync();

    expect(appDelegate, contains('import CryptoKit'));
    expect(appDelegate, contains('com.lemonaid.mobile/certificate_pins'));
    expect(appDelegate, contains('verifyServerPins'));
    expect(appDelegate, contains('SecPolicyCreateSSL(true'));
    expect(appDelegate, contains('SecTrustSetPolicies'));
    expect(appDelegate, contains('SecTrustEvaluateWithError'));
    expect(appDelegate, contains('SecCertificateCopyData'));
    expect(appDelegate, contains('SHA256.hash'));
    expect(appDelegate, contains('certificate_trust_evaluation_failed'));
    expect(appDelegate, contains('certificate_pin_mismatch'));
  });
}
