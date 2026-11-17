import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class MemoryExplorerScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;
  final ValueChanged<int> onNavigate;

  const MemoryExplorerScreen({
    super.key,
    required this.themeNotifier,
    required this.onNavigate,
  });

  @override
  State<MemoryExplorerScreen> createState() => _MemoryExplorerScreenState();
}

class _MemoryExplorerScreenState extends State<MemoryExplorerScreen> {
  String _selectedSection = 'All Memory';
  List<Map<String, dynamic>> _memories = [];
  List<Map<String, dynamic>> _conversations = [];
  bool _loading = true;
  String _searchQuery = '';
  bool _sortNewest = true;

  Map<String, dynamic>? _selectedRecord;
  bool _isEditing = false;
  final TextEditingController _editTitleCtrl = TextEditingController();
  final TextEditingController _editContentCtrl = TextEditingController();

  // Owner Profile state
  Map<String, dynamic>? _ownerProfile;
  Map<String, dynamic>? _assistantIdentity;
  bool _ownerProfileLoading = false;
  bool _ownerProfileEditing = false;
  final TextEditingController _opNickCtrl = TextEditingController();
  final TextEditingController _opFullNameCtrl = TextEditingController();
  final TextEditingController _opPreferredCtrl = TextEditingController();
  final TextEditingController _opCallCtrl = TextEditingController();
  final TextEditingController _opOccupCtrl = TextEditingController();

  final List<String> _navSections = [
    'Owner Profile',
    'All Memory',
    'Conversations',
    'User Preferences',
    'Projects',
    'Important Information',
    'Private Memory',
    'Public Memory',
    'Short-Term Context',
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _editTitleCtrl.dispose();
    _editContentCtrl.dispose();
    _opNickCtrl.dispose();
    _opFullNameCtrl.dispose();
    _opPreferredCtrl.dispose();
    _opCallCtrl.dispose();
    _opOccupCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    final mems = await EvaApiClient.getMemories();
    final convs = await EvaApiClient.getConversations();
    final profileData = await EvaApiClient.getOwnerProfile();

    if (mounted) {
      setState(() {
        _memories = mems;
        _conversations = convs;
        if (profileData != null) {
          _ownerProfile = profileData['owner'] as Map<String, dynamic>?;
          _assistantIdentity = profileData['assistant'] as Map<String, dynamic>?;
          _syncOwnerControllers();
        }
        _loading = false;
        if (_selectedRecord != null) {
          // Refresh selected record if present
          final id = _selectedRecord!['memory_id'] ?? _selectedRecord!['conversation_id'];
          final updatedMem = _memories.firstWhere((m) => m['memory_id'] == id, orElse: () => {});
          if (updatedMem.isNotEmpty) _selectedRecord = updatedMem;
        }
      });
    }
  }

  void _syncOwnerControllers() {
    final p = _ownerProfile;
    if (p == null) return;
    _opNickCtrl.text = p['nickname']?.toString() ?? '';
    _opFullNameCtrl.text = p['full_name']?.toString() ?? '';
    _opPreferredCtrl.text = p['preferred_name']?.toString() ?? '';
    _opCallCtrl.text = p['call_name']?.toString() ?? '';
    _opOccupCtrl.text = p['occupation']?.toString() ?? '';
  }

  Future<void> _saveOwnerProfile() async {
    setState(() => _ownerProfileLoading = true);
    final res = await EvaApiClient.updateOwnerProfile(
      nickname: _opNickCtrl.text.trim(),
      fullName: _opFullNameCtrl.text.trim(),
      preferredName: _opPreferredCtrl.text.trim(),
      callName: _opCallCtrl.text.trim(),
      occupation: _opOccupCtrl.text.trim(),
    );
    if (mounted) {
      setState(() {
        _ownerProfileLoading = false;
        _ownerProfileEditing = false;
        if (res != null) {
          _ownerProfile = res['owner'] as Map<String, dynamic>? ?? _ownerProfile;
          _syncOwnerControllers();
        }
      });
    }
  }

