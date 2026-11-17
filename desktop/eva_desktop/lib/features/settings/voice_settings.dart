import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class VoiceSettings extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const VoiceSettings({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<VoiceSettings> createState() => _VoiceSettingsState();
}

class _VoiceSettingsState extends State<VoiceSettings> {
  Map<String, dynamic>? _ttsStatus;

  @override
  void initState() {
    super.initState();
    _fetchVoiceState();
  }

  Future<void> _fetchVoiceState() async {
    final tts = await EvaApiClient.getTtsStatus();
    if (mounted) {
      setState(() {
        _ttsStatus = tts;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Speech-to-Text Status ─────────────────────────────────────────
          Text('SPEECH RECOGNITION (STT)', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(color: palette.border),
            ),
            child: Column(
              children: [
                _StatusItem(
                  palette: palette,
                  scale: scale,
                  title: 'Recognition Engine',
                  value: 'Faster-Whisper (local CPU inference)',
                  isOk: true,
                ),
                const Divider(height: 16),
                _StatusItem(
                  palette: palette,
                  scale: scale,
                  title: 'Audio Capture Backend',
                  value: 'arecord / ALSA (Linux PipeWire compatibility)',
                  isOk: true,
                ),
                const Divider(height: 16),
                _StatusItem(
                  palette: palette,
                  scale: scale,
                  title: 'Silence Detection',
                  value: 'Automated RMS energy monitoring active',
                  isOk: true,
                ),
                const SizedBox(height: 12),
                Material(
                  type: MaterialType.transparency,
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Voice Conversation Mode', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w500)),
                    subtitle: Text('Automatically send transcribed audio without requiring manual review', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    value: widget.themeNotifier.voiceMode,
                    activeThumbColor: accent,
                    onChanged: (v) => widget.themeNotifier.setVoiceMode(v),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Text-to-Speech Settings ───────────────────────────────────────
          Text('TEXT-TO-SPEECH (TTS)', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(color: palette.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Material(
                  type: MaterialType.transparency,
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Enable Spoken Voice Responses', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                    subtitle: Text('EVA uses local Piper TTS to read responses aloud', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    value: widget.themeNotifier.ttsEnabled,
                    activeThumbColor: accent,
                    onChanged: (v) => widget.themeNotifier.setTtsEnabled(v),
                  ),
                ),
                const Divider(height: 18),
                _StatusItem(
                  palette: palette,
                  scale: scale,
                  title: 'TTS Engine',
                  value: _ttsStatus?['engine'] ?? 'piper-tts (local ONNX)',
                  isOk: _ttsStatus?['error'] == null,
                ),
                const Divider(height: 16),
                _StatusItem(
                  palette: palette,
                  scale: scale,
                  title: 'Active Voice Model',
                  value: _ttsStatus?['voice'] ?? 'en_US-amy-medium',
                  isOk: true,
                ),
                const Divider(height: 18),
                Row(
                  children: [
                    Text('Speech Rate (${widget.themeNotifier.ttsSpeed.toStringAsFixed(1)}x)', style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale)),
                    const Spacer(),
                    SizedBox(
                      width: 240,
                      child: Slider(
                        value: widget.themeNotifier.ttsSpeed,
                        min: 0.5,
                        max: 2.0,
                        divisions: 15,
                        activeColor: accent,
                        inactiveColor: palette.panel,
                        onChanged: (v) => widget.themeNotifier.setTtsSpeed(v),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusItem extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String title;
  final String value;
  final bool isOk;

  const _StatusItem({
    required this.palette,
    required this.scale,
    required this.title,
    required this.value,
    required this.isOk,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(title, style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
        const Spacer(),
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(shape: BoxShape.circle, color: isOk ? palette.success : palette.error),
        ),
        const SizedBox(width: 6),
        Text(value, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
      ],
    );
  }
}
