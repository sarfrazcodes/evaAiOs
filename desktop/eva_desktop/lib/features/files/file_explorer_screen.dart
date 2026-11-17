import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/theme_notifier.dart';
import '../../core/services/api_client.dart';

class FileExplorerScreen extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const FileExplorerScreen({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<FileExplorerScreen> createState() => _FileExplorerScreenState();
}

class _FileExplorerScreenState extends State<FileExplorerScreen> {
  String _currentPath = '';
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String _searchQuery = '';
  String _sortBy = 'name'; // 'name', 'date', 'type'
  bool _sortAsc = true;

  Map<String, dynamic>? _selectedFile;
  String? _fileContent;
  bool _loadingContent = false;

  @override
  void initState() {
    super.initState();
    _loadDirectory('');
  }

  Future<void> _loadDirectory(String path) async {
    setState(() {
      _loading = true;
      _selectedFile = null;
      _fileContent = null;
    });

    final data = await EvaApiClient.listFiles(path);
    if (mounted) {
      if (data != null) {
        setState(() {
          _currentPath = data['current_path'] as String? ?? path;
          _items = (data['items'] as List? ?? []).cast<Map<String, dynamic>>();
          _loading = false;
        });
      } else {
        setState(() => _loading = false);
        _showError('Could not load directory. Security boundary or folder error.');
      }
    }
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

  List<Map<String, dynamic>> get _sortedItems {
    final list = _items.where((item) {
      if (_searchQuery.isEmpty) return true;
      final name = (item['name'] ?? '').toString().toLowerCase();
      return name.contains(_searchQuery.toLowerCase());
    }).toList();

    list.sort((a, b) {
      final aDir = a['is_dir'] == true;
      final bDir = b['is_dir'] == true;
      if (aDir != bDir) {
        return aDir ? -1 : 1; // Folders always first
      }

      if (_sortBy == 'date') {
        final aDate = a['modified_at'] ?? '';
        final bDate = b['modified_at'] ?? '';
        return _sortAsc ? aDate.compareTo(bDate) : bDate.compareTo(aDate);
      } else if (_sortBy == 'type') {
        final aExt = a['extension'] ?? '';
        final bExt = b['extension'] ?? '';
        return _sortAsc ? aExt.compareTo(bExt) : bExt.compareTo(aExt);
      } else {
        final aName = (a['name'] ?? '').toString().toLowerCase();
        final bName = (b['name'] ?? '').toString().toLowerCase();
        return _sortAsc ? aName.compareTo(bName) : bName.compareTo(aName);
      }
    });

    return list;
  }

  Future<void> _openFile(Map<String, dynamic> item) async {
    if (item['is_dir'] == true) {
      final rel = item['relative_path'] as String;
      _loadDirectory(rel);
      return;
    }

    setState(() {
      _selectedFile = item;
      _loadingContent = true;
      _fileContent = null;
    });

    final res = await EvaApiClient.readFile(item['relative_path'] as String);
    if (mounted) {
      setState(() {
        _fileContent = res?['content'];
        _loadingContent = false;
      });
    }
  }

  void _navigateUp() {
    if (_currentPath.isEmpty) return;
    final parts = _currentPath.split('/');
    if (parts.length <= 1) {
      _loadDirectory('');
    } else {
      parts.removeLast();
      _loadDirectory(parts.join('/'));
    }
  }

  void _showNewFolderDialog() {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final nameCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: palette.surface,
        title: Text('New Directory', style: TextStyle(color: palette.textPri, fontSize: 15)),
        content: TextField(
          controller: nameCtrl,
          autofocus: true,
          style: TextStyle(color: palette.textPri, fontSize: 13),
          decoration: const InputDecoration(
            hintText: 'Directory name',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: TextStyle(color: palette.textSec)),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = nameCtrl.text.trim();
              if (name.isEmpty) return;
              final path = _currentPath.isEmpty ? name : '$_currentPath/$name';
              final ok = await EvaApiClient.createFile(path, '', isDirectory: true);
              if (ctx.mounted) Navigator.of(ctx).pop();
              if (ok) {
                _loadDirectory(_currentPath);
              } else {
                _showError('Directory creation failed.');
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showNewFileDialog() {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final nameCtrl = TextEditingController();
    final contentCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: palette.surface,
        title: Text('New Workspace File', style: TextStyle(color: palette.textPri, fontSize: 15)),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                style: TextStyle(color: palette.textPri, fontSize: 13),
                decoration: const InputDecoration(hintText: 'Filename (e.g. notes.md, main.py)'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: contentCtrl,
                minLines: 4,
                maxLines: 8,
                style: TextStyle(color: palette.textPri, fontSize: 13, fontFamily: 'monospace'),
                decoration: const InputDecoration(hintText: 'File content…'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: TextStyle(color: palette.textSec)),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = nameCtrl.text.trim();
              if (name.isEmpty) return;
              final path = _currentPath.isEmpty ? name : '$_currentPath/$name';
              final ok = await EvaApiClient.createFile(path, contentCtrl.text, isDirectory: false);
              if (ctx.mounted) Navigator.of(ctx).pop();
              if (ok) {
                _loadDirectory(_currentPath);
              } else {
                _showError('File creation failed.');
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: accent, foregroundColor: palette.bg),
            child: const Text('Create File'),
          ),
        ],
      ),
    );
  }

  IconData _iconForExt(String ext, bool isDir) {
    if (isDir) return Icons.folder_rounded;
    if (ext == '.py' || ext == '.dart' || ext == '.sh' || ext == '.json') return Icons.code_rounded;
    if (ext == '.md' || ext == '.txt') return Icons.article_outlined;
    if (ext == '.wav' || ext == '.mp3') return Icons.audiotrack_outlined;
    if (ext == '.png' || ext == '.jpg' || ext == '.webp') return Icons.image_outlined;
    return Icons.insert_drive_file_outlined;
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;
    final items = _sortedItems;

    final breadcrumbs = _currentPath.isEmpty ? <String>[] : _currentPath.split('/');

    return Row(
      children: [
        // ── Main File List Column ─────────────────────────────────────────
        Expanded(
          flex: _selectedFile != null ? 6 : 10,
          child: Container(
            color: palette.bg,
            child: Column(
              children: [
                // Toolbar
                Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: palette.surface,
                    border: Border(bottom: BorderSide(color: palette.border)),
                  ),
                  child: Row(
                    children: [
                      // Back / Up button
                      IconButton(
                        icon: const Icon(Icons.arrow_upward_rounded, size: 16),
                        color: _currentPath.isNotEmpty ? palette.textPri : palette.border,
                        tooltip: 'Up to parent folder',
                        onPressed: _currentPath.isNotEmpty ? _navigateUp : null,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                      ),
                      const SizedBox(width: 8),

                      // Breadcrumbs
                      Expanded(
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: [
                              InkWell(
                                onTap: () => _loadDirectory(''),
                                child: Text(
                                  'workspace',
                                  style: TextStyle(
                                    color: _currentPath.isEmpty ? palette.textPri : accent,
                                    fontSize: 12 * scale,
                                    fontWeight: FontWeight.w600,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                              ),
                              for (int i = 0; i < breadcrumbs.length; i++) ...[
                                Text(' / ', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                                InkWell(
                                  onTap: () {
                                    final sub = breadcrumbs.take(i + 1).join('/');
                                    _loadDirectory(sub);
                                  },
                                  child: Text(
                                    breadcrumbs[i],
                                    style: TextStyle(
                                      color: i == breadcrumbs.length - 1 ? palette.textPri : accent,
                                      fontSize: 12 * scale,
                                      fontWeight: i == breadcrumbs.length - 1 ? FontWeight.w600 : FontWeight.normal,
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),

                      // Search box
                      SizedBox(
                        width: 170,
                        height: 30,
                        child: TextField(
                          style: TextStyle(color: palette.textPri, fontSize: 12 * scale),
                          decoration: InputDecoration(
                            hintText: 'Filter files…',
                            prefixIcon: Icon(Icons.search_rounded, size: 14, color: palette.textSec),
                            contentPadding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
                            isDense: true,
                          ),
                          onChanged: (v) => setState(() => _searchQuery = v),
                        ),
                      ),
                      // Sort toggle
                      PopupMenuButton<String>(
                        icon: Icon(Icons.sort_rounded, size: 16, color: palette.textSec),
                        tooltip: 'Sort by',
                        color: palette.surface,
                        onSelected: (v) {
                          if (_sortBy == v) {
                            setState(() => _sortAsc = !_sortAsc);
                          } else {
                            setState(() {
                              _sortBy = v;
                              _sortAsc = true;
                            });
                          }
                        },
                        itemBuilder: (ctx) => [
                          PopupMenuItem(
                            value: 'name',
                            child: Text('Sort by Name ${_sortBy == 'name' ? (_sortAsc ? '▲' : '▼') : ''}'),
                          ),
                          PopupMenuItem(
                            value: 'date',
                            child: Text('Sort by Date ${_sortBy == 'date' ? (_sortAsc ? '▲' : '▼') : ''}'),
                          ),
                          PopupMenuItem(
                            value: 'type',
                            child: Text('Sort by Type ${_sortBy == 'type' ? (_sortAsc ? '▲' : '▼') : ''}'),
                          ),
                        ],
                      ),
                      const SizedBox(width: 4),
                      Tooltip(
                        message: 'New directory',
                        child: IconButton(
                          icon: const Icon(Icons.create_new_folder_outlined, size: 17),
                          color: palette.textSec,
                          onPressed: _showNewFolderDialog,
                        ),
                      ),

                      // New File
                      Tooltip(
                        message: 'New text file',
                        child: IconButton(
                          icon: const Icon(Icons.note_add_outlined, size: 17),
                          color: palette.textSec,
                          onPressed: _showNewFileDialog,
                        ),
                      ),

                      // Refresh
                      Tooltip(
                        message: 'Refresh directory',
                        child: IconButton(
                          icon: const Icon(Icons.refresh_rounded, size: 17),
                          color: palette.textSec,
                          onPressed: () => _loadDirectory(_currentPath),
                        ),
                      ),
                    ],
                  ),
                ),

                // Directory Contents Table
                Expanded(
                  child: _loading
                      ? Center(child: CircularProgressIndicator(color: accent))
                      : items.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.folder_open_rounded, size: 44, color: palette.textSec.withValues(alpha: 0.4)),
                                  const SizedBox(height: 10),
                                  Text('Folder is empty', style: TextStyle(color: palette.textPri, fontSize: 13.5 * scale, fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 4),
                                  Text('Use the toolbar to create folders or files.', style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
                                ],
                              ),
                            )
                          : ListView.builder(
                              itemCount: items.length,
                              itemBuilder: (ctx, i) {
                                final item = items[i];
                                final isDir = item['is_dir'] == true;
                                final ext = item['extension'] as String? ?? '';
                                final isSel = _selectedFile != null && _selectedFile!['relative_path'] == item['relative_path'];

                                return InkWell(
                                  onTap: () => _openFile(item),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: isSel ? accent.withValues(alpha: 0.12) : (i % 2 == 0 ? palette.surface : palette.bg),
                                      border: Border(bottom: BorderSide(color: palette.borderSubtle)),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          _iconForExt(ext, isDir),
                                          size: 16,
                                          color: isDir ? accent : palette.textSec,
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Text(
                                            item['name'] ?? '',
                                            style: TextStyle(
                                              color: palette.textPri,
                                              fontSize: 12.5 * scale,
                                              fontWeight: isDir ? FontWeight.w600 : FontWeight.normal,
                                            ),
                                          ),
                                        ),
                                        SizedBox(
                                          width: 90,
                                          child: Text(
                                            isDir ? 'Directory' : '${item['size']} B',
                                            style: TextStyle(color: palette.textSec, fontSize: 11 * scale),
                                          ),
                                        ),
                                        SizedBox(
                                          width: 120,
                                          child: Text(
                                            (item['modified_at'] as String? ?? '').substring(0, 10),
                                            style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace'),
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

        // ── File Content & Details Viewer ─────────────────────────────────
        if (_selectedFile != null)
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: 380,
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border(left: BorderSide(color: palette.border)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header
                Container(
                  height: 44,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: palette.panel,
                    border: Border(bottom: BorderSide(color: palette.border)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.description_outlined, size: 16, color: accent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _selectedFile!['name'] ?? '',
                          style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale, fontWeight: FontWeight.w600),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 16),
                        color: palette.textSec,
                        onPressed: () => setState(() => _selectedFile = null),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                      ),
                    ],
                  ),
                ),

                // File metadata
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: palette.bg,
                    border: Border(bottom: BorderSide(color: palette.borderSubtle)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Path: ${_selectedFile!['relative_path']}', style: TextStyle(color: palette.textSec, fontSize: 11 * scale, fontFamily: 'monospace')),
                      Text('Size: ${_selectedFile!['size']} bytes', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                      Text('Modified: ${_selectedFile!['modified_at']}', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    ],
                  ),
                ),

                // File content preview
                Expanded(
                  child: _loadingContent
                      ? Center(child: CircularProgressIndicator(color: accent))
                      : _fileContent != null
                          ? SingleChildScrollView(
                              padding: const EdgeInsets.all(14),
                              child: SelectableText(
                                _fileContent!,
                                style: TextStyle(color: palette.textPri, fontSize: 12 * scale, fontFamily: 'monospace', height: 1.4),
                              ),
                            )
                          : Center(
                              child: Text('Cannot preview this file type.', style: TextStyle(color: palette.textSec, fontSize: 12 * scale)),
                            ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
