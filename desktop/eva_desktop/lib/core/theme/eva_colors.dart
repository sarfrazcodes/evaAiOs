import 'package:flutter/material.dart';

enum EvaAccentColor {
  cyan('Electric Cyan', Color(0xFF00D6B9), Color(0xFF9B8CFF)),
  violet('Electric Violet', Color(0xFF9B8CFF), Color(0xFF00D6B9)),
  sage('Sage', Color(0xFF83A995), Color(0xFF648C83)),
  teal('Teal', Color(0xFF5FB3B3), Color(0xFF478A8A)),
  blueGrey('Blue-grey', Color(0xFF6B8299), Color(0xFF53677A)),
  amber('Amber', Color(0xFFD6A45D), Color(0xFFAB7E3C)),
  neutralGrey('Neutral grey', Color(0xFF8C9298), Color(0xFF6E747A));

  final String label;
  final Color primary;
  final Color secondary;
  const EvaAccentColor(this.label, this.primary, this.secondary);
}

class EvaPalette {
  final Color bg;
  final Color sidebar;
  final Color panel;
  final Color surface;
  final Color elevated;
  final Color textPri;
  final Color textSec;
  final Color border;
  final Color borderSubtle;
  final Color warning;
  final Color error;
  final Color success;
  final Color userMsg;
  final Color assistMsg;
  final Color inputBg;

  const EvaPalette({
    required this.bg,
    required this.sidebar,
    required this.panel,
    required this.surface,
    required this.elevated,
    required this.textPri,
    required this.textSec,
    required this.border,
    required this.borderSubtle,
    required this.warning,
    required this.error,
    required this.success,
    required this.userMsg,
    required this.assistMsg,
    required this.inputBg,
  });

  // Premium Desktop Dark Palette (EVA OS 2.0)
  static const EvaPalette dark = EvaPalette(
    bg: Color(0xFF101419),
    sidebar: Color(0xFF171E26),
    panel: Color(0xFF202A33),
    surface: Color(0xFF202A33),
    elevated: Color(0xFF2A3642),
    textPri: Color(0xFFE8EDF2),
    textSec: Color(0xFFA3B0BC),
    border: Color(0xFF32414F),
    borderSubtle: Color(0xFF26333E),
    warning: Color(0xFFE5B567),
    error: Color(0xFFE06C75),
    success: Color(0xFF00D6B9),
    userMsg: Color(0xFF1D3B38),
    assistMsg: Color(0xFF202A33),
    inputBg: Color(0xFF141A21),
  );

  // Warm Ivory Light Palette
  static const EvaPalette light = EvaPalette(
    bg: Color(0xFFF7F6F2),
    sidebar: Color(0xFFEDEAE4),
    panel: Color(0xFFE4E0D7),
    surface: Color(0xFFECE8E0),
    elevated: Color(0xFFDAD5CB),
    textPri: Color(0xFF20252B),
    textSec: Color(0xFF656E74),
    border: Color(0xFFCCC7BC),
    borderSubtle: Color(0xFFDED9CF),
    warning: Color(0xFFAB7E3C),
    error: Color(0xFFB55252),
    success: Color(0xFF4E7F66),
    userMsg: Color(0xFFDDECE5),
    assistMsg: Color(0xFFE9E5DD),
    inputBg: Color(0xFFFFFFFF),
  );
}
