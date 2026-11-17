import 'dart:io';
import 'package:flutter/material.dart';
import '../../core/theme/eva_colors.dart';
import '../../core/theme/eva_tokens.dart';
import '../../core/theme/theme_notifier.dart';

class AppearanceSettings extends StatefulWidget {
  final ThemeNotifier themeNotifier;

  const AppearanceSettings({
    super.key,
    required this.themeNotifier,
  });

  @override
  State<AppearanceSettings> createState() => _AppearanceSettingsState();
}

class _AppearanceSettingsState extends State<AppearanceSettings> {
  final TextEditingController _customPathCtrl = TextEditingController();

  final List<Map<String, String>> _systemPresets = [
    {
      'name': 'Dimmed Raccoon',
      'path': '/usr/share/backgrounds/Resolute_Raccoon_Wallpaper_Dimmed_3840x2160.png',
    },
    {
      'name': 'Electric Veins',
      'path': '/usr/share/backgrounds/vale1ntin0omf-Electric_Veins_of_the_Storm.jpg',
    },
    {
      'name': 'Bluebells',
      'path': '/usr/share/backgrounds/mendhak-Bluebells_Suspended_In_Time.jpg',
    },
    {
      'name': 'Flying Boxes Dark',
      'path': '/usr/share/backgrounds/endycal-Flying_Boxes_Dark.png',
    },
    {
      'name': 'Vor Dark',
      'path': '/usr/share/backgrounds/manuej-Vor.jpg',
    },
  ];

  @override
  void initState() {
    super.initState();
    _customPathCtrl.text = widget.themeNotifier.wallpaperPath;
  }

