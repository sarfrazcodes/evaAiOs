// EVA AI OS — UI redesign
// Only presentation has changed here. The data source, polling interval,
// JSON field names, and page/navigation structure are identical to the
// original implementation.

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const EvaOSApp());
}

/// Root widget. Owns the light/dark [ThemeMode] and passes a toggle callback
/// down to the shell so the user can switch themes from the sidebar.
class EvaOSApp extends StatefulWidget {
  const EvaOSApp({super.key});

  @override
  State<EvaOSApp> createState() => _EvaOSAppState();
}

class _EvaOSAppState extends State<EvaOSApp> {
  ThemeMode _themeMode = ThemeMode.dark;

  static const Color _accent = Color(0xFF17E0C7);

  void _toggleTheme() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EVA AI OS',
      debugShowCheckedModeBanner: false,
      themeMode: _themeMode,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _accent,
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF0F2F7),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _accent,
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF101115),
      ),
      home: DesktopShell(
        isDarkMode: _themeMode == ThemeMode.dark,
        onToggleTheme: _toggleTheme,
      ),
    );
  }
}

/// Small palette helper so every widget below doesn't need to hand-roll
/// light/dark colour branches.
class _Palette {
  final bool isDark;
  _Palette(this.isDark);

  Color get sidebarBg => isDark ? const Color(0xFF15161B) : Colors.white;
  Color get sidebarSelected =>
      isDark ? const Color(0xFF23262E) : const Color(0xFFEAF7F5);
  Color get cardBg => isDark ? const Color(0xFF1B1D23) : Colors.white;
  Color get cardBorder =>
      isDark ? Colors.white.withOpacity(0.06) : Colors.black.withOpacity(0.05);
  Color get textPrimary => isDark ? Colors.white : const Color(0xFF14151A);
  Color get textSecondary =>
      isDark ? Colors.white60 : const Color(0xFF6B7280);
  Color get shadow =>
      isDark ? Colors.black.withOpacity(0.35) : Colors.black.withOpacity(0.06);
}

class _NavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  const _NavItem(this.icon, this.selectedIcon, this.label);
}

class DesktopShell extends StatefulWidget {
  final bool isDarkMode;
  final VoidCallback onToggleTheme;

  const DesktopShell({
    super.key,
    required this.isDarkMode,
    required this.onToggleTheme,
  });

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  int _selectedIndex = 0;

  static const List<_NavItem> _navItems = [
    _NavItem(Icons.dashboard_outlined, Icons.dashboard, 'Home'),
    _NavItem(Icons.folder_outlined, Icons.folder, 'Files'),
    _NavItem(Icons.apps_outlined, Icons.apps, 'Apps'),
    _NavItem(Icons.memory_outlined, Icons.memory, 'Memory'),
    _NavItem(Icons.settings_outlined, Icons.settings, 'Settings'),
    _NavItem(Icons.assistant_outlined, Icons.assistant, 'EVA'),
  ];

