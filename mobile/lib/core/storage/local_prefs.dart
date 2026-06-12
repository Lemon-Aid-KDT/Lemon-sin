// core/storage/local_prefs.dart — 로컬 영속 래퍼 (shared_preferences)
//
// 화면·컨트롤러가 SharedPreferences 를 직접 만지지 않도록 얇게 감싼다.
// 테스트는 SharedPreferences.setMockInitialValues({...}) 로 초기값을 주입한 뒤
// LocalPrefs.create() 로 동일 인스턴스를 얻어 라운드트립을 검증한다.
//
// 영속 대상(가이드 02 (e) · SoT §9.5):
//   - 날짜별 영양제/복약 체크 상태 (자정 지나면 새 날짜 키로 자동 초기화).
//   - 사용자 선택 브랜드 테마.
//
// 키 설계 (날짜는 로컬 타임존 기준 yyyy-MM-dd):
//   home.supplement.checked.<yyyy-MM-dd>  → 체크된 supplement id 리스트
//   home.medication.checked.<yyyy-MM-dd>  → 체크된 medication id 리스트
//   brand.theme                           → 선택 브랜드 테마 코드

import 'package:shared_preferences/shared_preferences.dart';

/// 일별 체크 상태와 테마 선택을 영속하는 얇은 래퍼.
///
/// 모든 메서드는 동기 캐시(`SharedPreferences`)를 사용하므로 빠르게 동작한다.
class LocalPrefs {
  /// 미리 로드된 [SharedPreferences] 인스턴스로 래퍼를 만든다.
  const LocalPrefs(this._prefs);

  final SharedPreferences _prefs;

  static const String _supplementCheckedPrefix = 'home.supplement.checked.';
  static const String _medicationCheckedPrefix = 'home.medication.checked.';
  static const String _brandThemeKey = 'brand.theme';

  /// `SharedPreferences.getInstance()` 를 기다린 뒤 래퍼를 만든다.
  ///
  /// 테스트에서는 호출 전에 `SharedPreferences.setMockInitialValues({...})`
  /// 로 초기값을 주입할 수 있다.
  static Future<LocalPrefs> create() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    return LocalPrefs(prefs);
  }

  /// 로컬 [day] 를 `yyyy-MM-dd` 문자열로 만든다 (체크 키의 날짜 부분).
  static String dateKey(DateTime day) {
    final String month = day.month.toString().padLeft(2, '0');
    final String dayOfMonth = day.day.toString().padLeft(2, '0');
    return '${day.year}-$month-$dayOfMonth';
  }

  // ── 영양제 체크 ────────────────────────────────

  /// [day] 에 체크된 영양제 id 집합을 읽는다 (없으면 빈 집합).
  Set<String> supplementCheckedIds(DateTime day) {
    return _readIdSet('$_supplementCheckedPrefix${dateKey(day)}');
  }

  /// [day] 의 체크된 영양제 id 집합을 저장한다.
  Future<void> setSupplementCheckedIds(DateTime day, Set<String> ids) {
    return _writeIdSet('$_supplementCheckedPrefix${dateKey(day)}', ids);
  }

  // ── 복약 체크 ─────────────────────────────────

  /// [day] 에 체크된 복약 id 집합을 읽는다 (없으면 빈 집합).
  Set<String> medicationCheckedIds(DateTime day) {
    return _readIdSet('$_medicationCheckedPrefix${dateKey(day)}');
  }

  /// [day] 의 체크된 복약 id 집합을 저장한다.
  Future<void> setMedicationCheckedIds(DateTime day, Set<String> ids) {
    return _writeIdSet('$_medicationCheckedPrefix${dateKey(day)}', ids);
  }

  // ── 브랜드 테마 ────────────────────────────────

  /// 저장된 브랜드 테마 코드 (없으면 null).
  String? brandThemeCode() {
    final String? value = _prefs.getString(_brandThemeKey);
    if (value == null || value.trim().isEmpty) return null;
    return value;
  }

  /// 브랜드 테마 코드를 저장한다.
  Future<void> setBrandThemeCode(String code) {
    return _prefs.setString(_brandThemeKey, code);
  }

  // ── 내부 헬퍼 ─────────────────────────────────

  Set<String> _readIdSet(String key) {
    final List<String>? raw = _prefs.getStringList(key);
    if (raw == null) return <String>{};
    return raw.where((String id) => id.trim().isNotEmpty).toSet();
  }

  Future<void> _writeIdSet(String key, Set<String> ids) {
    if (ids.isEmpty) {
      return _prefs.remove(key);
    }
    return _prefs.setStringList(key, ids.toList(growable: false));
  }
}
