// PROTOTYPE - throwaway UI.
// Agent routine and chatbot are split into two bottom tabs.
// No persistence, no backend, no real camera, no LLM/API calls.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:math' as math;

import '../utils/design_tokens_v2.dart';

class AgentChatCameraPrototype extends StatefulWidget {
  const AgentChatCameraPrototype({super.key});

  @override
  State<AgentChatCameraPrototype> createState() =>
      _AgentChatCameraPrototypeState();
}

class _AgentChatCameraPrototypeState extends State<AgentChatCameraPrototype> {
  _PrototypeTab _tab = _PrototypeTab.agent;
  _AgentView _agentView = _AgentView.home;
  _AttachmentKind _attachment = _AttachmentKind.none;
  _AnalysisResult? _forwardedAnalysis;
  final List<_DietEntry> _dietEntries = [
    for (final slot in _MealSlot.values)
      _DietEntry(
        id: slot.name,
        name: slot.label,
        subtitle: '어떤 음식 드셨나요?',
        chip: '안 먹었어요',
        icon: slot.icon,
      ),
  ];
  final List<_RoutineItem> _routineEntries = [..._defaultRoutineItems];
  final List<_RegisteredSupplement> _registeredSupplements = [];
  final List<String> _addedPromiseDirections = [];
  final Set<String> _checkedDietEntryIds = {};
  final Set<String> _checkedSupplementEntryIds = {};
  final Set<String> _checkedPromiseIds = {};
  int _nextCustomDietEntryId = 0;
  int _nextRegisteredSupplementId = 0;

  void _setTab(_PrototypeTab tab) {
    HapticFeedback.selectionClick();
    setState(() => _tab = tab);
  }

  void _openAgentView(_AgentView view) {
    HapticFeedback.selectionClick();
    setState(() => _agentView = view);
  }

  void _backToAgentHome() {
    HapticFeedback.selectionClick();
    setState(() => _agentView = _AgentView.home);
  }

  void _askAboutAnalysis(_AnalysisResult analysis) {
    HapticFeedback.selectionClick();
    setState(() {
      _forwardedAnalysis = analysis;
      _tab = _PrototypeTab.chat;
    });
  }

  Future<void> _showAttachmentSheet() async {
    HapticFeedback.mediumImpact();
    final selected = await showModalBottomSheet<_AttachmentKind>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => const _AttachmentActionSheet(),
    );
    if (selected == null || !mounted) return;
    setState(() => _attachment = selected);
  }

  void _clearAttachment() {
    HapticFeedback.selectionClick();
    setState(() => _attachment = _AttachmentKind.none);
  }

  Future<void> _showRecordPhotoSheet(_AgentView view) async {
    HapticFeedback.mediumImpact();
    final selected = await showModalBottomSheet<_AttachmentKind>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => const _AttachmentActionSheet(),
    );
    if (selected == null || !mounted) return;
    if (view != _AgentView.supplement) return;
    final registered = await showModalBottomSheet<List<_RegisteredSupplement>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _SupplementRegistrationSheet(
        attachment: selected,
        targetLabels: _defaultSupplementTargetLabels,
      ),
    );
    if (registered == null || registered.isEmpty || !mounted) return;
    setState(() {
      _registeredSupplements.addAll([
        for (final supplement in registered)
          supplement.copyWith(
            id: 'registered-${_nextRegisteredSupplementId++}',
          ),
      ]);
    });
  }

  Future<void> _showCustomEntryDialog(_AgentView view) async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColor.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        title: Text(
          view == _AgentView.diet ? '식사 이름 설정' : '영양제 이름 설정',
          style: AppText.subtitle.copyWith(letterSpacing: 0),
        ),
        content: TextField(
          key: const Key('custom-entry-name'),
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            hintText: view == _AgentView.diet ? '예: 야식' : '예: 유산균',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('추가'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty || !mounted) return;
    if (view != _AgentView.diet) return;
    setState(() {
      _dietEntries.add(
        _DietEntry(
          id: 'custom-${_nextCustomDietEntryId++}',
          name: name,
          subtitle: '사용자가 추가한 식사',
          chip: '기록 대기',
          icon: Icons.restaurant_menu_rounded,
        ),
      );
    });
  }

  Future<String?> _showEntryEditDialog(String initialName) async {
    final controller = TextEditingController(text: initialName);
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColor.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        title: Text(
          '이름 수정',
          style: AppText.subtitle.copyWith(letterSpacing: 0),
        ),
        content: TextField(
          key: const Key('entry-edit-name'),
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: '이름을 입력하세요'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('수정'),
          ),
        ],
      ),
    );
  }

  Future<void> _renameDietEntry(String id) async {
    final index = _dietEntries.indexWhere((entry) => entry.id == id);
    if (index == -1) return;
    final name = await _showEntryEditDialog(_dietEntries[index].name);
    if (name == null || name.isEmpty || !mounted) return;
    setState(() {
      _dietEntries[index] = _dietEntries[index].copyWith(name: name);
    });
  }

  void _deleteDietEntry(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      _dietEntries.removeWhere((entry) => entry.id == id);
      _checkedDietEntryIds.remove(id);
    });
  }

  Future<void> _renameRoutineItem(String id) async {
    final index = _routineEntries.indexWhere((item) => item.id == id);
    if (index == -1) return;
    final name = await _showEntryEditDialog(_routineEntries[index].name);
    if (name == null || name.isEmpty || !mounted) return;
    setState(() {
      _routineEntries[index] = _routineEntries[index].copyWith(name: name);
    });
  }

  void _deleteRoutineItem(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      _routineEntries.removeWhere((item) => item.id == id);
      _checkedSupplementEntryIds.remove(id);
    });
  }

  Future<void> _renameRegisteredSupplement(String id) async {
    final index = _registeredSupplements.indexWhere(
      (supplement) => supplement.id == id,
    );
    if (index == -1) return;
    final name = await _showEntryEditDialog(_registeredSupplements[index].name);
    if (name == null || name.isEmpty || !mounted) return;
    setState(() {
      _registeredSupplements[index] = _registeredSupplements[index].copyWith(
        name: name,
      );
    });
  }

  void _deleteRegisteredSupplement(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      _registeredSupplements.removeWhere((supplement) => supplement.id == id);
      _checkedSupplementEntryIds.remove(id);
    });
  }

  void _toggleDietEntry(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      if (!_checkedDietEntryIds.add(id)) {
        _checkedDietEntryIds.remove(id);
      }
    });
  }

  void _toggleSupplementEntry(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      if (!_checkedSupplementEntryIds.add(id)) {
        _checkedSupplementEntryIds.remove(id);
      }
    });
  }

  void _togglePromise(String id) {
    HapticFeedback.selectionClick();
    setState(() {
      if (!_checkedPromiseIds.add(id)) {
        _checkedPromiseIds.remove(id);
      }
    });
  }

  void _addPromiseFromAnalysis(_AnalysisResult analysis) {
    HapticFeedback.selectionClick();
    final direction = analysis.promiseDirection;
    setState(() {
      if (!_addedPromiseDirections.contains(direction)) {
        _addedPromiseDirections.add(direction);
      }
    });
  }

  _AnalysisResult _buildCombinedAnalysis() {
    final checkedBasis = _checkedTodayBasis();
    final todayText = checkedBasis.isEmpty
        ? '오늘 진행 기준: 오늘 체크된 식단/영양제가 아직 없습니다.'
        : '오늘 진행 기준: ${_joinKorean(checkedBasis)} 기록을 기준으로 분석합니다.';
    const memoryText =
        '누적 메모리 기준: 최근 기록에서는 아침 루틴은 안정적이고 점심/저녁 기록은 비어 있는 날이 많습니다.';
    final checkedCount =
        _checkedDietEntryIds.length + _checkedSupplementEntryIds.length;

    return _AnalysisResult(
      id: 'combined',
      title: '통합 분석',
      description: '오늘 체크한 식단과 영양제를 함께 본 결과입니다.',
      resultText: '$todayText\n$memoryText',
      practiceDirection: checkedBasis.isEmpty
          ? '먼저 오늘 완료한 식사나 복용 항목을 체크해 주세요.'
          : '체크한 항목은 유지하고 비어 있는 점심/저녁 루틴은 다음 기록에서 확인해 보세요.',
      promiseDirection: '분석 기준에 맞춰 오늘 체크한 식사와 복용 루틴 이어가기',
      icon: Icons.insights_rounded,
      iconColor: AppColor.brand,
      metrics: [
        _AnalysisMetric(
          icon: Icons.fact_check_rounded,
          label: '오늘 기준',
          value: checkedCount == 0 ? '체크 없음' : '$checkedCount개 체크',
        ),
        const _AnalysisMetric(
          icon: Icons.history_rounded,
          label: '누적 기준',
          value: '아침 안정',
        ),
      ],
    );
  }

  List<String> _checkedTodayBasis() {
    final labels = <String>{};
    for (final entry in _dietEntries) {
      if (_checkedDietEntryIds.contains(entry.id)) {
        labels.add(_dietBasisLabel(entry));
      }
    }
    for (final item in _routineEntries) {
      if (_checkedSupplementEntryIds.contains(item.id)) {
        labels.add(_routineBasisLabel(item));
      }
    }
    for (final supplement in _registeredSupplements) {
      if (_checkedSupplementEntryIds.contains(supplement.id)) {
        labels.add('${supplement.groupLabel} 영양제');
      }
    }
    return labels.toList();
  }

  String _dietBasisLabel(_DietEntry entry) {
    if (entry.name.endsWith('식사')) return entry.name;
    return '${entry.name} 식사';
  }

  String _routineBasisLabel(_RoutineItem item) {
    final kindLabel = item.kind == _RoutineKind.supplement ? '영양제' : '복용약';
    return '${item.slot.label} $kindLabel';
  }

  String _joinKorean(List<String> items) {
    if (items.isEmpty) return '';
    if (items.length == 1) return items.first;
    if (items.length == 2) return '${items.first}와 ${items.last}';
    return '${items.sublist(0, items.length - 1).join(', ')}와 ${items.last}';
  }

  @override
  Widget build(BuildContext context) {
    final combinedAnalysis = _buildCombinedAnalysis();
    return Scaffold(
      backgroundColor: const Color(0xFF101216),
      body: _PhonePrototypeFrame(
        child: _PrototypeShell(
          currentTab: _tab,
          onTabChanged: _setTab,
          child: _tab == _PrototypeTab.agent
              ? _AgentExperienceTab(
                  view: _agentView,
                  dietEntries: _dietEntries,
                  routineEntries: _routineEntries,
                  registeredSupplements: _registeredSupplements,
                  addedPromiseDirections: _addedPromiseDirections,
                  checkedDietEntryIds: _checkedDietEntryIds,
                  checkedSupplementEntryIds: _checkedSupplementEntryIds,
                  checkedPromiseIds: _checkedPromiseIds,
                  analysis: combinedAnalysis,
                  onOpenView: _openAgentView,
                  onBack: _backToAgentHome,
                  onRecordPhoto: _showRecordPhotoSheet,
                  onAddCustomEntry: _showCustomEntryDialog,
                  onToggleDietEntry: _toggleDietEntry,
                  onToggleSupplementEntry: _toggleSupplementEntry,
                  onTogglePromise: _togglePromise,
                  onRenameDietEntry: _renameDietEntry,
                  onDeleteDietEntry: _deleteDietEntry,
                  onRenameRoutineItem: _renameRoutineItem,
                  onDeleteRoutineItem: _deleteRoutineItem,
                  onRenameRegisteredSupplement: _renameRegisteredSupplement,
                  onDeleteRegisteredSupplement: _deleteRegisteredSupplement,
                  onAnalysisQuestion: _askAboutAnalysis,
                  onAddPromise: _addPromiseFromAnalysis,
                )
              : _ChatbotTab(
                  attachment: _attachment,
                  forwardedAnalysis: _forwardedAnalysis,
                  onAddPressed: _showAttachmentSheet,
                  onClearAttachment: _clearAttachment,
                ),
        ),
      ),
    );
  }
}

