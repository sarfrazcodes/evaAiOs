import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class AiProviderSettings extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const AiProviderSettings({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<AiProviderSettings> createState() => _AiProviderSettingsState();
}

class _AiProviderSettingsState extends State<AiProviderSettings> {
  final TextEditingController _apiKeyCtrl = TextEditingController();
  bool _obscureKey = true;
  bool _loadingHealth = true;
  Map<String, dynamic>? _healthData;
  String _saveMessage = '';

  @override
  void initState() {
    super.initState();
    _apiKeyCtrl.text = widget.themeNotifier.geminiApiKey;
    _fetchHealth();
  }

  @override
  void dispose() {
    _apiKeyCtrl.dispose();
    super.dispose();
  }

  Future<void> _fetchHealth() async {
    setState(() => _loadingHealth = true);
    try {
      final res = await ApiClient.getSystemHealth();
      if (mounted) {
        setState(() {
          _healthData = res;
          _loadingHealth = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loadingHealth = false);
    }
  }

  Future<void> _saveSettings() async {
    final key = _apiKeyCtrl.text.trim();
    widget.themeNotifier.setGeminiApiKey(key);
    // Also save privacy mode to backend
    try {
      await ApiClient.saveSettings({
        'privacy_mode': widget.themeNotifier.privacyMode,
      });
      if (mounted) {
        setState(() => _saveMessage = 'AI Provider preferences saved successfully.');
        Future.delayed(const Duration(seconds: 3), () {
          if (mounted) setState(() => _saveMessage = '');
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _saveMessage = 'Saved locally.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;
    final currentMode = widget.themeNotifier.privacyMode;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header Notice ──────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(color: palette.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.shield_outlined, color: accent, size: 24 * scale),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Core Privacy Architecture',
                        style: TextStyle(
                          color: palette.textPri,
                          fontSize: 13.5 * scale,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'EVA enforces privacy boundaries inside the core backend engine. Local models keep your files private, while cloud reasoning is restricted to explicitly approved tasks.',
                        style: TextStyle(
                          color: palette.textSec,
                          fontSize: 11.5 * scale,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Operating Mode Selection ───────────────────────────────────────
          Text(
            'INTELLIGENCE ROUTING MODE',
            style: TextStyle(
              color: palette.textSec,
              fontSize: 10.5 * scale,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 10),

          _ModeCard(
            title: 'Private Mode (Local Only)',
            subtitle: 'Only local Ollama models (Llama 3.2). All external LLM requests blocked. Strict local memory and local document processing.',
            icon: Icons.lock_outline_rounded,
            isSelected: currentMode == 'private',
            palette: palette,
            accent: accent,
            scale: scale,
            onTap: () {
              widget.themeNotifier.setPrivacyMode('private');
              _saveSettings();
            },
          ),
          const SizedBox(height: 10),

          _ModeCard(
            title: 'Hybrid Mode (Recommended)',
            subtitle: 'Routine local tasks run on Ollama. Complex reasoning and code planning utilize Gemini API only when explicitly approved.',
            icon: Icons.hub_outlined,
            isSelected: currentMode == 'hybrid',
            palette: palette,
            accent: accent,
            scale: scale,
            onTap: () {
              widget.themeNotifier.setPrivacyMode('hybrid');
              _saveSettings();
            },
          ),
          const SizedBox(height: 10),

          _ModeCard(
            title: 'Public Mode (Cloud Augmented)',
            subtitle: 'Gemini API used for multi-step planning, complex tasks, and advanced code reasoning. Requires valid Gemini API Key.',
            icon: Icons.cloud_done_outlined,
            isSelected: currentMode == 'public',
            palette: palette,
            accent: accent,
            scale: scale,
            onTap: () {
              widget.themeNotifier.setPrivacyMode('public');
              _saveSettings();
            },
          ),

          const SizedBox(height: 24),

          // ── Gemini API Key Configuration ───────────────────────────────────
          Text(
            'GEMINI API CONFIGURATION',
            style: TextStyle(
              color: palette.textSec,
              fontSize: 10.5 * scale,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 10),

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
                Text(
                  'API Key',
                  style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  'Stored securely on your Linux workstation. Never transmitted to third-party servers.',
                  style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _apiKeyCtrl,
                        obscureText: _obscureKey,
                        style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontFamily: 'monospace'),
                        decoration: InputDecoration(
                          hintText: 'AIzaSy...',
                          hintStyle: TextStyle(color: palette.textSec.withValues(alpha: 0.5)),
                          filled: true,
                          fillColor: palette.inputBg,
                          border: OutlineInputBorder(borderRadius: EvaTokens.borderSm, borderSide: BorderSide(color: palette.border)),
                          suffixIcon: IconButton(
                            icon: Icon(_obscureKey ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 18 * scale, color: palette.textSec),
                            onPressed: () => setState(() => _obscureKey = !_obscureKey),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: accent,
                        foregroundColor: palette.bg,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      ),
                      onPressed: _saveSettings,
                      icon: const Icon(Icons.check_rounded, size: 18),
                      label: const Text('Save Key', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
                if (_saveMessage.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(_saveMessage, style: TextStyle(color: palette.success, fontSize: 11.5 * scale, fontWeight: FontWeight.w600)),
                ],
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Provider Health Status ─────────────────────────────────────────
          Text(
            'PROVIDER HEALTH STATUS',
            style: TextStyle(
              color: palette.textSec,
              fontSize: 10.5 * scale,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 10),

          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(color: palette.border),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Text('Provider Services', style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontWeight: FontWeight.w600)),
                    const Spacer(),
                    IconButton(
                      icon: Icon(Icons.refresh_rounded, size: 18 * scale, color: palette.textSec),
                      onPressed: _fetchHealth,
                      tooltip: 'Refresh Status',
                    ),
                  ],
                ),
                const Divider(),
                if (_loadingHealth)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: accent)),
                  )
                else ...[
                  _HealthRow(
                    label: 'Local Ollama Model',
                    detail: _healthData?['ollama']?['model'] ?? 'llama3.2:3b',
                    isOk: _healthData?['ollama']?['available'] == true,
                    palette: palette,
                    scale: scale,
                  ),
                  const SizedBox(height: 8),
                  _HealthRow(
                    label: 'Google Gemini REST Provider',
                    detail: widget.themeNotifier.geminiApiKey.isNotEmpty ? 'API Key Configured' : 'No API Key',
                    isOk: widget.themeNotifier.geminiApiKey.isNotEmpty,
                    palette: palette,
                    scale: scale,
                  ),
                  const SizedBox(height: 8),
                  _HealthRow(
                    label: 'SQLite Tasks Database',
                    detail: _healthData?['database']?['path'] ?? 'Local DB',
                    isOk: _healthData?['database']?['available'] == true,
                    palette: palette,
                    scale: scale,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModeCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final bool isSelected;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final VoidCallback onTap;

  const _ModeCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.isSelected,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: EvaTokens.borderMd,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected ? accent.withValues(alpha: 0.08) : palette.surface,
          borderRadius: EvaTokens.borderMd,
          border: Border.all(
            color: isSelected ? accent : palette.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isSelected ? accent.withValues(alpha: 0.15) : palette.panel,
                borderRadius: EvaTokens.borderSm,
              ),
              child: Icon(icon, size: 20 * scale, color: isSelected ? accent : palette.textSec),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          color: isSelected ? palette.textPri : palette.textPri.withValues(alpha: 0.9),
                          fontSize: 12.5 * scale,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const Spacer(),
                      if (isSelected)
                        Icon(Icons.check_circle_rounded, size: 18 * scale, color: accent),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: palette.textSec,
                      fontSize: 11 * scale,
                      height: 1.35,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HealthRow extends StatelessWidget {
  final String label;
  final String detail;
  final bool isOk;
  final EvaPalette palette;
  final double scale;

  const _HealthRow({
    required this.label,
    required this.detail,
    required this.isOk,
    required this.palette,
    required this.scale,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isOk ? palette.success : palette.warning,
          ),
        ),
        const SizedBox(width: 10),
        Text(label, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
        const Spacer(),
        Text(detail, style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace')),
      ],
    );
  }
}
