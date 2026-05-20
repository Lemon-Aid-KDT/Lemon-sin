// screens/camera_screen.dart — 영양제·식단 인앱 라이브 프리뷰
//
// 디자인 (Pillyze/토스 톤, LADS v2):
//   - 풀스크린 검정 BG (탭바 숨김 — MainShell 에서 처리)
//   - 카메라 라이브 프리뷰 (가이드 프레임 안)
//   - 4 모서리 강조 + 안내 텍스트
//   - 하단: 모드 토글 (영양제/식단) + 큰 셔터 + 갤러리
//   - 촬영 → 인앱 미리보기 → 분석하기 / 다시 촬영
//
// camera 패키지: 라이브 프리뷰 + takePicture()
// image_picker 는 갤러리 진입용으로만 사용
//
// 권한 (AndroidManifest / iOS Info.plist) 박혀있어야 함 — 이미 박혔음

import 'dart:io';
import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../utils/design_tokens_v2.dart';
import '../utils/device_env.dart';

enum _CaptureMode { supplement, meal }

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with WidgetsBindingObserver {
  _CaptureMode _mode = _CaptureMode.supplement;
  File? _captured;
  bool _picking = false;

  // ─── 카메라 컨트롤러 ───
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _initializing = true;
  String? _initError;
  // 카메라 방향 — 기본 후면 (영양제 라벨 촬영 가정)
  // 전면(셀카) 은 실기기에서만 의미 있음. 에뮬에서는 빈 화면.
  CameraLensDirection _lens = CameraLensDirection.back;
  // 에뮬 여부 — 카메라 영상 정렬 보정용
  bool _isEmulator = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // 동기 캐시 먼저 (warmUp 됐으면 즉시 반영)
    _isEmulator = DeviceEnv.isEmulatorSync;
    // 비동기 한 번 더 확정 (warmUp 늦었어도 잡힘)
    DeviceEnv.isEmulator.then((v) {
      if (mounted && _isEmulator != v) {
        setState(() => _isEmulator = v);
      }
    });
    _initCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disposeCamera();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden) {
      _disposeCamera();
      if (mounted) {
        setState(() {
          _initializing = false;
          _initError = null;
        });
      }
    } else if (state == AppLifecycleState.resumed) {
      if (mounted && _captured == null) {
        _initCamera();
      }
    }
  }

  bool _initInFlight = false;

  Future<void> _initCamera() async {
    // 동시 진입 방지
    if (_initInFlight) return;
    _initInFlight = true;
    // 이미 살아있으면 스킵
    if (_controller != null && _controller!.value.isInitialized) {
      _initInFlight = false;
      if (mounted && _initializing) {
        setState(() => _initializing = false);
      }
      return;
    }
    if (mounted) {
      setState(() {
        _initializing = true;
        _initError = null;
      });
    }
    try {
      _cameras ??= await availableCameras();
      if (_cameras == null || _cameras!.isEmpty) {
        if (mounted) {
          setState(() {
            _initError = '연결된 카메라가 없어요';
            _initializing = false;
          });
        }
        return;
      }
      // 셀카(전면)면 빈 화면으로만 두고 카메라 컨트롤러 안 만듦.
      // 에뮬에서는 노트북캠이 후면으로 잡혀있고 전면은 None → 셀카 시 검정.
      if (_lens == CameraLensDirection.front) {
        if (mounted) {
          setState(() {
            _controller = null;
            _initializing = false;
            _initError = null;
          });
        }
        return;
      }
      // 후면 우선 (영양제 라벨 촬영 용도)
      final cam = _cameras!.firstWhere(
        (c) => c.lensDirection == _lens,
        orElse: () => _cameras!.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.back,
          orElse: () => _cameras!.first,
        ),
      );
      final controller = CameraController(
        cam,
        ResolutionPreset.high,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _initializing = false;
        _initError = null;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _initError = '카메라를 열 수 없어요\n${e.toString()}';
          _initializing = false;
        });
      }
    } finally {
      _initInFlight = false;
    }
  }

  Future<void> _disposeCamera() async {
    final c = _controller;
    _controller = null;
    await c?.dispose();
  }

  Future<void> _shutter() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized || _picking) return;
    setState(() => _picking = true);
    HapticFeedback.mediumImpact();
    try {
      final XFile shot = await c.takePicture();
      if (mounted) {
        setState(() => _captured = File(shot.path));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('촬영을 못 했어요 · ${e.toString()}'),
            backgroundColor: AppColor.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _picking = false);
    }
  }

  // 카메라 전후면 토글
  Future<void> _toggleLens() async {
    HapticFeedback.selectionClick();
    final next = _lens == CameraLensDirection.back
        ? CameraLensDirection.front
        : CameraLensDirection.back;
    // 기존 컨트롤러 정리 후 재초기화
    await _disposeCamera();
    if (!mounted) return;
    setState(() {
      _lens = next;
      _initializing = true;
      _initError = null;
    });
    await _initCamera();
  }

  Future<void> _pickFromGallery() async {
    if (_picking) return;
    setState(() => _picking = true);
    HapticFeedback.lightImpact();
    try {
      final picker = ImagePicker();
      final XFile? file = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1600,
        imageQuality: 88,
      );
      if (file != null && mounted) {
        setState(() => _captured = File(file.path));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('갤러리를 못 열었어요 · ${e.toString()}'),
            backgroundColor: AppColor.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _picking = false);
    }
  }

  void _retake() {
    HapticFeedback.selectionClick();
    setState(() => _captured = null);
  }

  void _analyze() {
    if (_captured == null) return;
    HapticFeedback.mediumImpact();
    final modeArg = _mode == _CaptureMode.supplement ? 'supplement' : 'meal';
    context.push('/analysis-result?mode=$modeArg');
  }

  @override
  Widget build(BuildContext context) {
    // 화면 재진입 시 컨트롤러 죽어있으면 다시 켜기
    if (_captured == null &&
        !_initializing &&
        _initError == null &&
        (_controller == null || !_controller!.value.isInitialized)) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _initCamera();
      });
    }
    return Scaffold(
      backgroundColor: Colors.black,
      // 풀스크린 — body 가 화면 끝까지. SafeArea 는 컨트롤 위젯 안에서 처리.
      body: _captured == null ? _buildCapture() : _buildPreview(),
    );
  }

  // ─── 촬영 화면 (가이드 프레임 안에 라이브 프리뷰) ───
  Widget _buildCapture() {
    return Stack(
      fit: StackFit.expand,
      children: [
        _FullScreenPreview(
          controller: _controller,
          initializing: _initializing,
          error: _initError,
          isFront: _lens == CameraLensDirection.front,
          isEmulator: _isEmulator,
        ),
        _GuideOverlay(mode: _mode),
        Positioned(
          top: 0, left: 0, right: 0,
          child: SafeArea(
            bottom: false,
            child: _TopBar(
              mode: _mode,
              onClose: () =>
                  context.canPop() ? context.pop() : context.go('/shell/home'),
              onFlip: _toggleLens,
              isFront: _lens == CameraLensDirection.front,
            ),
          ),
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: SafeArea(
            top: false,
            child: _BottomControls(
              mode: _mode,
              onModeChange: (m) {
                HapticFeedback.selectionClick();
                setState(() => _mode = m);
              },
              onShutter: _shutter,
              onGallery: _pickFromGallery,
              loading: _picking,
              enabled: _controller?.value.isInitialized == true,
            ),
          ),
        ),
      ],
    );
  }

  // ─── 미리보기 (촬영 후) ───
  Widget _buildPreview() {
    return Column(
      children: [
        _TopBar(
          mode: _mode,
          title: '미리보기',
          onClose: _retake,
          closeIcon: Icons.arrow_back_rounded,
        ),
        const SizedBox(height: AppSpace.md),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.page),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.lg),
              child: Image.file(
                _captured!,
                fit: BoxFit.cover,
                width: double.infinity,
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.page),
          child: Row(
            children: [
              Expanded(
                child: _GhostButton(
                  label: '다시 촬영',
                  icon: Icons.refresh_rounded,
                  onTap: _retake,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                flex: 2,
                child: _PrimaryButton(
                  label: '분석하기',
                  onTap: _analyze,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.lg),
      ],
    );
  }
}

// ═══════════════════════════════════════════
// 상단 바
// ═══════════════════════════════════════════
class _TopBar extends StatelessWidget {
  final _CaptureMode mode;
  final VoidCallback onClose;
  final String? title;
  final IconData closeIcon;
  final VoidCallback? onFlip;
  final bool isFront;
  const _TopBar({
    required this.mode,
    required this.onClose,
    this.title,
    this.closeIcon = Icons.close_rounded,
    this.onFlip,
    this.isFront = false,
  });

  @override
  Widget build(BuildContext context) {
    final modeLabel = mode == _CaptureMode.supplement ? '영양제' : '식단';
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.md,
        AppSpace.page,
        0,
      ),
      child: Row(
        children: [
          _RoundIcon(icon: closeIcon, onTap: onClose),
          const Spacer(),
          Text(
            title ?? '$modeLabel 촬영',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          const Spacer(),
          // 우측: 카메라 전환 버튼 (회전 아이콘 고정)
          if (onFlip != null)
            _RoundIcon(
              icon: Icons.cameraswitch_rounded,
              onTap: onFlip!,
            )
          else
            const SizedBox(width: 48, height: 48),
        ],
      ),
    );
  }
}