class _PhonePrototypeFrame extends StatelessWidget {
  final Widget child;

  const _PhonePrototypeFrame({required this.child});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 560;
        final phone = ClipRRect(
          borderRadius: BorderRadius.circular(isWide ? 36 : 0),
          child: DecoratedBox(
            decoration: const BoxDecoration(color: AppColor.section),
            child: child,
          ),
        );
        if (!isWide) return phone;
        return Center(
          child: Container(
            width: 430,
            height: constraints.maxHeight.clamp(720, 932).toDouble(),
            decoration: BoxDecoration(
              color: AppColor.section,
              borderRadius: BorderRadius.circular(36),
              border: Border.all(color: const Color(0xFF3B3F46), width: 10),
              boxShadow: const [
                BoxShadow(
                  color: Color.fromRGBO(0, 0, 0, 0.45),
                  blurRadius: 40,
                  offset: Offset(0, 18),
                ),
              ],
            ),
            clipBehavior: Clip.antiAlias,
            child: phone,
          ),
        );
      },
    );
  }
}

class _PrototypeShell extends StatelessWidget {
  final _PrototypeTab currentTab;
  final ValueChanged<_PrototypeTab> onTabChanged;
  final Widget child;

  const _PrototypeShell({
    required this.currentTab,
    required this.onTabChanged,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Column(
        children: [
          Expanded(child: child),
          _BottomTabs(currentTab: currentTab, onTabChanged: onTabChanged),
        ],
      ),
    );
  }
}

enum _PrototypeTab {
  agent('Agent', Icons.auto_awesome_rounded),
  chat('챗봇', Icons.chat_bubble_rounded);

  final String label;
  final IconData icon;
  const _PrototypeTab(this.label, this.icon);
}

enum _MealSlot {
  morning('아침', '08:00', Icons.wb_sunny_rounded),
  lunch('점심', '12:30', Icons.light_mode_rounded),
  dinner('저녁', '19:00', Icons.nightlight_round);

  final String label;
  final String time;
  final IconData icon;
  const _MealSlot(this.label, this.time, this.icon);
}

enum _AgentView { home, diet, supplement, analysis }

enum _RoutineKind {
  medicine('복용약', AppColor.info, AppColor.infoSoft),
  supplement('영양제', AppColor.success, AppColor.successSoft);

  final String label;
  final Color color;
  final Color softColor;
  const _RoutineKind(this.label, this.color, this.softColor);
}

enum _AttachmentKind {
  none('', Icons.image_not_supported_rounded),
  camera('카메라 사진', Icons.photo_camera_rounded),
  upload('업로드 사진', Icons.photo_library_rounded);

  final String label;
  final IconData icon;
  const _AttachmentKind(this.label, this.icon);
}

const _mockSupplementImageAsset = 'assets/mock/supplement-label.png';
const _defaultSupplementTargetLabels = ['아침', '점심', '저녁'];

class _DietEntry {
  final String id;
  final String name;
  final String subtitle;
  final String chip;
  final IconData icon;

  const _DietEntry({
    required this.id,
    required this.name,
    required this.subtitle,
    required this.chip,
    required this.icon,
  });

  _DietEntry copyWith({String? name}) {
    return _DietEntry(
      id: id,
      name: name ?? this.name,
      subtitle: subtitle,
      chip: chip,
      icon: icon,
    );
  }
}

class _RegisteredSupplement {
  final String id;
  final String name;
  final String groupLabel;
  final String methodLabel;
  final _RoutineKind kind;

  const _RegisteredSupplement({
    this.id = '',
    required this.name,
    required this.groupLabel,
    required this.methodLabel,
    required this.kind,
  });

  _RegisteredSupplement copyWith({String? id, String? name}) {
    return _RegisteredSupplement(
      id: id ?? this.id,
      name: name ?? this.name,
      groupLabel: groupLabel,
      methodLabel: methodLabel,
      kind: kind,
    );
  }

  static String mockNameFor(_AttachmentKind attachment) => switch (attachment) {
    _AttachmentKind.camera => '카메라로 등록한 오메가-3',
    _AttachmentKind.upload => '업로드한 멀티비타민',
    _AttachmentKind.none => '등록 대기 영양제',
  };

  static String methodLabelFor(_AttachmentKind attachment) =>
      switch (attachment) {
        _AttachmentKind.camera => '카메라',
        _AttachmentKind.upload => '업로드',
        _AttachmentKind.none => '미선택',
      };
}

class _RoutineItem {
  final String id;
  final String name;
  final String dosage;
  final _RoutineKind kind;
  final _MealSlot slot;

  const _RoutineItem({
    required this.id,
    required this.name,
    required this.dosage,
    required this.kind,
    required this.slot,
  });

  _RoutineItem copyWith({String? name}) {
    return _RoutineItem(
      id: id,
      name: name ?? this.name,
      dosage: dosage,
      kind: kind,
      slot: slot,
    );
  }
}

class _DailyPromise {
  final String id;
  final _MealSlot slot;
  final String title;
  final String description;
  final bool highlighted;

  const _DailyPromise({
    required this.id,
    required this.slot,
    required this.title,
    required this.description,
    this.highlighted = false,
  });
}

class _AnalysisMetric {
  final IconData icon;
  final String label;
  final String value;

  const _AnalysisMetric({
    required this.icon,
    required this.label,
    required this.value,
  });
}

class _AnalysisResult {
  final String id;
  final String title;
  final String description;
  final String resultText;
  final String practiceDirection;
  final String promiseDirection;
  final IconData icon;
  final Color iconColor;
  final List<_AnalysisMetric> metrics;

  const _AnalysisResult({
    required this.id,
    required this.title,
    required this.description,
    String? resultText,
    String? practiceDirection,
    String? promiseDirection,
    required this.icon,
    required this.iconColor,
    required this.metrics,
  }) : resultText = resultText ?? description,
       practiceDirection = practiceDirection ?? description,
       promiseDirection = promiseDirection ?? description;
}

const _defaultRoutineItems = [
  _RoutineItem(
    id: 'morning-pressure-med',
    name: '혈압약 B',
    dosage: '아침 식후 · 1정',
    kind: _RoutineKind.medicine,
    slot: _MealSlot.morning,
  ),
  _RoutineItem(
    id: 'morning-omega3',
    name: '오메가-3',
    dosage: '아침 식사 직후',
    kind: _RoutineKind.supplement,
    slot: _MealSlot.morning,
  ),
  _RoutineItem(
    id: 'lunch-diabetes-med',
    name: '당뇨약 A',
    dosage: '점심 식후 · 1정',
    kind: _RoutineKind.medicine,
    slot: _MealSlot.lunch,
  ),
  _RoutineItem(
    id: 'lunch-vitamin-d',
    name: '비타민 D',
    dosage: '점심 식사 후 · 1캡슐',
    kind: _RoutineKind.supplement,
    slot: _MealSlot.lunch,
  ),
  _RoutineItem(
    id: 'dinner-magnesium',
    name: '마그네슘',
    dosage: '저녁 식후 · 수면 루틴',
    kind: _RoutineKind.supplement,
    slot: _MealSlot.dinner,
  ),
  _RoutineItem(
    id: 'dinner-probiotic',
    name: '프로바이오틱스',
    dosage: '물 1컵과 함께',
    kind: _RoutineKind.supplement,
    slot: _MealSlot.dinner,
  ),
];