  @override
  void dispose() {
    _customPathCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFileNative() async {
    try {
      final res = await Process.run('zenity', [
        '--file-selection',
        '--title=Choose EVA Desktop Background',
        '--file-filter=Images | *.png *.jpg *.jpeg *.webp *.bmp',
      ]);
      if (res.exitCode == 0) {
        final path = res.stdout.toString().trim();
        if (path.isNotEmpty && File(path).existsSync()) {
          _customPathCtrl.text = path;
          widget.themeNotifier.setWallpaper(path);
        }
      }
    } catch (_) {
      // Fallback: user can paste path into textfield
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.themeNotifier.getPalette(context);
    final accent = widget.themeNotifier.accent.primary;
    final scale = widget.themeNotifier.fontScale;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Theme Mode ──────────────────────────────────────────────────
          Text('DESKTOP THEME', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Row(
            children: [
              _ThemeOptionTile(
                title: 'Graphite Dark',
                desc: '#20252B • Deep Charcoal',
                isSelected: widget.themeNotifier.themeMode == ThemeMode.dark,
                palette: palette,
                accent: accent,
                scale: scale,
                icon: Icons.dark_mode_rounded,
                onTap: () => widget.themeNotifier.setThemeMode(ThemeMode.dark),
              ),
              const SizedBox(width: 12),
              _ThemeOptionTile(
                title: 'Ivory Light',
                desc: '#F7F6F2 • Warm Neutral',
                isSelected: widget.themeNotifier.themeMode == ThemeMode.light,
                palette: palette,
                accent: accent,
                scale: scale,
                icon: Icons.light_mode_rounded,
                onTap: () => widget.themeNotifier.setThemeMode(ThemeMode.light),
              ),
              const SizedBox(width: 12),
              _ThemeOptionTile(
                title: 'System Default',
                desc: 'Auto-sync with OS',
                isSelected: widget.themeNotifier.themeMode == ThemeMode.system,
                palette: palette,
                accent: accent,
                scale: scale,
                icon: Icons.brightness_auto_rounded,
                onTap: () => widget.themeNotifier.setThemeMode(ThemeMode.system),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // ── Accent Colors ───────────────────────────────────────────────
          Text('PRIMARY ACCENT COLOR', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: EvaAccentColor.values.map((ac) {
              final isSel = widget.themeNotifier.accent == ac;
              return InkWell(
                onTap: () => widget.themeNotifier.setAccent(ac),
                borderRadius: EvaTokens.borderMd,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSel ? ac.primary.withValues(alpha: 0.15) : palette.surface,
                    borderRadius: EvaTokens.borderMd,
                    border: Border.all(
                      color: isSel ? ac.primary : palette.border,
                      width: isSel ? 1.5 : 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(shape: BoxShape.circle, color: ac.primary),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        ac.label,
                        style: TextStyle(
                          color: isSel ? ac.primary : palette.textPri,
                          fontSize: 11.5 * scale,
                          fontWeight: isSel ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),

          const SizedBox(height: 24),

          // ── Desktop Background ───────────────────────────────────────────
          Text('DESKTOP WALLPAPER & BACKGROUND', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Container(
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
                    Expanded(
                      child: TextField(
                        controller: _customPathCtrl,
                        style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale),
                        decoration: InputDecoration(
                          labelText: 'Custom Background Image Path',
                          hintText: '/path/to/wallpaper.png',
                          suffixIcon: IconButton(
                            icon: const Icon(Icons.folder_open_rounded, size: 18),
                            tooltip: 'Browse local files',
                            onPressed: _pickFileNative,
                          ),
                        ),
                        onSubmitted: (v) {
                          if (v.trim().isEmpty) {
                            widget.themeNotifier.restoreDefaultWallpaper();
                          } else if (File(v.trim()).existsSync()) {
                            widget.themeNotifier.setWallpaper(v.trim());
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    OutlinedButton(
                      onPressed: () {
                        final path = _customPathCtrl.text.trim();
                        if (path.isEmpty) {
                          widget.themeNotifier.restoreDefaultWallpaper();
                        } else if (File(path).existsSync()) {
                          widget.themeNotifier.setWallpaper(path);
                        }
                      },
                      child: const Text('Apply'),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton(
                      onPressed: () {
                        _customPathCtrl.clear();
                        widget.themeNotifier.restoreDefaultWallpaper();
                      },
                      child: const Text('Restore Default'),
                    ),
                  ],
                ),

                const SizedBox(height: 14),

                // System Preset Wallpapers
                Text('System Linux Backgrounds', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale, fontWeight: FontWeight.w500)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _systemPresets.map((preset) {
                    final isSel = widget.themeNotifier.wallpaperPath == preset['path'];
                    return InkWell(
                      onTap: () {
                        _customPathCtrl.text = preset['path']!;
                        widget.themeNotifier.setWallpaper(preset['path']!);
                      },
                      borderRadius: EvaTokens.borderSm,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: isSel ? accent.withValues(alpha: 0.2) : palette.panel,
                          borderRadius: EvaTokens.borderSm,
                          border: Border.all(color: isSel ? accent : palette.borderSubtle),
                        ),
                        child: Text(
                          preset['name']!,
                          style: TextStyle(color: isSel ? accent : palette.textPri, fontSize: 11 * scale),
                        ),
                      ),
                    );
                  }).toList(),
                ),

                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 12),

                // Fit mode & Dimming slider
                Row(
                  children: [
                    Expanded(
                      flex: 4,
                      child: DropdownButtonFormField<BoxFit>(
                        initialValue: widget.themeNotifier.wallpaperFit,
                        dropdownColor: palette.surface,
                        style: TextStyle(color: palette.textPri, fontSize: 12 * scale),
                        decoration: const InputDecoration(labelText: 'Background Fit Mode'),
                        items: const [
                          DropdownMenuItem(value: BoxFit.cover, child: Text('Cover Screen')),
                          DropdownMenuItem(value: BoxFit.contain, child: Text('Contain (Fit Inside)')),
                          DropdownMenuItem(value: BoxFit.fill, child: Text('Stretch to Fill')),
                        ],
                        onChanged: (f) {
                          if (f != null) widget.themeNotifier.setWallpaperFit(f);
                        },
                      ),
                    ),
                    const SizedBox(width: 24),
                    Expanded(
                      flex: 6,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text('Background Overlay Dimming', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                              const Spacer(),
                              Text('${(widget.themeNotifier.wallpaperDim * 100).toInt()}%', style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w600)),
                            ],
                          ),
                          Slider(
                            value: widget.themeNotifier.wallpaperDim,
                            min: 0.0,
                            max: 0.85,
                            activeColor: accent,
                            inactiveColor: palette.panel,
                            onChanged: (v) => widget.themeNotifier.setWallpaperDim(v),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Text('Background Blur', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                              const Spacer(),
                              Text('${widget.themeNotifier.wallpaperBlur.toStringAsFixed(1)} px', style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w600)),
                            ],
                          ),
                          Slider(
                            value: widget.themeNotifier.wallpaperBlur,
                            min: 0.0,
                            max: 20.0,
                            activeColor: accent,
                            inactiveColor: palette.panel,
                            onChanged: (v) => widget.themeNotifier.setWallpaperBlur(v),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Text('Background Brightness / Opacity', style: TextStyle(color: palette.textSec, fontSize: 11.5 * scale)),
                              const Spacer(),
                              Text('${(widget.themeNotifier.wallpaperBrightness * 100).toInt()}%', style: TextStyle(color: palette.textPri, fontSize: 11.5 * scale, fontWeight: FontWeight.w600)),
                            ],
                          ),
                          Slider(
                            value: widget.themeNotifier.wallpaperBrightness,
                            min: 0.1,
                            max: 1.0,
                            activeColor: accent,
                            inactiveColor: palette.panel,
                            onChanged: (v) => widget.themeNotifier.setWallpaperBrightness(v),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Interface Density & Scale ─────────────────────────────────────
          Text('INTERFACE DENSITY & FONT SCALE', style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.surface,
              borderRadius: EvaTokens.borderMd,
              border: Border.all(color: palette.border),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<EvaDensity>(
                        initialValue: widget.themeNotifier.density,
                        dropdownColor: palette.surface,
                        style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale),
                        decoration: const InputDecoration(labelText: 'UI Density'),
                        items: EvaDensity.values.map((d) {
                          return DropdownMenuItem(value: d, child: Text(d.label));
                        }).toList(),
                        onChanged: (d) {
                          if (d != null) widget.themeNotifier.setDensity(d);
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: DropdownButtonFormField<double>(
                        initialValue: widget.themeNotifier.fontScale,
                        dropdownColor: palette.surface,
                        style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale),
                        decoration: const InputDecoration(labelText: 'Font Scale'),
                        items: const [
                          DropdownMenuItem(value: 0.9, child: Text('Small (90%)')),
                          DropdownMenuItem(value: 1.0, child: Text('Default (100%)')),
                          DropdownMenuItem(value: 1.1, child: Text('Medium (110%)')),
                          DropdownMenuItem(value: 1.2, child: Text('Large (120%)')),
                        ],
                        onChanged: (s) {
                          if (s != null) widget.themeNotifier.setFontScale(s);
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Material(
                  type: MaterialType.transparency,
                  child: SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Expand sidebar by default', style: TextStyle(color: palette.textPri, fontSize: 12.5 * scale)),
                    subtitle: Text('Show labels in the left desktop dock', style: TextStyle(color: palette.textSec, fontSize: 11 * scale)),
                    value: widget.themeNotifier.sidebarExpanded,
                    activeThumbColor: accent,
                    onChanged: (v) => widget.themeNotifier.setSidebarExpanded(v),
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

class _ThemeOptionTile extends StatelessWidget {
  final String title;
  final String desc;
  final bool isSelected;
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final IconData icon;
  final VoidCallback onTap;

  const _ThemeOptionTile({
    required this.title,
    required this.desc,
    required this.isSelected,
    required this.palette,
    required this.accent,
    required this.scale,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: EvaTokens.borderMd,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected ? accent.withValues(alpha: 0.12) : palette.surface,
            borderRadius: EvaTokens.borderMd,
            border: Border.all(
              color: isSelected ? accent : palette.border,
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Row(
            children: [
              Icon(icon, size: 22, color: isSelected ? accent : palette.textSec),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isSelected ? accent : palette.textPri,
                        fontSize: 13 * scale,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      desc,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: palette.textSec, fontSize: 10.5 * scale),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
