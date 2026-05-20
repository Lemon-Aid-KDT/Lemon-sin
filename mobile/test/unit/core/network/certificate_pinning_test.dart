/// ``certificate_pinning`` 단위 테스트 — Brand-New-update 감사 H3 대응 검증.
///
/// SPKI 추출 / 핀 매칭 / 호스트 화이트리스트 / 운영 빌드 안전장치 등을 검증한다.
library;

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_healthcare/core/network/certificate_pinning.dart';

/// 테스트용 X509Certificate 더블.
///
/// dart:io ``X509Certificate`` 는 final class 가 아니므로 implements 가능.
class _FakeX509Certificate implements X509Certificate {
  _FakeX509Certificate(this.derBytes);

  final Uint8List derBytes;

  @override
  Uint8List get der => derBytes;

  @override
  String get subject => 'CN=Test';

  @override
  String get issuer => 'CN=TestIssuer';

  @override
  DateTime get startValidity => DateTime(2024);

  @override
  DateTime get endValidity => DateTime(2030);

  @override
  String get pem => '-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----';

  @override
  Uint8List get sha1 => Uint8List(20);
}

/// 최소 X509 Certificate DER 생성기.
///
/// SubjectPublicKeyInfo 의 형태를 매우 단순한 SEQUENCE 로 두고, 그것의 SHA-256
/// 을 우리가 사전에 계산할 수 있도록 한다. ASN.1 헤더는 직접 조립한다.
({Uint8List der, String expectedSpkiPin}) _buildTestCertificate({
  required List<int> publicKeyContent,
}) {
  // SPKI: SEQUENCE { content }
  final Uint8List spkiContent = Uint8List.fromList(publicKeyContent);
  final Uint8List spki = _encodeSequence(spkiContent);

  // TBSCertificate: 7개의 더미 필드 + spki 가 필요.
  //   version[0] OPTIONAL — 생략 (v1)
  //   serial(INTEGER) → INTEGER 0
  //   signature(SEQ)   → SEQ empty
  //   issuer(SEQ)      → SEQ empty
  //   validity(SEQ)    → SEQ empty
  //   subject(SEQ)     → SEQ empty
  //   subjectPublicKeyInfo → spki
  final List<int> tbsContent = <int>[
    ..._encodeInteger(0),
    ..._encodeSequence(Uint8List(0)),
    ..._encodeSequence(Uint8List(0)),
    ..._encodeSequence(Uint8List(0)),
    ..._encodeSequence(Uint8List(0)),
    ...spki,
  ];
  final Uint8List tbs = _encodeSequence(Uint8List.fromList(tbsContent));

  // Certificate: SEQ { tbs, sigAlgo (SEQ empty), sigValue (BITSTRING empty) }
  final List<int> certContent = <int>[
    ...tbs,
    ..._encodeSequence(Uint8List(0)),
    ..._encodeBitString(Uint8List(0)),
  ];
  final Uint8List cert = _encodeSequence(Uint8List.fromList(certContent));

  final String pin = base64.encode(sha256.convert(spki).bytes);
  return (der: cert, expectedSpkiPin: pin);
}

Uint8List _encodeSequence(Uint8List content) {
  return Uint8List.fromList(<int>[0x30, ..._encodeLength(content.length), ...content]);
}

Uint8List _encodeInteger(int value) {
  return Uint8List.fromList(<int>[0x02, 0x01, value]);
}

Uint8List _encodeBitString(Uint8List content) {
  // BIT STRING: tag 0x03, length, 1 byte unused-bits prefix, content.
  final List<int> body = <int>[0x00, ...content];
  return Uint8List.fromList(<int>[0x03, ..._encodeLength(body.length), ...body]);
}

List<int> _encodeLength(int len) {
  if (len < 128) {
    return <int>[len];
  }
  final List<int> bytes = <int>[];
  int v = len;
  while (v > 0) {
    bytes.insert(0, v & 0xFF);
    v >>= 8;
  }
  return <int>[0x80 | bytes.length, ...bytes];
}

void main() {
  group('extractSubjectPublicKeyInfoDer', () {
    test('returns null for invalid DER', () {
      final Uint8List bad = Uint8List.fromList(<int>[0xFF, 0xFF, 0xFF]);
      expect(extractSubjectPublicKeyInfoDer(bad), isNull);
    });

    test('extracts SPKI from minimal cert', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[1, 2, 3, 4, 5]);

      final Uint8List? spki = extractSubjectPublicKeyInfoDer(c.der);
      expect(spki, isNotNull);
    });
  });

  group('spkiSha256Base64', () {
    test('computes expected pin from minimal cert', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[10, 20, 30]);

      final _FakeX509Certificate cert = _FakeX509Certificate(c.der);
      final String? pin = spkiSha256Base64(cert);
      expect(pin, equals(c.expectedSpkiPin));
    });

    test('returns null for non-cert bytes', () {
      final _FakeX509Certificate cert =
          _FakeX509Certificate(Uint8List.fromList(<int>[0x01, 0x02, 0x03]));
      expect(spkiSha256Base64(cert), isNull);
    });
  });

  group('buildCertificatePinValidator', () {
    test('accepts cert whose SPKI matches a pinned value', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[7, 8, 9]);
      final CertificatePinValidator validate = buildCertificatePinValidator(
        pins: <String>[c.expectedSpkiPin],
        pinnedHosts: <String>['api.example.com'],
      );
      expect(
        validate(_FakeX509Certificate(c.der), 'api.example.com', 443),
        isTrue,
      );
    });

    test('rejects cert whose SPKI does not match', () {
      final ({Uint8List der, String expectedSpkiPin}) actual =
          _buildTestCertificate(publicKeyContent: <int>[1, 2, 3]);
      const String wrongPin = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';
      final CertificatePinValidator validate = buildCertificatePinValidator(
        pins: <String>[wrongPin],
        pinnedHosts: <String>['api.example.com'],
      );
      expect(
        validate(_FakeX509Certificate(actual.der), 'api.example.com', 443),
        isFalse,
      );
    });

    test('rejects connection to host not in pinnedHosts whitelist', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[1]);
      final CertificatePinValidator validate = buildCertificatePinValidator(
        pins: <String>[c.expectedSpkiPin],
        pinnedHosts: <String>['api.example.com'],
      );
      expect(
        validate(_FakeX509Certificate(c.der), 'evil.example.com', 443),
        isFalse,
      );
    });

    test('exempts localhost and 127.0.0.1 by default', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[1]);
      // 핀 미매칭 cert 라도 exempt 호스트는 통과.
      const String wrongPin = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';
      final CertificatePinValidator validate = buildCertificatePinValidator(
        pins: <String>[wrongPin],
        pinnedHosts: <String>['api.example.com'],
      );
      expect(
        validate(_FakeX509Certificate(c.der), 'localhost', 443),
        isTrue,
      );
      expect(
        validate(_FakeX509Certificate(c.der), '127.0.0.1', 443),
        isTrue,
      );
    });

    test('is case-insensitive for host matching', () {
      final ({Uint8List der, String expectedSpkiPin}) c =
          _buildTestCertificate(publicKeyContent: <int>[1, 2]);
      final CertificatePinValidator validate = buildCertificatePinValidator(
        pins: <String>[c.expectedSpkiPin],
        pinnedHosts: <String>['api.example.com'],
      );
      expect(
        validate(_FakeX509Certificate(c.der), 'API.example.COM', 443),
        isTrue,
      );
    });
  });
}