const _dailyPromises = [
  _DailyPromise(
    id: 'morning',
    slot: _MealSlot.morning,
    title: '아침 약속',
    description: '단 음식은 줄이고 오메가-3는 식사 직후 복용해요.',
    highlighted: true,
  ),
  _DailyPromise(
    id: 'lunch',
    slot: _MealSlot.lunch,
    title: '점심 약속',
    description: '탄수화물 양을 평소보다 한 숟갈 줄이고 물을 먼저 마셔요.',
  ),
  _DailyPromise(
    id: 'dinner',
    slot: _MealSlot.dinner,
    title: '저녁 약속',
    description: '마그네슘은 저녁 식후로 유지하고 늦은 간식은 피합니다.',
  ),
];

final _analysisResults = [
  _AnalysisResult(
    id: 'diet',
    title: '식단 분석',
    description: '아침 식단은 당 함량을 낮추는 방향이 좋고, 점심은 탄수화물 양을 평소보다 한 숟갈 줄이는 흐름이 좋습니다.',
    icon: Icons.restaurant_rounded,
    iconColor: AppColor.brand,
    metrics: [
      _AnalysisMetric(
        icon: Icons.rice_bowl_rounded,
        label: '식단 주의',
        value: '탄수화물 양 조절',
      ),
      _AnalysisMetric(
        icon: Icons.water_drop_rounded,
        label: '실천 방향',
        value: '식전 물 먼저 마시기',
      ),
    ],
  ),
  _AnalysisResult(
    id: 'supplement',
    title: '영양제 분석',
    description: '오메가-3는 식사 직후, 마그네슘은 저녁 식후로 유지하면 현재 루틴 안에서 이해하기 쉽습니다.',
    icon: Icons.medication_liquid_rounded,
    iconColor: AppColor.success,
    metrics: [
      _AnalysisMetric(
        icon: Icons.schedule_rounded,
        label: '복용 흐름',
        value: '식후 중심으로 정리',
      ),
      _AnalysisMetric(
        icon: Icons.fact_check_rounded,
        label: '확인 결과',
        value: '겹치는 성분 없음',
      ),
    ],
  ),
  _AnalysisResult(
    id: 'combined',
    title: '식단 + 영양제 통합 분석',
    description:
        '식단의 당과 탄수화물 조절을 먼저 잡고, 영양제는 식사 직후 복용 흐름으로 연결하면 오늘 루틴이 안정적입니다.',
    icon: Icons.insights_rounded,
    iconColor: AppColor.brand,
    metrics: [
      _AnalysisMetric(
        icon: Icons.restaurant_menu_rounded,
        label: '식단 연결',
        value: '당 함량 낮추기',
      ),
      _AnalysisMetric(
        icon: Icons.medication_rounded,
        label: '복용 연결',
        value: '식후 루틴 유지',
      ),
    ],
  ),
];

class _AgentExperienceTab extends StatelessWidget {
  final _AgentView view;
  final List<_DietEntry> dietEntries;
  final List<_RoutineItem> routineEntries;
  final List<_RegisteredSupplement> registeredSupplements;
  final List<String> addedPromiseDirections;
  final Set<String> checkedDietEntryIds;
  final Set<String> checkedSupplementEntryIds;
  final Set<String> checkedPromiseIds;
  final _AnalysisResult analysis;
  final ValueChanged<_AgentView> onOpenView;
  final VoidCallback onBack;
  final ValueChanged<_AgentView> onRecordPhoto;
  final ValueChanged<_AgentView> onAddCustomEntry;
  final ValueChanged<String> onToggleDietEntry;
  final ValueChanged<String> onToggleSupplementEntry;
  final ValueChanged<String> onTogglePromise;
  final ValueChanged<String> onRenameDietEntry;
  final ValueChanged<String> onDeleteDietEntry;
  final ValueChanged<String> onRenameRoutineItem;
  final ValueChanged<String> onDeleteRoutineItem;
  final ValueChanged<String> onRenameRegisteredSupplement;
  final ValueChanged<String> onDeleteRegisteredSupplement;
  final ValueChanged<_AnalysisResult> onAnalysisQuestion;
  final ValueChanged<_AnalysisResult> onAddPromise;

  const _AgentExperienceTab({
    required this.view,
    required this.dietEntries,
    required this.routineEntries,
    required this.registeredSupplements,
    required this.addedPromiseDirections,
    required this.checkedDietEntryIds,
    required this.checkedSupplementEntryIds,
    required this.checkedPromiseIds,
    required this.analysis,
    required this.onOpenView,
    required this.onBack,
    required this.onRecordPhoto,
    required this.onAddCustomEntry,
    required this.onToggleDietEntry,
    required this.onToggleSupplementEntry,
    required this.onTogglePromise,
    required this.onRenameDietEntry,
    required this.onDeleteDietEntry,
    required this.onRenameRoutineItem,
    required this.onDeleteRoutineItem,
    required this.onRenameRegisteredSupplement,
    required this.onDeleteRegisteredSupplement,
    required this.onAnalysisQuestion,
    required this.onAddPromise,
  });

  @override
  Widget build(BuildContext context) {
    return switch (view) {
      _AgentView.home => _AgentHomeView(
        addedPromiseDirections: addedPromiseDirections,
        checkedPromiseIds: checkedPromiseIds,
        onOpenView: onOpenView,
        onTogglePromise: onTogglePromise,
      ),
      _AgentView.diet => _TrackingDetailView(
        view: _AgentView.diet,
        title: '식단 기록',
        subtitle: '아침, 점심, 저녁과 그 외 식사를 기록합니다',
        addLabel: '그 외 식사 추가하기',
        entries: dietEntries,
        checkedEntryIds: checkedDietEntryIds,
        onBack: onBack,
        onRecordPhoto: () => onRecordPhoto(_AgentView.diet),
        onAddCustomEntry: () => onAddCustomEntry(_AgentView.diet),
        onToggleEntry: onToggleDietEntry,
        onRenameEntry: onRenameDietEntry,
        onDeleteEntry: onDeleteDietEntry,
      ),
      _AgentView.supplement => _SupplementRegistrationView(
        title: '영양제 기록',
        subtitle: '복용 중인 영양제를 등록해두고 시간대별로 관리합니다.',
        routineEntries: routineEntries,
        supplements: registeredSupplements,
        checkedEntryIds: checkedSupplementEntryIds,
        onBack: onBack,
        onRegister: () => onRecordPhoto(_AgentView.supplement),
        onToggleEntry: onToggleSupplementEntry,
        onRenameRoutineItem: onRenameRoutineItem,
        onDeleteRoutineItem: onDeleteRoutineItem,
        onRenameRegisteredSupplement: onRenameRegisteredSupplement,
        onDeleteRegisteredSupplement: onDeleteRegisteredSupplement,
      ),
      _AgentView.analysis => _AnalysisDetailView(
        analysis: analysis,
        onBack: onBack,
        onQuestion: () => onAnalysisQuestion(analysis),
        onAddPromise: () => onAddPromise(analysis),
      ),
    };
  }
}

class _AgentHomeView extends StatelessWidget {
  final List<String> addedPromiseDirections;
  final Set<String> checkedPromiseIds;
  final ValueChanged<_AgentView> onOpenView;
  final ValueChanged<String> onTogglePromise;

  const _AgentHomeView({
    required this.addedPromiseDirections,
    required this.checkedPromiseIds,
    required this.onOpenView,
    required this.onTogglePromise,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.lg,
        AppSpace.page,
        AppSpace.xxl,
      ),
      children: [
        _PrototypeHeader(
          eyebrow: '오늘의 Agent',
          title: '기록과 약속을 카드로 확인합니다',
          subtitle: '식단, 영양제, 분석을 나눠서 봅니다',
        ),
        const SizedBox(height: AppSpace.lg),
        _AgentDashboardCard(
          key: const Key('agent-card-diet'),
          title: '식단',
          value: '0 kcal',
          description: '아침, 점심, 저녁 기록',
          icon: Icons.restaurant_rounded,
          color: AppColor.info,
          onTap: () => onOpenView(_AgentView.diet),
        ),
        const SizedBox(height: AppSpace.md),
        _AgentDashboardCard(
          key: const Key('agent-card-supplement'),
          title: '영양제',
          value: '0개',
          description: '복용 기록 추가',
          icon: Icons.medication_liquid_rounded,
          color: AppColor.success,
          onTap: () => onOpenView(_AgentView.supplement),
        ),
        const SizedBox(height: AppSpace.md),
        _AgentDashboardCard(
          key: const Key('agent-card-analysis'),
          title: '분석',
          value: '82점',
          description: '오늘 점수와 누적 흐름',
          icon: Icons.speed_rounded,
          color: AppColor.brand,
          onTap: () => onOpenView(_AgentView.analysis),
        ),
        const SizedBox(height: AppSpace.lg),
        _DailyPromiseTimeline(
          selectedSlot: _MealSlot.morning,
          extraDirections: addedPromiseDirections,
          checkedPromiseIds: checkedPromiseIds,
          onPromiseToggle: onTogglePromise,
        ),
      ],
    );
  }
}

