import 'dart:async';
import 'package:flutter/material.dart';
import '../theme/eva_tokens.dart';
import '../theme/theme_notifier.dart';
import '../services/api_client.dart';

class TopPanel extends StatefulWidget {
  final ThemeNotifier themeNotifier;
  final String activeSectionName;
  final VoidCallback onOpenSettings;
  final VoidCallback? onToggleMic;
  final VoidCallback? onToggleTts;
  final VoidCallback? onStopSpeech;
  final String micStatusText;
  final IconData micStatusIcon;
  final Color micStatusColor;
  final bool ttsSpeaking;

  const TopPanel({
    super.key,
    required this.themeNotifier,
    required this.activeSectionName,
    required this.onOpenSettings,
    this.onToggleMic,
    this.onToggleTts,
    this.onStopSpeech,
    this.micStatusText = 'Mic Ready',
    this.micStatusIcon = Icons.mic_rounded,
    this.micStatusColor = const Color(0xFFA3AAA9),
    this.ttsSpeaking = false,
  });

  @override
  State<TopPanel> createState() => _TopPanelState();
}

class _TopPanelState extends State<TopPanel> {
  bool _backendOnline = false;
  Timer? _statusTimer;
  Timer? _clockTimer;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _checkHealth();
    _statusTimer = Timer.periodic(const Duration(seconds: 4), (_) => _checkHealth());
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    _clockTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkHealth() async {
    final ok = await EvaApiClient.isBackendHealthy();
    if (mounted && ok != _backendOnline) {
      setState(() => _backendOnline = ok);
    }
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  String _formatDate(DateTime dt) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    final weekday = weekdays[dt.weekday - 1];
    final month = months[dt.month - 1];
    return '$weekday, $month ${dt.day}';
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    return Container(
      height: EvaTokens.topBarHeight,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: palette.panel.withValues(alpha: widget.themeNotifier.panelOpacity),
        border: Border(bottom: BorderSide(color: palette.border)),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final showDate = constraints.maxWidth >= 960;

          return Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // ── Left: EVA Branding & Workspace Indicator ───────────────────
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.12),
                      borderRadius: EvaTokens.borderSm,
                      border: Border.all(color: accent.withValues(alpha: 0.35)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.terminal_rounded, size: 14, color: accent),
                        const SizedBox(width: 6),
                        Text(
                          'EVA AI OS',
                          style: TextStyle(
                            color: palette.textPri,
                            fontSize: 11.5 * scale,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.6,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: palette.surface.withValues(alpha: 0.8),
                      borderRadius: EvaTokens.borderSm,
                      border: Border.all(color: palette.borderSubtle),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.folder_shared_outlined, size: 13, color: palette.textSec),
                        const SizedBox(width: 5),
                        Text(
                          'workspace',
                          style: TextStyle(
                            color: palette.textSec,
                            fontSize: 11 * scale,
                            fontFamily: 'monospace',
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text('•', style: TextStyle(color: palette.border, fontSize: 10)),
                        const SizedBox(width: 6),
                        Text(
                          widget.activeSectionName,
                          style: TextStyle(
                            color: palette.textPri,
                            fontSize: 11 * scale,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              // ── Center Date / Clock Pill ─────────────────────────────────────
              if (showDate)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                  decoration: BoxDecoration(
                    color: palette.surface.withValues(alpha: 0.6),
                    borderRadius: EvaTokens.borderPill,
                    border: Border.all(color: palette.borderSubtle),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _formatDate(_now),
                        style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _formatTime(_now),
                        style: TextStyle(
                          color: palette.textPri,
                          fontSize: 11.5 * scale,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),

              // ── Right Action Badges & Controls ──────────────────────────────
              Flexible(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  reverse: true,
                  physics: const ClampingScrollPhysics(),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // ── Microphone Status ────────────────────────────────────
                      Tooltip(
                        message: 'Microphone status (${widget.micStatusText})',
                        child: InkWell(
                          onTap: widget.onToggleMic,
                          borderRadius: EvaTokens.borderSm,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(
                              color: widget.micStatusColor.withValues(alpha: 0.1),
                              borderRadius: EvaTokens.borderSm,
                              border: Border.all(color: widget.micStatusColor.withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(widget.micStatusIcon, size: 13, color: widget.micStatusColor),
                                const SizedBox(width: 4),
                                Text(
                                  widget.micStatusText,
                                  style: TextStyle(
                                    color: widget.micStatusColor,
                                    fontSize: 10.5 * scale,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),

                      // ── Voice Output / TTS Status ────────────────────────────
                      Tooltip(
                        message: widget.ttsSpeaking
                            ? 'Piper TTS is speaking (Click to stop)'
                            : (widget.themeNotifier.ttsEnabled ? 'Voice output enabled' : 'Voice output disabled'),
                        child: InkWell(
                          onTap: widget.ttsSpeaking ? widget.onStopSpeech : widget.onToggleTts,
                          borderRadius: EvaTokens.borderSm,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(
                              color: (widget.ttsSpeaking ? palette.warning : (widget.themeNotifier.ttsEnabled ? accent : palette.border))
                                  .withValues(alpha: 0.1),
                              borderRadius: EvaTokens.borderSm,
                              border: Border.all(
                                color: (widget.ttsSpeaking ? palette.warning : (widget.themeNotifier.ttsEnabled ? accent : palette.border))
                                    .withValues(alpha: 0.3),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  widget.ttsSpeaking
                                      ? Icons.volume_up_rounded
                                      : (widget.themeNotifier.ttsEnabled ? Icons.volume_up_outlined : Icons.volume_off_outlined),
                                  size: 13,
                                  color: widget.ttsSpeaking ? palette.warning : (widget.themeNotifier.ttsEnabled ? accent : palette.textSec),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  widget.ttsSpeaking ? 'Speaking' : (widget.themeNotifier.ttsEnabled ? 'TTS On' : 'TTS Off'),
                                  style: TextStyle(
                                    color: widget.ttsSpeaking ? palette.warning : (widget.themeNotifier.ttsEnabled ? accent : palette.textSec),
                                    fontSize: 10.5 * scale,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),

                      // ── System / Backend Health ──────────────────────────────
                      Tooltip(
                        message: _backendOnline ? 'EVA Core 127.0.0.1:8000 (Connected)' : 'EVA Core (Offline / Starting)',
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                          decoration: BoxDecoration(
                            color: (_backendOnline ? palette.success : palette.error).withValues(alpha: 0.1),
                            borderRadius: EvaTokens.borderSm,
                            border: Border.all(color: (_backendOnline ? palette.success : palette.error).withValues(alpha: 0.3)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 7,
                                height: 7,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: _backendOnline ? palette.success : palette.error,
                                ),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                _backendOnline ? 'Core Online' : 'Core Offline',
                                style: TextStyle(
                                  color: _backendOnline ? palette.success : palette.error,
                                  fontSize: 10.5 * scale,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),

                      // ── Agentic Voice Mode Toggle ──────────────────────────
                      Tooltip(
                        message: widget.themeNotifier.agenticVoiceActive
                            ? 'Agentic Voice Mode Active: Hands-free listening enabled. Click to pause.'
                            : 'Enable Agentic Voice Mode (Hands-free autonomous listening)',
                        child: InkWell(
                          onTap: () async {
                            final next = !widget.themeNotifier.agenticVoiceActive;
                            widget.themeNotifier.setAgenticVoiceActive(next);
                            if (next) {
                              await EvaApiClient.startAgenticVoice();
                            } else {
                              await EvaApiClient.stopAgenticVoice();
                            }
                          },
                          borderRadius: EvaTokens.borderSm,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: (widget.themeNotifier.agenticVoiceActive ? accent : palette.panel)
                                  .withValues(alpha: widget.themeNotifier.agenticVoiceActive ? 0.2 : 0.6),
                              borderRadius: EvaTokens.borderSm,
                              border: Border.all(
                                color: widget.themeNotifier.agenticVoiceActive ? accent : palette.border,
                                width: widget.themeNotifier.agenticVoiceActive ? 1.5 : 1.0,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  widget.themeNotifier.agenticVoiceActive ? Icons.graphic_eq_rounded : Icons.auto_mode_rounded,
                                  size: 13,
                                  color: widget.themeNotifier.agenticVoiceActive ? accent : palette.textSec,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  widget.themeNotifier.agenticVoiceActive ? 'Agentic Voice' : 'Agentic Mode',
                                  style: TextStyle(
                                    color: widget.themeNotifier.agenticVoiceActive ? accent : palette.textSec,
                                    fontSize: 10.5 * scale,
                                    fontWeight: widget.themeNotifier.agenticVoiceActive ? FontWeight.w700 : FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),

                      // ── Emergency Stop Button ───────────────────────────────
                      Tooltip(
                        message: 'Emergency Stop: Instantly halt all active agent executions, speech output, and recording',
                        child: InkWell(
                          onTap: () async {
                            widget.themeNotifier.setAgenticVoiceActive(false);
                            await EvaApiClient.emergencyStopAgenticVoice();
                            widget.onStopSpeech?.call();
                          },
                          borderRadius: EvaTokens.borderSm,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                            decoration: BoxDecoration(
                              color: palette.error.withValues(alpha: 0.15),
                              borderRadius: EvaTokens.borderSm,
                              border: Border.all(color: palette.error.withValues(alpha: 0.4)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.stop_circle_outlined, size: 13, color: palette.error),
                                const SizedBox(width: 4),
                                Text(
                                  'HALT',
                                  style: TextStyle(
                                    color: palette.error,
                                    fontSize: 10 * scale,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.5,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),

                      // ── Settings Shortcut ────────────────────────────────────
                      Tooltip(
                        message: 'Desktop Settings',
                        child: IconButton(
                          icon: const Icon(Icons.settings_outlined, size: 16),
                          color: palette.textSec,
                          onPressed: widget.onOpenSettings,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
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
}
