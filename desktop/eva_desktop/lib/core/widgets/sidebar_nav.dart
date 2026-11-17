import 'package:flutter/material.dart';
import '../theme/eva_colors.dart';
import '../theme/eva_tokens.dart';
import '../theme/theme_notifier.dart';

class NavItemDef {
  final IconData idleIcon;
  final IconData activeIcon;
  final String label;
  final String badgeText;

  const NavItemDef({
    required this.idleIcon,
    required this.activeIcon,
    required this.label,
    this.badgeText = '',
  });
}

class SidebarNav extends StatelessWidget {
  final ThemeNotifier themeNotifier;
  final List<NavItemDef> items;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final VoidCallback onToggleCollapse;

  const SidebarNav({
    super.key,
    required this.themeNotifier,
    required this.items,
    required this.selectedIndex,
    required this.onSelect,
    required this.onToggleCollapse,
  });

  @override
  Widget build(BuildContext context) {
    final palette = themeNotifier.getPalette(context);
    final isExpanded = themeNotifier.sidebarExpanded;
    final accent = themeNotifier.accent.primary;
    final scale = themeNotifier.fontScale;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeInOut,
      width: isExpanded ? EvaTokens.sidebarExpandedWidth : EvaTokens.sidebarCollapsedWidth,
      decoration: BoxDecoration(
        color: palette.sidebar.withValues(alpha: themeNotifier.panelOpacity),
        border: Border(right: BorderSide(color: palette.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 12),
          // ── App Brand Header ──────────────────────────────────────────
          Padding(
            padding: EdgeInsets.symmetric(horizontal: isExpanded ? 14 : 10),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showBrandText = isExpanded && constraints.maxWidth > 80;
                return Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.15),
                        borderRadius: EvaTokens.borderSm,
                        border: Border.all(color: accent.withValues(alpha: 0.4)),
                      ),
                      child: Center(
                        child: Icon(Icons.auto_awesome_rounded, color: accent, size: 16),
                      ),
                    ),
                    if (showBrandText) ...[
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'EVA AI OS',
                              style: TextStyle(
                                color: palette.textPri,
                                fontSize: 13 * scale,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.4,
                              ),
                            ),
                            Text(
                              'Linux Workstation',
                              style: TextStyle(
                                color: palette.textSec,
                                fontSize: 10 * scale,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),

          const SizedBox(height: 14),
          Divider(
            color: palette.borderSubtle,
            indent: isExpanded ? 12 : 8,
            endIndent: isExpanded ? 12 : 8,
          ),
          const SizedBox(height: 8),

          // ── Nav items ──────────────────────────────────────────────────
          Expanded(
            child: ListView.builder(
              padding: EdgeInsets.symmetric(horizontal: isExpanded ? 8 : 6),
              itemCount: items.length,
              itemBuilder: (ctx, i) {
                final item = items[i];
                final isSelected = i == selectedIndex;

                return Tooltip(
                  message: !isExpanded ? item.label : '',
                  waitDuration: const Duration(milliseconds: 300),
                  child: _SidebarTile(
                    palette: palette,
                    accent: accent,
                    scale: scale,
                    item: item,
                    isSelected: isSelected,
                    isExpanded: isExpanded,
                    onTap: () => onSelect(i),
                  ),
                );
              },
            ),
          ),

          // ── Bottom Collapse/Expand Toggle ──────────────────────────────
          Divider(
            color: palette.borderSubtle,
            indent: isExpanded ? 12 : 8,
            endIndent: isExpanded ? 12 : 8,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: InkWell(
              onTap: onToggleCollapse,
              borderRadius: EvaTokens.borderSm,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final showCollapseText = isExpanded && constraints.maxWidth > 80;
                    return Row(
                      mainAxisAlignment: showCollapseText ? MainAxisAlignment.start : MainAxisAlignment.center,
                      children: [
                        Icon(
                          isExpanded ? Icons.keyboard_double_arrow_left_rounded : Icons.keyboard_double_arrow_right_rounded,
                          size: 16,
                          color: palette.textSec,
                        ),
                        if (showCollapseText) ...[
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Collapse sidebar',
                              style: TextStyle(
                                color: palette.textSec,
                                fontSize: 11 * scale,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SidebarTile extends StatefulWidget {
  final EvaPalette palette;
  final Color accent;
  final double scale;
  final NavItemDef item;
  final bool isSelected;
  final bool isExpanded;
  final VoidCallback onTap;

  const _SidebarTile({
    required this.palette,
    required this.accent,
    required this.scale,
    required this.item,
    required this.isSelected,
    required this.isExpanded,
    required this.onTap,
  });

  @override
  State<_SidebarTile> createState() => _SidebarTileState();
}

class _SidebarTileState extends State<_SidebarTile> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final bg = widget.isSelected
        ? widget.accent.withValues(alpha: 0.15)
        : (_hovered ? widget.palette.surface : Colors.transparent);
    final fg = widget.isSelected ? widget.accent : (_hovered ? widget.palette.textPri : widget.palette.textSec);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          margin: const EdgeInsets.symmetric(vertical: 2.5),
          padding: EdgeInsets.symmetric(
            horizontal: widget.isExpanded ? 10 : 8,
            vertical: 8,
          ),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: EvaTokens.borderSm,
            border: widget.isSelected
                ? Border.all(color: widget.accent.withValues(alpha: 0.35))
                : Border.all(color: Colors.transparent),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final showTileText = widget.isExpanded && constraints.maxWidth > 80;
              return Row(
                mainAxisAlignment: showTileText ? MainAxisAlignment.start : MainAxisAlignment.center,
                children: [
                  Icon(
                    widget.isSelected ? widget.item.activeIcon : widget.item.idleIcon,
                    size: 18,
                    color: fg,
                  ),
                  if (showTileText) ...[
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        widget.item.label,
                        style: TextStyle(
                          color: fg,
                          fontSize: 12.5 * widget.scale,
                          fontWeight: widget.isSelected ? FontWeight.w600 : FontWeight.w400,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (widget.item.badgeText.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: widget.accent.withValues(alpha: 0.2),
                          borderRadius: EvaTokens.borderSm,
                        ),
                        child: Text(
                          widget.item.badgeText,
                          style: TextStyle(
                            color: widget.accent,
                            fontSize: 9 * widget.scale,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
