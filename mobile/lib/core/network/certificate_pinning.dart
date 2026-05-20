/// 인증서 핀닝 — Dio 의 ``IOHttpClientAdapter`` 에 부착할 SPKI 검증 콜백.
///
/// Brand-New-update 감사(2026-05-18) H3 (Certificate pinning) 대응 모듈.
///
/// 동작:
///   1. TLS 핸드셰이크에서 서버 leaf 인증서의 SubjectPublicKeyInfo (SPKI) DER 을 추출.
///   2. SHA-256 → Base64 변환.
///   3. ``Env.certificatePins`` 에 포함된 핀과 정확히 매칭되는지 확인.
///   4. 매칭되지 않으면 [logger] 로 사고 기록 후 ``false`` 반환 → 연결 거부.
///
/// 적용 범위:
///   - ``Env.pinnedHosts`` 가 비어 있지 않으면 그 목록만 핀셋.
///   - 비어 있으면 ``apiBaseUrl`` 의 host 만 핀셋.
///   - 로컬 dev (``localhost`` / ``127.0.0.1``) 는 핀셋 우회 (개발 편의).
///
/// Reference:
///   Brand-New-update/2026-05-18-high-findings-implementation-guideline.md (H3)
///   https://datatracker.ietf.org/doc/html/rfc7469 (HPKP, SPKI 핀 형식 원본)
library;

import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

import '../config/env.dart';

/// Dio 가 호출하는 ``badCertificateCallback`` 시그니처와 호환되는 검증 콜백.
///
/// [pins]:
///     ``Env.certificatePins`` 또는 테스트용 명시 목록.
/// [pinnedHosts]:
///     핀셋이 적용될 호스트(소문자). ``null`` / 비어있음 → ``apiBaseUrl`` 호스트만.
/// [exemptHosts]:
///     핀셋 우회 호스트 (dev / loopback). 기본값 ``{'localhost', '127.0.0.1'}``.
///
/// 반환값: 신뢰 가능한 인증서면 ``true``, 거부면 ``false``.
typedef CertificatePinValidator = bool Function(
  X509Certificate cert,
  String host,
  int port,
);

/// production / staging 환경에서 사용하기 위한 [CertificatePinValidator] 빌더.
///
/// Args:
///   pins: SPKI SHA-256 (Base64) 핀 목록. 비어있고 release 빌드면 ``StateError``.
///   pinnedHosts: 핀셋 적용 호스트 목록(소문자). 비어있으면 ``apiBaseUrl`` host 사용.
///   exemptHosts: 핀셋 우회 호스트 (dev 용).
///
/// Returns:
///   Dio 의 ``badCertificateCallback`` 으로 바로 넘길 수 있는 함수.
///
/// Throws:
///   StateError: release 빌드에서 핀이 비어 있는 경우.
CertificatePinValidator buildCertificatePinValidator({
  List<String>? pins,
  List<String>? pinnedHosts,
  Set<String> exemptHosts = const <String>{'localhost', '127.0.0.1'},
}) {
  final List<String> resolvedPins = pins ?? Env.certificatePins;
  final List<String> resolvedHosts = (pinnedHosts ?? Env.pinnedHosts).isNotEmpty
      ? (pinnedHosts ?? Env.pinnedHosts)
      : <String>[Uri.parse(Env.apiBaseUrl).host.toLowerCase()];

  if (resolvedPins.isEmpty && Env.isProduction) {
    throw StateError(
      'CERTIFICATE_PINS must be provided in production builds — '
      '운영 빌드는 SPKI 핀 미적용 상태로 출시될 수 없습니다.',
    );
  }

  return (X509Certificate cert, String host, int port) {
    final String hostLower = host.toLowerCase();
    if (exemptHosts.contains(hostLower)) {
      return true;
    }
    if (!resolvedHosts.contains(hostLower)) {
      // 핀셋 대상 호스트가 아니면 기본 동작(거부) — dio 는 false → 연결 차단.
      developer.log(
        'Untrusted host (not in pinnedHosts): $hostLower',
        name: 'certificate_pinning',
      );
      return false;
    }
    final String? actualPin = spkiSha256Base64(cert);
    if (actualPin == null) {
      developer.log(
        'Failed to compute SPKI pin for $hostLower',
        name: 'certificate_pinning',
      );
      return false;
    }
    final bool matched = resolvedPins.contains(actualPin);
    if (!matched) {
      developer.log(
        'Certificate pin mismatch: host=$hostLower actual=$actualPin',
        name: 'certificate_pinning',
      );
    }
    return matched;
  };
}

