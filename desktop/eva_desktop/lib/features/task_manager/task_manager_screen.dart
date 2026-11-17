import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class TaskManagerScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const TaskManagerScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<TaskManagerScreen> createState() => _TaskManagerScreenState();
}

class _TaskManagerScreenState extends State<TaskManagerScreen> {
  List<Map<String, dynamic>> _tasks = [];
  bool _loading = true;
  String _filter = 'All'; // 'All', 'Active', 'Completed', 'Failed', 'Blocked'
  Map<String, dynamic>? _selectedTask;
  Timer? _poller;
  bool _actionLoading = false;
  StreamSubscription? _eventSubscription;
  final List<Map<String, dynamic>> _liveEvents = [];

  @override
  void initState() {
    super.initState();
    _loadTasks();
    _poller = Timer.periodic(const Duration(seconds: 3), (_) => _loadTasks(silent: true));
  }

  @override
  void dispose() {
    _poller?.cancel();
    _eventSubscription?.cancel();
    super.dispose();
  }

  void _selectTask(Map<String, dynamic> task) {
    setState(() {
      _selectedTask = task;
      _liveEvents.clear();
    });
    _eventSubscription?.cancel();
    final taskId = task['task_id'] as String? ?? '';
    if (taskId.isNotEmpty) {
      _eventSubscription = EvaApiClient.streamTaskEvents(taskId).listen((event) {
        if (mounted) {
          setState(() {
            _liveEvents.add(event);
          });
        }
      });
    }
  }

  Future<void> _loadTasks({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    final list = await EvaApiClient.getTasks(limit: 100);
    if (mounted) {
      setState(() {
        _tasks = list;
        _loading = false;
        if (_selectedTask != null) {
          final id = _selectedTask!['task_id'];
          final updated = _tasks.firstWhere((t) => t['task_id'] == id, orElse: () => {});
          if (updated.isNotEmpty) _selectedTask = updated;
        }
      });
    }
  }

  List<Map<String, dynamic>> get _filteredTasks {
    return _tasks.where((t) {
      final s = t['status'] as String? ?? '';
      if (_filter == 'Active') return s == 'running' || s == 'planned' || s == 'action_resolution_required';
      if (_filter == 'Completed') return s == 'completed';
      if (_filter == 'Failed') return s == 'failed' || s == 'cancelled';
      if (_filter == 'Blocked') return s == 'blocked';
      return true;
    }).toList();
  }

  Future<void> _controlTask(String taskId, String action) async {
    setState(() => _actionLoading = true);
    await EvaApiClient.controlTask(taskId, action);
    await _loadTasks(silent: true);
    if (mounted) setState(() => _actionLoading = false);
  }

  Future<void> _executeTask(String taskId) async {
    setState(() => _actionLoading = true);
    await EvaApiClient.executeTask(taskId);
    await _loadTasks(silent: true);
    if (mounted) setState(() => _actionLoading = false);
  }

  Future<void> _handleConfirmation(String confId, bool approve) async {
    setState(() => _actionLoading = true);
    await EvaApiClient.respondConfirmation(confId, approve);
    await _loadTasks(silent: true);
    if (mounted) setState(() => _actionLoading = false);
  }

  Color _statusColor(String status, EvaPalette palette, Color accent) {
    switch (status) {
      case 'completed':
        return palette.success;
      case 'running':
        return accent;
      case 'blocked':
      case 'paused':
        return palette.warning;
      case 'failed':
      case 'cancelled':
        return palette.error;
      default:
        return palette.textSec;
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;
    final tasks = _filteredTasks;

    return Row(
      children: [
        // ── Task Queue & List ─────────────────────────────────────────────
        Expanded(
          flex: _selectedTask != null ? 5 : 10,
          child: Container(
            color: palette.bg,
            child: Column(
              children: [
                // Toolbar & Filters
                Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: palette.surface,
                    border: Border(bottom: BorderSide(color: palette.border)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.alt_route_rounded, size: 16, color: accent),
                      const SizedBox(width: 8),
                      Text('Task Manager', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                      const SizedBox(width: 12),
                      // Filter pills
                      for (final f in ['All', 'Active', 'Completed', 'Failed', 'Blocked']) ...[
                        InkWell(
                          onTap: () => setState(() => _filter = f),
                          borderRadius: EvaTokens.borderSm,
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 2),
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: _filter == f ? accent.withValues(alpha: 0.15) : Colors.transparent,
                              borderRadius: EvaTokens.borderSm,
                              border: _filter == f ? Border.all(color: accent.withValues(alpha: 0.4)) : null,
                            ),
                            child: Text(
                              f,
                              style: TextStyle(
                                color: _filter == f ? accent : palette.textSec,
                                fontSize: 11 * scale,
                                fontWeight: _filter == f ? FontWeight.w600 : FontWeight.normal,
                              ),
                            ),
                          ),
                        ),
                      ],
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        color: palette.textSec,
                        tooltip: 'Refresh tasks',
                        onPressed: () => _loadTasks(),
                      ),
                    ],
                  ),
                ),

                // Task List
                Expanded(
                  child: _loading
                      ? Center(child: CircularProgressIndicator(color: accent))
                      : tasks.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.task_alt_rounded, size: 40, color: palette.textSec.withValues(alpha: 0.4)),
                                  const SizedBox(height: 10),
                                  Text('No tasks found in "$_filter"', style: TextStyle(color: palette.textPri, fontSize: 13.5 * scale, fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 4),
                                  Text('Tasks are created when natural language requests are planned.', style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
                                ],
                              ),
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.all(12),
                              itemCount: tasks.length,
                              itemBuilder: (ctx, i) {
                                final t = tasks[i];
                                final isSel = _selectedTask != null && _selectedTask!['task_id'] == t['task_id'];
                                final status = t['status'] as String? ?? 'unknown';
                                final stColor = _statusColor(status, palette, accent);
                                final intent = t['intent'] as String? ?? 'general_operation';
                                final steps = (t['steps'] as List? ?? []).length;
                                final taskId = (t['task_id'] as String? ?? '').substring(0, 8);

                                return GestureDetector(
                                  onTap: () => _selectTask(t),
                                  child: Container(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: isSel ? accent.withValues(alpha: 0.1) : palette.surface,
                                      borderRadius: EvaTokens.borderMd,
                                      border: Border.all(
                                        color: isSel ? accent : palette.border,
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 8,
                                          height: 8,
                                          decoration: BoxDecoration(shape: BoxShape.circle, color: stColor),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  Text(
                                                    intent,
                                                    style: TextStyle(
                                                      color: isSel ? accent : palette.textPri,
                                                      fontSize: 13 * scale,
                                                      fontWeight: FontWeight.w600,
                                                    ),
                                                  ),
                                                  const SizedBox(width: 8),
                                                  Text('#$taskId', style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace')),
                                                ],
                                              ),
                                              const SizedBox(height: 3),
                                              Text(
                                                '$steps pipeline steps • Created: ${(t['created_at'] ?? '').substring(0, 16)}',
                                                style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                                              ),
                                            ],
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: stColor.withValues(alpha: 0.15),
                                            borderRadius: EvaTokens.borderSm,
                                          ),
                                          child: Text(
                                            status.toUpperCase(),
                                            style: TextStyle(color: stColor, fontSize: 9.5 * scale, fontWeight: FontWeight.w700),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                ),
              ],
            ),
          ),
        ),