  List<Map<String, dynamic>> get _filteredRecords {
    if (_selectedSection == 'Owner Profile') {
      // Owner profile has a custom view — return empty for the list
      return [];
    }
    if (_selectedSection == 'Conversations') {
      return _conversations.where((c) {
        if (_searchQuery.isEmpty) return true;
        final title = (c['title'] ?? '').toString().toLowerCase();
        return title.contains(_searchQuery.toLowerCase());
      }).map((c) => {
        'id': c['conversation_id'],
        'title': c['title'] ?? 'Conversation',
        'category': 'Conversation History',
        'content': 'Persistent conversation record with ${c['message_count']} messages.',
        'created_at': c['created_at'],
        'updated_at': c['updated_at'],
        'source': 'eva-chat',
        'privacy': 'public',
        'pinned': false,
        'is_conversation': true,
      }).toList();
    }

    if (_selectedSection == 'Short-Term Context') {
      return [
        {
          'id': 'ctx-live',
          'title': 'Active Session Context Window',
          'category': 'Short-Term Context',
          'content': 'In-memory sliding window (max 12 messages). Evaluated per-turn by EVA intent and router engines before LLM inference.',
          'created_at': DateTime.now().toIso8601String(),
          'updated_at': DateTime.now().toIso8601String(),
          'source': 'context_manager',
          'privacy': 'private',
          'pinned': true,
          'is_context': true,
        }
      ];
    }

    return _memories.where((m) {
      if (_selectedSection == 'User Preferences' && m['category'] != 'User Preferences') return false;
      if (_selectedSection == 'Projects' && m['category'] != 'Projects') return false;
      if (_selectedSection == 'Important Information' && m['pinned'] != true) return false;
      if (_selectedSection == 'Private Memory' && m['privacy'] != 'private') return false;
      if (_selectedSection == 'Public Memory' && m['privacy'] != 'public') return false;

      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final title = (m['title'] ?? '').toString().toLowerCase();
        final content = (m['content'] ?? '').toString().toLowerCase();
        if (!title.contains(query) && !content.contains(query)) return false;
      }
      return true;
    }).toList()
      ..sort((a, b) {
        final at = a['updated_at'] ?? '';
        final bt = b['updated_at'] ?? '';
        return _sortNewest ? bt.compareTo(at) : at.compareTo(bt);
      });
  }

  void _inspectRecord(Map<String, dynamic> record) {
    setState(() {
      _selectedRecord = record;
      _isEditing = false;
      _editTitleCtrl.text = record['title'] ?? '';
      _editContentCtrl.text = record['content'] ?? '';
    });
  }

  Future<void> _saveEdit() async {
    if (_selectedRecord == null || _selectedRecord!['memory_id'] == null) return;
    final id = _selectedRecord!['memory_id'] as String;
    final res = await EvaApiClient.updateMemory(
      id,
      title: _editTitleCtrl.text.trim(),
      content: _editContentCtrl.text.trim(),
    );
    if (res != null) {
      setState(() {
        _selectedRecord = res;
        _isEditing = false;
      });
      _loadData();
    }
  }

  Future<void> _deleteSelected() async {
    if (_selectedRecord == null) return;
    final isConv = _selectedRecord!['is_conversation'] == true;
    final id = (_selectedRecord!['memory_id'] ?? _selectedRecord!['id'] ?? '') as String;

    final palette = widget.themeNotifier.getPalette(context);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: palette.surface,
        title: Text('Delete record?', style: TextStyle(color: palette.textPri)),
        content: Text('Are you sure you want to delete this memory record? This cannot be undone.', style: TextStyle(color: palette.textSec)),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: Text('Cancel', style: TextStyle(color: palette.textSec))),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text('Delete', style: TextStyle(color: palette.error))),
        ],
      ),
    );

    if (confirm == true) {
      if (isConv) {
        await EvaApiClient.deleteConversation(id);
      } else {
        await EvaApiClient.deleteMemory(id);
      }
      setState(() => _selectedRecord = null);
      _loadData();
    }
  }

  Future<void> _togglePin(Map<String, dynamic> record) async {
    final id = record['memory_id'] as String?;
    if (id == null) return;
    await EvaApiClient.togglePinMemory(id);
    _loadData();
  }

  void _showCreateDialog() {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    final titleCtrl = TextEditingController();
    final contentCtrl = TextEditingController();
    String category = _selectedSection == 'Projects'
        ? 'Projects'
        : (_selectedSection == 'User Preferences' ? 'User Preferences' : 'General');
    String privacy = _selectedSection == 'Private Memory' ? 'private' : 'public';
    bool pinned = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: palette.surface,
          shape: RoundedRectangleBorder(borderRadius: EvaTokens.borderMd),
          title: Text('New Memory Record', style: TextStyle(color: palette.textPri, fontSize: 16 * scale)),
          content: SizedBox(
            width: 480,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: titleCtrl,
                    style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
                    decoration: const InputDecoration(
                      labelText: 'Title',
                      hintText: 'e.g. Project EVA Architecture Specs',
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: category,
                          dropdownColor: palette.surface,
                          style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale),
                          decoration: const InputDecoration(labelText: 'Category'),
                          items: const [
                            DropdownMenuItem(value: 'General', child: Text('General')),
                            DropdownMenuItem(value: 'Projects', child: Text('Projects')),
                            DropdownMenuItem(value: 'User Preferences', child: Text('User Preferences')),
                            DropdownMenuItem(value: 'Important Information', child: Text('Important Information')),
                          ],
                          onChanged: (v) => setDialogState(() => category = v ?? 'General'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: privacy,
                          dropdownColor: palette.surface,
                          style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale),
                          decoration: const InputDecoration(labelText: 'Privacy'),
                          items: const [
                            DropdownMenuItem(value: 'public', child: Text('Public Memory')),
                            DropdownMenuItem(value: 'private', child: Text('Private Memory')),
                          ],
                          onChanged: (v) => setDialogState(() => privacy = v ?? 'public'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Material(
                    type: MaterialType.transparency,
                    child: CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('Pin to Important', style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale)),
                      value: pinned,
                      activeColor: accent,
                      onChanged: (v) => setDialogState(() => pinned = v ?? false),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: contentCtrl,
                    minLines: 4,
                    maxLines: 8,
                    style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
                    decoration: const InputDecoration(
                      labelText: 'Memory Content',
                      hintText: 'Write structured notes, project details, or configuration facts…',
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text('Cancel', style: TextStyle(color: palette.textSec)),
            ),
            ElevatedButton(
              onPressed: () async {
                if (titleCtrl.text.trim().isEmpty) return;
                await EvaApiClient.createMemory(
                  title: titleCtrl.text.trim(),
                  content: contentCtrl.text.trim(),
                  category: category,
                  privacy: privacy,
                  pinned: pinned,
                );
                if (ctx.mounted) Navigator.of(ctx).pop();
                _loadData();
              },
              style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
              child: const Text('Save Record'),
            ),
          ],
        ),
      ),
    );
  }

  void _exportRecord(Map<String, dynamic> record) {
    final title = record['title'] ?? 'Record';
    final content = record['content'] ?? '';
    final category = record['category'] ?? '';
    final created = record['created_at'] ?? '';
    final markdown = '# $title\n\n- **Category:** $category\n- **Created:** $created\n\n$content\n';

    Clipboard.setData(ClipboardData(text: markdown));
    final palette = widget.themeNotifier.getPalette(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Exported "$title" to clipboard as Markdown.', style: TextStyle(color: palette.textPri)),
        backgroundColor: palette.panel,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Widget _buildOwnerProfileView(dynamic palette, Color accent, double scale) {
    final p = _ownerProfile;
    final a = _assistantIdentity;
    if (p == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.person_off_outlined, size: 36, color: palette.textSec.withValues(alpha: 0.5)),
            const SizedBox(height: 10),
            Text('Owner profile not loaded', style: TextStyle(color: palette.textSec, fontSize: 13 * scale)),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _loadData,
              icon: const Icon(Icons.refresh_rounded, size: 14),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    Widget buildField(String label, TextEditingController ctrl, {bool enabled = true}) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label.toUpperCase(),
              style: TextStyle(color: palette.textSec, fontSize: 10 * scale, fontWeight: FontWeight.w600, letterSpacing: 0.5),
            ),
            const SizedBox(height: 4),
            TextField(
              controller: ctrl,
              enabled: enabled && _ownerProfileEditing,
              style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
              decoration: InputDecoration(
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                filled: true,
                fillColor: _ownerProfileEditing ? palette.panel : palette.bg,
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: const BorderRadius.all(Radius.circular(5)),
                  borderSide: BorderSide(color: palette.border),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: const BorderRadius.all(Radius.circular(5)),
                  borderSide: BorderSide(color: accent.withValues(alpha: 0.5)),
                ),
                disabledBorder: OutlineInputBorder(
                  borderRadius: const BorderRadius.all(Radius.circular(5)),
                  borderSide: BorderSide(color: palette.border),
                ),
              ),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.15),
                  borderRadius: const BorderRadius.all(Radius.circular(8)),
                  border: Border.all(color: accent.withValues(alpha: 0.3)),
                ),
                child: Icon(Icons.person_outline_rounded, size: 22, color: accent),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Owner Profile', style: TextStyle(color: palette.textPri, fontSize: 16 * scale, fontWeight: FontWeight.w700)),
                    Text('Persistent verified identity — stored in SQLite, never LLM-hallucinated',
                        style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                  ],
                ),
              ),
              if (_ownerProfileLoading)
                SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: accent))
              else if (_ownerProfileEditing) ...[
                TextButton(
                  onPressed: () => setState(() {
                    _ownerProfileEditing = false;
                    _syncOwnerControllers();
                  }),
                  child: Text('Cancel', style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
                ),
                const SizedBox(width: 6),
                FilledButton.icon(
                  onPressed: _saveOwnerProfile,
                  icon: const Icon(Icons.save_outlined, size: 14),
                  label: const Text('Save'),
                  style: FilledButton.styleFrom(backgroundColor: accent, foregroundColor: Colors.black),
                ),
              ] else
                TextButton.icon(
                  onPressed: () => setState(() => _ownerProfileEditing = true),
                  icon: Icon(Icons.edit_outlined, size: 14, color: accent),
                  label: Text('Edit', style: TextStyle(color: accent, fontSize: 12 * scale)),
                ),
            ],
          ),

          const SizedBox(height: 24),

          // Owner Identity Fields
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: const BorderRadius.all(Radius.circular(8)),
              border: Border.all(color: palette.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Icon(Icons.badge_outlined, size: 14, color: accent),
                  const SizedBox(width: 6),
                  Text('Identity', style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w600)),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.12),
                      borderRadius: const BorderRadius.all(Radius.circular(4)),
                    ),
                    child: Text('verified', style: TextStyle(color: accent, fontSize: 9.5 * scale, fontWeight: FontWeight.w600, letterSpacing: 0.3)),
                  ),
                ]),
                const SizedBox(height: 14),
                buildField('Nickname / Call Name', _opNickCtrl),
                buildField('Full Name', _opFullNameCtrl),
                buildField('Preferred Name', _opPreferredCtrl),
                buildField('Display Call Name', _opCallCtrl),
                buildField('Occupation', _opOccupCtrl),
                // Creator badge
                Row(
                  children: [
                    Icon(Icons.verified_outlined, size: 13, color: accent),
                    const SizedBox(width: 6),
                    Text('Creator of EVA', style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.12),
                        borderRadius: const BorderRadius.all(Radius.circular(4)),
                        border: Border.all(color: accent.withValues(alpha: 0.3)),
                      ),
                      child: Text('YES', style: TextStyle(color: accent, fontSize: 10 * scale, fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Assistant Identity (read-only)
          if (a != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: palette.surface,
                borderRadius: const BorderRadius.all(Radius.circular(8)),
                border: Border.all(color: palette.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(Icons.smart_toy_outlined, size: 14, color: accent),
                    const SizedBox(width: 6),
                    Text('Assistant Identity', style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontWeight: FontWeight.w600)),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(color: palette.panel, borderRadius: const BorderRadius.all(Radius.circular(4))),
                      child: Text('read-only', style: TextStyle(color: palette.textSec, fontSize: 9.5 * scale)),
                    ),
                  ]),
                  const SizedBox(height: 14),
                  _buildReadOnlyField('Assistant Name', a['name']?.toString() ?? '—', palette, scale),
                  _buildReadOnlyField('Creator Name', a['creator_name']?.toString() ?? '—', palette, scale),
                  _buildReadOnlyField('Creator Full Name', a['creator_full_name']?.toString() ?? '—', palette, scale),
                ],
              ),
            ),

          const SizedBox(height: 16),

          // Info note
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: palette.panel,
              borderRadius: const BorderRadius.all(Radius.circular(6)),
              border: Border.all(color: palette.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded, size: 14, color: palette.textSec),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Owner profile is stored in SQLite and loaded into every conversation. '
                    'Identity questions bypass the LLM entirely — answers come directly from this record.',
                    style: TextStyle(color: palette.textSec, fontSize: 11 * scale, height: 1.5),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReadOnlyField(String label, String value, dynamic palette, double scale) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
          ),
          Expanded(
            child: Text(value, style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;
    final records = _filteredRecords;

    return Row(
      children: [
        // ── Left Knowledge Category Navigation ────────────────────────────
        Container(
          width: 210,
          decoration: BoxDecoration(
            color: palette.sidebar,
            border: Border(right: BorderSide(color: palette.border)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
                child: Row(
                  children: [
                    Icon(Icons.psychology_outlined, size: 16, color: accent),
                    const SizedBox(width: 8),
                    Text(
                      'KNOWLEDGE BASE',
                      style: TextStyle(
                        color: palette.textSec,
                        fontSize: 10 * scale,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 12),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  children: _navSections.map((sec) {
                    final isSel = sec == _selectedSection;
                    IconData icon;
                    if (sec == 'Owner Profile') {
                      icon = Icons.person_outline_rounded;
                    } else if (sec == 'All Memory') {
                      icon = Icons.inventory_2_outlined;
                    } else if (sec == 'Conversations') {
                      icon = Icons.forum_outlined;
                    } else if (sec == 'User Preferences') {
                      icon = Icons.tune_rounded;
                    } else if (sec == 'Projects') {
                      icon = Icons.terminal_rounded;
                    } else if (sec == 'Important Information') {
                      icon = Icons.push_pin_outlined;
                    } else if (sec == 'Private Memory') {
                      icon = Icons.lock_outline_rounded;
                    } else if (sec == 'Public Memory') {
                      icon = Icons.public_outlined;
                    } else {
                      icon = Icons.history_toggle_off_rounded;
                    }

                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: InkWell(
                        onTap: () {
                          setState(() {
                            _selectedSection = sec;
                            _selectedRecord = null;
                          });
                        },
                        borderRadius: EvaTokens.borderSm,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          decoration: BoxDecoration(
                            color: isSel ? accent.withValues(alpha: 0.15) : Colors.transparent,
                            borderRadius: EvaTokens.borderSm,
                            border: isSel ? Border.all(color: accent.withValues(alpha: 0.35)) : null,
                          ),
                          child: Row(
                            children: [
                              Icon(icon, size: 16, color: isSel ? accent : palette.textSec),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  sec,
                                  style: TextStyle(
                                    color: isSel ? accent : palette.textPri,
                                    fontSize: 12 * scale,
                                    fontWeight: isSel ? FontWeight.w600 : FontWeight.normal,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(10),
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.add_rounded, size: 16),
                  label: const Text('New Memory'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: accent,
                    foregroundColor: palette.bg,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                  ),
                  onPressed: _showCreateDialog,
                ),
              ),
            ],
          ),
        ),

        // ── Main Memory Records List ──────────────────────────────────────
        Expanded(
          flex: _selectedRecord != null ? 6 : 10,
          child: Container(
            color: palette.bg,
            child: Column(
              children: [
                // Top Action & Filter Toolbar
                Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: palette.surface,
                    border: Border(bottom: BorderSide(color: palette.border)),
                  ),
                  child: Row(
                    children: [
                      Text(
                        _selectedSection,
                        style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: palette.panel,
                          borderRadius: EvaTokens.borderSm,
                        ),
                        child: Text(
                          '${records.length} items',
                          style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale),
                        ),
                      ),
                      const Spacer(),
                      // Search box
                      SizedBox(
                        width: 200,
                        height: 30,
                        child: TextField(
                          style: TextStyle(color: palette.textPri, fontSize: 12 * scale),
                          decoration: InputDecoration(
                            hintText: 'Search memory…',
                            prefixIcon: Icon(Icons.search_rounded, size: 15, color: palette.textSec),
                            contentPadding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
                            isDense: true,
                          ),
                          onChanged: (v) => setState(() => _searchQuery = v),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        icon: Icon(_sortNewest ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded, size: 16),
                        color: palette.textSec,
                        tooltip: _sortNewest ? 'Sort: Newest first' : 'Sort: Oldest first',
                        onPressed: () => setState(() => _sortNewest = !_sortNewest),
                      ),
                      IconButton(
                        icon: const Icon(Icons.refresh_rounded, size: 16),
                        color: palette.textSec,
                        tooltip: 'Refresh',
                        onPressed: _loadData,
                      ),
                    ],
                  ),
                ),

                // Records Grid/List
                Expanded(
                  child: _loading
                      ? Center(child: CircularProgressIndicator(color: accent))
                      : _selectedSection == 'Owner Profile'
                          ? _buildOwnerProfileView(palette, accent, scale)
                          : records.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.inventory_2_outlined, size: 40, color: palette.textSec.withValues(alpha: 0.5)),
                                  const SizedBox(height: 12),
                                  Text(
                                    'No records found in "$_selectedSection"',
                                    style: TextStyle(color: palette.textPri, fontSize: 14 * scale, fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    'Create a memory or run assistant commands to persist records.',
                                    style: TextStyle(color: palette.textSec, fontSize: 12 * scale),
                                  ),
                                ],
                              ),
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.all(12),
                              itemCount: records.length,
                              itemBuilder: (ctx, i) {
                                final r = records[i];
                                final isSel = _selectedRecord != null && (_selectedRecord!['memory_id'] == r['memory_id'] || _selectedRecord!['id'] == r['id']);
                                return _MemoryCard(
                                  record: r,
                                  isSelected: isSel,
                                  palette: palette,
                                  accent: accent,
                                  scale: scale,
                                  onTap: () => _inspectRecord(r),
                                  onTogglePin: () => _togglePin(r),
                                );
                              },
                            ),
                ),
              ],
            ),
          ),
        ),

        // ── Inspection & Details Drawer ───────────────────────────────────
        if (_selectedRecord != null)
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 340,
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
                      Icon(Icons.fact_check_outlined, size: 16, color: accent),
                      const SizedBox(width: 8),
                      Text('Record Details', style: TextStyle(color: palette.textPri, fontSize: 13 * scale, fontWeight: FontWeight.w600)),
                      const Spacer(),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 16),
                        color: palette.textSec,
                        onPressed: () => setState(() => _selectedRecord = null),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                      ),
                    ],
                  ),
                ),

                // Inspector Body
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (_isEditing) ...[
                          TextField(
                            controller: _editTitleCtrl,
                            style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
                            decoration: const InputDecoration(labelText: 'Title'),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _editContentCtrl,
                            minLines: 5,
                            maxLines: 12,
                            style: TextStyle(color: palette.textPri, fontSize: 13 * scale),
                            decoration: const InputDecoration(labelText: 'Content'),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              ElevatedButton(
                                onPressed: _saveEdit,
                                style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
                                child: const Text('Save Changes'),
                              ),
                              const SizedBox(width: 8),
                              OutlinedButton(
                                onPressed: () => setState(() => _isEditing = false),
                                child: const Text('Cancel'),
                              ),
                            ],
                          ),
                        ] else ...[
                          Text(
                            _selectedRecord!['title'] ?? 'Untitled Record',
                            style: TextStyle(color: palette.textPri, fontSize: 15 * scale, fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: accent.withValues(alpha: 0.15),
                                  borderRadius: EvaTokens.borderSm,
                                ),
                                child: Text(
                                  _selectedRecord!['category'] ?? 'General',
                                  style: TextStyle(color: accent, fontSize: 10.5 * scale, fontWeight: FontWeight.w600),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: (_selectedRecord!['privacy'] == 'private' ? palette.warning : palette.border).withValues(alpha: 0.2),
                                  borderRadius: EvaTokens.borderSm,
                                ),
                                child: Text(
                                  _selectedRecord!['privacy'] == 'private' ? 'Private' : 'Public',
                                  style: TextStyle(
                                    color: _selectedRecord!['privacy'] == 'private' ? palette.warning : palette.textSec,
                                    fontSize: 10.5 * scale,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                              if (_selectedRecord!['pinned'] == true)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: accent.withValues(alpha: 0.2),
                                    borderRadius: EvaTokens.borderSm,
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.push_pin_rounded, size: 10, color: accent),
                                      const SizedBox(width: 3),
                                      Text('Pinned', style: TextStyle(color: accent, fontSize: 10 * scale)),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          const Divider(),
                          const SizedBox(height: 10),
                          Text('CONTENT', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 6),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: palette.panel,
                              borderRadius: EvaTokens.borderSm,
                              border: Border.all(color: palette.borderSubtle),
                            ),
                            child: Text(
                              _selectedRecord!['content'] ?? 'No content',
                              style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, height: 1.45),
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text('METADATA', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 6),
                          _DetailRow(palette: palette, scale: scale, label: 'Source', value: _selectedRecord!['source'] ?? 'unknown'),
                          _DetailRow(palette: palette, scale: scale, label: 'Created', value: _selectedRecord!['created_at'] ?? 'N/A'),
                          _DetailRow(palette: palette, scale: scale, label: 'Updated', value: _selectedRecord!['updated_at'] ?? 'N/A'),
                          const SizedBox(height: 20),
                          // Actions
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              if (_selectedRecord!['memory_id'] != null)
                                OutlinedButton.icon(
                                  icon: const Icon(Icons.edit_outlined, size: 14),
                                  label: const Text('Edit'),
                                  onPressed: () => setState(() => _isEditing = true),
                                ),
                              OutlinedButton.icon(
                                icon: const Icon(Icons.copy_rounded, size: 14),
                                label: const Text('Export'),
                                onPressed: () => _exportRecord(_selectedRecord!),
                              ),
                              OutlinedButton.icon(
                                icon: Icon(Icons.delete_outline_rounded, size: 14, color: palette.error),
                                label: Text('Delete', style: TextStyle(color: palette.error)),
                                onPressed: _deleteSelected,
                              ),
                            ],
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

class _MemoryCard extends StatelessWidget {
  final Map<String, dynamic> record;
  final bool isSelected;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final VoidCallback onTap;
  final VoidCallback onTogglePin;

  const _MemoryCard({
    required this.record,
    required this.isSelected,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.onTap,
    required this.onTogglePin,
  });

  @override
  Widget build(BuildContext context) {
    final title = record['title'] ?? 'Record';
    final content = record['content'] ?? '';
    final category = record['category'] ?? 'General';
    final isPrivate = record['privacy'] == 'private';
    final isPinned = record['pinned'] == true;
    final updated = record['updated_at'] ?? '';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected ? accent.withValues(alpha: 0.1) : palette.surface,
          borderRadius: EvaTokens.borderMd,
          border: Border.all(
            color: isSelected ? accent : palette.border,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      color: isSelected ? accent : palette.textPri,
                      fontSize: 13.5 * scale,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.15),
                    borderRadius: EvaTokens.borderSm,
                  ),
                  child: Text(
                    category,
                    style: TextStyle(color: accent, fontSize: 10 * scale, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  isPrivate ? Icons.lock_outline_rounded : Icons.public_outlined,
                  size: 13,
                  color: isPrivate ? palette.warning : palette.textSec,
                ),
                if (record['memory_id'] != null)
                  IconButton(
                    icon: Icon(isPinned ? Icons.push_pin_rounded : Icons.push_pin_outlined, size: 14),
                    color: isPinned ? accent : palette.textSec,
                    onPressed: onTogglePin,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              content,
              style: TextStyle(color: palette.textSec, fontSize: 12 * scale),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  'Source: ${record['source'] ?? 'user'}',
                  style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale),
                ),
                const Spacer(),
                Text(
                  updated.length >= 10 ? updated.substring(0, 10) : updated,
                  style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontFamily: 'monospace'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final EvaPalette palette;
  final double scale;
  final String label;
  final String value;

  const _DetailRow({
    required this.palette,
    required this.scale,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(label, style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
          ),
          Expanded(
            child: Text(value, style: TextStyle(color: palette.textPri, fontSize: 11 * scale, fontFamily: 'monospace')),
          ),
        ],
      ),
    );
  }
}
