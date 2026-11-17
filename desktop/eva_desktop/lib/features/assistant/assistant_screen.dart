import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

enum MicState { idle, recording, transcribing, error }

class ConvSummary {
  final String id;
  final String title;
  final String updatedAt;
  final int messageCount;

  ConvSummary({
    required this.id,
    required this.title,
    required this.updatedAt,
    required this.messageCount,
  });

  factory ConvSummary.fromJson(Map<String, dynamic> j) => ConvSummary(
        id: j['conversation_id'] as String,
        title: j['title'] as String,
        updatedAt: j['updated_at'] as String,
        messageCount: j['message_count'] as int,
      );
}

class AssistantScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const AssistantScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<AssistantScreen> createState() => AssistantScreenState();
}

class AssistantScreenState extends State<AssistantScreen> {
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();
  late final FocusNode _inputFocusNode;
  final List<Map<String, dynamic>> _messages = [];
  bool _isLoading = false;
  String? _sessionId;

  bool _historyOpen = true;
  List<ConvSummary> _conversations = [];
  bool _loadingHistory = false;

  MicState _micState = MicState.idle;
  String? _micError;
  String? _recordingId;
  int _recordingCountdown = 5;
  Timer? _countdownTimer;
  Timer? _silencePoller;

  bool _ttsSpeaking = false;
  Timer? _ttsStatusTimer;
  Timer? _taskPoller;
  Timer? _agenticVoicePoller;
  String? _lastAgenticTranscript;

  MicState get micState => _micState;
  bool get ttsSpeaking => _ttsSpeaking;
  int get recordingCountdown => _recordingCountdown;

  @override
  void initState() {
    super.initState();
    _inputFocusNode = FocusNode(
      onKeyEvent: (node, event) {
        if (event is KeyDownEvent && event.logicalKey == LogicalKeyboardKey.enter) {
          if (HardwareKeyboard.instance.isShiftPressed) {
            return KeyEventResult.ignored; // Allows Shift+Enter for newline
          } else {
            sendMessage();
            return KeyEventResult.handled; // Submits message and prevents newline
          }
        }
        return KeyEventResult.ignored;
      },
    );
    _loadConversationHistory();
    _startTtsStatusPolling();
    _startAgenticVoicePolling();
    _taskPoller = Timer.periodic(const Duration(milliseconds: 900), (_) => _refreshTasks());
  }

  @override
  void dispose() {
    _ttsStatusTimer?.cancel();
    _agenticVoicePoller?.cancel();
    _taskPoller?.cancel();
    _silencePoller?.cancel();
    _countdownTimer?.cancel();
    if (_recordingId != null) {
      http.post(
        Uri.parse('http://127.0.0.1:8000/api/v1/stt/record/cancel?recording_id=$_recordingId'),
      ).then<void>((_) {}, onError: (_) {});
    }
    _inputFocusNode.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 80), () {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 240),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _loadConversationHistory() async {
    setState(() => _loadingHistory = true);
    try {
      final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/conversations'));
      if (resp.statusCode == 200) {
        final list = json.decode(resp.body) as List;
        setState(() {
          _conversations = list.map((j) => ConvSummary.fromJson(j as Map<String, dynamic>)).toList();
        });
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingHistory = false);
    }
  }