/// 단일 X509 인증서 → SubjectPublicKeyInfo 의 SHA-256 (Base64) 추출.
///
/// dart:io ``X509Certificate`` 는 SPKI 를 직접 노출하지 않지만 ``der`` 가 인증서
/// 전체 DER 을 제공한다. ASN.1 파싱으로 ``tbsCertificate.subjectPublicKeyInfo`` 의
/// SEQUENCE 를 추출한다.
///
/// Returns:
///   Base64(SHA-256(SPKI DER)). 파싱 실패 시 ``null``.
String? spkiSha256Base64(X509Certificate cert) {
  final Uint8List? spki = extractSubjectPublicKeyInfoDer(cert.der);
  if (spki == null) {
    return null;
  }
  return base64.encode(sha256.convert(spki).bytes);
}

/// DER-encoded X509 Certificate → SubjectPublicKeyInfo DER bytes 추출.
///
/// X509 Certificate ASN.1 구조 (RFC 5280):
///   Certificate ::= SEQUENCE {
///     tbsCertificate       TBSCertificate,
///     signatureAlgorithm   AlgorithmIdentifier,
///     signatureValue       BIT STRING
///   }
///   TBSCertificate ::= SEQUENCE {
///     [0]  EXPLICIT Version,             -- optional (v2/v3)
///     serialNumber         INTEGER,
///     signature            AlgorithmIdentifier,
///     issuer               Name,
///     validity             Validity,
///     subject              Name,
///     subjectPublicKeyInfo SubjectPublicKeyInfo,
///     ...
///   }
///
/// 따라서 SPKI 는 outer SEQUENCE → tbsCertificate (첫 SEQUENCE 자식) 안의
/// 일곱 번째 자식 (version 이 명시되면 인덱스 6, optional 이면 인덱스 5).
///
/// 가벼운 ASN.1 reader 로 추출. 파싱 실패 시 ``null``.
Uint8List? extractSubjectPublicKeyInfoDer(Uint8List derCertificate) {
  try {
    final _AsnReader outer = _AsnReader(derCertificate);
    final _AsnObject certSeq = outer.readSequence();
    final _AsnReader certReader = _AsnReader(certSeq.content);
    final _AsnObject tbs = certReader.readSequence();
    final _AsnReader tbsReader = _AsnReader(tbs.content);

    // [0] EXPLICIT Version (tag 0xA0) - optional
    final int? firstTag = tbsReader.peekTag();
    if (firstTag == null) {
      return null;
    }
    if (firstTag == 0xA0) {
      tbsReader.skip(); // version
    }
    tbsReader.skip(); // serialNumber (INTEGER)
    tbsReader.skip(); // signature (SEQUENCE)
    tbsReader.skip(); // issuer   (SEQUENCE)
    tbsReader.skip(); // validity (SEQUENCE)
    tbsReader.skip(); // subject  (SEQUENCE)

    // 다음 SEQUENCE 가 SubjectPublicKeyInfo. content 가 아닌 전체 TLV 가 필요.
    return tbsReader.readFullTlv();
  } catch (_) {
    return null;
  }
}

class _AsnObject {
  _AsnObject({required this.tag, required this.content, required this.full});
  final int tag;
  final Uint8List content;
  final Uint8List full;
}

class _AsnReader {
  _AsnReader(this._bytes);

  final Uint8List _bytes;
  int _pos = 0;

  int? peekTag() {
    if (_pos >= _bytes.length) {
      return null;
    }
    return _bytes[_pos];
  }

  _AsnObject _readObject() {
    final int start = _pos;
    if (_pos >= _bytes.length) {
      throw const FormatException('ASN.1: unexpected EOF (tag)');
    }
    final int tag = _bytes[_pos++];
    final int len = _readLength();
    if (_pos + len > _bytes.length) {
      throw const FormatException('ASN.1: length exceeds buffer');
    }
    final Uint8List content = Uint8List.sublistView(_bytes, _pos, _pos + len);
    final Uint8List full = Uint8List.sublistView(_bytes, start, _pos + len);
    _pos += len;
    return _AsnObject(tag: tag, content: content, full: full);
  }

  int _readLength() {
    if (_pos >= _bytes.length) {
      throw const FormatException('ASN.1: unexpected EOF (length)');
    }
    final int first = _bytes[_pos++];
    if ((first & 0x80) == 0) {
      return first;
    }
    final int nBytes = first & 0x7F;
    if (nBytes == 0 || nBytes > 4) {
      throw const FormatException('ASN.1: unsupported length form');
    }
    int len = 0;
    for (int i = 0; i < nBytes; i++) {
      len = (len << 8) | _bytes[_pos++];
    }
    return len;
  }

  _AsnObject readSequence() {
    final _AsnObject obj = _readObject();
    if (obj.tag != 0x30) {
      throw FormatException('ASN.1: expected SEQUENCE, got 0x${obj.tag.toRadixString(16)}');
    }
    return obj;
  }

  void skip() {
    _readObject();
  }

  Uint8List readFullTlv() {
    return _readObject().full;
  }
}