class _RoundIcon extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _RoundIcon({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.10),
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(icon, color: Colors.white, size: 22),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// 풀스크린 라이브 프리뷰
//   - 화면 전체에 카메라 영상을 cover 로 깐다
//   - 비율 계산 없이 FittedBox 정중앙 cover
// ═══════════════════════════════════════════
class _FullScreenPreview extends StatelessWidget {
  final CameraController? controller;
  final bool initializing;
  final String? error;
  final bool isFront;
  final bool isEmulator;
  const _FullScreenPreview({
    required this.controller,
    required this.initializing,
    required this.error,
    this.isFront = false,
    this.isEmulator = false,
  });

  @override
  Widget build(BuildContext context) {
    // 셀카 모드 — 에뮬에서는 전면 카메라가 None 이므로 빈 검정 화면
    if (isFront) {
      return Container(color: Colors.black);
    }
    if (initializing) {
      return Container(
        color: Colors.black,
        alignment: Alignment.center,
        child: _SpinnerWithLabel(label: '카메라를 켜는 중이에요'),
      );
    }
    if (error != null) {
      return Container(
        color: Colors.black,
        alignment: Alignment.center,
        child: _ErrorBox(message: error!),
      );
    }
    final c = controller;
    if (c == null || !c.value.isInitialized) {
      return Container(
        color: Colors.black,
        alignment: Alignment.center,
        child: _SpinnerWithLabel(label: '카메라를 켜는 중이에요'),
      );
    }
    final size = c.value.previewSize;
    if (size == null) {
      return Container(color: Colors.black);
    }
    // 풀스크린 cover — 안드로이드 previewSize 는 가로 좌표계라 세로 화면 그릴 때 swap.
    // FittedBox(cover, center) 가 정중앙 기준으로 양쪽 똑같이 자름.
    //
    // 에뮬/실기기 동일 — 정상 cover, 보정 없음.
    // 에뮬에서 사람이 우측에 보이는 건 노트북 웹캠 구도 문제.
    // 실기기 (휴대폰) 에서는 사용자가 휴대폰을 들고 피사체를 가운데에 두는 거라
    // 코드 보정 불필요.
    return ClipRect(
      child: SizedBox.expand(
        child: FittedBox(
          fit: BoxFit.cover,
          alignment: Alignment.center,
          child: SizedBox(
            width: size.height,
            height: size.width,
            child: CameraPreview(c),
          ),
        ),
      ),
    );
  }
}

class _GuideOverlay extends StatelessWidget {
  final _CaptureMode mode;
  const _GuideOverlay({required this.mode});

  @override
  Widget build(BuildContext context) {
    final hint = mode == _CaptureMode.supplement
        ? '성분표를 화면 안에 또렷하게 맞춰주세요'
        : '음식 전체가 화면 안에 들어오게 맞춰주세요';

    return IgnorePointer(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = Size(constraints.maxWidth, constraints.maxHeight);
          final rect = _guideRect(size);

          return Stack(
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: _GuideMaskPainter(
                    guideRect: rect,
                    radius: AppRadius.lg,
                  ),
                ),
              ),
              Positioned.fromRect(
                rect: rect,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.34),
                      width: 1,
                    ),
                  ),
                  child: Stack(
                    children: [
                      Positioned(
                        top: 14,
                        left: 14,
                        child: _Corner(corner: _CornerType.tl),
                      ),
                      Positioned(
                        top: 14,
                        right: 14,
                        child: _Corner(corner: _CornerType.tr),
                      ),
                      Positioned(
                        bottom: 14,
                        left: 14,
                        child: _Corner(corner: _CornerType.bl),
                      ),
                      Positioned(
                        bottom: 14,
                        right: 14,
                        child: _Corner(corner: _CornerType.br),
                      ),
                      Align(
                        alignment: Alignment.bottomCenter,
                        child: Container(
                          margin: const EdgeInsets.all(AppSpace.lg),
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpace.lg,
                            vertical: AppSpace.md,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.58),
                            borderRadius: BorderRadius.circular(AppRadius.full),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.18),
                            ),
                          ),
                          child: Text(
                            hint,
                            textAlign: TextAlign.center,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              height: 1.35,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Rect _guideRect(Size size) {
    final aspect = mode == _CaptureMode.supplement ? 0.72 : 1.0;
    final topReserved = math.min(112.0, size.height * 0.18);
    final bottomReserved = math.min(212.0, size.height * 0.28);
    final usableHeight =
        math.max(220.0, size.height - topReserved - bottomReserved);
    final maxWidth =
        math.max(1.0, math.min(size.width - (AppSpace.page * 2), 420.0));
    final maxHeight = math.min(
      usableHeight,
      mode == _CaptureMode.supplement ? 520.0 : 420.0,
    );

    var width = math.min(maxWidth, maxHeight * aspect);
    var height = width / aspect;
    if (height > maxHeight) {
      height = maxHeight;
      width = height * aspect;
    }

    return Rect.fromCenter(
      center: Offset(size.width / 2, topReserved + usableHeight / 2),
      width: width,
      height: height,
    );
  }
}

class _GuideMaskPainter extends CustomPainter {
  final Rect guideRect;
  final double radius;
  const _GuideMaskPainter({required this.guideRect, required this.radius});

  @override
  void paint(Canvas canvas, Size size) {
    final hole = RRect.fromRectAndRadius(
      guideRect,
      Radius.circular(radius),
    );
    final paint = Paint()..color = Colors.black.withValues(alpha: 0.48);
    final outer = Path()..addRect(Offset.zero & size);
    final inner = Path()..addRRect(hole);
    final mask = Path.combine(PathOperation.difference, outer, inner);
    canvas.drawPath(mask, paint);
  }

  @override
  bool shouldRepaint(_GuideMaskPainter oldDelegate) {
    return oldDelegate.guideRect != guideRect || oldDelegate.radius != radius;
  }
}

class _SpinnerWithLabel extends StatelessWidget {
  final String label;
  const _SpinnerWithLabel({required this.label});
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.6,
            valueColor: AlwaysStoppedAnimation<Color>(AppColor.brand),
          ),
        ),
        const SizedBox(height: AppSpace.md),
        Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.72),
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  const _ErrorBox({required this.message});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.no_photography_rounded,
            color: Colors.white.withValues(alpha: 0.4),
            size: 48,
          ),
          const SizedBox(height: AppSpace.md),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.72),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