  List<Widget> _buildPages(_Palette palette) {
    return [
      HomeDashboard(palette: palette),
      PlaceholderPage(
        title: 'Files (Phase 1 Placeholder)',
        icon: Icons.folder_outlined,
        palette: palette,
      ),
      PlaceholderPage(
        title: 'Applications (Phase 1 Placeholder)',
        icon: Icons.apps_outlined,
        palette: palette,
      ),
      PlaceholderPage(
        title: 'Memory (Phase 1 Placeholder)',
        icon: Icons.memory_outlined,
        palette: palette,
      ),
      PlaceholderPage(
        title: 'Settings (Phase 1 Placeholder)',
        icon: Icons.settings_outlined,
        palette: palette,
      ),
      EvaInteractionArea(palette: palette),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final palette = _Palette(widget.isDarkMode);
    final pages = _buildPages(palette);

    return Scaffold(
      body: Row(
        children: [
          _Sidebar(
            items: _navItems,
            selectedIndex: _selectedIndex,
            palette: palette,
            onSelect: (index) => setState(() => _selectedIndex = index),
            isDarkMode: widget.isDarkMode,
            onToggleTheme: widget.onToggleTheme,
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _TopBar(
                  title: _navItems[_selectedIndex].label,
                  palette: palette,
                ),
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    child: KeyedSubtree(
                      key: ValueKey<int>(_selectedIndex),
                      child: pages[_selectedIndex],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Custom-styled left navigation rail — replaces the stock NavigationRail
/// look with rounded selection pills, a logo badge, and a theme toggle.
class _Sidebar extends StatelessWidget {
  final List<_NavItem> items;
  final int selectedIndex;
  final _Palette palette;
  final ValueChanged<int> onSelect;
  final bool isDarkMode;
  final VoidCallback onToggleTheme;

  const _Sidebar({
    required this.items,
    required this.selectedIndex,
    required this.palette,
    required this.onSelect,
    required this.isDarkMode,
    required this.onToggleTheme,
  });

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;

    return Container(
      width: 96,
      decoration: BoxDecoration(
        color: palette.sidebarBg,
        border: Border(right: BorderSide(color: palette.cardBorder)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 28),
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [accent, accent.withOpacity(0.55)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.auto_awesome,
                color: Colors.black87, size: 22),
          ),
          const SizedBox(height: 32),
          Expanded(
            child: ListView.builder(
              padding: EdgeInsets.zero,
              itemCount: items.length,
              itemBuilder: (context, index) {
                final item = items[index];
                final selected = index == selectedIndex;
                return Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 6, horizontal: 14),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => onSelect(index),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: selected
                              ? palette.sidebarSelected
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(16),
                          border: selected
                              ? Border.all(color: accent.withOpacity(0.4))
                              : null,
                        ),
                        child: Column(
                          children: [
                            Icon(
                              selected ? item.selectedIcon : item.icon,
                              color: selected ? accent : palette.textSecondary,
                              size: 22,
                            ),
                            const SizedBox(height: 6),
                            Text(
                              item.label,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight:
                                    selected ? FontWeight.w600 : FontWeight.w400,
                                color:
                                    selected ? accent : palette.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 24),
            child: IconButton(
              tooltip:
                  isDarkMode ? 'Switch to light mode' : 'Switch to dark mode',
              onPressed: onToggleTheme,
              icon: Icon(
                isDarkMode ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                color: palette.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Top bar showing the current section title and a live clock.
class _TopBar extends StatefulWidget {
  final String title;
  final _Palette palette;

  const _TopBar({required this.title, required this.palette});

  @override
  State<_TopBar> createState() => _TopBarState();
}

class _TopBarState extends State<_TopBar> {
  late DateTime _now;
  Timer? _clockTimer;

  @override
  void initState() {
    super.initState();
    _now = DateTime.now();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _clockTimer?.cancel();
    super.dispose();
  }

  String get _timeString {
    final h = _now.hour.toString().padLeft(2, '0');
    final m = _now.minute.toString().padLeft(2, '0');
    final s = _now.second.toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 28),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: widget.palette.cardBorder)),
      ),
      child: Row(
        children: [
          Text(
            widget.title,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: widget.palette.textPrimary,
            ),
          ),
          const Spacer(),
          Icon(Icons.schedule, size: 16, color: widget.palette.textSecondary),
          const SizedBox(width: 6),
          Text(
            _timeString,
            style: TextStyle(fontSize: 13, color: widget.palette.textSecondary),
          ),
        ],
      ),
    );
  }
}

class HomeDashboard extends StatefulWidget {
  final _Palette palette;
  const HomeDashboard({super.key, required this.palette});

  @override
  State<HomeDashboard> createState() => _HomeDashboardState();
}

class _HomeDashboardState extends State<HomeDashboard> {
  // Unchanged from the original: same endpoint, same polling interval,
  // same parsing logic.
  Map<String, dynamic>? _sysInfo;
  String _error = "";
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchSysInfo();
    _timer = Timer.periodic(const Duration(seconds: 5), (timer) {
      _fetchSysInfo();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchSysInfo() async {
    try {
      final response =
          await http.get(Uri.parse('http://127.0.0.1:8000/api/system/info'));
      if (response.statusCode == 200) {
        setState(() {
          _sysInfo = json.decode(response.body);
          _error = "";
        });
      } else {
        setState(() {
          _error = "Failed to load system info.";
        });
      }
    } catch (e) {
      setState(() {
        _error = "Cannot connect to EVA Core System Layer.";
      });
    }
  }

  double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;
    final accent = Theme.of(context).colorScheme.primary;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: accent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(Icons.auto_awesome, color: accent, size: 26),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'EVA AI OS',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: palette.textPrimary,
                    ),
                  ),
                  Text(
                    'System Dashboard',
                    style: TextStyle(fontSize: 15, color: palette.textSecondary),
                  ),
                ],
              ),
              const Spacer(),
              _StatusPill(
                connected: _error.isEmpty && _sysInfo != null,
                palette: palette,
              ),
            ],
          ),
          const SizedBox(height: 32),
          if (_error.isNotEmpty)
            _ErrorBanner(message: _error, palette: palette)
          else if (_sysInfo == null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 60),
              child: Center(child: CircularProgressIndicator(color: accent)),
            )
          else
            LayoutBuilder(
              builder: (context, constraints) {
                final cardWidth = constraints.maxWidth > 900
                    ? (constraints.maxWidth - 2 * 20) / 3
                    : constraints.maxWidth > 560
                        ? (constraints.maxWidth - 20) / 2
                        : constraints.maxWidth;
                return Wrap(
                  spacing: 20,
                  runSpacing: 20,
                  children: [
                    _InfoCard(
                      width: cardWidth,
                      title: 'Hostname',
                      value: '${_sysInfo!['hostname']}',
                      icon: Icons.computer,
                      palette: palette,
                      accent: accent,
                    ),
                    _InfoCard(
                      width: cardWidth,
                      title: 'OS Version',
                      value: '${_sysInfo!['os']}',
                      icon: Icons.laptop,
                      palette: palette,
                      accent: accent,
                    ),
                    _InfoCard(
                      width: cardWidth,
                      title: 'CPU',
                      value: '${_sysInfo!['cpu']}',
                      icon: Icons.memory,
                      palette: palette,
                      accent: accent,
                    ),
                    _InfoCard(
                      width: cardWidth,
                      title: 'RAM',
                      value:
                          '${_sysInfo!['ram_used_gb']} GB / ${_sysInfo!['ram_total_gb']} GB',
                      icon: Icons.storage,
                      palette: palette,
                      accent: accent,
                      percent: _asDouble(_sysInfo!['ram_percent']),
                    ),
                    _InfoCard(
                      width: cardWidth,
                      title: 'Disk',
                      value:
                          '${_sysInfo!['disk_used_gb']} GB / ${_sysInfo!['disk_total_gb']} GB',
                      icon: Icons.save,
                      palette: palette,
                      accent: accent,
                      percent: _asDouble(_sysInfo!['disk_percent']),
                    ),
                    _InfoCard(
                      width: cardWidth,
                      title: 'EVA Core',
                      value: 'Connected',
                      icon: Icons.check_circle,
                      palette: palette,
                      accent: const Color(0xFF3DDC84),
                    ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final double width;
  final String title;
  final String value;
  final IconData icon;
  final _Palette palette;
  final Color accent;
  final double? percent; // 0-100, optional progress bar (RAM / Disk)

  const _InfoCard({
    required this.width,
    required this.title,
    required this.value,
    required this.icon,
    required this.palette,
    required this.accent,
    this.percent,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: palette.cardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.cardBorder),
        boxShadow: [
          BoxShadow(
            color: palette.shadow,
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: accent, size: 22),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style:
                        TextStyle(fontSize: 13, color: palette.textSecondary)),
                const SizedBox(height: 6),
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: palette.textPrimary,
                  ),
                ),
                if (percent != null) ...[
                  const SizedBox(height: 10),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: percent!.clamp(0, 100) / 100,
                      minHeight: 6,
                      backgroundColor: palette.cardBorder,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        percent! > 85 ? const Color(0xFFEF5350) : accent,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${percent!.toStringAsFixed(0)}%',
                    style:
                        TextStyle(fontSize: 11, color: palette.textSecondary),
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

class _StatusPill extends StatelessWidget {
  final bool connected;
  final _Palette palette;
  const _StatusPill({required this.connected, required this.palette});

  @override
  Widget build(BuildContext context) {
    final color =
        connected ? const Color(0xFF3DDC84) : const Color(0xFFEF5350);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            connected ? 'Core Connected' : 'Core Offline',
            style:
                TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String message;
  final _Palette palette;
  const _ErrorBanner({required this.message, required this.palette});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFEF5350).withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFEF5350).withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFEF5350)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                  color: Color(0xFFEF5350), fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

class PlaceholderPage extends StatelessWidget {
  final String title;
  final IconData icon;
  final _Palette palette;

  const PlaceholderPage({
    super.key,
    required this.title,
    required this.icon,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Icon(icon, size: 32, color: accent),
          ),
          const SizedBox(height: 20),
          Text(
            title,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: palette.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'This module is coming soon.',
            style: TextStyle(fontSize: 14, color: palette.textSecondary),
          ),
        ],
      ),
    );
  }
}

class EvaInteractionArea extends StatefulWidget {
  final _Palette palette;
  const EvaInteractionArea({super.key, required this.palette});

  @override
  State<EvaInteractionArea> createState() => _EvaInteractionAreaState();
}

class _EvaInteractionAreaState extends State<EvaInteractionArea> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  bool _isLoading = false;

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({"sender": "user", "text": text});
      _isLoading = true;
    });
    _controller.clear();

    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8000/api/v1/core/request'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "source": "desktop",
          "input_type": "text",
          "content": text,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _messages.add({
            "sender": "eva",
            "text": data['message'],
            "status": data['status'],
            "intent": data['data'] != null ? data['data']['intent'] : null,
            "confidence": data['data'] != null ? data['data']['confidence'] : null,
            "route": data['data'] != null ? data['data']['route'] : null,
            "task": data['data'] != null ? data['data']['task'] : null,
          });
        });
      } else {
        setState(() {
          _messages.add({"sender": "system", "text": "Error: ${response.statusCode}"});
        });
      }
    } catch (e) {
      setState(() {
        _messages.add({"sender": "system", "text": "Connection failed."});
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(32),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final msg = _messages[index];
              final isUser = msg['sender'] == 'user';
              final isSystem = msg['sender'] == 'system';
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: isUser
                        ? accent.withOpacity(0.2)
                        : (isSystem ? Colors.red.withOpacity(0.2) : widget.palette.cardBg),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isUser ? accent.withOpacity(0.5) : widget.palette.cardBorder,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isUser ? "You" : (isSystem ? "System Error" : "EVA Core"),
                        style: TextStyle(
                          fontSize: 12,
                          color: widget.palette.textSecondary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        msg['text'],
                        style: TextStyle(color: widget.palette.textPrimary),
                      ),
                      if (!isUser && !isSystem && msg['status'] != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          "Status: ${msg['status']}",
                          style: TextStyle(fontSize: 10, color: accent),
                        ),
                        if (msg['intent'] != null)
                          Text(
                            "Intent: ${msg['intent']} (Conf: ${((msg['confidence'] as double) * 100).toStringAsFixed(0)}%)",
                            style: TextStyle(fontSize: 10, color: Colors.blueAccent),
                          ),
                        if (msg['route'] != null)
                          Text(
                            "Route: ${msg['route']}",
                            style: TextStyle(fontSize: 10, color: Colors.green),
                          ),
                        if (msg['task'] != null) ...[
                          const SizedBox(height: 12),
                          Text("Task ID: ${msg['task']['task_id']}", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: widget.palette.textPrimary)),
                          Text("Task Status: ${msg['task']['status']}", style: TextStyle(fontSize: 11, color: accent)),
                          const SizedBox(height: 8),
                          ...List<Widget>.generate(
                            (msg['task']['steps'] as List).length,
                            (i) {
                              final step = msg['task']['steps'][i];
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 4.0, left: 8.0),
                                child: Text(
                                  "${step['sequence']}. ${step['description']}\n   [${step['status']}]",
                                  style: TextStyle(fontSize: 10, color: widget.palette.textSecondary),
                                ),
                              );
                            },
                          ),
                        ]
                      ]
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        if (_isLoading)
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: CircularProgressIndicator(),
          ),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: widget.palette.cardBg,
            border: Border(top: BorderSide(color: widget.palette.cardBorder)),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  onSubmitted: (_) => _sendMessage(),
                  style: TextStyle(color: widget.palette.textPrimary),
                  decoration: InputDecoration(
                    hintText: "Type a message or command...",
                    hintStyle: TextStyle(color: widget.palette.textSecondary),
                    filled: true,
                    fillColor: widget.palette.sidebarBg,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              FloatingActionButton(
                onPressed: _sendMessage,
                backgroundColor: accent,
                child: const Icon(Icons.send, color: Colors.black),
              ),
            ],
          ),
        ),
      ],
    );
  }
}