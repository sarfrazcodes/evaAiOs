import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class PrivacySettings extends StatelessWidget {
  final ThemeNotifier themeNotifier;

  const PrivacySettings({
    super.key,
    required this.themeNotifier,
  });

  Future<void> _clearAllConversations(BuildContext context) async {
    final palette = themeNotifier.getPalette(context);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: palette.surface,
        title: Text('Clear All Conversations?', style: TextStyle(color: palette.textPri)),
        content: Text(
          'This will permanently delete all conversation sessions and messages from the local SQLite database. This cannot be undone.',
          style: TextStyle(color: palette.textSec),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text('Cancel', style: TextStyle(color: palette.textSec))),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text('Clear All', style: TextStyle(color: palette.error))),
        ],
      ),
    );

    if (confirm == true) {
      final convs = await EvaApiClient.getConversations();
      for (final c in convs) {
        await EvaApiClient.deleteConversation(c['conversation_id']);
      }
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('All conversation records cleared.', style: TextStyle(color: palette.textPri)),
            backgroundColor: palette.panel,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = themeNotifier.getPalette(context);
    final accent = themeNotifier.accent.primary;
    final scale = themeNotifier.fontScale;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── History & Context ─────────────────────────────────────────────
          Text('CONVERSATION HISTORY & RETENTION', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
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
                    title: Text('Show Conversation History Panel', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                    subtitle: Text('Display previous chat sessions in the assistant sidebar', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    value: themeNotifier.historyVisible,
                    activeThumbColor: accent,
                    onChanged: (v) => themeNotifier.setHistoryVisible(v),
                  ),
                ),
                const Divider(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Clear Stored Conversation History', style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontWeight: FontWeight.w500)),
                          Text('Permanently deletes all stored messages from SQLite database', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                        ],
                      ),
                    ),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: palette.error,
                        side: BorderSide(color: palette.error.withValues(alpha: 0.4)),
                      ),
                      onPressed: () => _clearAllConversations(context),
                      child: const Text('Clear All Chats'),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Security & Confirmation Settings ──────────────────────────────
          Text('SECURITY & PERMISSION SAFEGUARDS', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
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
                    title: Text('Require Confirmation for High-Risk Actions', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                    subtitle: Text('Operations that write files, close apps, or modify local state require explicit user approval', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    value: themeNotifier.requireConfirmHighRisk,
                    activeThumbColor: accent,
                    onChanged: (v) => themeNotifier.setRequireConfirmHighRisk(v),
                  ),
                ),
                const Divider(height: 18),
                Text(
                  'Workspace Sandbox Isolation: Filesystem operations are strictly bound to the workspace directory. Path traversal attempts are blocked by the permission engine.',
                  style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale, height: 1.4),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Storage Architecture Info ─────────────────────────────────────
          Text('LOCAL STORAGE ARCHITECTURE', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
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
                _InfoLine(palette: palette, scale: scale, label: 'Database Engine', value: 'SQLite 3 (Local Serverless)'),
                const SizedBox(height: 6),
                _InfoLine(palette: palette, scale: scale, label: 'Database Path', value: 'core/eva_core/eva.db'),
                const SizedBox(height: 6),
                _InfoLine(palette: palette, scale: scale, label: 'Config Store', value: '~/.config/eva_os/settings.json'),
                const SizedBox(height: 6),
                _InfoLine(palette: palette, scale: scale, label: 'Workspace Root', value: '~/workspace'),
                const SizedBox(height: 12),
                Text(
                  'Privacy Note: EVA OS operates entirely locally on your Linux workstation. No telemetry or speech audio is uploaded to external clouds.',
                  style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale, fontStyle: FontStyle.italic),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String label;
  final String value;

  const _InfoLine({
    required this.palette,
    required this.scale,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 130,
          child: Text(label, style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
        ),
        Expanded(
          child: Text(value, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontFamily: 'monospace')),
        ),
      ],
    );
  }
}