enum _CornerType { tl, tr, bl, br }

class _Corner extends StatelessWidget {
  final _CornerType corner;
  const _Corner({required this.corner});

  @override
  Widget build(BuildContext context) {
    const len = 32.0;
    const thick = 4.0;
    final color = AppColor.brand;
    const radius = Radius.circular(2);
    BorderSide side(bool show) =>
        show ? BorderSide(color: color, width: thick) : BorderSide.none;
    Border border;
    BorderRadius br;
    switch (corner) {
      case _CornerType.tl:
        border = Border(top: side(true), left: side(true));
        br = const BorderRadius.only(topLeft: radius);
        break;
      case _CornerType.tr:
        border = Border(top: side(true), right: side(true));
        br = const BorderRadius.only(topRight: radius);
        break;
      case _CornerType.bl:
        border = Border(bottom: side(true), left: side(true));
        br = const BorderRadius.only(bottomLeft: radius);
        break;
      case _CornerType.br:
        border = Border(bottom: side(true), right: side(true));
        br = const BorderRadius.only(bottomRight: radius);
        break;
    }
    return Container(
      width: len,
      height: len,
      decoration: BoxDecoration(border: border, borderRadius: br),
    );
  }
}

// ═══════════════════════════════════════════
// 하단 컨트롤 — 모드 토글 + 셔터 + 갤러리
// ═══════════════════════════════════════════
class _BottomControls extends StatelessWidget {
  final _CaptureMode mode;
  final ValueChanged<_CaptureMode> onModeChange;
  final VoidCallback onShutter;
  final VoidCallback onGallery;
  final bool loading;
  final bool enabled;