  Future<void> _refreshTasks() async {
    final taskIds = _messages
        .map((message) => (message['task'] as Map<String, dynamic>?)?['task_id'])
        .whereType<String>()
        .toSet();
    if (taskIds.isEmpty || !mounted) return;
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/core/tasks'));
      if (response.statusCode != 200) return;
      final tasks = (json.decode(response.body) as List).cast<Map<String, dynamic>>();
      final byId = {for (final task in tasks) task['task_id'] as String: task};
      var changed = false;
      for (final message in _messages) {
        final task = message['task'] as Map<String, dynamic>?;
        final updated = task == null ? null : byId[task['task_id']];
        if (updated != null && json.encode(updated) != json.encode(task)) {
          message['task'] = updated;
          changed = true;
        }
      }
      if (changed && mounted) setState(() {});
    } catch (_) {}
  }

  Future<void> _openConversation(ConvSummary conv) async {
    try {
      final resp = await http.get(
        Uri.parse('http://127.0.0.1:8000/api/v1/conversations/${conv.id}/messages'),
      );
      if (resp.statusCode == 200) {
        final msgs = json.decode(resp.body) as List;
        setState(() {
          _sessionId = conv.id;
          _messages.clear();
          for (final m in msgs) {
            final role = m['role'] as String;
            _messages.add({
              'sender': role == 'user' ? 'user' : 'eva',
              'text': m['content'] as String,
            });
          }
        });
        _scrollToBottom();
      }
    } catch (_) {
      _showError('Could not load conversation.');
    }
  }

  Future<void> _deleteConversation(ConvSummary conv) async {
    final palette = widget.themeNotifier.getPalette(context);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: palette.surface,
        title: Text('Delete conversation?', style: TextStyle(color: palette.textPri)),
        content: Text(
          'This will permanently delete "${conv.title}" and its message history.',
          style: TextStyle(color: palette.textSec),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text('Cancel', style: TextStyle(color: palette.textSec)),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text('Delete', style: TextStyle(color: palette.error)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final resp = await http.delete(
        Uri.parse('http://127.0.0.1:8000/api/v1/conversations/${conv.id}'),
      );
      if (resp.statusCode == 200) {
        if (_sessionId == conv.id) {
          startNewChat();
        }
        await _loadConversationHistory();
      }
    } catch (_) {
      _showError('Delete failed.');
    }
  }

  void startNewChat() {
    setState(() {
      _sessionId = null;
      _messages.clear();
    });
  }

  Future<void> sendMessage([String? forcedText]) async {
    final text = (forcedText ?? _input.text).trim();
    if (text.isEmpty || _isLoading) return;
    if (forcedText == null) _input.clear();

    setState(() {
      _messages.add({'sender': 'user', 'text': text});
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final request = http.Request(
        'POST',
        Uri.parse('http://127.0.0.1:8000/api/v1/core/chat/stream'),
      );
      request.headers['Content-Type'] = 'application/json';

      final body = <String, dynamic>{
        'source': 'desktop',
        'input_type': 'text',
        'content': text,
        'metadata': {'tts_enabled': widget.themeNotifier.ttsEnabled},
      };
      if (_sessionId != null) body['session_id'] = _sessionId;
      request.body = json.encode(body);

      final streamed = await request.send();

      if (streamed.statusCode == 200) {
        bool firstMeta = false;
        var lineBuffer = '';
        await for (final chunk in streamed.stream.transform(utf8.decoder)) {
          lineBuffer += chunk;
          final lines = lineBuffer.split('\n');
          lineBuffer = lines.removeLast();
          for (final line in lines) {
            if (line.trim().isEmpty) continue;
            try {
              final data = json.decode(line) as Map<String, dynamic>;
              _handleStreamEvent(data, firstMeta);
              if (data['type'] == 'metadata') firstMeta = true;
            } catch (_) {}
          }
        }
        if (lineBuffer.trim().isNotEmpty) {
          try {
            final data = json.decode(lineBuffer) as Map<String, dynamic>;
            _handleStreamEvent(data, firstMeta);
          } catch (_) {}
        }
        await _loadConversationHistory();
      } else {
        _addSystemError('Server error: ${streamed.statusCode}');
      }
    } catch (e) {
      _addSystemError('Connection failed. Is EVA Core running?');
    } finally {
      if (mounted) setState(() => _isLoading = false);
      _scrollToBottom();
    }
  }

  void _handleStreamEvent(Map<String, dynamic> data, bool firstMetaReceived) {
    switch (data['type']) {
      case 'status':
        break;
      case 'metadata':
        final d = data['data'] as Map<String, dynamic>;
        if (d['session_id'] != null) {
          _sessionId = d['session_id'] as String;
        }
        if (!firstMetaReceived) {
          setState(() {
            _messages.add({
              'sender': 'eva',
              'text': '',
              'intent': d['intent'],
              'confidence': d['confidence'],
              'route': d['route'],
              'task': d['task'],
              'provider': d['provider'],
            });
          });
        }
        break;
      case 'token':
        final content = (data['content'] as String?) ?? '';
        if (content.isEmpty) break;
        setState(() {
          if (_messages.isNotEmpty && _messages.last['sender'] == 'eva') {
            _messages.last['text'] += content;
          }
        });
        if (_scroll.hasClients) {
          _scroll.jumpTo(_scroll.position.maxScrollExtent);
        }
        break;
      case 'task_update':
        setState(() {
          if (_messages.isNotEmpty && _messages.last['sender'] == 'eva') {
            _messages.last['task'] = data['data'];
          }
        });
        break;
      case 'done':
        setState(() => _isLoading = false);
        break;
      case 'error':
        _addSystemError((data['message'] as String?) ?? 'Response generation failed.');
        break;
    }
  }

  void _addSystemError(String msg) {
    setState(() => _messages.add({'sender': 'system', 'text': msg}));
  }

  void _showError(String msg) {
    final palette = widget.themeNotifier.getPalette(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg, style: TextStyle(color: palette.textPri)),
        backgroundColor: palette.error.withValues(alpha: 0.9),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _startTtsStatusPolling() {
    _ttsStatusTimer ??= Timer.periodic(const Duration(milliseconds: 600), (_) async {
      try {
        final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/tts/status'));
        if (resp.statusCode == 200 && mounted) {
          final data = json.decode(resp.body) as Map<String, dynamic>;
          setState(() {
            _ttsSpeaking = data['speaking'] == true;
          });
        }
      } catch (_) {}
    });
  }

  Future<void> stopSpeech() async {
    try {
      await http.post(Uri.parse('http://127.0.0.1:8000/api/v1/tts/stop'));
    } catch (_) {}
    if (mounted) setState(() => _ttsSpeaking = false);
  }

  void _startAgenticVoicePolling() {
    _agenticVoicePoller ??= Timer.periodic(const Duration(milliseconds: 700), (_) async {
      if (!mounted || !widget.themeNotifier.agenticVoiceActive) return;
      try {
        final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/stt/agentic/status'));
        if (resp.statusCode == 200 && mounted) {
          final data = json.decode(resp.body) as Map<String, dynamic>;
          final transcript = (data['last_transcript'] as String? ?? '').trim();
          final response = (data['last_response'] as String? ?? '').trim();

          if (transcript.isNotEmpty && transcript != _lastAgenticTranscript) {
            _lastAgenticTranscript = transcript;
            setState(() {
              _messages.add({
                'role': 'user',
                'content': transcript,
                'timestamp': DateTime.now().toIso8601String(),
                'source': 'agentic_voice',
              });
              if (response.isNotEmpty) {
                _messages.add({
                  'role': 'assistant',
                  'content': response,
                  'timestamp': DateTime.now().toIso8601String(),
                  'source': 'eva',
                });
              }
            });
            _scrollToBottom();
          }
        }
      } catch (_) {}
    });
  }

  Future<void> handleMicButton() async {
    if (_micState == MicState.recording && _recordingId != null) {
      _countdownTimer?.cancel();
      setState(() => _micState = MicState.transcribing);
      await _stopAndTranscribe(_recordingId!);
      return;
    }

    setState(() {
      _micState = MicState.recording;
      _micError = null;
      _recordingCountdown = 5;
    });

    try {
      final recId = await EvaApiClient.startRecording(duration: 5.0);
      if (recId != null) {
        _recordingId = recId;
        _startSilencePolling(recId);
        _countdownTimer?.cancel();
        _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
          if (!mounted) {
            timer.cancel();
            return;
          }
          if (_micState != MicState.recording || _recordingId != recId) {
            timer.cancel();
            return;
          }
          setState(() {
            _recordingCountdown -= 1;
          });
          if (_recordingCountdown <= 0) {
            timer.cancel();
            if (_recordingId == recId && _micState == MicState.recording) {
              setState(() => _micState = MicState.transcribing);
              _stopAndTranscribe(recId);
            }
          }
        });
      } else {
        setState(() {
          _micState = MicState.error;
          _micError = 'Could not start recording. Is EVA Core running?';
          _recordingId = null;
        });
      }
    } catch (e) {
      setState(() {
        _micState = MicState.error;
        _micError = 'Connection error: is EVA Core running?';
        _recordingId = null;
      });
    }
  }

  Future<void> cancelRecording() async {
    _countdownTimer?.cancel();
    _silencePoller?.cancel();
    final recId = _recordingId;
    setState(() {
      _recordingId = null;
      _micState = MicState.idle;
      _recordingCountdown = 5;
      _micError = null;
    });
    if (recId != null) {
      await EvaApiClient.cancelRecording(recId);
    }
  }

  void _startSilencePolling(String recordingId) {
    _silencePoller?.cancel();
    _silencePoller = Timer.periodic(const Duration(milliseconds: 300), (_) async {
      if (!mounted || _micState != MicState.recording || _recordingId != recordingId) return;
      try {
        final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/stt/record/status?recording_id=$recordingId'));
        if (resp.statusCode == 200) {
          final data = json.decode(resp.body) as Map<String, dynamic>;
          if (data['silence_detected'] == true && _recordingId == recordingId) {
            _countdownTimer?.cancel();
            _silencePoller?.cancel();
            setState(() => _micState = MicState.transcribing);
            await _stopAndTranscribe(recordingId);
          }
        }
      } catch (_) {}
    });
  }

  Future<void> _stopAndTranscribe(String recordingId) async {
    _countdownTimer?.cancel();
    _silencePoller?.cancel();
    try {
      final resp = await http.post(Uri.parse('http://127.0.0.1:8000/api/v1/stt/record/stop?recording_id=$recordingId'));
      _recordingId = null;
      final body = json.decode(resp.body) as Map<String, dynamic>;

      if (resp.statusCode == 200) {
        final transcript = (body['transcript'] as String? ?? '').trim();
        setState(() {
          _input.text = transcript;
          _input.selection = TextSelection.fromPosition(TextPosition(offset: transcript.length));
          _micState = MicState.idle;
          _recordingCountdown = 5;
        });
        if (transcript.isNotEmpty) {
          await sendMessage(transcript);
        }
      } else if (resp.statusCode == 422) {
        setState(() {
          _micState = MicState.idle;
          _recordingCountdown = 5;
          _micError = 'No speech detected — please try again.';
        });
      } else {
        setState(() {
          _micState = MicState.error;
          _recordingCountdown = 5;
          _micError = body['detail']?.toString() ?? 'Transcription failed.';
        });
      }
    } catch (e) {
      _recordingId = null;
      setState(() {
        _micState = MicState.error;
        _recordingCountdown = 5;
        _micError = 'Error during transcription: $e';
      });
    }
  }

  Future<void> _executeTask(String taskId, int msgIndex) async {
    setState(() => _isLoading = true);
    try {
      final resp = await http.post(Uri.parse('http://127.0.0.1:8000/api/v1/core/task/$taskId/execute'));
      if (resp.statusCode == 200) {
        setState(() => _messages[msgIndex]['task'] = json.decode(resp.body));
      } else {
        _addSystemError('Execute error: ${resp.statusCode}');
      }
    } catch (_) {
      _addSystemError('Execute connection failed.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _controlTask(String taskId, String action, int msgIndex) async {
    try {
      final response = await http.post(Uri.parse('http://127.0.0.1:8000/api/v1/core/task/$taskId/$action'));
      if (response.statusCode == 200 && mounted) {
        setState(() => _messages[msgIndex]['task'] = json.decode(response.body));
      } else {
        _addSystemError('Could not $action task (${response.statusCode}).');
      }
    } catch (_) {
      _addSystemError('Could not reach EVA Core to $action task.');
    }
  }

  Future<void> _respondToConfirmation(String confirmationId, int msgIndex, bool approve) async {
    setState(() => _isLoading = true);
    try {
      final action = approve ? 'approve' : 'deny';
      final response = await http.post(Uri.parse('http://127.0.0.1:8000/api/v1/core/confirmation/$confirmationId/$action'));
      if (response.statusCode == 200) {
        final body = json.decode(response.body) as Map<String, dynamic>;
        setState(() {
          _messages[msgIndex]['task'] = body['task'];
          _messages[msgIndex]['text'] = approve
              ? 'Confirmation approved. The requested operation was processed.'
              : 'Confirmation denied. The requested operation was cancelled.';
        });
      } else {
        _addSystemError('Confirmation was not accepted (${response.statusCode}).');
      }
    } catch (_) {
      _addSystemError('Could not reach EVA Core to update confirmation.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    return Row(
      children: [
        // ── Conversation History Drawer ───────────────────────────────────
        if (widget.themeNotifier.historyVisible)
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: _historyOpen ? 230 : 0,
            curve: Curves.easeInOut,
            child: _historyOpen
                ? Container(
                    decoration: BoxDecoration(
                      color: palette.sidebar,
                      border: Border(right: BorderSide(color: palette.border)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(14, 12, 10, 8),
                          child: Row(
                            children: [
                              Text(
                                'CONVERSATIONS',
                                style: TextStyle(
                                  color: palette.textSec,
                                  fontSize: 10.5 * scale,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.6,
                                ),
                              ),
                              const Spacer(),
                              IconButton(
                                icon: const Icon(Icons.refresh_rounded, size: 15),
                                color: palette.textSec,
                                tooltip: 'Refresh conversations',
                                onPressed: _loadConversationHistory,
                                padding: EdgeInsets.zero,
                                constraints: const BoxConstraints(minWidth: 26, minHeight: 26),
                              ),
                            ],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          child: SizedBox(
                            height: 32,
                            child: ElevatedButton.icon(
                              icon: const Icon(Icons.add_rounded, size: 15),
                              label: Text('New Chat', style: TextStyle(fontSize: 11.5 * scale)),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: accent.withValues(alpha: 0.15),
                                foregroundColor: accent,
                                elevation: 0,
                                side: BorderSide(color: accent.withValues(alpha: 0.5)),
                                shape: RoundedRectangleBorder(borderRadius: EvaTokens.borderSm),
                              ),
                              onPressed: startNewChat,
                            ),
                          ),
                        ),
                        const Divider(height: 14),
                        Expanded(
                          child: _loadingHistory
                              ? Center(child: CircularProgressIndicator(color: accent, strokeWidth: 2))
                              : _conversations.isEmpty
                                  ? Center(
                                      child: Text(
                                        'No conversations yet.',
                                        style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale),
                                      ),
                                    )
                                  : ListView.builder(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                                      itemCount: _conversations.length,
                                      itemBuilder: (ctx, i) {
                                        final conv = _conversations[i];
                                        final active = conv.id == _sessionId;
                                        return _ConvListItem(
                                          conv: conv,
                                          active: active,
                                          palette: palette,
                                          accent: accent,
                                          scale: scale,
                                          onTap: () => _openConversation(conv),
                                          onDelete: () => _deleteConversation(conv),
                                        );
                                      },
                                    ),
                        ),
                      ],
                    ),
                  )
                : null,
          ),

        // ── Main Interaction Column ──────────────────────────────────────
        Expanded(
          child: Column(
            children: [
              // Header bar with status & controls
              Container(
                height: 38,
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                  color: palette.surface,
                  border: Border(bottom: BorderSide(color: palette.border)),
                ),
                child: Row(
                  children: [
                    if (widget.themeNotifier.historyVisible)
                      IconButton(
                        icon: Icon(
                          _historyOpen ? Icons.menu_open_rounded : Icons.menu_rounded,
                          size: 17,
                          color: palette.textSec,
                        ),
                        tooltip: _historyOpen ? 'Hide conversations' : 'Show conversations',
                        onPressed: () => setState(() => _historyOpen = !_historyOpen),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                      ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: (_micState == MicState.recording || _isLoading ? accent : palette.border).withValues(alpha: 0.15),
                        borderRadius: EvaTokens.borderSm,
                        border: Border.all(
                          color: (_micState == MicState.recording || _isLoading ? accent : palette.border).withValues(alpha: 0.35),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _micState == MicState.recording
                                ? Icons.mic_rounded
                                : (_isLoading ? Icons.psychology_rounded : Icons.circle),
                            size: 11,
                            color: _micState == MicState.recording || _isLoading ? accent : palette.textSec,
                          ),
                          const SizedBox(width: 5),
                          Text(
                            _micState == MicState.recording
                                ? 'Listening'
                                : (_micState == MicState.transcribing
                                    ? 'Transcribing'
                                    : (_isLoading ? 'Thinking…' : 'Ready')),
                            style: TextStyle(
                              color: _micState == MicState.recording || _isLoading ? accent : palette.textSec,
                              fontSize: 10 * scale,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _sessionId != null ? 'Session: ${_sessionId!.substring(0, 8)}…' : 'Active Conversation',
                        style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (_ttsSpeaking)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: palette.warning.withValues(alpha: 0.15),
                          borderRadius: EvaTokens.borderSm,
                          border: Border.all(color: palette.warning.withValues(alpha: 0.4)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.volume_up_rounded, size: 12, color: palette.warning),
                            const SizedBox(width: 4),
                            Text('Piper Speaking', style: TextStyle(color: palette.warning, fontSize: 10 * scale)),
                            const SizedBox(width: 4),
                            InkWell(
                              onTap: stopSpeech,
                              child: Icon(Icons.stop_rounded, size: 13, color: palette.warning),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              // ── Agentic Voice Active Banner ───────────────────────────────
              if (widget.themeNotifier.agenticVoiceActive)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
                  color: accent.withValues(alpha: 0.12),
                  child: Row(
                    children: [
                      Icon(Icons.graphic_eq_rounded, color: accent, size: 16 * scale),
                      const SizedBox(width: 8),
                      Text(
                        'Agentic Mode Active — 5-Second Voice Capture & Autonomous Execution',
                        style: TextStyle(color: accent, fontSize: 11 * scale, fontWeight: FontWeight.w600),
                      ),
                      const Spacer(),
                      InkWell(
                        onTap: () async {
                          widget.themeNotifier.setAgenticVoiceActive(false);
                          await EvaApiClient.emergencyStopAgenticVoice();
                          stopSpeech();
                        },
                        borderRadius: EvaTokens.borderSm,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: palette.error,
                            borderRadius: EvaTokens.borderSm,
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.stop_circle_rounded, size: 13, color: Colors.white),
                              SizedBox(width: 4),
                              Text(
                                'EMERGENCY STOP',
                                style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              // Chat Messages View
              Expanded(
                child: _messages.isEmpty
                    ? Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 480),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 56,
                                height: 56,
                                decoration: BoxDecoration(
                                  color: accent.withValues(alpha: 0.12),
                                  borderRadius: EvaTokens.borderLg,
                                  border: Border.all(color: accent.withValues(alpha: 0.3)),
                                ),
                                child: Icon(Icons.terminal_rounded, size: 28, color: accent),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'EVA Assistant Engine',
                                style: TextStyle(
                                  color: palette.textPri,
                                  fontSize: 17 * scale,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Ask questions, control desktop applications, manage files in your workspace, or execute planned actions.',
                                style: TextStyle(color: palette.textSec, fontSize: 12.5 * scale, height: 1.4),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 18),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                alignment: WrapAlignment.center,
                                children: [
                                  _PromptChip(
                                    palette: palette,
                                    scale: scale,
                                    label: 'Open Chrome and search Linux kernel',
                                    onTap: () => sendMessage('Open Chrome and search Linux kernel'),
                                  ),
                                  _PromptChip(
                                    palette: palette,
                                    scale: scale,
                                    label: 'Open VS Code',
                                    onTap: () => sendMessage('Open VS Code'),
                                  ),
                                  _PromptChip(
                                    palette: palette,
                                    scale: scale,
                                    label: 'List files in workspace',
                                    onTap: () => sendMessage('List files in workspace'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                        itemCount: _messages.length,
                        itemBuilder: (ctx, i) => _AssistantBubble(
                          message: _messages[i],
                          palette: palette,
                          accent: accent,
                          scale: scale,
                          onExecuteTask: (taskId) => _executeTask(taskId, i),
                          onControlTask: (taskId, action) => _controlTask(taskId, action, i),
                          onApproveConfirmation: (id) => _respondToConfirmation(id, i, true),
                          onDenyConfirmation: (id) => _respondToConfirmation(id, i, false),
                        ),
                      ),
              ),

              if (_isLoading)
                Padding(
                  padding: const EdgeInsets.fromLTRB(40, 0, 20, 8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                        decoration: BoxDecoration(
                          color: palette.assistMsg,
                          borderRadius: EvaTokens.borderSm,
                          border: Border.all(color: palette.border),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(strokeWidth: 1.5, color: accent),
                            ),
                            const SizedBox(width: 8),
                            Text('EVA is processing request…', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

              if (_micState == MicState.error && _micError != null)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: palette.error.withValues(alpha: 0.1),
                    borderRadius: EvaTokens.borderSm,
                    border: Border.all(color: palette.error.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.mic_off_rounded, color: palette.error, size: 15),
                      const SizedBox(width: 8),
                      Expanded(child: Text(_micError!, style: TextStyle(color: palette.error, fontSize: 11.5 * scale))),
                      IconButton(
                        icon: Icon(Icons.close_rounded, size: 15, color: palette.error),
                        onPressed: () => setState(() => _micState = MicState.idle),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                      ),
                    ],
                  ),
                ),

              // ── 5-Second Voice Input Listening Countdown Banner ────────────
              if (_micState == MicState.recording)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: palette.error.withValues(alpha: 0.12),
                    borderRadius: EvaTokens.borderSm,
                    border: Border.all(color: palette.error.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          color: palette.error.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(Icons.graphic_eq_rounded, color: palette.error, size: 16),
                      ),
                      const SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Listening (5-Second Automatic Capture)',
                            style: TextStyle(
                              color: palette.textPri,
                              fontSize: 12 * scale,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            '$_recordingCountdown seconds remaining • speak now or click Stop',
                            style: TextStyle(color: palette.error, fontSize: 11 * scale),
                          ),
                        ],
                      ),
                      const Spacer(),
                      TextButton.icon(
                        icon: Icon(Icons.close_rounded, size: 14, color: palette.textSec),
                        label: Text('Cancel', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                        onPressed: cancelRecording,
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.stop_rounded, size: 14),
                        label: const Text('Stop & Transcribe'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: palette.error,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        ),
                        onPressed: () {
                          if (_recordingId != null) {
                            _countdownTimer?.cancel();
                            setState(() => _micState = MicState.transcribing);
                            _stopAndTranscribe(_recordingId!);
                          }
                        },
                      ),
                    ],
                  ),
                ),

              // ── Transcribing Status Banner ────────────────────────────────
              if (_micState == MicState.transcribing)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: EvaTokens.borderSm,
                    border: Border.all(color: accent.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: accent),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'Transcribing speech with Faster-Whisper…',
                        style: TextStyle(
                          color: palette.textPri,
                          fontSize: 12 * scale,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),

              // Composer
              Container(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
                decoration: BoxDecoration(
                  color: palette.surface,
                  border: Border(top: BorderSide(color: palette.border)),
                ),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 860),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Tooltip(
                          message: 'New chat session',
                          child: IconButton(
                            icon: const Icon(Icons.add_comment_outlined, size: 18),
                            color: palette.textSec,
                            onPressed: startNewChat,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: TextField(
                            controller: _input,
                            focusNode: _inputFocusNode,
                            minLines: 1,
                            maxLines: 5,
                            textInputAction: TextInputAction.send,
                            style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
                            decoration: InputDecoration(
                              hintText: 'Ask EVA, give a command, or inspect tasks…',
                              hintStyle: TextStyle(color: palette.textSec, fontSize: 12.5 * scale),
                              isDense: true,
                              fillColor: palette.inputBg,
                            ),
                            onSubmitted: (_) => sendMessage(),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Tooltip(
                          message: _micState == MicState.recording ? 'Stop recording' : 'Voice input (Faster-Whisper)',
                          child: IconButton(
                            icon: _micState == MicState.transcribing
                                ? SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: accent),
                                  )
                                : Icon(
                                    _micState == MicState.recording ? Icons.stop_rounded : Icons.mic_rounded,
                                    size: 19,
                                    color: _micState == MicState.recording ? palette.error : palette.textSec,
                                  ),
                            onPressed: handleMicButton,
                          ),
                        ),
                        const SizedBox(width: 6),
                        SizedBox(
                          width: 36,
                          height: 36,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : () => sendMessage(),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: accent,
                              foregroundColor: widget.themeNotifier.isDark(context) ? palette.bg : Colors.white,
                              padding: EdgeInsets.zero,
                              shape: RoundedRectangleBorder(borderRadius: EvaTokens.borderSm),
                            ),
                            child: _isLoading
                                ? SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: palette.bg))
                                : const Icon(Icons.send_rounded, size: 16),
                          ),
                        ),
                      ],
                    ),
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

class _ConvListItem extends StatefulWidget {
  final ConvSummary conv;
  final bool active;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _ConvListItem({
    required this.conv,
    required this.active,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onTap,
    required this.onDelete,
  });

  @override
  State<_ConvListItem> createState() => _ConvListItemState();
}

class _ConvListItemState extends State<_ConvListItem> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 2),
          padding: const EdgeInsets.fromLTRB(10, 8, 6, 8),
          decoration: BoxDecoration(
            color: widget.active
                ? widget.accent.withValues(alpha: 0.15)
                : (_hovered ? widget.palette.surface : Colors.transparent),
            borderRadius: EvaTokens.borderSm,
            border: widget.active
                ? Border.all(color: widget.accent.withValues(alpha: 0.4))
                : Border.all(color: Colors.transparent),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.conv.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: widget.active ? widget.accent : widget.palette.textPri,
                        fontSize: 12 * widget.scale,
                        fontWeight: widget.active ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${widget.conv.messageCount} messages',
                      style: TextStyle(color: widget.palette.textSec, fontSize: 10 * widget.scale),
                    ),
                  ],
                ),
              ),
              if (_hovered || widget.active)
                GestureDetector(
                  onTap: widget.onDelete,
                  child: Padding(
                    padding: const EdgeInsets.only(left: 4),
                    child: Icon(Icons.delete_outline_rounded, size: 14, color: widget.palette.error),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PromptChip extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String label;
  final VoidCallback onTap;

  const _PromptChip({
    required this.palette,
    required this.scale,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: EvaTokens.borderSm,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: palette.surface,
          borderRadius: EvaTokens.borderSm,
          border: Border.all(color: palette.border),
        ),
        child: Text(label, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale)),
      ),
    );
  }
}

class _AssistantBubble extends StatelessWidget {
  final Map<String, dynamic> message;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final ValueChanged<String> onExecuteTask;
  final void Function(String, String) onControlTask;
  final ValueChanged<String> onApproveConfirmation;
  final ValueChanged<String> onDenyConfirmation;

  const _AssistantBubble({
    required this.message,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onExecuteTask,
    required this.onControlTask,
    required this.onApproveConfirmation,
    required this.onDenyConfirmation,
  });

  @override
  Widget build(BuildContext context) {
    final sender = message['sender'] as String? ?? 'eva';
    final text = message['text'] as String? ?? '';
    final task = message['task'] as Map<String, dynamic>?;
    final isUser = sender == 'user';
    final isSystem = sender == 'system';

    if (isSystem) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: palette.error.withValues(alpha: 0.12),
              borderRadius: EvaTokens.borderSm,
              border: Border.all(color: palette.error.withValues(alpha: 0.3)),
            ),
            child: Text(text, style: TextStyle(color: palette.error, fontSize: 11.5 * scale)),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              width: 28,
              height: 28,
              margin: const EdgeInsets.only(top: 2, right: 8),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.15),
                borderRadius: EvaTokens.borderSm,
                border: Border.all(color: accent.withValues(alpha: 0.35)),
              ),
              child: Icon(Icons.auto_awesome_rounded, size: 14, color: accent),
            ),
          ],
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.65),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isUser ? palette.userMsg : palette.assistMsg,
                  borderRadius: EvaTokens.borderMd,
                  border: Border.all(
                    color: isUser ? accent.withValues(alpha: 0.3) : palette.border,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (text.isNotEmpty)
                      isUser
                          ? Text(text, style: TextStyle(color: palette.textPri, fontSize: 13 * scale, height: 1.45))
                          : MarkdownBody(
                              data: text,
                              styleSheet: MarkdownStyleSheet(
                                p: TextStyle(color: palette.textPri, fontSize: 13 * scale, height: 1.45),
                                code: TextStyle(
                                  color: accent,
                                  fontSize: 12 * scale,
                                  backgroundColor: palette.panel,
                                ),
                                codeblockDecoration: BoxDecoration(
                                  color: palette.panel,
                                  borderRadius: EvaTokens.borderSm,
                                  border: Border.all(color: palette.border),
                                ),
                              ),
                            ),
                    if (!isUser && message['provider'] != null && message['provider'].toString().isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            message['provider'] == 'gemini' ? Icons.cloud_done_outlined : Icons.memory_rounded,
                            size: 11 * scale,
                            color: message['provider'] == 'gemini' ? accent : palette.textSec,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            message['provider'] == 'gemini' ? 'Gemini 2.5 Flash' : 'Ollama (Local)',
                            style: TextStyle(
                              color: message['provider'] == 'gemini' ? accent : palette.textSec,
                              fontSize: 10 * scale,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.2,
                            ),
                          ),
                        ],
                      ),
                    ],
                    if (task != null) ...[
                      const SizedBox(height: 10),
                      _InlineTaskCard(
                        task: task,
                        palette: palette,
                        accent: accent,
                        scale: scale,
                        onExecute: onExecuteTask,
                        onControl: onControlTask,
                        onApprove: onApproveConfirmation,
                        onDeny: onDenyConfirmation,
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InlineTaskCard extends StatelessWidget {
  final Map<String, dynamic> task;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final ValueChanged<String> onExecute;
  final void Function(String, String) onControl;
  final ValueChanged<String> onApprove;
  final ValueChanged<String> onDeny;

  const _InlineTaskCard({
    required this.task,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onExecute,
    required this.onControl,
    required this.onApprove,
    required this.onDeny,
  });

  @override
  Widget build(BuildContext context) {
    final taskId = task['task_id'] as String? ?? '';
    final status = task['status'] as String? ?? '';
    final steps = (task['steps'] as List? ?? []).cast<Map<String, dynamic>>();
    final canExec = status == 'planned' || status == 'action_resolution_required';

    Map<String, dynamic>? confirmationStep;
    for (final step in steps) {
      final error = step['error'] as Map<String, dynamic>?;
      if (step['status'] == 'blocked' && error?['code'] == 'RequiresConfirmation') {
        confirmationStep = step;
        break;
      }
    }
    final confDetails = confirmationStep == null ? null : ((confirmationStep['error'] as Map<String, dynamic>?)?['details'] as Map<String, dynamic>?);
    final confId = confDetails?['confirmation_id'] as String?;

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: palette.panel,
        borderRadius: EvaTokens.borderSm,
        border: Border.all(color: palette.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.alt_route_rounded, size: 14, color: accent),
              const SizedBox(width: 6),
              Text(
                'Plan Pipeline  •  $status',
                style: TextStyle(color: accent, fontSize: 11 * scale, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          if (steps.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...steps.map((s) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    children: [
                      Text('${s['sequence']}. ', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                      Expanded(
                        child: Text(s['description'] as String? ?? '', style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale)),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: (s['status'] == 'completed' ? palette.success : palette.warning).withValues(alpha: 0.15),
                          borderRadius: EvaTokens.borderSm,
                        ),
                        child: Text(
                          s['status'] ?? '',
                          style: TextStyle(
                            color: s['status'] == 'completed' ? palette.success : palette.warning,
                            fontSize: 9.5 * scale,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                )),
          ],
          if (canExec) ...[
            const SizedBox(height: 8),
            ElevatedButton.icon(
              icon: const Icon(Icons.play_arrow_rounded, size: 14),
              label: Text('Execute Plan', style: TextStyle(fontSize: 11 * scale)),
              style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
              onPressed: () => onExecute(taskId),
            ),
          ],
          if (confId != null && confDetails != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: palette.warning.withValues(alpha: 0.1),
                borderRadius: EvaTokens.borderSm,
                border: Border.all(color: palette.warning.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Confirmation Required', style: TextStyle(color: palette.warning, fontSize: 11 * scale, fontWeight: FontWeight.w700)),
                  Text(
                    'Tool: ${confDetails['tool_name']} • Operation: ${confDetails['arguments']?['operation']}',
                    style: TextStyle(color: palette.textPri, fontSize: 10.5 * scale),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      ElevatedButton(
                        onPressed: () => onApprove(confId),
                        style: ElevatedButton.styleFrom(backgroundColor: palette.success, foregroundColor: Colors.white),
                        child: Text('Approve', style: TextStyle(fontSize: 10.5 * scale)),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: () => onDeny(confId),
                        child: Text('Deny', style: TextStyle(color: palette.error, fontSize: 10.5 * scale)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
          if (taskId.isNotEmpty && (status == 'running' || status == 'paused')) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                if (status == 'running')
                  OutlinedButton.icon(
                    icon: const Icon(Icons.pause_rounded, size: 14),
                    label: const Text('Pause'),
                    onPressed: () => onControl(taskId, 'pause'),
                  ),
                if (status == 'paused')
                  OutlinedButton.icon(
                    icon: const Icon(Icons.play_arrow_rounded, size: 14),
                    label: const Text('Resume'),
                    onPressed: () => onControl(taskId, 'resume'),
                  ),
                const SizedBox(width: 6),
                OutlinedButton.icon(
                  icon: const Icon(Icons.stop_rounded, size: 14),
                  label: const Text('Stop'),
                  onPressed: () => onControl(taskId, 'stop'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
