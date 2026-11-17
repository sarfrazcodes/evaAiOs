import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import 'appearance_settings.dart';
import 'voice_settings.dart';
import 'privacy_settings.dart';
import 'ai_provider_settings.dart';

class SettingsScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const SettingsScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  int _tab = 0;

  final List<Map<String, dynamic>> _tabs = [
    {'title': 'Appearance', 'icon': Icons.palette_outlined},
    {'title': 'AI Provider', 'icon': Icons.smart_toy_outlined},
    {'title': 'Voice & Audio', 'icon': Icons.record_voice_over_outlined},
    {'title': 'Privacy & Security', 'icon': Icons.shield_outlined},
    {'title': 'About EVA', 'icon': Icons.info_outline_rounded},
  ];

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    return Scaffold(
      backgroundColor: palette.bg,
      body: Column(
        children: [
          // Toolbar with Tab Navigation
          Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 20),
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border(bottom: BorderSide(color: palette.border)),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  Icon(Icons.tune_rounded, size: 16, color: accent),
                  const SizedBox(width: 8),
                  Text('System Preferences', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                  const SizedBox(width: 20),
                  for (int i = 0; i < _tabs.length; i++) ...[
                    InkWell(
                      onTap: () => setState(() => _tab = i),
                      borderRadius: EvaTokens.borderSm,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: _tab == i ? accent.withValues(alpha: 0.15) : Colors.transparent,
                          borderRadius: EvaTokens.borderSm,
                          border: _tab == i ? Border.all(color: accent.withValues(alpha: 0.4)) : null,
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _tabs[i]['icon'] as IconData,
                              size: 14,
                              color: _tab == i ? accent : palette.textSec,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              _tabs[i]['title'] as String,
                              style: TextStyle(
                                color: _tab == i ? accent : palette.textSec,
                                fontSize: 11.5 * scale,
                                fontWeight: _tab == i ? FontWeight.w600 : FontWeight.normal,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                ],
              ),
            ),
          ),

          // Main Tab Body
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 820),
                  child: _buildCurrentTab(palette, accent, scale),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrentTab(EvaPalette palette, Color accent, double scale) {
    switch (_tab) {
      case 0:
        return AppearanceSettings(themeNotifier: widget.themeNotifier);
      case 1:
        return AiProviderSettings(themeNotifier: widget.themeNotifier);
      case 2:
        return VoiceSettings(themeNotifier: widget.themeNotifier);
      case 3:
        return PrivacySettings(themeNotifier: widget.themeNotifier);
      case 4:
      default:
        return _AboutEvaView(palette: palette, accent: accent, scale: scale);
    }
  }
}

class _AboutEvaView extends StatelessWidget {
  final EvaPalette palette;
  final Color accent;
  final double scale;

  const _AboutEvaView({
    required this.palette,
    required this.accent,
    required this.scale,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: EvaTokens.borderMd,
        border: Border.all(color: palette.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.15),
                  borderRadius: EvaTokens.borderSm,
                  border: Border.all(color: accent.withValues(alpha: 0.4)),
                ),
                child: Icon(Icons.auto_awesome_rounded, color: accent, size: 22),
              ),
              const SizedBox(width: 14),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('EVA AI OS', style: TextStyle(color: palette.textPri, fontSize: 16 * scale, fontWeight: FontWeight.w700)),
                  Text('Engineered Linux Desktop Environment', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 12),
          Text(
            'EVA (Electronic Virtual Assistant) is a customized Linux desktop environment engineered with a multi-phase AI pipeline: '
            'lexicon fast-path matching, LLM intent classification, stateful task planning, permission risk validation, and allowlisted application lifecycle control.',
            style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, height: 1.5),
          ),
          const SizedBox(height: 16),
          Text('CORE ARCHITECTURE', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          _SpecItem(palette: palette, scale: scale, title: 'Frontend UI', value: 'Flutter Desktop 3.47 / Linux GTK'),
          _SpecItem(palette: palette, scale: scale, title: 'Backend Core', value: 'FastAPI / Python 3.14'),
          _SpecItem(palette: palette, scale: scale, title: 'Local LLM Engine', value: 'Ollama (Llama 3.2 3B)'),
          _SpecItem(palette: palette, scale: scale, title: 'Speech-to-Text', value: 'Faster-Whisper (CPU ONNX)'),
          _SpecItem(palette: palette, scale: scale, title: 'Text-to-Speech', value: 'Piper Voice (Local ONNX)'),
          _SpecItem(palette: palette, scale: scale, title: 'Database Store', value: 'SQLite 3 (Local ACID Store)'),
        ],
      ),
    );
  }
}

class _SpecItem extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String title;
  final String value;

  const _SpecItem({
    required this.palette,
    required this.scale,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(title, style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
          ),
          Text(value, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}