  const _BottomControls({
    required this.mode,
    required this.onModeChange,
    required this.onShutter,
    required this.onGallery,
    required this.loading,
    required this.enabled,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.xxl,
        AppSpace.page,
        AppSpace.lg,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.black.withValues(alpha: 0.0),
            Colors.black.withValues(alpha: 0.78),
          ],
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ModeSegment(mode: mode, onChange: onModeChange),
          const SizedBox(height: AppSpace.lg),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 72,
                child: Align(
                  alignment: Alignment.centerRight,
                  child: _GalleryButton(onTap: onGallery),
                ),
              ),
              const SizedBox(width: AppSpace.xl),
              _ShutterButton(
                onTap: enabled ? onShutter : () {},
                loading: loading,
                enabled: enabled,
              ),
              const SizedBox(width: AppSpace.xl),
              const SizedBox(width: 72),
            ],
          ),
        ],
      ),
    );
  }
}

class _ModeSegment extends StatelessWidget {
  final _CaptureMode mode;
  final ValueChanged<_CaptureMode> onChange;
  const _ModeSegment({required this.mode, required this.onChange});

  @override
  Widget build(BuildContext context) {
    Widget item(_CaptureMode m, String label) {
      final active = m == mode;
      return Expanded(
        child: GestureDetector(
          onTap: () => onChange(m),
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            height: 48,
            decoration: BoxDecoration(
              color: active ? AppColor.brand : Colors.transparent,
              borderRadius: BorderRadius.circular(AppRadius.full),
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: TextStyle(
                color: active
                    ? AppColor.ink
                    : Colors.white.withValues(alpha: 0.65),
                fontSize: 17,
                fontWeight: active ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ),
        ),
      );
    }

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 320),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
          child: Row(
            children: [
              item(_CaptureMode.supplement, '영양제'),
              item(_CaptureMode.meal, '식단'),
            ],
          ),
        ),
      ),
    );
  }
}

