// EVA AI OS — Phase 3B
// Complete UI redesign: Graphite + Muted Teal OS theme,
// conversation history sidebar, microphone / STT integration.
//
// All Phase 1 / 2 / 3A backend wiring is preserved.

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Palette — Graphite + Muted Teal
// ─────────────────────────────────────────────────────────────────────────────

class _EvaColors {
  static const Color bg        = Color(0xFF17191D);
  static const Color sidebar   = Color(0xFF202329);
  static const Color surface   = Color(0xFF252930);
  static const Color inputBg   = Color(0xFF1D2026);
  static const Color accent    = Color(0xFF78CDBD);
  static const Color textPri   = Color(0xFFE8EAED);
  static const Color textSec   = Color(0xFFA1A7B0);
  static const Color border    = Color(0xFF353A43);
  static const Color error     = Color(0xFFE57373);
  static const Color userMsg   = Color(0xFF1E2C2A); // subtle teal tint
  static const Color assistMsg = Color(0xFF1C1F26);
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

void main() {
  runApp(const EvaOSApp());
}

class EvaOSApp extends StatelessWidget {
  const EvaOSApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EVA AI OS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: _EvaColors.bg,
        colorScheme: const ColorScheme.dark(
          surface: _EvaColors.surface,
          primary: _EvaColors.accent,
          error: _EvaColors.error,
        ),
        textTheme: const TextTheme(
          bodyLarge:   TextStyle(color: _EvaColors.textPri,  fontSize: 14),
          bodyMedium:  TextStyle(color: _EvaColors.textPri,  fontSize: 13),
          bodySmall:   TextStyle(color: _EvaColors.textSec,  fontSize: 12),
          labelLarge:  TextStyle(color: _EvaColors.textPri,  fontWeight: FontWeight.w500),
          titleMedium: TextStyle(color: _EvaColors.textPri,  fontSize: 14, fontWeight: FontWeight.w600),
        ),
        dividerColor: _EvaColors.border,
        dividerTheme: const DividerThemeData(color: _EvaColors.border, space: 1),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _EvaColors.inputBg,
          hintStyle: const TextStyle(color: _EvaColors.textSec),
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _EvaColors.border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _EvaColors.border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: _EvaColors.accent, width: 1.5),
          ),
        ),
      ),
      home: const DesktopShell(),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Desktop Shell
// ─────────────────────────────────────────────────────────────────────────────

class DesktopShell extends StatefulWidget {
  const DesktopShell({super.key});

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  int _tab = 5; // Default to EVA tab

