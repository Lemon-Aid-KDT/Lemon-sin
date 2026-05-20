// utils/device_env.dart — 에뮬레이터 / 실기기 구분
//
// 용도:
//   - 카메라 화면에서 에뮬일 때 영상 보정(translate) 적용
//   - 실기기에서는 코드 변경 없이 자동으로 정상 cover
//
// Android: AndroidDeviceInfo.isPhysicalDevice
// iOS:     IosDeviceInfo.isPhysicalDevice
// (둘 다 false 면 에뮬레이터 / 시뮬레이터)
//
// 한 번 감지 후 캐시 — 매번 비동기 호출 막음.

import 'dart:io' show Platform;

import 'package:device_info_plus/device_info_plus.dart';

class DeviceEnv {
  static bool? _isEmulatorCache;

  /// 에뮬레이터 / 시뮬레이터 여부 (Android·iOS 통합)
  /// 첫 호출 후 캐시. 데스크톱/웹은 false 반환.
  static Future<bool> get isEmulator async {
    if (_isEmulatorCache != null) return _isEmulatorCache!;
    final info = DeviceInfoPlugin();
    try {
      if (Platform.isAndroid) {
        final a = await info.androidInfo;
        _isEmulatorCache = !a.isPhysicalDevice;
      } else if (Platform.isIOS) {
        final i = await info.iosInfo;
        _isEmulatorCache = !i.isPhysicalDevice;
      } else {
        _isEmulatorCache = false;
      }
    } catch (_) {
      _isEmulatorCache = false;
    }
    return _isEmulatorCache!;
  }

  /// 동기 접근 — initState 등에서 캐시값만 읽을 때.
  /// 아직 미감지면 false 반환 (안전 기본값).
  static bool get isEmulatorSync => _isEmulatorCache ?? false;

  /// 부트 단계에서 한 번 호출하면 이후 동기 접근 가능.
  static Future<void> warmUp() => isEmulator;
}