class _AgentDashboardCard extends StatelessWidget {
  final String title;
  final String value;
  final String description;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _AgentDashboardCard({
    super.key,
    required this.title,
    required this.value,
    required this.description,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpace.lg),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 108),
        child: Row(
          children: [
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(AppRadius.lg),
              ),
              child: Icon(icon, color: color, size: 30),
            ),
            const SizedBox(width: AppSpace.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppText.caption.copyWith(
                      color: AppColor.inkSecondary,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: AppSpace.xs),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppText.title.copyWith(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: AppSpace.xs),
                  Text(
                    description,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppText.caption.copyWith(
                      color: AppColor.inkTertiary,
                      letterSpacing: 0,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpace.md),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColor.inkDisabled,
            ),
          ],
        ),
      ),
    );
  }
}

class _TrackingDetailView extends StatelessWidget {
  final _AgentView view;
  final String title;
  final String subtitle;
  final String addLabel;
  final List<_DietEntry> entries;
  final Set<String> checkedEntryIds;
  final VoidCallback onBack;
  final VoidCallback onRecordPhoto;
  final VoidCallback onAddCustomEntry;
  final ValueChanged<String> onToggleEntry;
  final ValueChanged<String> onRenameEntry;
  final ValueChanged<String> onDeleteEntry;

  const _TrackingDetailView({
    required this.view,
    required this.title,
    required this.subtitle,
    required this.addLabel,
    required this.entries,
    required this.checkedEntryIds,
    required this.onBack,
    required this.onRecordPhoto,
    required this.onAddCustomEntry,
    required this.onToggleEntry,
    required this.onRenameEntry,
    required this.onDeleteEntry,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.lg,
        AppSpace.page,
        AppSpace.xxl,
      ),
      children: [
        _DetailHeader(title: title, subtitle: subtitle, onBack: onBack),
        const SizedBox(height: AppSpace.lg),
        for (final entry in entries) ...[
          _TrackEntryRow(
            key: Key('${view.name}-photo-${entry.id}'),
            title: entry.name,
            subtitle: entry.subtitle,
            chip: checkedEntryIds.contains(entry.id) ? '먹었어요' : entry.chip,
            icon: entry.icon,
            checked: checkedEntryIds.contains(entry.id),
            onPhoto: onRecordPhoto,
            toggleKey: Key('${view.name}-toggle-${entry.id}'),
            onToggle: () => onToggleEntry(entry.id),
            editKey: Key('${view.name}-edit-${entry.id}'),
            deleteKey: Key('${view.name}-delete-${entry.id}'),
            onRename: () => onRenameEntry(entry.id),
            onDelete: () => onDeleteEntry(entry.id),
          ),
          const SizedBox(height: AppSpace.md),
        ],
        _AddCustomEntryCard(label: addLabel, onTap: onAddCustomEntry),
      ],
    );
  }
}

class _SupplementRegistrationView extends StatelessWidget {
  final String title;
  final String subtitle;
  final List<_RoutineItem> routineEntries;
  final List<_RegisteredSupplement> supplements;
  final Set<String> checkedEntryIds;
  final VoidCallback onBack;
  final VoidCallback onRegister;
  final ValueChanged<String> onToggleEntry;
  final ValueChanged<String> onRenameRoutineItem;
  final ValueChanged<String> onDeleteRoutineItem;
  final ValueChanged<String> onRenameRegisteredSupplement;
  final ValueChanged<String> onDeleteRegisteredSupplement;

  const _SupplementRegistrationView({
    required this.title,
    required this.subtitle,
    required this.routineEntries,
    required this.supplements,
    required this.checkedEntryIds,
    required this.onBack,
    required this.onRegister,
    required this.onToggleEntry,
    required this.onRenameRoutineItem,
    required this.onDeleteRoutineItem,
    required this.onRenameRegisteredSupplement,
    required this.onDeleteRegisteredSupplement,
  });

  @override
  Widget build(BuildContext context) {
    final customGroupLabels = supplements
        .map((supplement) => supplement.groupLabel)
        .where((label) => !_defaultSupplementTargetLabels.contains(label))
        .toSet()
        .toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.lg,
        AppSpace.page,
        AppSpace.xxl,
      ),
      children: [
        _DetailHeader(title: title, subtitle: subtitle, onBack: onBack),
        const SizedBox(height: AppSpace.lg),
        _RegisterSupplementCard(onTap: onRegister),
        const SizedBox(height: AppSpace.md),
        for (final slot in _MealSlot.values) ...[
          _SupplementRoutineSection(
            slot: slot,
            items: routineEntries.where((item) => item.slot == slot).toList(),
            supplements: supplements
                .where((supplement) => supplement.groupLabel == slot.label)
                .toList(),
            checkedEntryIds: checkedEntryIds,
            onToggleEntry: onToggleEntry,
            onRenameRoutineItem: onRenameRoutineItem,
            onDeleteRoutineItem: onDeleteRoutineItem,
            onRenameRegisteredSupplement: onRenameRegisteredSupplement,
            onDeleteRegisteredSupplement: onDeleteRegisteredSupplement,
          ),
          const SizedBox(height: AppSpace.md),
        ],
        for (final groupLabel in customGroupLabels) ...[
          _SupplementCustomGroupSection(
            groupLabel: groupLabel,
            supplements: supplements
                .where((supplement) => supplement.groupLabel == groupLabel)
                .toList(),
            checkedEntryIds: checkedEntryIds,
            onToggleEntry: onToggleEntry,
            onRenameRegisteredSupplement: onRenameRegisteredSupplement,
            onDeleteRegisteredSupplement: onDeleteRegisteredSupplement,
          ),
          if (groupLabel != customGroupLabels.last)
            const SizedBox(height: AppSpace.md),
        ],
      ],
    );
  }
}

class _RegisterSupplementCard extends StatelessWidget {
  final VoidCallback onTap;

  const _RegisterSupplementCard({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: AppColor.successSoft,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: const Icon(
              Icons.add_rounded,
              color: AppColor.success,
              size: 32,
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Text(
              '영양제 등록하기',
              style: AppText.subtitle.copyWith(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ),
          const Icon(Icons.chevron_right_rounded, color: AppColor.inkTertiary),
        ],
      ),
    );
  }
}

class _SupplementRegistrationSheet extends StatefulWidget {
  final _AttachmentKind attachment;
  final List<String> targetLabels;

  const _SupplementRegistrationSheet({
    required this.attachment,
    required this.targetLabels,
  });

  @override
  State<_SupplementRegistrationSheet> createState() =>
      _SupplementRegistrationSheetState();
}