class _ShutterButton extends StatelessWidget {
  final VoidCallback onTap;
  final bool loading;
  final bool enabled;
  const _ShutterButton({
    required this.onTap,
    required this.loading,
    required this.enabled,
  });

  @override
  Widget build(BuildContext context) {
    final opacity = enabled ? 1.0 : 0.4;
    return Semantics(
      button: true,
      label: '사진 촬영',
      child: Opacity(
        opacity: opacity,
        child: GestureDetector(
          onTap: loading ? null : onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 84,
            height: 84,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 4),
            ),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [AppColor.brandTint, AppColor.brand],
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColor.brand.withValues(alpha: 0.35),
                      blurRadius: 18,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: loading
                    ? const Center(
                        child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.6,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(AppColor.ink),
                          ),
                        ),
                      )
                    : null,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GalleryButton extends StatelessWidget {
  final VoidCallback onTap;
  const _GalleryButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '갤러리에서 선택',
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
          ),
          alignment: Alignment.center,
          child: const Icon(
            Icons.photo_library_rounded,
            color: Colors.white,
            size: 24,
          ),
        ),
      ),
    );
  }
}

// ═══════════════════════════════════════════
// CTA 버튼 (미리보기 화면용)
// ═══════════════════════════════════════════
class _PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _PrimaryButton({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColor.brandTint, AppColor.brand],
          ),
          borderRadius: BorderRadius.circular(AppRadius.md),
          boxShadow: [
            BoxShadow(
              color: AppColor.brand.withValues(alpha: 0.40),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: const TextStyle(
            color: AppColor.ink,
            fontSize: 17,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _GhostButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const _GhostButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 56,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 18),
            const SizedBox(width: AppSpace.xs),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
