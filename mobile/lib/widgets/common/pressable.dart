import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Source-style tap feedback wrapper for cards and buttons.
class Pressable extends StatefulWidget {
  /// Creates a pressable wrapper.
  ///
  /// Args:
  ///   child: Visual content to render.
  ///   onTap: Optional tap callback. When null, the child is not interactive.
  ///   pressedScale: Scale used while the pointer is down.
  ///   haptic: Whether to emit a light haptic signal on tap.
  const Pressable({
    required this.child,
    this.onTap,
    this.pressedScale = 0.97,
    this.haptic = true,
    super.key,
  });

  /// Wrapped content.
  final Widget child;

  /// Tap callback.
  final VoidCallback? onTap;

  /// Scale used while pressed.
  final double pressedScale;

  /// Whether haptics should run on tap.
  final bool haptic;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onTap == null
          ? null
          : () {
              if (widget.haptic) {
                HapticFeedback.lightImpact();
              }
              widget.onTap!();
            },
      onTapDown: widget.onTap == null ? null : (_) => _setPressed(true),
      onTapUp: widget.onTap == null ? null : (_) => _setPressed(false),
      onTapCancel: widget.onTap == null ? null : () => _setPressed(false),
      child: AnimatedScale(
        scale: _pressed ? widget.pressedScale : 1,
        duration: const Duration(milliseconds: 140),
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }

  void _setPressed(bool value) {
    if (_pressed == value) {
      return;
    }
    setState(() {
      _pressed = value;
    });
  }
}
