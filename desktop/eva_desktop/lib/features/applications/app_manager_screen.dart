import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class AppManagerScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const AppManagerScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<AppManagerScreen> createState() => _AppManagerScreenState();
}

class _AppManagerScreenState extends State<AppManagerScreen> {
  List<Map<String, dynamic>> _apps = [];
  bool _loading = true;
  String? _actionInProgress;
  Timer? _poller;

  @override
  void initState() {
    super.initState();
    _loadApps();
    _poller = Timer.periodic(const Duration(seconds: 4), (_) => _loadApps(silent: true));
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _loadApps({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    final list = await EvaApiClient.getApplications();
    if (mounted) {
      setState(() {
        _apps = list;
        _loading = false;
      });
    }
  }

  Future<void> _triggerAction(String appKey, String action) async {
    setState(() => _actionInProgress = '$appKey-$action');
    final res = await EvaApiClient.performAppAction(appKey, action);
    if (mounted) {
      setState(() => _actionInProgress = null);
      if (res != null && res['message'] != null) {
        _showNotification(res['message'] as String, isError: res['success'] != true);
      }
      _loadApps(silent: true);
    }
  }

  void _showNotification(String msg, {bool isError = false}) {
    final palette = widget.themeNotifier.getPalette(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg, style: TextStyle(color: palette.textPri)),
        backgroundColor: isError ? palette.error.withValues(alpha: 0.9) : palette.surface,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  IconData _iconForApp(String iconName) {
    switch (iconName) {
      case 'web':
      case 'language':
        return Icons.language_rounded;
      case 'shield':
        return Icons.shield_outlined;
      case 'code':
        return Icons.code_rounded;
      case 'calculate':
        return Icons.calculate_outlined;
      case 'settings':
        return Icons.settings_outlined;
      case 'edit_note':
        return Icons.edit_note_rounded;
      case 'folder':
        return Icons.folder_rounded;
      default:
        return Icons.apps_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    final runningApps = _apps.where((a) => a['is_running'] == true).toList();
    final categories = <String, List<Map<String, dynamic>>>{};
    for (final app in _apps) {
      final cat = app['category'] as String? ?? 'General';
      categories.putIfAbsent(cat, () => []).add(app);
    }

    return Scaffold(
      backgroundColor: palette.bg,
      body: Column(
        children: [
          // Toolbar
          Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 20),
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border(bottom: BorderSide(color: palette.border)),
            ),
            child: Row(
              children: [
                Icon(Icons.apps_rounded, size: 16, color: accent),
                const SizedBox(width: 8),
                Text('Application Lifecycle Manager', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: palette.panel,
                    borderRadius: EvaTokens.borderSm,
                  ),
                  child: Text(
                    '${runningApps.length} running • ${_apps.length} available',
                    style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                  ),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  color: palette.textSec,
                  tooltip: 'Refresh process list',
                  onPressed: () => _loadApps(),
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: _loading
                ? Center(child: CircularProgressIndicator(color: accent))
                : SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: EvaTokens.maxContentWidth),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // ── Active Processes Overview ──────────────────────────
                            if (runningApps.isNotEmpty) ...[
                              Text('Active Running Applications', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 12,
                                runSpacing: 12,
                                children: runningApps.map((app) {
                                  return _RunningAppChip(
                                    app: app,
                                    palette: palette,
                                    accent: accent,
                                    scale: scale,
                                    onFocus: () => _triggerAction(app['key'], 'focus'),
                                    onClose: () => _triggerAction(app['key'], 'close'),
                                  );
                                }).toList(),
                              ),
                              const SizedBox(height: 24),
                            ],

                            // ── Categorized Apps ───────────────────────────────────
                            for (final entry in categories.entries) ...[
                              Text(entry.key, style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                              const SizedBox(height: 10),
                              GridView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 3,
                                  crossAxisSpacing: 12,
                                  mainAxisSpacing: 12,
                                  childAspectRatio: 2.3,
                                ),
                                itemCount: entry.value.length,
                                itemBuilder: (ctx, i) {
                                  final app = entry.value[i];
                                  final isRunning = app['is_running'] == true;
                                  final isInstalled = app['is_installed'] == true;
                                  final inAction = _actionInProgress?.startsWith(app['key']) == true;

                                  return Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: palette.surface,
                                      borderRadius: EvaTokens.borderMd,
                                      border: Border.all(
                                        color: isRunning ? accent.withValues(alpha: 0.5) : palette.border,
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 38,
                                          height: 38,
                                          decoration: BoxDecoration(
                                            color: accent.withValues(alpha: 0.12),
                                            borderRadius: EvaTokens.borderSm,
                                          ),
                                          child: Icon(_iconForApp(app['icon']), size: 20, color: accent),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              Row(
                                                children: [
                                                  Expanded(
                                                    child: Text(
                                                      app['display_name'] ?? '',
                                                      style: TextStyle(
                                                        color: palette.textPri,
                                                        fontSize: 12.5 * scale,
                                                        fontWeight: FontWeight.w600,
                                                      ),
                                                      maxLines: 1,
                                                      overflow: TextOverflow.ellipsis,
                                                    ),
                                                  ),
                                                  Container(
                                                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                                    decoration: BoxDecoration(
                                                      color: (isRunning
                                                              ? palette.success
                                                              : (isInstalled ? palette.panel : palette.error))
                                                          .withValues(alpha: 0.15),
                                                      borderRadius: EvaTokens.borderSm,
                                                    ),
                                                    child: Text(
                                                      isRunning ? 'Running' : (isInstalled ? 'Installed' : 'Missing'),
                                                      style: TextStyle(
                                                        color: isRunning
                                                            ? palette.success
                                                            : (isInstalled ? palette.textSec : palette.error),
                                                        fontSize: 9.5 * scale,
                                                        fontWeight: FontWeight.w600,
                                                      ),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                              const SizedBox(height: 6),
                                              Row(
                                                children: [
                                                  if (!isRunning)
                                                    ElevatedButton(
                                                      onPressed: inAction || !isInstalled
                                                          ? null
                                                          : () => _triggerAction(app['key'], 'launch'),
                                                      style: ElevatedButton.styleFrom(
                                                        backgroundColor: accent,
                                                        foregroundColor: palette.bg,
                                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                                      ),
                                                      child: Text('Launch', style: TextStyle(fontSize: 11 * scale)),
                                                    )
                                                  else ...[
                                                    OutlinedButton(
                                                      onPressed: inAction ? null : () => _triggerAction(app['key'], 'focus'),
                                                      style: OutlinedButton.styleFrom(
                                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                      ),
                                                      child: Text('Focus', style: TextStyle(fontSize: 11 * scale)),
                                                    ),
                                                    const SizedBox(width: 6),
                                                    OutlinedButton(
                                                      onPressed: inAction ? null : () => _triggerAction(app['key'], 'close'),
                                                      style: OutlinedButton.styleFrom(
                                                        foregroundColor: palette.error,
                                                        side: BorderSide(color: palette.error.withValues(alpha: 0.4)),
                                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                      ),
                                                      child: Text('Close', style: TextStyle(fontSize: 11 * scale)),
                                                    ),
                                                  ],
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                              const SizedBox(height: 20),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _RunningAppChip extends StatelessWidget {
  final Map<String, dynamic> app;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final VoidCallback onFocus;
  final VoidCallback onClose;

  const _RunningAppChip({
    required this.app,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onFocus,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: palette.surface,
        borderRadius: EvaTokens.borderSm,
        border: Border.all(color: accent.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(shape: BoxShape.circle, color: palette.success),
          ),
          const SizedBox(width: 8),
          Text(
            app['display_name'] ?? '',
            style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w600),
          ),
          if (app['pid'] != null) ...[
            const SizedBox(width: 6),
            Text('PID ${app['pid']}', style: TextStyle(color: palette.textSec, fontSize: 10 * scale, fontFamily: 'monospace')),
          ],
          const SizedBox(width: 10),
          InkWell(
            onTap: onFocus,
            child: Icon(Icons.fullscreen_rounded, size: 16, color: accent),
          ),
          const SizedBox(width: 6),
          InkWell(
            onTap: onClose,
            child: Icon(Icons.close_rounded, size: 16, color: palette.error),
          ),
        ],
      ),
    );
  }
}