  static const _tabs = [
    _TabDef(Icons.dashboard_outlined, Icons.dashboard_rounded, 'Home'),
    _TabDef(Icons.folder_outlined,    Icons.folder_rounded,    'Files'),
    _TabDef(Icons.apps_outlined,      Icons.apps_rounded,      'Apps'),
    _TabDef(Icons.memory_outlined,    Icons.memory_rounded,    'Memory'),
    _TabDef(Icons.settings_outlined,  Icons.settings_rounded,  'Settings'),
    _TabDef(Icons.assistant_outlined, Icons.assistant_rounded, 'EVA'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _EvaColors.bg,
      body: Row(
        children: [
          // ── Left nav rail ───────────────────────────────────────────────
          _NavRail(
            tabs: _tabs,
            selectedIndex: _tab,
            onSelect: (i) => setState(() => _tab = i),
          ),
          // ── Main content ────────────────────────────────────────────────
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _TitleBar(label: _tabs[_tab].label),
                Expanded(child: _buildPage(_tab)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPage(int index) {
    switch (index) {
      case 0:
        return const _HomeDashboard();
      case 5:
        return const EvaInteractionArea();
      default:
        return _PlaceholderPage(
          icon: _tabs[index].idleIcon,
          label: _tabs[index].label,
        );
    }
  }
}

class _TabDef {
  final IconData idleIcon;
  final IconData activeIcon;
  final String label;
  const _TabDef(this.idleIcon, this.activeIcon, this.label);
}

// ─────────────────────────────────────────────────────────────────────────────
// Nav Rail
// ─────────────────────────────────────────────────────────────────────────────

class _NavRail extends StatelessWidget {
  final List<_TabDef> tabs;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  const _NavRail({required this.tabs, required this.selectedIndex, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 72,
      color: _EvaColors.sidebar,
      child: Column(
        children: [
          const SizedBox(height: 20),
          // Logo
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: _EvaColors.accent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _EvaColors.accent.withOpacity(0.4)),
            ),
            child: const Icon(Icons.auto_awesome_rounded, color: _EvaColors.accent, size: 18),
          ),
          const SizedBox(height: 24),
          const Divider(indent: 12, endIndent: 12),
          const SizedBox(height: 8),
          // Nav items
          Expanded(
            child: ListView.builder(
              padding: EdgeInsets.zero,
              itemCount: tabs.length,
              itemBuilder: (ctx, i) {
                final sel = i == selectedIndex;
                return Tooltip(
                  message: tabs[i].label,
                  preferBelow: false,
                  child: GestureDetector(
                    onTap: () => onSelect(i),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 150),
                      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: sel ? _EvaColors.accent.withOpacity(0.12) : Colors.transparent,
                        borderRadius: BorderRadius.circular(8),
                        border: sel
                            ? Border.all(color: _EvaColors.accent.withOpacity(0.3))
                            : null,
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            sel ? tabs[i].activeIcon : tabs[i].idleIcon,
                            size: 20,
                            color: sel ? _EvaColors.accent : _EvaColors.textSec,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            tabs[i].label,
                            style: TextStyle(
                              fontSize: 9.5,
                              fontWeight: sel ? FontWeight.w600 : FontWeight.w400,
                              color: sel ? _EvaColors.accent : _EvaColors.textSec,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Title Bar
// ─────────────────────────────────────────────────────────────────────────────

class _TitleBar extends StatelessWidget {
  final String label;
  const _TitleBar({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: _EvaColors.surface,
        border: Border(bottom: BorderSide(color: _EvaColors.border)),
      ),
      child: Row(
        children: [
          Text(label, style: const TextStyle(
            color: _EvaColors.textPri,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          )),
          const Spacer(),
          Text('EVA AI OS', style: TextStyle(color: _EvaColors.textSec.withOpacity(0.5), fontSize: 11)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Home Dashboard
// ─────────────────────────────────────────────────────────────────────────────

class _HomeDashboard extends StatefulWidget {
  const _HomeDashboard();

  @override
  State<_HomeDashboard> createState() => _HomeDashboardState();
}

class _HomeDashboardState extends State<_HomeDashboard> {
  Map<String, dynamic>? _sysInfo;

  @override
  void initState() {
    super.initState();
    _loadInfo();
  }

  Future<void> _loadInfo() async {
    try {
      final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/system/info'));
      if (resp.statusCode == 200) {
        setState(() => _sysInfo = json.decode(resp.body) as Map<String, dynamic>);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('System Overview', style: TextStyle(
            color: _EvaColors.textPri,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          )),
          const SizedBox(height: 4),
          const Text('Live hardware information from the EVA system layer.',
            style: TextStyle(color: _EvaColors.textSec, fontSize: 13)),
          const SizedBox(height: 24),
          if (_sysInfo == null)
            const Center(child: CircularProgressIndicator(color: _EvaColors.accent))
          else
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: _sysInfo!.entries.map((e) => _InfoCard(
                label: e.key.toUpperCase().replaceAll('_', ' '),
                value: e.value.toString(),
              )).toList(),
            ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String label;
  final String value;
  const _InfoCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _EvaColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _EvaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: _EvaColors.textSec, fontSize: 11)),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(color: _EvaColors.textPri, fontSize: 13, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Placeholder Page
// ─────────────────────────────────────────────────────────────────────────────

class _PlaceholderPage extends StatelessWidget {
  final IconData icon;
  final String label;
  const _PlaceholderPage({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 48, color: _EvaColors.textSec.withOpacity(0.4)),
          const SizedBox(height: 16),
          Text(label, style: const TextStyle(color: _EvaColors.textSec, fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('This module is planned for a future phase.',
            style: TextStyle(color: _EvaColors.textSec, fontSize: 13)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Conversation data models (frontend-only)
// ─────────────────────────────────────────────────────────────────────────────

class _ConvSummary {
  final String id;
  final String title;
  final String updatedAt;
  final int messageCount;
  _ConvSummary({required this.id, required this.title, required this.updatedAt, required this.messageCount});

  factory _ConvSummary.fromJson(Map<String, dynamic> j) => _ConvSummary(
    id: j['conversation_id'] as String,
    title: j['title'] as String,
    updatedAt: j['updated_at'] as String,
    messageCount: j['message_count'] as int,
  );
}

enum _MicState { idle, recording, transcribing, error }

// ─────────────────────────────────────────────────────────────────────────────
// EVA Interaction Area — main chat screen
// ─────────────────────────────────────────────────────────────────────────────

class EvaInteractionArea extends StatefulWidget {
  const EvaInteractionArea({super.key});

  @override
  State<EvaInteractionArea> createState() => _EvaInteractionAreaState();
}

class _EvaInteractionAreaState extends State<EvaInteractionArea> {
  // ── Chat state ────────────────────────────────────────────────────────────
  final TextEditingController _input   = TextEditingController();
  final ScrollController      _scroll  = ScrollController();
  final List<Map<String, dynamic>> _messages = [];
  bool    _isLoading = false;
  String? _sessionId;

  // ── Typewriter ────────────────────────────────────────────────────────────
  Timer?         _typewriter;
  final List<String> _pending = [];

  // ── Conversation history panel ────────────────────────────────────────────
  bool               _historyOpen = true;
  List<_ConvSummary> _conversations = [];
  bool               _loadingHistory = false;

  // ── Microphone state ─────────────────────────────────────────────────────
  _MicState _micState = _MicState.idle;
  String?   _micError;
  final AudioRecorder _recorder = AudioRecorder();
  String?   _recordingPath;

  @override
  void initState() {
    super.initState();
    _loadConversationHistory();
  }

  @override
  void dispose() {
    _typewriter?.cancel();
    _recorder.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  // ── Typewriter ────────────────────────────────────────────────────────────

  void _startTypewriter() {
    if (_typewriter != null && _typewriter!.isActive) return;
    _typewriter = Timer.periodic(const Duration(milliseconds: 12), (t) {
      if (_pending.isEmpty) { t.cancel(); return; }
      setState(() {
        if (_messages.isNotEmpty && _messages.last['sender'] == 'eva') {
          // Drain faster when buffer is large — keeps up with fast LLM
          final batch = _pending.length > 40 ? 5 : 1;
          for (var i = 0; i < batch && _pending.isNotEmpty; i++) {
            _messages.last['text'] += _pending.removeAt(0);
          }
        } else {
          _pending.clear();
        }
      });
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  // ── Scroll ────────────────────────────────────────────────────────────────

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 80), () {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  // ── Conversation History ──────────────────────────────────────────────────

  Future<void> _loadConversationHistory() async {
    setState(() => _loadingHistory = true);
    try {
      final resp = await http.get(Uri.parse('http://127.0.0.1:8000/api/v1/conversations'));
      if (resp.statusCode == 200) {
        final list = json.decode(resp.body) as List;
        setState(() => _conversations = list.map((j) => _ConvSummary.fromJson(j as Map<String, dynamic>)).toList());
      }
    } catch (e) {
      // Backend may be starting up — fail silently
    } finally {
      setState(() => _loadingHistory = false);
    }
  }

  Future<void> _openConversation(_ConvSummary conv) async {
    try {
      final resp = await http.get(
        Uri.parse('http://127.0.0.1:8000/api/v1/conversations/${conv.id}/messages'),
      );
      if (resp.statusCode == 200) {
        final msgs = json.decode(resp.body) as List;
        setState(() {
          _sessionId = conv.id;
          _messages.clear();
          _pending.clear();
          for (final m in msgs) {
            final role = m['role'] as String;
            _messages.add({
              'sender': role == 'user' ? 'user' : 'eva',
              'text':   m['content'] as String,
            });
          }
        });
        _scrollToBottom();
      }
    } catch (e) {
      _showError('Could not load conversation.');
    }
  }

  Future<void> _deleteConversation(_ConvSummary conv) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: _EvaColors.surface,
        title: const Text('Delete conversation?', style: TextStyle(color: _EvaColors.textPri)),
        content: Text(
          'This will permanently delete "${conv.title}" and all its messages.',
          style: const TextStyle(color: _EvaColors.textSec),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel', style: TextStyle(color: _EvaColors.textSec)),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete', style: TextStyle(color: _EvaColors.error)),
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
          _startNewChat();
        }
        await _loadConversationHistory();
      }
    } catch (e) {
      _showError('Delete failed. Please try again.');
    }
  }

  void _startNewChat() {
    setState(() {
      _sessionId = null;
      _messages.clear();
      _pending.clear();
    });
    _typewriter?.cancel();
  }

  // ── Send Message ──────────────────────────────────────────────────────────

  Future<void> _sendMessage() async {
    final text = _input.text.trim();
    if (text.isEmpty || _isLoading) return;
    _input.clear();

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
      };
      if (_sessionId != null) body['session_id'] = _sessionId;
      request.body = json.encode(body);

      final streamed = await request.send();

      if (streamed.statusCode == 200) {
        bool firstMeta = false;
        await for (final chunk in streamed.stream.transform(utf8.decoder)) {
          for (final line in chunk.split('\n')) {
            if (line.trim().isEmpty) continue;
            try {
              final data = json.decode(line) as Map<String, dynamic>;
              _handleStreamEvent(data, firstMeta);
              if (data['type'] == 'metadata') firstMeta = true;
            } catch (_) {}
          }
        }
        // Refresh history list after a successful message
        await _loadConversationHistory();
      } else {
        _addSystemError('Server error ${streamed.statusCode}');
      }
    } catch (e) {
      _addSystemError('Connection failed. Is EVA Core running?');
    } finally {
      setState(() => _isLoading = false);
      _scrollToBottom();
    }
  }

  void _handleStreamEvent(Map<String, dynamic> data, bool firstMetaReceived) {
    switch (data['type']) {
      case 'status':
        // thinking / understanding / planned — handled by _isLoading indicator
        break;

      case 'metadata':
        final d = data['data'] as Map<String, dynamic>;
        if (d['session_id'] != null) _sessionId = d['session_id'] as String;
        if (!firstMetaReceived) {
          setState(() {
            _messages.add({
              'sender':     'eva',
              'text':       '',
              'intent':     d['intent'],
              'confidence': d['confidence'],
              'route':      d['route'],
              'task':       d['task'],
            });
            _isLoading = false;
          });
        }
        break;

      case 'token':
        setState(() => _isLoading = false);
        final content = (data['content'] as String?) ?? '';
        for (final ch in content.runes) {
          _pending.add(String.fromCharCode(ch));
        }
        _startTypewriter();
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
    }
  }

  void _addSystemError(String msg) {
    setState(() => _messages.add({'sender': 'system', 'text': msg}));
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg, style: const TextStyle(color: _EvaColors.textPri)),
        backgroundColor: _EvaColors.error.withOpacity(0.9),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // ── Microphone / STT ─────────────────────────────────────────────────────
  // Real audio recording via the `record` package (PulseAudio/ALSA on Linux).
  // Flow: idle → tap → recording → tap again / auto-stop → transcribing →
  //       transcript placed in composer → user presses Send.

  Future<void> _handleMicButton() async {
    // ── Cancel / stop ongoing recording ──────────────────────────────────
    if (_micState == _MicState.recording) {
      setState(() => _micState = _MicState.transcribing);
      try {
        final path = await _recorder.stop();
        if (path != null) await _transcribeFile(path);
      } catch (e) {
        setState(() {
          _micState = _MicState.error;
          _micError = 'Recording error: $e';
        });
      }
      return;
    }

    // ── Start recording ───────────────────────────────────────────────────
    setState(() { _micState = _MicState.recording; _micError = null; });

    try {
      // Check microphone permission (Linux: usually allowed by default)
      final hasPermission = await _recorder.hasPermission();
      if (!hasPermission) {
        setState(() {
          _micState = _MicState.error;
          _micError = 'Microphone permission denied.';
        });
        return;
      }

      // Write to a temp file in the system temp directory
      final dir  = await getTemporaryDirectory();
      final path = '${dir.path}/eva_rec_${DateTime.now().millisecondsSinceEpoch}.wav';
      _recordingPath = path;

      await _recorder.start(
        const RecordConfig(
          encoder:     AudioEncoder.wav,
          sampleRate:  16000,
          numChannels: 1,
          bitRate:     128000,
        ),
        path: path,
      );
    } catch (e) {
      setState(() {
        _micState = _MicState.error;
        _micError = 'Could not start recording: $e';
      });
    }
  }

  Future<void> _transcribeFile(String path) async {
    setState(() => _micState = _MicState.transcribing);
    try {
      final file = File(path);
      final bytes = await file.readAsBytes();

      // Always clean up — no audio persisted on disk
      await file.delete().catchError((_) {});

      final request = http.MultipartRequest(
        'POST',
        Uri.parse('http://127.0.0.1:8000/api/v1/stt/transcribe'),
      );
      request.files.add(http.MultipartFile.fromBytes(
        'audio',
        bytes,
        filename: 'recording.wav',
      ));

      final streamed  = await request.send();
      final respBody  = json.decode(await streamed.stream.bytesToString()) as Map<String, dynamic>;

      if (streamed.statusCode == 200) {
        final transcript = (respBody['transcript'] as String? ?? '').trim();
        setState(() {
          _input.text = transcript;
          _input.selection = TextSelection.fromPosition(
            TextPosition(offset: transcript.length),
          );
          _micState = _MicState.idle;
        });
      } else if (streamed.statusCode == 503) {
        setState(() {
          _micState = _MicState.error;
          _micError = 'Whisper model unavailable.\nRun: pip install faster-whisper';
        });
      } else if (streamed.statusCode == 422) {
        // No speech in the clip — silently reset
        setState(() {
          _micState = _MicState.idle;
          _micError = 'No speech detected. Please try again.';
        });
      } else {
        setState(() {
          _micState = _MicState.error;
          _micError = respBody['detail']?.toString() ?? 'Transcription failed (${streamed.statusCode})';
        });
      }
    } catch (e) {
      setState(() {
        _micState = _MicState.error;
        _micError = 'Connection error during transcription: $e';
      });
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // ── Conversation history panel ──────────────────────────────────────
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: _historyOpen ? 240 : 0,
          curve: Curves.easeInOut,
          child: _historyOpen ? _HistoryPanel(
            conversations: _conversations,
            activeId: _sessionId,
            loading: _loadingHistory,
            onOpen: _openConversation,
            onDelete: _deleteConversation,
            onNewChat: _startNewChat,
            onRefresh: _loadConversationHistory,
          ) : null,
        ),

        // ── Chat area ───────────────────────────────────────────────────────
        Expanded(
          child: Column(
            children: [
              // Toggle + conversation header
              _ChatHeader(
                sessionId: _sessionId,
                historyOpen: _historyOpen,
                onToggleHistory: () => setState(() => _historyOpen = !_historyOpen),
              ),

              // Message list
              Expanded(
                child: _messages.isEmpty
                    ? const _EmptyState()
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
                        itemCount: _messages.length,
                        itemBuilder: (ctx, i) => _MessageBubble(
                          message: _messages[i],
                          onExecuteTask: (taskId) => _executeTask(taskId, i),
                        ),
                      ),
              ),

              // Thinking indicator
              if (_isLoading)
                const _ThinkingIndicator(),

              // Mic error banner
              if (_micState == _MicState.error && _micError != null)
                _MicErrorBanner(
                  message: _micError!,
                  onDismiss: () => setState(() { _micState = _MicState.idle; _micError = null; }),
                ),

              // Composer
              _Composer(
                controller: _input,
                micState: _micState,
                isLoading: _isLoading,
                onSend: _sendMessage,
                onMic: _handleMicButton,
                onClearContext: () {
                  setState(() {
                    _sessionId = null;
                    _messages.clear();
                    _pending.clear();
                  });
                },
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ── Task execution ────────────────────────────────────────────────────────

  Future<void> _executeTask(String taskId, int msgIndex) async {
    setState(() => _isLoading = true);
    try {
      final resp = await http.post(
        Uri.parse('http://127.0.0.1:8000/api/v1/core/task/$taskId/execute'),
      );
      if (resp.statusCode == 200) {
        setState(() => _messages[msgIndex]['task'] = json.decode(resp.body));
      } else {
        _addSystemError('Execute error: ${resp.statusCode}');
      }
    } catch (e) {
      _addSystemError('Execute connection failed.');
    } finally {
      setState(() => _isLoading = false);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// History Panel
// ─────────────────────────────────────────────────────────────────────────────

class _HistoryPanel extends StatelessWidget {
  final List<_ConvSummary> conversations;
  final String?            activeId;
  final bool               loading;
  final ValueChanged<_ConvSummary>   onOpen;
  final ValueChanged<_ConvSummary>   onDelete;
  final VoidCallback                 onNewChat;
  final VoidCallback                 onRefresh;

  const _HistoryPanel({
    required this.conversations,
    required this.activeId,
    required this.loading,
    required this.onOpen,
    required this.onDelete,
    required this.onNewChat,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: _EvaColors.sidebar,
        border: Border(right: BorderSide(color: _EvaColors.border)),
      ),
      child: Column(
        children: [
          // Panel header
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 8, 8),
            child: Row(
              children: [
                const Text('History', style: TextStyle(
                  color: _EvaColors.textSec,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.8,
                )),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  color: _EvaColors.textSec,
                  tooltip: 'Refresh',
                  onPressed: onRefresh,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                ),
              ],
            ),
          ),

          // New Chat button
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            child: SizedBox(
              width: double.infinity,
              height: 34,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text('New Chat', style: TextStyle(fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _EvaColors.accent.withOpacity(0.15),
                  foregroundColor: _EvaColors.accent,
                  elevation: 0,
                  side: const BorderSide(color: _EvaColors.accent, width: 0.8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
                ),
                onPressed: onNewChat,
              ),
            ),
          ),

          const Divider(height: 16),

          // List
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator(
                    color: _EvaColors.accent, strokeWidth: 2))
                : conversations.isEmpty
                    ? const Center(
                        child: Text('No conversations yet.',
                          style: TextStyle(color: _EvaColors.textSec, fontSize: 12)))
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                        itemCount: conversations.length,
                        itemBuilder: (ctx, i) {
                          final conv = conversations[i];
                          final active = conv.id == activeId;
                          return _HistoryItem(
                            conv: conv,
                            active: active,
                            onTap: () => onOpen(conv),
                            onDelete: () => onDelete(conv),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _HistoryItem extends StatefulWidget {
  final _ConvSummary conv;
  final bool         active;
  final VoidCallback onTap;
  final VoidCallback onDelete;
  const _HistoryItem({required this.conv, required this.active, required this.onTap, required this.onDelete});

  @override
  State<_HistoryItem> createState() => _HistoryItemState();
}

class _HistoryItemState extends State<_HistoryItem> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit:  (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          margin: const EdgeInsets.symmetric(vertical: 2),
          padding: const EdgeInsets.fromLTRB(10, 8, 6, 8),
          decoration: BoxDecoration(
            color: widget.active
                ? _EvaColors.accent.withOpacity(0.12)
                : _hovered
                    ? _EvaColors.surface
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(7),
            border: widget.active
                ? Border.all(color: _EvaColors.accent.withOpacity(0.3))
                : null,
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.conv.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: widget.active ? _EvaColors.accent : _EvaColors.textPri,
                        fontSize: 12,
                        fontWeight: widget.active ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${widget.conv.messageCount} messages',
                      style: const TextStyle(color: _EvaColors.textSec, fontSize: 10),
                    ),
                  ],
                ),
              ),
              if (_hovered || widget.active)
                GestureDetector(
                  onTap: widget.onDelete,
                  child: Padding(
                    padding: const EdgeInsets.only(left: 4),
                    child: Icon(Icons.delete_outline_rounded, size: 15,
                      color: _EvaColors.error.withOpacity(0.7)),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat Header
// ─────────────────────────────────────────────────────────────────────────────

class _ChatHeader extends StatelessWidget {
  final String?  sessionId;
  final bool     historyOpen;
  final VoidCallback onToggleHistory;
  const _ChatHeader({required this.sessionId, required this.historyOpen, required this.onToggleHistory});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: const BoxDecoration(
        color: _EvaColors.surface,
        border: Border(bottom: BorderSide(color: _EvaColors.border)),
      ),
      child: Row(
        children: [
          IconButton(
            icon: Icon(
              historyOpen ? Icons.menu_open_rounded : Icons.menu_rounded,
              size: 18,
              color: _EvaColors.textSec,
            ),
            tooltip: historyOpen ? 'Hide history' : 'Show history',
            onPressed: onToggleHistory,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              sessionId != null
                  ? 'Session: ${sessionId!.substring(0, 8)}…'
                  : 'New Conversation',
              style: const TextStyle(color: _EvaColors.textSec, fontSize: 11),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty State
// ─────────────────────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.assistant_rounded, size: 48, color: _EvaColors.accent),
          SizedBox(height: 16),
          Text('EVA AI OS', style: TextStyle(
            color: _EvaColors.textPri,
            fontSize: 20,
            fontWeight: FontWeight.w600,
          )),
          SizedBox(height: 6),
          Text('Type a message, ask a question, or give a command.',
            style: TextStyle(color: _EvaColors.textSec, fontSize: 13)),
          SizedBox(height: 4),
          Text('Press the microphone button to use voice input.',
            style: TextStyle(color: _EvaColors.textSec, fontSize: 12)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Message Bubble
// ─────────────────────────────────────────────────────────────────────────────

class _MessageBubble extends StatelessWidget {
  final Map<String, dynamic> message;
  final ValueChanged<String> onExecuteTask;
  const _MessageBubble({required this.message, required this.onExecuteTask});

  @override
  Widget build(BuildContext context) {
    final sender = message['sender'] as String;
    final text   = message['text'] as String;
    final task   = message['task'];
    final isUser = sender == 'user';
    final isSystem = sender == 'system';

    if (isSystem) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: _EvaColors.error.withOpacity(0.12),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: _EvaColors.error.withOpacity(0.3)),
            ),
            child: Text(text, style: const TextStyle(color: _EvaColors.error, fontSize: 12)),
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
          // ── Assistant avatar ──────────────────────────────────────────────
          if (!isUser) ...[
            Container(
              width: 28,
              height: 28,
              margin: const EdgeInsets.only(top: 4, right: 10),
              decoration: BoxDecoration(
                color: _EvaColors.accent.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: _EvaColors.accent.withOpacity(0.3)),
              ),
              child: const Icon(Icons.assistant_rounded, size: 15, color: _EvaColors.accent),
            ),
          ],

          // ── Bubble ────────────────────────────────────────────────────────
          Flexible(
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.62,
              ),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isUser ? _EvaColors.userMsg : _EvaColors.assistMsg,
                  borderRadius: BorderRadius.only(
                    topLeft: const Radius.circular(12),
                    topRight: const Radius.circular(12),
                    bottomLeft: Radius.circular(isUser ? 12 : 4),
                    bottomRight: Radius.circular(isUser ? 4 : 12),
                  ),
                  border: Border.all(
                    color: isUser
                        ? _EvaColors.accent.withOpacity(0.25)
                        : _EvaColors.border,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (text.isNotEmpty)
                      isUser
                          ? Text(text, style: const TextStyle(
                              color: _EvaColors.textPri, fontSize: 13, height: 1.5))
                          : MarkdownBody(
                              data: text,
                              styleSheet: MarkdownStyleSheet(
                                p:      const TextStyle(color: _EvaColors.textPri, fontSize: 13, height: 1.55),
                                code:   const TextStyle(color: _EvaColors.accent,  fontSize: 12,
                                          backgroundColor: Color(0xFF1A1E26)),
                                codeblockDecoration: BoxDecoration(
                                  color: const Color(0xFF1A1E26),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: _EvaColors.border),
                                ),
                                h1: const TextStyle(color: _EvaColors.textPri, fontSize: 16, fontWeight: FontWeight.w700),
                                h2: const TextStyle(color: _EvaColors.textPri, fontSize: 14, fontWeight: FontWeight.w600),
                                h3: const TextStyle(color: _EvaColors.textPri, fontSize: 13, fontWeight: FontWeight.w600),
                                listBullet: const TextStyle(color: _EvaColors.accent),
                              ),
                            ),

                    // ── Task card ─────────────────────────────────────────
                    if (task != null) ...[
                      const SizedBox(height: 12),
                      _TaskCard(task: task as Map<String, dynamic>, onExecute: onExecuteTask),
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

// ─────────────────────────────────────────────────────────────────────────────
// Task Card
// ─────────────────────────────────────────────────────────────────────────────

class _TaskCard extends StatelessWidget {
  final Map<String, dynamic> task;
  final ValueChanged<String> onExecute;
  const _TaskCard({required this.task, required this.onExecute});

  @override
  Widget build(BuildContext context) {
    final taskId  = task['task_id'] as String? ?? '';
    final status  = task['status'] as String? ?? '';
    final steps   = (task['steps'] as List? ?? []).cast<Map<String, dynamic>>();
    final canExec = status == 'planned' || status == 'action_resolution_required';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _EvaColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _EvaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_tree_rounded, size: 13, color: _EvaColors.accent),
              const SizedBox(width: 6),
              Text('Plan  •  $status',
                style: const TextStyle(color: _EvaColors.accent, fontSize: 11, fontWeight: FontWeight.w600)),
            ],
          ),
          if (steps.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...steps.map((s) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${s['sequence']}. ', style: const TextStyle(color: _EvaColors.textSec, fontSize: 11)),
                  Expanded(child: Text(s['description'] as String? ?? '',
                    style: const TextStyle(color: _EvaColors.textPri, fontSize: 11))),
                  const SizedBox(width: 6),
                  _StepStatus(status: s['status'] as String? ?? ''),
                ],
              ),
            )),
          ],
          if (canExec) ...[
            const SizedBox(height: 10),
            SizedBox(
              height: 30,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.play_arrow_rounded, size: 14),
                label: const Text('Execute', style: TextStyle(fontSize: 11)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _EvaColors.accent,
                  foregroundColor: _EvaColors.bg,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                ),
                onPressed: () => onExecute(taskId),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _StepStatus extends StatelessWidget {
  final String status;
  const _StepStatus({required this.status});

  Color get _color {
    switch (status) {
      case 'completed': return Colors.greenAccent;
      case 'failed':    return _EvaColors.error;
      case 'running':   return _EvaColors.accent;
      default:          return _EvaColors.textSec;
    }
  }

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
    decoration: BoxDecoration(
      color: _color.withOpacity(0.12),
      borderRadius: BorderRadius.circular(4),
      border: Border.all(color: _color.withOpacity(0.4)),
    ),
    child: Text(status, style: TextStyle(color: _color, fontSize: 9, fontWeight: FontWeight.w500)),
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Thinking Indicator
// ─────────────────────────────────────────────────────────────────────────────

class _ThinkingIndicator extends StatelessWidget {
  const _ThinkingIndicator();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(48, 0, 24, 4),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _EvaColors.assistMsg,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _EvaColors.border),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.5,
                    color: _EvaColors.accent.withOpacity(0.8),
                  ),
                ),
                const SizedBox(width: 8),
                const Text('EVA is thinking…',
                  style: TextStyle(color: _EvaColors.textSec, fontSize: 12, fontStyle: FontStyle.italic)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Mic Error Banner
// ─────────────────────────────────────────────────────────────────────────────

class _MicErrorBanner extends StatelessWidget {
  final String message;
  final VoidCallback onDismiss;
  const _MicErrorBanner({required this.message, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _EvaColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _EvaColors.error.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.mic_off_rounded, color: _EvaColors.error, size: 16),
          const SizedBox(width: 10),
          Expanded(child: Text(message,
            style: const TextStyle(color: _EvaColors.error, fontSize: 12))),
          IconButton(
            icon: const Icon(Icons.close_rounded, size: 16, color: _EvaColors.error),
            onPressed: onDismiss,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Composer
// ─────────────────────────────────────────────────────────────────────────────

class _Composer extends StatelessWidget {
  final TextEditingController controller;
  final _MicState   micState;
  final bool        isLoading;
  final VoidCallback onSend;
  final VoidCallback onMic;
  final VoidCallback onClearContext;

  const _Composer({
    required this.controller,
    required this.micState,
    required this.isLoading,
    required this.onSend,
    required this.onMic,
    required this.onClearContext,
  });

  Color get _micColor {
    switch (micState) {
      case _MicState.recording:    return _EvaColors.error;
      case _MicState.transcribing: return _EvaColors.accent.withOpacity(0.6);
      case _MicState.error:        return _EvaColors.error.withOpacity(0.6);
      case _MicState.idle:         return _EvaColors.textSec;
    }
  }

  IconData get _micIcon {
    switch (micState) {
      case _MicState.recording:    return Icons.stop_rounded;
      case _MicState.transcribing: return Icons.hourglass_empty_rounded;
      case _MicState.error:        return Icons.mic_off_rounded;
      case _MicState.idle:         return Icons.mic_rounded;
    }
  }

  String get _micTooltip {
    switch (micState) {
      case _MicState.recording:    return 'Cancel recording';
      case _MicState.transcribing: return 'Transcribing…';
      case _MicState.error:        return 'Microphone error';
      case _MicState.idle:         return 'Voice input';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: const BoxDecoration(
        color: _EvaColors.surface,
        border: Border(top: BorderSide(color: _EvaColors.border)),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 820),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Clear context button
              Tooltip(
                message: 'New conversation (keeps history)',
                child: IconButton(
                  icon: const Icon(Icons.add_comment_outlined, size: 18),
                  color: _EvaColors.textSec,
                  onPressed: onClearContext,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                ),
              ),
              const SizedBox(width: 8),

              // Text field
              Expanded(
                child: TextField(
                  controller: controller,
                  minLines: 1,
                  maxLines: 6,
                  style: const TextStyle(color: _EvaColors.textPri, fontSize: 13),
                  decoration: const InputDecoration(
                    hintText: 'Type a message or command…',
                    hintStyle: TextStyle(color: _EvaColors.textSec),
                    isDense: true,
                  ),
                  onSubmitted: (_) => onSend(),
                  textInputAction: TextInputAction.newline,
                  keyboardType: TextInputType.multiline,
                ),
              ),
              const SizedBox(width: 8),

              // Mic button
              Tooltip(
                message: _micTooltip,
                child: IconButton(
                  icon: micState == _MicState.transcribing
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: _EvaColors.accent.withOpacity(0.7),
                          ),
                        )
                      : Icon(_micIcon, size: 20),
                  color: _micColor,
                  onPressed: micState == _MicState.transcribing ? null : onMic,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                ),
              ),
              const SizedBox(width: 6),

              // Send button
              SizedBox(
                width: 36,
                height: 36,
                child: ElevatedButton(
                  onPressed: isLoading ? null : onSend,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _EvaColors.accent,
                    foregroundColor: _EvaColors.bg,
                    padding: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    elevation: 0,
                    disabledBackgroundColor: _EvaColors.accent.withOpacity(0.3),
                  ),
                  child: isLoading
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: _EvaColors.bg,
                          ),
                        )
                      : const Icon(Icons.send_rounded, size: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}