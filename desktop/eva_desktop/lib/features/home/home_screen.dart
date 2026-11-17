import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class HomeScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;
  final ValueChanged<int> onNavigate;
  final VoidCallback onOpenAssistant;
  final VoidCallback onTriggerVoice;

  const HomeScreen({
    super.key,
    required this.themeNotifier,
    required this.onNavigate,
    required this.onOpenAssistant,
    required this.onTriggerVoice,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? _sysInfo;
  Map<String, dynamic>? _health;
  List<Map<String, dynamic>> _recentFiles = [];
  List<Map<String, dynamic>> _recentConversations = [];
  List<Map<String, dynamic>> _activeTasks = [];
  bool _loading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
    _refreshTimer = Timer.periodic(const Duration(seconds: 8), (_) => _loadDashboardData());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadDashboardData() async {
    final sys = await EvaApiClient.getSystemInfo();
    final health = await EvaApiClient.getDetailedHealth();
    final filesData = await EvaApiClient.listFiles('');
    final convs = await EvaApiClient.getConversations();
    final tasks = await EvaApiClient.getTasks(limit: 20);

    if (mounted) {
      setState(() {
        _sysInfo = sys;
        _health = health;
        _recentFiles = (filesData?['items'] as List? ?? []).cast<Map<String, dynamic>>().take(5).toList();
        _recentConversations = convs.take(4).toList();
        _activeTasks = tasks.where((t) {
          final s = t['status'];
          return s == 'running' || s == 'planned' || s == 'action_resolution_required' || s == 'blocked';
        }).take(4).toList();
        _loading = false;
      });
    }
  }

  String _formatDateTime(DateTime dt) {
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return '${weekdays[dt.weekday - 1]}, ${months[dt.month - 1]} ${dt.day}, ${dt.year}';
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;
    final now = DateTime.now();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: EvaTokens.maxContentWidth),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Welcome Header ───────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: palette.surface.withValues(alpha: widget.themeNotifier.panelOpacity),
                  borderRadius: EvaTokens.borderMd,
                  border: Border.all(color: palette.border),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.15),
                        borderRadius: EvaTokens.borderMd,
                        border: Border.all(color: accent.withValues(alpha: 0.4)),
                      ),
                      child: Icon(Icons.desktop_windows_rounded, color: accent, size: 24),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                'EVA Workstation',
                                style: TextStyle(
                                  color: palette.textPri,
                                  fontSize: 18 * scale,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                decoration: BoxDecoration(
                                  color: palette.panel,
                                  borderRadius: EvaTokens.borderSm,
                                  border: Border.all(color: palette.borderSubtle),
                                ),
                                child: Text(
                                  _sysInfo?['hostname'] ?? 'linux-node',
                                  style: TextStyle(
                                    color: palette.textSec,
                                    fontSize: 10.5 * scale,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _formatDateTime(now),
                            style: TextStyle(color: palette.textSec, fontSize: 12.5 * scale),
                          ),
                        ],
                      ),
                    ),
                    // Voice Action Shortcut
                    ElevatedButton.icon(
                      icon: const Icon(Icons.mic_rounded, size: 16),
                      label: const Text('Voice Assistant'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: accent,
                        foregroundColor: widget.themeNotifier.isDark(context) ? palette.bg : Colors.white,
                      ),
                      onPressed: widget.onTriggerVoice,
                    ),
                    const SizedBox(width: 10),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.chat_bubble_outline_rounded, size: 16),
                      label: const Text('Open EVA'),
                      onPressed: widget.onOpenAssistant,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // ── Quick Access Applications ────────────────────────────────
              if (_loading)
                LinearProgressIndicator(minHeight: 2, color: accent, backgroundColor: palette.panel),
              Text('Applications', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
              const SizedBox(height: 10),
              Row(
                children: [
                  _QuickAppCard(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    icon: Icons.language_rounded,
                    name: 'Browser',
                    sub: 'Chrome / Firefox',
                    onTap: () => EvaApiClient.performAppAction('chrome', 'launch'),
                  ),
                  const SizedBox(width: 12),
                  _QuickAppCard(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    icon: Icons.code_rounded,
                    name: 'Code Editor',
                    sub: 'VS Code',
                    onTap: () => EvaApiClient.performAppAction('vscode', 'launch'),
                  ),
                  const SizedBox(width: 12),
                  _QuickAppCard(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    icon: Icons.folder_open_rounded,
                    name: 'Files',
                    sub: 'Workspace Browser',
                    onTap: () => widget.onNavigate(3), // Jump to File Explorer tab
                  ),
                  const SizedBox(width: 12),
                  _QuickAppCard(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    icon: Icons.calculate_outlined,
                    name: 'Calculator',
                    sub: 'GNOME Utility',
                    onTap: () => EvaApiClient.performAppAction('calculator', 'launch'),
                  ),
                  const SizedBox(width: 12),
                  _QuickAppCard(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    icon: Icons.edit_note_rounded,
                    name: 'Text Editor',
                    sub: 'Desktop Editor',
                    onTap: () => EvaApiClient.performAppAction('text editor', 'launch'),
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // ── Two Column Grid: Hardware & AI Services + Active Tasks ──
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Left Column: System & AI Service Status
                  Expanded(
                    flex: 5,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('System & AI Status', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
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
                              _StatusRow(
                                palette: palette,
                                label: 'EVA Core Engine',
                                value: _health != null ? 'Active (HTTP 127.0.0.1:8000)' : 'Unavailable',
                                isPositive: _health != null,
                              ),
                              const Divider(height: 16),
                              _StatusRow(
                                palette: palette,
                                label: 'SQLite Task & Memory DB',
                                value: (_health?['database']?['available'] == true) ? 'Connected' : 'Degraded',
                                isPositive: _health?['database']?['available'] == true,
                              ),
                              const Divider(height: 16),
                              _StatusRow(
                                palette: palette,
                                label: 'Ollama LLM Provider',
                                value: _health?['ollama']?['available'] == true
                                    ? 'Connected (${_health?['ollama']?['model'] ?? 'model'})'
                                    : 'Offline / Standby',
                                isPositive: _health?['ollama']?['available'] == true,
                              ),
                              const Divider(height: 16),
                              _StatusRow(
                                palette: palette,
                                label: 'Speech Engines',
                                value: 'Faster-Whisper (STT) & Piper (TTS)',
                                isPositive: true,
                              ),
                              const Divider(height: 16),
                              _StatusRow(
                                palette: palette,
                                label: 'Operating System',
                                value: _sysInfo?['os'] ?? 'Linux Workstation',
                                isPositive: true,
                              ),
                              const Divider(height: 16),
                              _StatusRow(
                                palette: palette,
                                label: 'Memory (RAM)',
                                value: _sysInfo != null
                                    ? '${_sysInfo!['ram_used_gb']} GB / ${_sysInfo!['ram_total_gb']} GB (${_sysInfo!['ram_percent']}%)'
                                    : 'Loading…',
                                isPositive: true,
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 20),

                        // Recent Files Card
                        Text('Recent Workspace Files', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: palette.surface,
                            borderRadius: EvaTokens.borderMd,
                            border: Border.all(color: palette.border),
                          ),
                          child: _recentFiles.isEmpty
                              ? Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Center(
                                    child: Text(
                                      'Workspace directory is ready. No files created yet.',
                                      style: TextStyle(color: palette.textSec, fontSize: 12 * scale),
                                    ),
                                  ),
                                )
                              : Column(
                                  children: _recentFiles.map((file) {
                                    final isDir = file['is_dir'] == true;
                                    return InkWell(
                                      onTap: () => widget.onNavigate(3), // Jump to File Explorer
                                      child: Padding(
                                        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                                        child: Row(
                                          children: [
                                            Icon(
                                              isDir ? Icons.folder_rounded : Icons.insert_drive_file_outlined,
                                              size: 16,
                                              color: isDir ? accent : palette.textSec,
                                            ),
                                            const SizedBox(width: 8),
                                            Expanded(
                                              child: Text(
                                                file['name'] ?? '',
                                                style: TextStyle(color: palette.textPri, fontSize: 12 * scale),
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                            Text(
                                              isDir ? 'Folder' : '${file['size']} B',
                                              style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                                            ),
                                          ],
                                        ),
                                      ),
                                    );
                                  }).toList(),
                                ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(width: 20),

                  // Right Column: Active Tasks & Recent Conversations
                  Expanded(
                    flex: 5,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Active Tasks
                        Row(
                          children: [
                            Text('Active / Recent Tasks', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                            const Spacer(),
                            InkWell(
                              onTap: () => widget.onNavigate(5), // Jump to Task Manager
                              child: Text('View all', style: TextStyle(color: accent, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: palette.surface,
                            borderRadius: EvaTokens.borderMd,
                            border: Border.all(color: palette.border),
                          ),
                          child: _activeTasks.isEmpty
                              ? Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Center(
                                    child: Text(
                                      'No pending or active tasks. EVA is ready.',
                                      style: TextStyle(color: palette.textSec, fontSize: 12 * scale),
                                    ),
                                  ),
                                )
                              : Column(
                                  children: _activeTasks.map((t) {
                                    final status = t['status'] as String? ?? '';
                                    final intent = t['intent'] as String? ?? 'General Task';
                                    final taskId = (t['task_id'] as String? ?? '').substring(0, 8);
                                    return Padding(
                                      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                                      child: Row(
                                        children: [
                                          Container(
                                            width: 6,
                                            height: 6,
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: status == 'running' ? accent : palette.warning,
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              intent,
                                              style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w500),
                                            ),
                                          ),
                                          Text(
                                            '#$taskId • $status',
                                            style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
                                          ),
                                        ],
                                      ),
                                    );
                                  }).toList(),
                                ),
                        ),

                        const SizedBox(height: 20),

                        // Recent Conversations
                        Row(
                          children: [
                            Text('Recent Conversations', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                            const Spacer(),
                            InkWell(
                              onTap: () => widget.onNavigate(1), // Jump to Assistant
                              child: Text('Open Assistant', style: TextStyle(color: accent, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: palette.surface,
                            borderRadius: EvaTokens.borderMd,
                            border: Border.all(color: palette.border),
                          ),
                          child: _recentConversations.isEmpty
                              ? Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Center(
                                    child: Text(
                                      'No previous conversations found.',
                                      style: TextStyle(color: palette.textSec, fontSize: 12 * scale),
                                    ),
                                  ),
                                )
                              : Column(
                                  children: _recentConversations.map((c) {
                                    return InkWell(
                                      onTap: () => widget.onNavigate(1),
                                      child: Padding(
                                        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                                        child: Row(
                                          children: [
                                            Icon(Icons.chat_bubble_outline_rounded, size: 15, color: palette.textSec),
                                            const SizedBox(width: 8),
                                            Expanded(
                                              child: Text(
                                                c['title'] ?? 'New Conversation',
                                                style: TextStyle(color: palette.textPri, fontSize: 12 * scale),
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                            Text(
                                              '${c['message_count'] ?? 0} msgs',
                                              style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale),
                                            ),
                                          ],
                                        ),
                                      ),
                                    );
                                  }).toList(),
                                ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickAppCard extends StatefulWidget {
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final IconData icon;
  final String name;
  final String sub;
  final VoidCallback onTap;

  const _QuickAppCard({
    required this.palette,
    required this.accent,
    required this.scale,
    required this.icon,
    required this.name,
    required this.sub,
    required this.onTap,
  });

  @override
  State<_QuickAppCard> createState() => _QuickAppCardState();
}

class _QuickAppCardState extends State<_QuickAppCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 140),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: _hovered ? widget.palette.elevated : widget.palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(
                color: _hovered ? widget.accent.withValues(alpha: 0.5) : widget.palette.border,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: widget.accent.withValues(alpha: 0.12),
                    borderRadius: EvaTokens.borderSm,
                  ),
                  child: Icon(widget.icon, size: 16, color: widget.accent),
                ),
                const SizedBox(height: 10),
                Text(
                  widget.name,
                  style: TextStyle(
                    color: widget.palette.textPri,
                    fontSize: 12.5 * widget.scale,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  widget.sub,
                  style: TextStyle(
                    color: widget.palette.textSec,
                    fontSize: 10.5 * widget.scale,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  final EvaPalette palette;
  final String label;
  final String value;
  final bool isPositive;

  const _StatusRow({
    required this.palette,
    required this.label,
    required this.value,
    required this.isPositive,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          flex: 4,
          child: Text(
            label,
            style: TextStyle(color: palette.textSec, fontSize: 12),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isPositive ? palette.success : palette.error,
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          flex: 6,
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(
              color: palette.textPri,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}
