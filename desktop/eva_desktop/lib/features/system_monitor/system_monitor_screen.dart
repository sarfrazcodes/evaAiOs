import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class SystemMonitorScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const SystemMonitorScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<SystemMonitorScreen> createState() => _SystemMonitorScreenState();
}

class _SystemMonitorScreenState extends State<SystemMonitorScreen> {
  Map<String, dynamic>? _sysInfo;
  Map<String, dynamic>? _detailedHealth;
  Map<String, dynamic>? _ttsStatus;
  bool _loading = true;
  Timer? _poller;

  @override
  void initState() {
    super.initState();
    _fetchMetrics();
    _poller = Timer.periodic(const Duration(seconds: 4), (_) => _fetchMetrics(silent: true));
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _fetchMetrics({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    final sys = await EvaApiClient.getSystemInfo();
    final health = await EvaApiClient.getDetailedHealth();
    final tts = await EvaApiClient.getTtsStatus();

    if (mounted) {
      setState(() {
        _sysInfo = sys;
        _detailedHealth = health;
        _ttsStatus = tts;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    final ramPercent = (_sysInfo?['ram_percent'] as num?)?.toDouble() ?? 0.0;
    final diskPercent = (_sysInfo?['disk_percent'] as num?)?.toDouble() ?? 0.0;
    final dbAvailable = _detailedHealth?['database']?['available'] == true;
    final ollamaAvailable = _detailedHealth?['ollama']?['available'] == true;
    final modelName = _detailedHealth?['ollama']?['model'] ?? 'llama3.2:3b';
    final modelReady = _detailedHealth?['ollama']?['model_available'] == true;

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
                Icon(Icons.speed_outlined, size: 16, color: accent),
                const SizedBox(width: 8),
                Text('System Monitor & Infrastructure', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  color: palette.textSec,
                  tooltip: 'Refresh metrics',
                  onPressed: () => _fetchMetrics(),
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
                            // ── Hardware Metrics Grid ──────────────────────────────
                            Text('Hardware Resources', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                // RAM Gauge
                                Expanded(
                                  child: _MetricCard(
                                    palette: palette,
                                    accent: accent,
                                    scale: scale,
                                    title: 'RAM Utilization',
                                    percent: ramPercent / 100.0,
                                    percentLabel: '$ramPercent%',
                                    subtitle: _sysInfo != null
                                        ? '${_sysInfo!['ram_used_gb']} GB of ${_sysInfo!['ram_total_gb']} GB'
                                        : 'Unavailable',
                                    icon: Icons.memory_rounded,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                // Disk Gauge
                                Expanded(
                                  child: _MetricCard(
                                    palette: palette,
                                    accent: accent,
                                    scale: scale,
                                    title: 'Storage Root (/)',
                                    percent: diskPercent / 100.0,
                                    percentLabel: '$diskPercent%',
                                    subtitle: _sysInfo != null
                                        ? '${_sysInfo!['disk_used_gb']} GB of ${_sysInfo!['disk_total_gb']} GB'
                                        : 'Unavailable',
                                    icon: Icons.storage_rounded,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                // CPU Overview
                                Expanded(
                                  child: Container(
                                    padding: const EdgeInsets.all(16),
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
                                            Icon(Icons.developer_board_rounded, size: 18, color: accent),
                                            const SizedBox(width: 8),
                                            Text('Processor (CPU)', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                                          ],
                                        ),
                                        const SizedBox(height: 12),
                                        Text(
                                          _sysInfo?['cpu'] ?? 'Unknown CPU',
                                          style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w500),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Logical Cores: ${_sysInfo?['cpu_cores'] ?? 'Unavailable'}',
                                          style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Host: ${_sysInfo?['hostname'] ?? 'localhost'}',
                                          style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),

                            const SizedBox(height: 24),

                            // ── System Layer & Services Status ─────────────────────
                            Text('EVA Core Services & Subsystems', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: palette.surface,
                                borderRadius: EvaTokens.borderMd,
                                border: Border.all(color: palette.border),
                              ),
                              child: Column(
                                children: [
                                  _ServiceStatusTile(
                                    palette: palette,
                                    scale: scale,
                                    title: 'EVA Core HTTP Service',
                                    endpoint: 'http://127.0.0.1:8000',
                                    isHealthy: _detailedHealth != null,
                                    statusNote: _detailedHealth != null ? 'Online & serving API requests' : 'Offline / Unreachable',
                                  ),
                                  const Divider(height: 18),
                                  _ServiceStatusTile(
                                    palette: palette,
                                    scale: scale,
                                    title: 'SQLite Database Persistence',
                                    endpoint: 'core/eva_core/eva.db',
                                    isHealthy: dbAvailable,
                                    statusNote: dbAvailable ? 'PRAGMA foreign_keys ON • Operational' : 'Database Unavailable',
                                  ),
                                  const Divider(height: 18),
                                  _ServiceStatusTile(
                                    palette: palette,
                                    scale: scale,
                                    title: 'Ollama LLM Engine',
                                    endpoint: 'http://127.0.0.1:11434',
                                    isHealthy: ollamaAvailable,
                                    statusNote: ollamaAvailable
                                        ? 'Connected • Model "$modelName" (${modelReady ? 'Ready' : 'Not Loaded'})'
                                        : 'Standby / Local Ollama instance not detected',
                                  ),
                                  const Divider(height: 18),
                                  _ServiceStatusTile(
                                    palette: palette,
                                    scale: scale,
                                    title: 'Speech Recognition (STT)',
                                    endpoint: 'Faster-Whisper (ALSA/arecord backend)',
                                    isHealthy: true,
                                    statusNote: 'Native arecord PipeWire compatibility layer active',
                                  ),
                                  const Divider(height: 18),
                                  _ServiceStatusTile(
                                    palette: palette,
                                    scale: scale,
                                    title: 'Text-to-Speech Engine (TTS)',
                                    endpoint: 'Piper Voice Service',
                                    isHealthy: _ttsStatus?['error'] == null,
                                    statusNote: _ttsStatus != null
                                        ? 'Engine: ${_ttsStatus!['engine']} • Voice: ${_ttsStatus!['voice']} • Speed: ${_ttsStatus!['speed']}x'
                                        : 'Piper voice ready',
                                  ),
                                ],
                              ),
                            ),

                            const SizedBox(height: 24),

                            // ── Operating System Info ──────────────────────────────
                            Text('Workstation Information', style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: palette.surface,
                                borderRadius: EvaTokens.borderMd,
                                border: Border.all(color: palette.border),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Operating System', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                                        Text(_sysInfo?['os'] ?? 'Linux', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                                      ],
                                    ),
                                  ),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Hostname', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                                        Text(_sysInfo?['hostname'] ?? 'localhost', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600, fontFamily: 'monospace')),
                                      ],
                                    ),
                                  ),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('Architecture', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                                        Text('x86_64 Linux Desktop', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
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

class _MetricCard extends StatelessWidget {
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final String title;
  final double percent;
  final String percentLabel;
  final String subtitle;
  final IconData icon;

  const _MetricCard({
    required this.palette,
    required this.accent,
    required this.scale,
    required this.title,
    required this.percent,
    required this.percentLabel,
    required this.subtitle,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final clamped = percent.clamp(0.0, 1.0);
    final isHigh = clamped > 0.85;

    return Container(
      padding: const EdgeInsets.all(16),
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
              Icon(icon, size: 18, color: accent),
              const SizedBox(width: 8),
              Expanded(
                child: Text(title, style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
              ),
              Text(
                percentLabel,
                style: TextStyle(
                  color: isHigh ? palette.warning : accent,
                  fontSize: 14 * scale,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: EvaTokens.borderPill,
            child: LinearProgressIndicator(
              value: clamped,
              minHeight: 6,
              backgroundColor: palette.panel,
              valueColor: AlwaysStoppedAnimation<Color>(isHigh ? palette.warning : accent),
            ),
          ),
          const SizedBox(height: 8),
          Text(subtitle, style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
        ],
      ),
    );
  }
}

class _ServiceStatusTile extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String title;
  final String endpoint;
  final bool isHealthy;
  final String statusNote;

  const _ServiceStatusTile({
    required this.palette,
    required this.scale,
    required this.title,
    required this.endpoint,
    required this.isHealthy,
    required this.statusNote,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isHealthy ? palette.success : palette.error,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontWeight: FontWeight.w600)),
              Text(endpoint, style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontFamily: 'monospace')),
            ],
          ),
        ),
        Text(
          statusNote,
          style: TextStyle(
            color: isHealthy ? palette.textPri : palette.error,
            fontSize: 11 * scale,
          ),
        ),
      ],
    );
  }
}
