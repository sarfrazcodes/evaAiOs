import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/theme_notifier.dart';
import 'top_panel.dart';
import 'sidebar_nav.dart';

import '../../features/home/home_screen.dart';
import '../../features/assistant/assistant_screen.dart';
import '../../features/applications/app_manager_screen.dart';
import '../../features/files/file_explorer_screen.dart';
import '../../features/memory/memory_explorer_screen.dart';
import '../../features/task_manager/task_manager_screen.dart';
import '../../features/system_monitor/system_monitor_screen.dart';
import '../../features/settings/settings_screen.dart';

class DesktopShell extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const DesktopShell({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  int _activeTab = 0; // Starts at Home
  final GlobalKey<AssistantScreenState> _assistantKey = GlobalKey<AssistantScreenState>();

  static const List<NavItemDef> _navItems = [
    NavItemDef(
      idleIcon: Icons.dashboard_outlined,
      activeIcon: Icons.dashboard_rounded,
      label: 'Home',
    ),
    NavItemDef(
      idleIcon: Icons.chat_bubble_outline_rounded,
      activeIcon: Icons.chat_bubble_rounded,
      label: 'EVA Assistant',
    ),
    NavItemDef(
      idleIcon: Icons.apps_outlined,
      activeIcon: Icons.apps_rounded,
      label: 'Applications',
    ),
    NavItemDef(
      idleIcon: Icons.folder_outlined,
      activeIcon: Icons.folder_rounded,
      label: 'File Explorer',
    ),
    NavItemDef(
      idleIcon: Icons.psychology_outlined,
      activeIcon: Icons.psychology_rounded,
      label: 'Memory',
    ),
    NavItemDef(
      idleIcon: Icons.alt_route_rounded,
      activeIcon: Icons.alt_route_rounded,
      label: 'Task Manager',
    ),
    NavItemDef(
      idleIcon: Icons.speed_outlined,
      activeIcon: Icons.speed_rounded,
      label: 'System Monitor',
    ),
    NavItemDef(
      idleIcon: Icons.tune_rounded,
      activeIcon: Icons.tune_rounded,
      label: 'Settings',
    ),
  ];

  void _navigateTo(int index) {
    if (index >= 0 && index < _navItems.length) {
      setState(() => _activeTab = index);
    }
  }

  void _triggerVoiceInput() {
    _navigateTo(1); // Switch to Assistant
    Future.delayed(const Duration(milliseconds: 150), () {
      _assistantKey.currentState?.handleMicButton();
    });
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final currentNav = _navItems[_activeTab];
    final hasWallpaper = widget.themeNotifier.hasValidWallpaper;

    // Mic & TTS Status from Assistant state
    final assistantState = _assistantKey.currentState;
    final micState = assistantState?.micState ?? MicState.idle;
    final ttsSpeaking = assistantState?.ttsSpeaking ?? false;

    String micText = 'Mic Ready';
    IconData micIcon = Icons.mic_rounded;
    Color micColor = palette.textSec;

    if (micState == MicState.recording) {
      final cd = assistantState?.recordingCountdown ?? 5;
      micText = 'Listening (${cd}s)…';
      micIcon = Icons.graphic_eq_rounded;
      micColor = palette.error;
    } else if (micState == MicState.transcribing) {
      micText = 'Transcribing…';
      micIcon = Icons.hourglass_top_rounded;
      micColor = widget.themeNotifier.accent.primary;
    } else if (micState == MicState.error) {
      micText = 'Mic Error';
      micIcon = Icons.mic_off_rounded;
      micColor = palette.error;
    }

    return Scaffold(
      backgroundColor: palette.bg,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // ── Background Wallpaper (if configured) ──────────────────────────
          if (hasWallpaper) ...[
            ImageFiltered(
              imageFilter: widget.themeNotifier.wallpaperBlur > 0
                  ? ImageFilter.blur(
                      sigmaX: widget.themeNotifier.wallpaperBlur,
                      sigmaY: widget.themeNotifier.wallpaperBlur,
                    )
                  : ImageFilter.blur(sigmaX: 0.0, sigmaY: 0.0),
              child: Opacity(
                opacity: widget.themeNotifier.wallpaperBrightness.clamp(0.1, 1.0),
                child: Image.file(
                  File(widget.themeNotifier.wallpaperPath),
                  fit: widget.themeNotifier.wallpaperFit,
                  errorBuilder: (_, _, _) => const SizedBox.shrink(),
                ),
              ),
            ),
            Container(
              color: palette.bg.withValues(alpha: widget.themeNotifier.wallpaperDim),
            ),
          ],

          // ── Main Desktop Environment Shell ───────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Left Collapsible Sidebar Dock
              SidebarNav(
                themeNotifier: widget.themeNotifier,
                items: _navItems,
                selectedIndex: _activeTab,
                onSelect: _navigateTo,
                onToggleCollapse: widget.themeNotifier.toggleSidebar,
              ),

              // Main Workspace & Top Bar
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Top Panel
                    TopPanel(
                      themeNotifier: widget.themeNotifier,
                      activeSectionName: currentNav.label,
                      onOpenSettings: () => _navigateTo(7),
                      onToggleMic: _triggerVoiceInput,
                      onToggleTts: () => widget.themeNotifier.setTtsEnabled(!widget.themeNotifier.ttsEnabled),
                      onStopSpeech: () => _assistantKey.currentState?.stopSpeech(),
                      micStatusText: micText,
                      micStatusIcon: micIcon,
                      micStatusColor: micColor,
                      ttsSpeaking: ttsSpeaking,
                    ),

                    // Indexed Stack to preserve all pages, chat history, and active streams
                    Expanded(
                      child: IndexedStack(
                        index: _activeTab,
                        children: [
                          HomeScreen(
                            themeNotifier: widget.themeNotifier,
                            onNavigate: _navigateTo,
                            onOpenAssistant: () => _navigateTo(1),
                            onTriggerVoice: _triggerVoiceInput,
                          ),
                          AssistantScreen(
                            key: _assistantKey,
                            themeNotifier: widget.themeNotifier,
                          ),
                          AppManagerScreen(themeNotifier: widget.themeNotifier),
                          FileExplorerScreen(themeNotifier: widget.themeNotifier),
                          MemoryExplorerScreen(
                            themeNotifier: widget.themeNotifier,
                            onNavigate: _navigateTo,
                          ),
                          TaskManagerScreen(themeNotifier: widget.themeNotifier),
                          SystemMonitorScreen(themeNotifier: widget.themeNotifier),
                          SettingsScreen(themeNotifier: widget.themeNotifier),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