        // ── Execution Inspector Details Pane ──────────────────────────────
        if (_selectedTask != null)
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 500,
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border(left: BorderSide(color: palette.border)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Inspector Header
                Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: palette.panel,
                    border: Border(bottom: BorderSide(color: palette.border)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.manage_search_rounded, size: 18, color: accent),
                      const SizedBox(width: 8),
                      Text('Execution Inspector', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 16),
                        color: palette.textSec,
                        onPressed: () => setState(() => _selectedTask = null),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                      ),
                    ],
                  ),
                ),

                // Inspector Content
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Overview Card
                        _InspectorHeaderCard(
                          task: _selectedTask!,
                          palette: palette,
                          accent: accent,
                          scale: scale,
                          onControl: _controlTask,
                          onExecute: _executeTask,
                          actionLoading: _actionLoading,
                        ),

                        const SizedBox(height: 18),

                        // Structured Architecture Pipeline Explanation
                        Text(
                          'EXECUTION PIPELINE ARCHITECTURE',
                          style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6),
                        ),
                        const SizedBox(height: 8),
                        _ArchitecturePipelineFlow(
                          task: _selectedTask!,
                          palette: palette,
                          accent: accent,
                          scale: scale,
                        ),

                        const SizedBox(height: 18),

                        // Planned & Executed Steps Checklist
                        Text(
                          'STEP DETAILS & TOOL OUTPUT',
                          style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6),
                        ),
                        const SizedBox(height: 8),
                        ...((_selectedTask!['steps'] as List? ?? []).cast<Map<String, dynamic>>()).map((step) {
                          return _StepDetailCard(
                            step: step,
                            palette: palette,
                            accent: accent,
                            scale: scale,
                            onApprove: (id) => _handleConfirmation(id, true),
                            onDeny: (id) => _handleConfirmation(id, false),
                          );
                        }),
                        if (_liveEvents.isNotEmpty) ...[
                          const SizedBox(height: 18),
                          Text(
                            'LIVE EXECUTION EVENT STREAM (PERSISTENT LOGS)',
                            style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6),
                          ),
                          const SizedBox(height: 8),
                          _LiveEventsViewer(
                            events: _liveEvents,
                            palette: palette,
                            accent: accent,
                            scale: scale,
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _InspectorHeaderCard extends StatelessWidget {
  final Map<String, dynamic> task;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final void Function(String, String) onControl;
  final ValueChanged<String> onExecute;
  final bool actionLoading;

  const _InspectorHeaderCard({
    required this.task,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onControl,
    required this.onExecute,
    required this.actionLoading,
  });

  @override
  Widget build(BuildContext context) {
    final taskId = task['task_id'] as String? ?? '';
    final intent = task['intent'] as String? ?? 'General Intent';
    final status = task['status'] as String? ?? '';
    final canExec = status == 'planned' || status == 'action_resolution_required';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: EvaTokens.borderMd,
        border: Border.all(color: palette.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  intent,
                  style: TextStyle(color: palette.textPri, fontSize: 15 * scale, fontWeight: FontWeight.w700),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.15),
                  borderRadius: EvaTokens.borderSm,
                ),
                child: Text(
                  status.toUpperCase(),
                  style: TextStyle(color: accent, fontSize: 10 * scale, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Task ID: $taskId',
            style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
          ),
          Text(
            'Request ID: ${task['request_id'] ?? 'unknown'}',
            style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              if (canExec)
                ElevatedButton.icon(
                  icon: const Icon(Icons.play_arrow_rounded, size: 14),
                  label: const Text('Execute Plan'),
                  style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
                  onPressed: actionLoading ? null : () => onExecute(taskId),
                ),
              if (status == 'running')
                OutlinedButton.icon(
                  icon: const Icon(Icons.pause_rounded, size: 14),
                  label: const Text('Pause'),
                  onPressed: actionLoading ? null : () => onControl(taskId, 'pause'),
                ),
              if (status == 'paused')
                OutlinedButton.icon(
                  icon: const Icon(Icons.play_arrow_rounded, size: 14),
                  label: const Text('Resume'),
                  onPressed: actionLoading ? null : () => onControl(taskId, 'resume'),
                ),
              if (status == 'running' || status == 'paused') ...[
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  icon: const Icon(Icons.stop_rounded, size: 14),
                  label: const Text('Stop'),
                  onPressed: actionLoading ? null : () => onControl(taskId, 'stop'),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _ArchitecturePipelineFlow extends StatelessWidget {
  final Map<String, dynamic> task;
  final EvaPalette palette;
  final Color accent;
  final double scale;

  const _ArchitecturePipelineFlow({
    required this.task,
    required this.palette,
    required this.accent,
    required this.scale,
  });

  @override
  Widget build(BuildContext context) {
    final steps = (task['steps'] as List? ?? []).cast<Map<String, dynamic>>();
    final status = task['status'] as String? ?? '';
    final hasTool = steps.isNotEmpty && steps[0]['action'] != null;
    final toolName = hasTool ? (steps[0]['action']['tool'] ?? 'general_tool') : 'none';

    final stages = [
      {'num': '1', 'name': 'Request Received', 'desc': 'Normalized text input', 'done': true},
      {'num': '2', 'name': 'Intent Classification', 'desc': task['intent'] ?? 'Resolved', 'done': true},
      {'num': '3', 'name': 'Context Resolution', 'desc': 'Target session & entities resolved', 'done': true},
      {'num': '4', 'name': 'Task Planning', 'desc': '${steps.length} ordered steps', 'done': steps.isNotEmpty},
      {'num': '5', 'name': 'Permission Validation', 'desc': 'Allowlist & boundary check', 'done': steps.isNotEmpty},
      {'num': '6', 'name': 'Tool Selection', 'desc': toolName, 'done': hasTool},
      {'num': '7', 'name': 'Execution', 'desc': status == 'completed' ? 'Executed successfully' : (status == 'running' ? 'In progress' : status), 'done': status == 'completed'},
      {'num': '8', 'name': 'Result Verification', 'desc': status == 'completed' ? 'Verified in OS' : 'Pending', 'done': status == 'completed'},
    ];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: EvaTokens.borderMd,
        border: Border.all(color: palette.borderSubtle),
      ),
      child: Column(
        children: stages.map((s) {
          final isDone = s['done'] == true;
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: (isDone ? accent : palette.border).withValues(alpha: 0.2),
                    border: Border.all(color: isDone ? accent : palette.border),
                  ),
                  child: Center(
                    child: Text(
                      s['num'] as String,
                      style: TextStyle(color: isDone ? accent : palette.textSec, fontSize: 10 * scale, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  s['name'] as String,
                  style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                Text(
                  s['desc'] as String,
                  style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontFamily: 'monospace'),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _StepDetailCard extends StatelessWidget {
  final Map<String, dynamic> step;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final ValueChanged<String> onApprove;
  final ValueChanged<String> onDeny;

  const _StepDetailCard({
    required this.step,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onApprove,
    required this.onDeny,
  });

  @override
  Widget build(BuildContext context) {
    final seq = step['sequence'];
    final desc = step['description'] ?? '';
    final status = step['status'] ?? 'planned';
    final action = step['action'] as Map<String, dynamic>?;
    final result = step['result'] as Map<String, dynamic>?;
    final error = step['error'] as Map<String, dynamic>?;

    final isConfirmation = status == 'blocked' && error?['code'] == 'RequiresConfirmation';
    final confId = isConfirmation ? (error?['details']?['confirmation_id'] as String?) : null;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: EvaTokens.borderSm,
        border: Border.all(
          color: isConfirmation ? palette.warning : palette.borderSubtle,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('Step $seq: ', style: TextStyle(color: accent, fontSize: 12 * scale, fontWeight: FontWeight.w700)),
              Expanded(
                child: Text(desc, style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w600)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: (status == 'completed' ? palette.success : (status == 'failed' ? palette.error : palette.warning)).withValues(alpha: 0.15),
                  borderRadius: EvaTokens.borderSm,
                ),
                child: Text(
                  status.toUpperCase(),
                  style: TextStyle(
                    color: status == 'completed' ? palette.success : (status == 'failed' ? palette.error : palette.warning),
                    fontSize: 9.5 * scale,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          if (action != null) ...[
            const SizedBox(height: 6),
            Text(
              'Tool: ${action['tool']} • Arguments: ${action['arguments']}',
              style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
            ),
          ],
          if (result != null) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: palette.surface,
                borderRadius: EvaTokens.borderSm,
              ),
              child: Text(
                'Result: ${result['message'] ?? result}',
                style: TextStyle(color: palette.success, fontSize: 11 * scale, fontFamily: 'monospace'),
              ),
            ),
          ],
          if (error != null) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: palette.surface,
                borderRadius: EvaTokens.borderSm,
              ),
              child: Text(
                'Error: ${error['message'] ?? error['code'] ?? error}',
                style: TextStyle(color: palette.error, fontSize: 11 * scale, fontFamily: 'monospace'),
              ),
            ),
          ],
          if (isConfirmation && confId != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                ElevatedButton(
                  onPressed: () => onApprove(confId),
                  style: ElevatedButton.styleFrom(backgroundColor: palette.success, foregroundColor: Colors.white),
                  child: const Text('Approve Action'),
                ),
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: () => onDeny(confId),
                  child: Text('Deny', style: TextStyle(color: palette.error)),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _LiveEventsViewer extends StatelessWidget {
  final List<Map<String, dynamic>> events;
  final EvaPalette palette;
  final Color accent;
  final double scale;

  const _LiveEventsViewer({
    required this.events,
    required this.palette,
    required this.accent,
    required this.scale,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: palette.inputBg,
        borderRadius: EvaTokens.borderMd,
        border: Border.all(color: palette.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.stream_rounded, size: 14 * scale, color: accent),
              const SizedBox(width: 6),
              Text(
                'Live Task Events (${events.length})',
                style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(shape: BoxShape.circle, color: palette.success),
              ),
              const SizedBox(width: 4),
              Text('Connected', style: TextStyle(color: palette.success, fontSize: 10 * scale)),
            ],
          ),
          const Divider(height: 16),
          for (final ev in events.reversed.take(12)) ...[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2.5),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    ev['timestamp'] != null ? ev['timestamp'].toString().split('T').last.split('.').first : '',
                    style: TextStyle(color: palette.textSec, fontSize: 10 * scale, fontFamily: 'monospace'),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.15),
                      borderRadius: EvaTokens.borderSm,
                    ),
                    child: Text(
                      ev['event_type'] ?? ev['type'] ?? 'event',
                      style: TextStyle(color: accent, fontSize: 9.5 * scale, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      ev['data'] != null ? ev['data'].toString() : (ev['step_id'] != null ? 'Step: ${ev['step_id']}' : ''),
                      style: TextStyle(color: palette.textPri, fontSize: 10.5 * scale, fontFamily: 'monospace'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