class _SupplementRegistrationSheetState
    extends State<_SupplementRegistrationSheet> {
  late final TextEditingController _nameController;
  late final TextEditingController _newGroupController;
  late final List<String> _targetLabels;
  final Set<String> _selectedLabels = {};
  _RoutineKind _kind = _RoutineKind.supplement;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(
      text: _RegisteredSupplement.mockNameFor(widget.attachment),
    );
    _newGroupController = TextEditingController();
    _targetLabels = [...widget.targetLabels];
  }

  @override
  void dispose() {
    _nameController.dispose();
    _newGroupController.dispose();
    super.dispose();
  }

  void _toggleTarget(String label, bool? selected) {
    setState(() {
      if (selected ?? false) {
        _selectedLabels.add(label);
      } else {
        _selectedLabels.remove(label);
      }
    });
  }

  void _addTargetGroup() {
    final label = _newGroupController.text.trim();
    if (label.isEmpty || _targetLabels.contains(label)) return;
    setState(() {
      _targetLabels.insert(0, label);
      _newGroupController.clear();
    });
  }

  void _apply() {
    final name = _nameController.text.trim();
    if (name.isEmpty || _selectedLabels.isEmpty) return;
    Navigator.of(context).pop([
      for (final label in _selectedLabels)
        _RegisteredSupplement(
          name: name,
          groupLabel: label,
          methodLabel: _RegisteredSupplement.methodLabelFor(widget.attachment),
          kind: _kind,
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final canApply =
        _selectedLabels.isNotEmpty && _nameController.text.trim().isNotEmpty;
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          AppSpace.md,
          AppSpace.md,
          AppSpace.md,
          AppSpace.md + bottomInset,
        ),
        child: Align(
          alignment: Alignment.bottomCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: FractionallySizedBox(
              heightFactor: 0.96,
              child: Material(
                color: AppColor.surface,
                elevation: 18,
                shadowColor: const Color.fromRGBO(0, 0, 0, 0.18),
                borderRadius: BorderRadius.circular(AppRadius.xl),
                clipBehavior: Clip.antiAlias,
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        AppSpace.lg,
                        AppSpace.lg,
                        AppSpace.lg,
                        AppSpace.sm,
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              '인식값 확인',
                              style: AppText.subtitle.copyWith(
                                fontSize: 18,
                                letterSpacing: 0,
                              ),
                            ),
                          ),
                          Tooltip(
                            message: '닫기',
                            child: IconButton(
                              onPressed: () => Navigator.of(context).pop(),
                              icon: const Icon(Icons.close_rounded),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(
                          AppSpace.lg,
                          0,
                          AppSpace.lg,
                          AppSpace.lg,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _MockSupplementPreview(
                              attachment: widget.attachment,
                            ),
                            const SizedBox(height: AppSpace.lg),
                            TextField(
                              key: const Key('supplement-name-input'),
                              controller: _nameController,
                              onChanged: (_) => setState(() {}),
                              decoration: const InputDecoration(
                                labelText: '인식된 이름',
                                hintText: '영양제 이름을 입력하세요',
                                border: OutlineInputBorder(),
                              ),
                            ),
                            const SizedBox(height: AppSpace.lg),
                            Text(
                              '유형',
                              style: AppText.caption.copyWith(
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0,
                              ),
                            ),
                            const SizedBox(height: AppSpace.sm),
                            Wrap(
                              spacing: AppSpace.sm,
                              children: [
                                for (final kind in _RoutineKind.values)
                                  ChoiceChip(
                                    label: Text(kind.label),
                                    selected: _kind == kind,
                                    selectedColor: kind.softColor,
                                    onSelected: (_) =>
                                        setState(() => _kind = kind),
                                  ),
                              ],
                            ),
                            const SizedBox(height: AppSpace.lg),
                            Text(
                              '추가 대상',
                              style: AppText.caption.copyWith(
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0,
                              ),
                            ),
                            const SizedBox(height: AppSpace.sm),
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    key: const Key('new-group-input'),
                                    controller: _newGroupController,
                                    textInputAction: TextInputAction.done,
                                    onSubmitted: (_) => _addTargetGroup(),
                                    decoration: const InputDecoration(
                                      hintText: '새 그룹 추가',
                                      border: OutlineInputBorder(),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: AppSpace.sm),
                                Tooltip(
                                  message: '그룹 추가',
                                  child: IconButton.filled(
                                    key: const Key('add-target-group'),
                                    onPressed: _addTargetGroup,
                                    icon: const Icon(Icons.add_rounded),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpace.sm),
                            for (final label in _targetLabels)
                              _TargetGroupCheckbox(
                                key: Key('target-group-$label'),
                                label: label,
                                selected: _selectedLabels.contains(label),
                                onChanged: (selected) =>
                                    _toggleTarget(label, selected),
                              ),
                          ],
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        AppSpace.lg,
                        AppSpace.md,
                        AppSpace.lg,
                        AppSpace.lg,
                      ),
                      child: SizedBox(
                        width: double.infinity,
                        height: 52,
                        child: ElevatedButton(
                          key: const Key('apply-supplement-registration'),
                          onPressed: canApply ? _apply : null,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColor.brand,
                            foregroundColor: AppColor.ink,
                            disabledBackgroundColor: AppColor.borderStrong,
                            disabledForegroundColor: AppColor.inkTertiary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppRadius.sm),
                            ),
                          ),
                          child: const Text('적용하기'),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TargetGroupCheckbox extends StatelessWidget {
  final String label;
  final bool selected;
  final ValueChanged<bool> onChanged;

  const _TargetGroupCheckbox({
    super.key,
    required this.label,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => onChanged(!selected),
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: SizedBox(
        height: 36,
        child: Row(
          children: [
            Checkbox(
              value: selected,
              onChanged: (value) => onChanged(value ?? false),
              visualDensity: VisualDensity.compact,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            const SizedBox(width: AppSpace.xs),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppText.body.copyWith(letterSpacing: 0),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MockSupplementPreview extends StatelessWidget {
  final _AttachmentKind attachment;

  const _MockSupplementPreview({required this.attachment});

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('supplement-mock-preview'),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColor.border),
      ),
      child: SizedBox(
        height: 104,
        width: double.infinity,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset(
              _mockSupplementImageAsset,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => const ColoredBox(
                color: AppColor.successSoft,
                child: Center(
                  child: Icon(
                    Icons.medication_liquid_rounded,
                    color: AppColor.success,
                    size: 52,
                  ),
                ),
              ),
            ),
            Positioned(
              left: AppSpace.sm,
              bottom: AppSpace.sm,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpace.sm,
                  vertical: AppSpace.xs,
                ),
                decoration: BoxDecoration(
                  color: AppColor.surface.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(AppRadius.full),
                ),
                child: Row(
                  children: [
                    Icon(
                      attachment.icon,
                      color: AppColor.inkSecondary,
                      size: 16,
                    ),
                    const SizedBox(width: AppSpace.xs),
                    Text(
                      '${_RegisteredSupplement.methodLabelFor(attachment)} mock',
                      style: AppText.micro.copyWith(letterSpacing: 0),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SupplementRoutineSection extends StatelessWidget {
  final _MealSlot slot;
  final List<_RoutineItem> items;
  final List<_RegisteredSupplement> supplements;
  final Set<String> checkedEntryIds;
  final ValueChanged<String> onToggleEntry;
  final ValueChanged<String> onRenameRoutineItem;
  final ValueChanged<String> onDeleteRoutineItem;
  final ValueChanged<String> onRenameRegisteredSupplement;
  final ValueChanged<String> onDeleteRegisteredSupplement;

  const _SupplementRoutineSection({
    required this.slot,
    required this.items,
    required this.supplements,
    required this.checkedEntryIds,
    required this.onToggleEntry,
    required this.onRenameRoutineItem,
    required this.onDeleteRoutineItem,
    required this.onRenameRegisteredSupplement,
    required this.onDeleteRegisteredSupplement,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _SlotIcon(slot: slot, selected: false),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Text(
                  slot.label,
                  style: AppText.subtitle.copyWith(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          for (final item in items) ...[
            _SupplementRoutineCard(
              name: item.name,
              kind: item.kind,
              checked: checkedEntryIds.contains(item.id),
              toggleKey: Key('supplement-toggle-${item.id}'),
              onToggle: () => onToggleEntry(item.id),
              editKey: Key('supplement-edit-${item.id}'),
              deleteKey: Key('supplement-delete-${item.id}'),
              onRename: () => onRenameRoutineItem(item.id),
              onDelete: () => onDeleteRoutineItem(item.id),
            ),
            const SizedBox(height: AppSpace.sm),
          ],
          for (final supplement in supplements) ...[
            _SupplementRoutineCard(
              name: supplement.name,
              kind: supplement.kind,
              checked: checkedEntryIds.contains(supplement.id),
              toggleKey: Key('supplement-toggle-${supplement.id}'),
              onToggle: () => onToggleEntry(supplement.id),
              editKey: Key('supplement-edit-${supplement.id}'),
              deleteKey: Key('supplement-delete-${supplement.id}'),
              onRename: () => onRenameRegisteredSupplement(supplement.id),
              onDelete: () => onDeleteRegisteredSupplement(supplement.id),
            ),
            if (supplement != supplements.last)
              const SizedBox(height: AppSpace.sm),
          ],
        ],
      ),
    );
  }
}

class _SupplementCustomGroupSection extends StatelessWidget {
  final String groupLabel;
  final List<_RegisteredSupplement> supplements;
  final Set<String> checkedEntryIds;
  final ValueChanged<String> onToggleEntry;
  final ValueChanged<String> onRenameRegisteredSupplement;
  final ValueChanged<String> onDeleteRegisteredSupplement;

  const _SupplementCustomGroupSection({
    required this.groupLabel,
    required this.supplements,
    required this.checkedEntryIds,
    required this.onToggleEntry,
    required this.onRenameRegisteredSupplement,
    required this.onDeleteRegisteredSupplement,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: AppColor.reviewSoft,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: const Icon(
                  Icons.folder_special_rounded,
                  color: AppColor.review,
                ),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Text(
                  groupLabel,
                  style: AppText.subtitle.copyWith(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          for (final supplement in supplements) ...[
            _SupplementRoutineCard(
              name: supplement.name,
              kind: supplement.kind,
              checked: checkedEntryIds.contains(supplement.id),
              toggleKey: Key('supplement-toggle-${supplement.id}'),
              onToggle: () => onToggleEntry(supplement.id),
              editKey: Key('supplement-edit-${supplement.id}'),
              deleteKey: Key('supplement-delete-${supplement.id}'),
              onRename: () => onRenameRegisteredSupplement(supplement.id),
              onDelete: () => onDeleteRegisteredSupplement(supplement.id),
            ),
            if (supplement != supplements.last)
              const SizedBox(height: AppSpace.sm),
          ],
        ],
      ),
    );
  }
}

class _SupplementRoutineCard extends StatelessWidget {
  final String name;
  final _RoutineKind kind;
  final bool checked;
  final Key toggleKey;
  final VoidCallback onToggle;
  final Key editKey;
  final Key deleteKey;
  final VoidCallback onRename;
  final VoidCallback onDelete;

  const _SupplementRoutineCard({
    required this.name,
    required this.kind,
    required this.checked,
    required this.toggleKey,
    required this.onToggle,
    required this.editKey,
    required this.deleteKey,
    required this.onRename,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 62),
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColor.border),
      ),
      child: Row(
        children: [
          _EntryActionButton(
            buttonKey: toggleKey,
            icon: checked
                ? Icons.check_circle_rounded
                : Icons.radio_button_unchecked_rounded,
            tooltip: checked ? '복용 완료 해제' : '복용 완료',
            onTap: onToggle,
          ),
          const SizedBox(width: AppSpace.xs),
          Icon(
            kind == _RoutineKind.medicine
                ? Icons.medication_rounded
                : Icons.medication_liquid_rounded,
            color: kind.color,
            size: 24,
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.body.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: AppSpace.xs),
                Text(
                  checked ? '복용 완료' : '복용 대기',
                  style: AppText.micro.copyWith(
                    color: checked ? AppColor.success : AppColor.inkTertiary,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          _KindPill(kind: kind),
          const SizedBox(width: AppSpace.xs),
          _EntryActionButton(
            buttonKey: editKey,
            icon: Icons.edit_rounded,
            tooltip: '이름 수정',
            onTap: onRename,
          ),
          _EntryActionButton(
            buttonKey: deleteKey,
            icon: Icons.delete_outline_rounded,
            tooltip: '삭제',
            onTap: onDelete,
          ),
        ],
      ),
    );
  }
}

class _DetailHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback onBack;

  const _DetailHeader({
    required this.title,
    required this.subtitle,
    required this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Tooltip(
          message: '뒤로',
          child: _RoundIconButton(
            icon: Icons.arrow_back_ios_new_rounded,
            onTap: onBack,
          ),
        ),
        const SizedBox(width: AppSpace.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppText.title.copyWith(fontSize: 22, letterSpacing: 0),
              ),
              const SizedBox(height: AppSpace.xs),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: AppText.caption.copyWith(letterSpacing: 0),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TrackEntryRow extends StatelessWidget {
  final String title;
  final String subtitle;
  final String chip;
  final IconData icon;
  final bool checked;
  final VoidCallback onPhoto;
  final Key toggleKey;
  final VoidCallback onToggle;
  final Key editKey;
  final Key deleteKey;
  final VoidCallback onRename;
  final VoidCallback onDelete;

  const _TrackEntryRow({
    super.key,
    required this.title,
    required this.subtitle,
    required this.chip,
    required this.icon,
    required this.checked,
    required this.onPhoto,
    required this.toggleKey,
    required this.onToggle,
    required this.editKey,
    required this.deleteKey,
    required this.onRename,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onPhoto,
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Row(
        children: [
          _EntryActionButton(
            buttonKey: toggleKey,
            icon: checked
                ? Icons.check_circle_rounded
                : Icons.radio_button_unchecked_rounded,
            tooltip: checked ? '먹은 기록 해제' : '먹었어요',
            onTap: onToggle,
          ),
          const SizedBox(width: AppSpace.xs),
          Container(
            width: 86,
            height: 86,
            decoration: BoxDecoration(
              color: AppColor.sunken,
              borderRadius: BorderRadius.circular(AppRadius.lg),
            ),
            child: Icon(icon, color: AppColor.brandDeep, size: 34),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.subtitle.copyWith(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: AppSpace.xs),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.caption.copyWith(
                    color: AppColor.inkTertiary,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: AppSpace.md),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpace.md,
                    vertical: AppSpace.sm,
                  ),
                  decoration: BoxDecoration(
                    color: checked ? AppColor.successSoft : AppColor.sunken,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    chip,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppText.caption.copyWith(
                      color: checked ? AppColor.success : AppColor.inkTertiary,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          Tooltip(
            message: '사진 추가',
            child: _RoundIconButton(
              icon: Icons.add_rounded,
              filled: true,
              onTap: onPhoto,
            ),
          ),
          const SizedBox(width: AppSpace.xs),
          _EntryActionButton(
            buttonKey: editKey,
            icon: Icons.edit_rounded,
            tooltip: '이름 수정',
            onTap: onRename,
          ),
          _EntryActionButton(
            buttonKey: deleteKey,
            icon: Icons.delete_outline_rounded,
            tooltip: '삭제',
            onTap: onDelete,
          ),
        ],
      ),
    );
  }
}

class _EntryActionButton extends StatelessWidget {
  final Key buttonKey;
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _EntryActionButton({
    required this.buttonKey,
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: SizedBox.square(
        dimension: 38,
        child: IconButton(
          key: buttonKey,
          padding: EdgeInsets.zero,
          visualDensity: VisualDensity.compact,
          iconSize: 20,
          color: AppColor.inkSecondary,
          onPressed: onTap,
          icon: Icon(icon),
        ),
      ),
    );
  }
}

class _AddCustomEntryCard extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _AddCustomEntryCard({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(AppSpace.xl),
      child: Column(
        children: [
          Text(
            label,
            textAlign: TextAlign.center,
            style: AppText.subtitle.copyWith(
              color: AppColor.inkTertiary,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AppColor.borderStrong, width: 2),
            ),
            child: const Icon(
              Icons.add_rounded,
              size: 36,
              color: AppColor.inkTertiary,
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalysisDetailView extends StatelessWidget {
  final _AnalysisResult analysis;
  final VoidCallback onBack;
  final VoidCallback onQuestion;
  final VoidCallback onAddPromise;

  const _AnalysisDetailView({
    required this.analysis,
    required this.onBack,
    required this.onQuestion,
    required this.onAddPromise,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.lg,
        AppSpace.page,
        AppSpace.xxl,
      ),
      children: [
        _DetailHeader(
          title: '분석',
          subtitle: '오늘 등록한 내용과 누적 점수를 봅니다',
          onBack: onBack,
        ),
        const SizedBox(height: AppSpace.lg),
        const Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _ScoreGaugeCard(title: '오늘 분석 점수', score: 82)),
            SizedBox(width: AppSpace.md),
            Expanded(child: _ScoreGaugeCard(title: '누적 점수', score: 76)),
          ],
        ),
        const SizedBox(height: AppSpace.lg),
        _AnalysisDetailResultCard(
          analysis: analysis,
          onQuestion: onQuestion,
          onAddPromise: onAddPromise,
        ),
      ],
    );
  }
}

class _ScoreGaugeCard extends StatelessWidget {
  final String title;
  final double score;

  const _ScoreGaugeCard({required this.title, required this.score});

  @override
  Widget build(BuildContext context) {
    final stageLabel = _scoreStageLabel(score);
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppText.caption.copyWith(
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          SizedBox(
            height: 96,
            child: CustomPaint(
              painter: _ScoreGaugePainter(score: score),
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.only(top: 28),
                  child: Text(
                    score.toStringAsFixed(0),
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppColor.ink,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          Wrap(
            spacing: 4,
            runSpacing: 4,
            children: [
              for (final stage in _scoreStages)
                _ScoreStagePill(
                  stage: stage,
                  active: stage.label == stageLabel,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

const _scoreStages = [
  _ScoreStage('주의', '0-19'),
  _ScoreStage('점검', '20-39'),
  _ScoreStage('보통', '40-59'),
  _ScoreStage('좋음', '60-79'),
  _ScoreStage('안정', '80-100'),
];

class _ScoreStage {
  final String label;
  final String range;

  const _ScoreStage(this.label, this.range);
}

String _scoreStageLabel(double score) {
  final bounded = score.clamp(0, 100);
  if (bounded < 20) return '주의';
  if (bounded < 40) return '점검';
  if (bounded < 60) return '보통';
  if (bounded < 80) return '좋음';
  return '안정';
}

class _ScoreStagePill extends StatelessWidget {
  final _ScoreStage stage;
  final bool active;

  const _ScoreStagePill({required this.stage, required this.active});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      decoration: BoxDecoration(
        color: active ? AppColor.brandSoft : AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: active ? AppColor.brand : AppColor.border),
      ),
      child: Text(
        '${stage.label}\n${stage.range}',
        textAlign: TextAlign.center,
        style: AppText.micro.copyWith(
          color: active ? AppColor.brandDeep : AppColor.inkTertiary,
          fontWeight: active ? FontWeight.w900 : FontWeight.w700,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _ScoreGaugePainter extends CustomPainter {
  final double score;

  const _ScoreGaugePainter({required this.score});

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(8, 8, size.width - 16, size.height * 1.55);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.butt
      ..strokeWidth = 15;
    final colors = [
      AppColor.danger,
      AppColor.warning,
      AppColor.brand,
      AppColor.info,
      AppColor.success,
    ];
    const start = math.pi;
    const segment = math.pi / 5;
    for (var i = 0; i < colors.length; i += 1) {
      paint.color = colors[i];
      canvas.drawArc(
        rect,
        start + segment * i + 0.025,
        segment - 0.05,
        false,
        paint,
      );
    }
    final center = Offset(size.width / 2, size.height - 12);
    final angle = start + math.pi * (score / 100);
    final needle = Offset(
      center.dx + math.cos(angle) * size.width * 0.36,
      center.dy + math.sin(angle) * size.width * 0.36,
    );
    canvas.drawLine(
      center,
      needle,
      Paint()
        ..color = AppColor.ink
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawCircle(center, 10, Paint()..color = AppColor.ink);
    canvas.drawCircle(center, 5, Paint()..color = AppColor.surface);
  }

  @override
  bool shouldRepaint(covariant _ScoreGaugePainter oldDelegate) {
    return oldDelegate.score != score;
  }
}

class _AnalysisDetailResultCard extends StatelessWidget {
  final _AnalysisResult analysis;
  final VoidCallback onQuestion;
  final VoidCallback onAddPromise;

  const _AnalysisDetailResultCard({
    required this.analysis,
    required this.onQuestion,
    required this.onAddPromise,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      color: const Color(0xFFFFFBEB),
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: analysis.iconColor,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(analysis.icon, color: AppColor.ink),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Text(
                  '분석 결과',
                  style: AppText.subtitle.copyWith(
                    fontSize: 17,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          Text(
            analysis.resultText,
            style: AppText.body.copyWith(letterSpacing: 0),
          ),
          const SizedBox(height: AppSpace.md),
          for (final metric in analysis.metrics) ...[
            _AnalysisMetricRow(
              icon: metric.icon,
              label: metric.label,
              value: metric.value,
            ),
            if (metric != analysis.metrics.last)
              const SizedBox(height: AppSpace.sm),
          ],
          const SizedBox(height: AppSpace.lg),
          Text(
            '실천 방향',
            style: AppText.caption.copyWith(
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.xs),
          Text(
            analysis.practiceDirection,
            style: AppText.body.copyWith(letterSpacing: 0),
          ),
          const SizedBox(height: AppSpace.md),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: AppSpace.sm,
            runSpacing: AppSpace.sm,
            children: [
              TextButton.icon(
                key: const Key('analysis-add-promise'),
                onPressed: onAddPromise,
                icon: const Icon(Icons.playlist_add_check_rounded, size: 18),
                label: const Text('오늘 하루 약속에 추가'),
                style: TextButton.styleFrom(
                  foregroundColor: AppColor.success,
                  textStyle: AppText.caption.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ),
              TextButton.icon(
                key: Key('analysis-question-${analysis.id}'),
                onPressed: onQuestion,
                icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
                label: const Text('이 결과로 질문하기'),
                style: TextButton.styleFrom(
                  foregroundColor: AppColor.brandDeep,
                  textStyle: AppText.caption.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ignore: unused_element
class _AgentTab extends StatelessWidget {
  final _MealSlot selectedSlot;
  final Set<String> checkedRoutineIds;
  final ValueChanged<String> onRoutineToggle;
  final ValueChanged<_AnalysisResult> onAnalysisQuestion;

  const _AgentTab({
    required this.selectedSlot,
    required this.checkedRoutineIds,
    required this.onRoutineToggle,
    required this.onAnalysisQuestion,
  });

  @override
  Widget build(BuildContext context) {
    final total = _defaultRoutineItems.length;
    final completed = checkedRoutineIds.length;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.lg,
        AppSpace.page,
        AppSpace.xxl,
      ),
      children: [
        _PrototypeHeader(
          eyebrow: '오늘의 Agent',
          title: '식단과 영양제 기준을 나눠 봅니다',
          subtitle: '$completed/$total개 항목 확인됨',
        ),
        const SizedBox(height: AppSpace.lg),
        for (final analysis in _analysisResults) ...[
          _AnalysisResultCard(
            analysis: analysis,
            onQuestion: () => onAnalysisQuestion(analysis),
          ),
          const SizedBox(height: AppSpace.md),
        ],
        const SizedBox(height: AppSpace.sm),
        _DailyPromiseTimeline(selectedSlot: selectedSlot),
        const SizedBox(height: AppSpace.lg),
        for (final slot in _MealSlot.values) ...[
          _RoutineSection(
            slot: slot,
            selected: slot == selectedSlot,
            checkedRoutineIds: checkedRoutineIds,
            onRoutineToggle: onRoutineToggle,
          ),
          const SizedBox(height: AppSpace.md),
        ],
      ],
    );
  }
}

class _PrototypeHeader extends StatelessWidget {
  final String eyebrow;
  final String title;
  final String subtitle;

  const _PrototypeHeader({
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow,
          style: AppText.caption.copyWith(
            color: AppColor.brandDeep,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: AppSpace.sm),
        Text(
          title,
          style: AppText.title.copyWith(
            fontSize: 22,
            height: 1.28,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: AppSpace.xs),
        Text(subtitle, style: AppText.caption.copyWith(letterSpacing: 0)),
      ],
    );
  }
}

class _RoutineSection extends StatelessWidget {
  final _MealSlot slot;
  final bool selected;
  final Set<String> checkedRoutineIds;
  final ValueChanged<String> onRoutineToggle;

  const _RoutineSection({
    required this.slot,
    required this.selected,
    required this.checkedRoutineIds,
    required this.onRoutineToggle,
  });

  @override
  Widget build(BuildContext context) {
    final items = _defaultRoutineItems
        .where((item) => item.slot == slot)
        .toList();
    final checkedCount = items
        .where((item) => checkedRoutineIds.contains(item.id))
        .length;
    return AppCard(
      elevated: selected,
      color: selected ? AppColor.surface : AppColor.sunken,
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _SlotIcon(slot: slot, selected: selected),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${slot.label} 루틴',
                      style: AppText.subtitle.copyWith(
                        fontSize: 17,
                        letterSpacing: 0,
                      ),
                    ),
                    Text(
                      '${slot.time} 기준 · $checkedCount/${items.length} 완료',
                      style: AppText.micro.copyWith(letterSpacing: 0),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          for (final item in items) ...[
            _RoutineRow(
              item: item,
              checked: checkedRoutineIds.contains(item.id),
              onTap: () => onRoutineToggle(item.id),
            ),
            if (item != items.last) const SizedBox(height: AppSpace.sm),
          ],
        ],
      ),
    );
  }
}

class _SlotIcon extends StatelessWidget {
  final _MealSlot slot;
  final bool selected;

  const _SlotIcon({required this.slot, required this.selected});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 42,
      height: 42,
      decoration: BoxDecoration(
        color: selected ? AppColor.brandSoft : AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: selected ? AppColor.brand : AppColor.border),
      ),
      child: Icon(
        slot.icon,
        color: selected ? AppColor.brandDeep : AppColor.inkTertiary,
      ),
    );
  }
}

class _RoutineRow extends StatelessWidget {
  final _RoutineItem item;
  final bool checked;
  final VoidCallback onTap;

  const _RoutineRow({
    required this.item,
    required this.checked,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColor.surface,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 64),
          padding: const EdgeInsets.all(AppSpace.md),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColor.border),
          ),
          child: Row(
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  color: checked ? AppColor.brand : Colors.transparent,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: checked ? AppColor.brand : AppColor.borderStrong,
                    width: 2,
                  ),
                ),
                child: checked
                    ? const Icon(
                        Icons.check_rounded,
                        size: 17,
                        color: AppColor.ink,
                      )
                    : null,
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      item.name,
                      style: AppText.body.copyWith(
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      item.dosage,
                      style: AppText.micro.copyWith(letterSpacing: 0),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              _KindPill(kind: item.kind),
            ],
          ),
        ),
      ),
    );
  }
}

class _KindPill extends StatelessWidget {
  final _RoutineKind kind;

  const _KindPill({required this.kind});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.sm,
        vertical: AppSpace.xs,
      ),
      decoration: BoxDecoration(
        color: kind.softColor,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        kind.label,
        style: AppText.micro.copyWith(
          color: kind.color,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _AnalysisResultCard extends StatelessWidget {
  final _AnalysisResult analysis;
  final VoidCallback onQuestion;

  const _AnalysisResultCard({required this.analysis, required this.onQuestion});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      color: const Color(0xFFFFFBEB),
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: analysis.iconColor,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(analysis.icon, color: AppColor.ink),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Text(
                  analysis.title,
                  style: AppText.subtitle.copyWith(
                    fontSize: 17,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          Text(
            analysis.description,
            style: AppText.body.copyWith(letterSpacing: 0),
          ),
          const SizedBox(height: AppSpace.md),
          for (final metric in analysis.metrics) ...[
            _AnalysisMetricRow(
              icon: metric.icon,
              label: metric.label,
              value: metric.value,
            ),
            if (metric != analysis.metrics.last)
              const SizedBox(height: AppSpace.sm),
          ],
          const SizedBox(height: AppSpace.md),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              key: Key('analysis-question-${analysis.id}'),
              onPressed: onQuestion,
              icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
              label: const Text('이 결과로 질문하기'),
              style: TextButton.styleFrom(
                foregroundColor: AppColor.brandDeep,
                textStyle: AppText.caption.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalysisMetricRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _AnalysisMetricRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColor.review),
        const SizedBox(width: AppSpace.sm),
        SizedBox(
          width: 72,
          child: Text(
            label,
            style: AppText.micro.copyWith(
              color: AppColor.review,
              letterSpacing: 0,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: AppText.caption.copyWith(
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
        ),
      ],
    );
  }
}

class _DailyPromiseTimeline extends StatelessWidget {
  final _MealSlot selectedSlot;
  final List<String> extraDirections;
  final Set<String> checkedPromiseIds;
  final ValueChanged<String>? onPromiseToggle;

  const _DailyPromiseTimeline({
    required this.selectedSlot,
    this.extraDirections = const [],
    this.checkedPromiseIds = const {},
    this.onPromiseToggle,
  });

  @override
  Widget build(BuildContext context) {
    final promises = [
      ..._dailyPromises,
      for (final indexed in extraDirections.indexed)
        _DailyPromise(
          id: 'analysis-${indexed.$1}',
          slot: _MealSlot.dinner,
          title: '분석 제안 약속',
          description: indexed.$2,
          highlighted: true,
        ),
    ];
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '오늘 하루 약속',
            style: AppText.subtitle.copyWith(fontSize: 18, letterSpacing: 0),
          ),
          const SizedBox(height: AppSpace.md),
          for (final promise in promises)
            _TimelinePromiseRow(
              promise: promise,
              selected: promise.slot == selectedSlot,
              checked: checkedPromiseIds.contains(promise.id),
              onToggle: onPromiseToggle == null
                  ? null
                  : () => onPromiseToggle!(promise.id),
              isLast: promise == promises.last,
            ),
        ],
      ),
    );
  }
}

class _TimelinePromiseRow extends StatelessWidget {
  final _DailyPromise promise;
  final bool selected;
  final bool checked;
  final VoidCallback? onToggle;
  final bool isLast;

  const _TimelinePromiseRow({
    required this.promise,
    required this.selected,
    required this.checked,
    required this.onToggle,
    required this.isLast,
  });

  @override
  Widget build(BuildContext context) {
    final color = selected || promise.highlighted
        ? AppColor.brandDeep
        : AppColor.inkTertiary;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 34,
            child: Column(
              children: [
                InkWell(
                  key: Key('promise-toggle-${promise.id}'),
                  customBorder: const CircleBorder(),
                  onTap: onToggle,
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: checked ? AppColor.brand : AppColor.surface,
                      shape: BoxShape.circle,
                      border: Border.all(color: color, width: 2),
                    ),
                    child: checked
                        ? const Icon(
                            Icons.check_rounded,
                            size: 16,
                            color: AppColor.ink,
                          )
                        : null,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(width: 2, color: AppColor.borderStrong),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                left: AppSpace.sm,
                bottom: isLast ? 0 : AppSpace.lg,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    promise.title,
                    style: AppText.body.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: AppSpace.xs),
                  Text(
                    promise.description,
                    style: AppText.caption.copyWith(letterSpacing: 0),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatbotTab extends StatelessWidget {
  final _AttachmentKind attachment;
  final _AnalysisResult? forwardedAnalysis;
  final VoidCallback onAddPressed;
  final VoidCallback onClearAttachment;

  const _ChatbotTab({
    required this.attachment,
    required this.forwardedAnalysis,
    required this.onAddPressed,
    required this.onClearAttachment,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(
            AppSpace.page,
            AppSpace.lg,
            AppSpace.page,
            AppSpace.md,
          ),
          child: _PrototypeHeader(
            eyebrow: '챗봇',
            title: '대화와 질문 사진만 관리합니다',
            subtitle: '첨부 사진은 질문용 임시 사진으로만 표시',
          ),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.page,
              AppSpace.sm,
              AppSpace.page,
              AppSpace.lg,
            ),
            children: const [
              _MessageBubble(text: '오늘 아침 식단과 영양제를 같이 봐줄 수 있어?', mine: true),
              SizedBox(height: AppSpace.sm),
              _MessageBubble(
                text: '네. 사진을 첨부하면 현재 루틴과 함께 질문 맥락으로만 참고할게요.',
                mine: false,
              ),
              SizedBox(height: AppSpace.sm),
              _MessageBubble(
                text: '사진은 기본 저장하지 않고 이 질문에만 임시로 연결됩니다.',
                mine: false,
              ),
            ],
          ),
        ),
        if (forwardedAnalysis != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.page,
              0,
              AppSpace.page,
              AppSpace.md,
            ),
            child: _ForwardedAnalysisPreview(analysis: forwardedAnalysis!),
          ),
        _ChatInputArea(
          attachment: attachment,
          onAddPressed: onAddPressed,
          onClearAttachment: onClearAttachment,
        ),
      ],
    );
  }
}

class _ForwardedAnalysisPreview extends StatelessWidget {
  final _AnalysisResult analysis;

  const _ForwardedAnalysisPreview({required this.analysis});

  @override
  Widget build(BuildContext context) {
    return _MessageBubble(
      text: '${analysis.title}\n${analysis.description}',
      mine: true,
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final String text;
  final bool mine;

  const _MessageBubble({required this.text, required this.mine});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 300),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.lg,
          vertical: AppSpace.md,
        ),
        decoration: BoxDecoration(
          color: mine ? AppColor.brand : AppColor.surface,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(AppRadius.lg),
            topRight: const Radius.circular(AppRadius.lg),
            bottomLeft: Radius.circular(mine ? AppRadius.lg : AppRadius.xs),
            bottomRight: Radius.circular(mine ? AppRadius.xs : AppRadius.lg),
          ),
          border: Border.all(color: mine ? AppColor.brand : AppColor.border),
          boxShadow: mine ? null : AppShadow.elev1,
        ),
        child: Text(text, style: AppText.body.copyWith(letterSpacing: 0)),
      ),
    );
  }
}

class _ChatInputArea extends StatelessWidget {
  final _AttachmentKind attachment;
  final VoidCallback onAddPressed;
  final VoidCallback onClearAttachment;

  const _ChatInputArea({
    required this.attachment,
    required this.onAddPressed,
    required this.onClearAttachment,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.md,
        AppSpace.page,
        MediaQuery.of(context).padding.bottom + AppSpace.md,
      ),
      decoration: const BoxDecoration(
        color: AppColor.surface,
        border: Border(top: BorderSide(color: AppColor.border)),
      ),
      child: Column(
        children: [
          if (attachment != _AttachmentKind.none) ...[
            _AttachmentPreview(
              attachment: attachment,
              onClear: onClearAttachment,
            ),
            const SizedBox(height: AppSpace.md),
          ],
          Row(
            children: [
              Tooltip(
                message: '사진 첨부',
                child: _RoundIconButton(
                  icon: Icons.add_rounded,
                  onTap: onAddPressed,
                ),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Container(
                  height: 48,
                  padding: const EdgeInsets.symmetric(horizontal: AppSpace.lg),
                  decoration: BoxDecoration(
                    color: AppColor.sunken,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    border: Border.all(color: AppColor.border),
                  ),
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '식단이나 복용 루틴에 대해 질문하기',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppText.caption.copyWith(
                      color: AppColor.inkTertiary,
                      letterSpacing: 0,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: AppSpace.md),
              Tooltip(
                message: '전송',
                child: _RoundIconButton(
                  icon: Icons.arrow_upward_rounded,
                  filled: true,
                  onTap: () => HapticFeedback.lightImpact(),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AttachmentPreview extends StatelessWidget {
  final _AttachmentKind attachment;
  final VoidCallback onClear;

  const _AttachmentPreview({required this.attachment, required this.onClear});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.brandSoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColor.brandTint),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColor.surface,
              borderRadius: BorderRadius.circular(AppRadius.sm),
              border: Border.all(color: AppColor.border),
            ),
            child: Icon(attachment.icon, color: AppColor.brandDeep),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  attachment.label,
                  style: AppText.caption.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                Text(
                  '질문에 첨부된 임시 사진',
                  style: AppText.micro.copyWith(letterSpacing: 0),
                ),
              ],
            ),
          ),
          Tooltip(
            message: '첨부 제거',
            child: IconButton(
              onPressed: onClear,
              icon: const Icon(Icons.close_rounded),
              color: AppColor.inkSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RoundIconButton extends StatelessWidget {
  final IconData icon;
  final bool filled;
  final VoidCallback onTap;

  const _RoundIconButton({
    required this.icon,
    required this.onTap,
    this.filled = false,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: filled ? AppColor.brand : AppColor.sunken,
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: SizedBox(
          width: 48,
          height: 48,
          child: Icon(
            icon,
            color: filled ? AppColor.ink : AppColor.inkSecondary,
          ),
        ),
      ),
    );
  }
}

class _AttachmentActionSheet extends StatelessWidget {
  const _AttachmentActionSheet();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.all(AppSpace.md),
        padding: const EdgeInsets.all(AppSpace.lg),
        decoration: BoxDecoration(
          color: AppColor.surface,
          borderRadius: BorderRadius.circular(AppRadius.xl),
          boxShadow: AppShadow.elev3,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '사진 첨부',
              style: AppText.subtitle.copyWith(fontSize: 18, letterSpacing: 0),
            ),
            const SizedBox(height: AppSpace.md),
            _SheetActionRow(
              icon: Icons.photo_camera_rounded,
              title: '카메라로 찍기',
              subtitle: '실제 카메라 호출 없이 임시 첨부로 표시',
              onTap: () => Navigator.of(context).pop(_AttachmentKind.camera),
            ),
            const SizedBox(height: AppSpace.sm),
            _SheetActionRow(
              icon: Icons.photo_library_rounded,
              title: '사진 업로드',
              subtitle: '선택한 사진을 질문용 임시 사진으로 표시',
              onTap: () => Navigator.of(context).pop(_AttachmentKind.upload),
            ),
          ],
        ),
      ),
    );
  }
}

class _SheetActionRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _SheetActionRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColor.sunken,
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 72),
          padding: const EdgeInsets.all(AppSpace.md),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppColor.surface,
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  border: Border.all(color: AppColor.border),
                ),
                child: Icon(icon, color: AppColor.inkSecondary),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      style: AppText.body.copyWith(
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0,
                      ),
                    ),
                    Text(
                      subtitle,
                      style: AppText.micro.copyWith(letterSpacing: 0),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

class _BottomTabs extends StatelessWidget {
  final _PrototypeTab currentTab;
  final ValueChanged<_PrototypeTab> onTabChanged;

  const _BottomTabs({required this.currentTab, required this.onTabChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.sm,
        AppSpace.page,
        MediaQuery.of(context).padding.bottom + AppSpace.sm,
      ),
      decoration: const BoxDecoration(
        color: AppColor.surface,
        border: Border(top: BorderSide(color: AppColor.border)),
      ),
      child: Row(
        children: [
          for (final tab in _PrototypeTab.values)
            Expanded(
              child: _BottomTabButton(
                tab: tab,
                selected: currentTab == tab,
                onTap: () => onTabChanged(tab),
              ),
            ),
        ],
      ),
    );
  }
}

class _BottomTabButton extends StatelessWidget {
  final _PrototypeTab tab;
  final bool selected;
  final VoidCallback onTap;

  const _BottomTabButton({
    required this.tab,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.md),
          onTap: onTap,
          child: SizedBox(
            height: 56,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  tab.icon,
                  color: selected ? AppColor.brandDeep : AppColor.inkTertiary,
                ),
                const SizedBox(height: 3),
                Text(
                  tab.label,
                  style: AppText.micro.copyWith(
                    color: selected ? AppColor.brandDeep : AppColor.inkTertiary,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
