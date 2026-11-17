import 'dart:io';
import 'package:flutter/material.dart';
import 'eva_colors.dart';
import 'eva_tokens.dart';
import 'eva_theme.dart';
import '../services/settings_service.dart';

class ThemeNotifier extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.dark;
  EvaAccentColor _accent = EvaAccentColor.sage;
  EvaDensity _density = EvaDensity.comfortable;
  double _fontScale = 1.0;
  bool _sidebarExpanded = true;
  String _wallpaperPath = '';
  BoxFit _wallpaperFit = BoxFit.cover;
  double _wallpaperDim = 0.35;
  double _wallpaperBlur = 0.0;
  double _wallpaperBrightness = 1.0;
  double _panelOpacity = 0.95;

  // Voice & Audio
  bool _ttsEnabled = true;
  double _ttsSpeed = 1.0;
  bool _voiceMode = false;
  bool _agenticVoiceActive = false;

  // Privacy & AI Provider
  bool _historyVisible = true;
  bool _requireConfirmHighRisk = true;
  String _privacyMode = 'hybrid';
  String _geminiApiKey = '';

  ThemeNotifier() {
    _loadFromDisk();
  }

  // Getters
  ThemeMode get themeMode => _themeMode;
  EvaAccentColor get accent => _accent;
  EvaDensity get density => _density;
  double get fontScale => _fontScale;
  bool get sidebarExpanded => _sidebarExpanded;
  String get wallpaperPath => _wallpaperPath;
  BoxFit get wallpaperFit => _wallpaperFit;
  double get wallpaperDim => _wallpaperDim;
  double get wallpaperBlur => _wallpaperBlur;
  double get wallpaperBrightness => _wallpaperBrightness;
  double get panelOpacity => _panelOpacity;

  bool get ttsEnabled => _ttsEnabled;
  double get ttsSpeed => _ttsSpeed;
  bool get voiceMode => _voiceMode;
  bool get agenticVoiceActive => _agenticVoiceActive;

  bool get historyVisible => _historyVisible;
  bool get requireConfirmHighRisk => _requireConfirmHighRisk;
  String get privacyMode => _privacyMode;
  String get geminiApiKey => _geminiApiKey;

  bool isDark(BuildContext context) {
    if (_themeMode == ThemeMode.system) {
      return MediaQuery.platformBrightnessOf(context) == Brightness.dark;
    }
    return _themeMode == ThemeMode.dark;
  }

  EvaPalette getPalette(BuildContext context) {
    return isDark(context) ? EvaPalette.dark : EvaPalette.light;
  }

  ThemeData getThemeData(BuildContext context) {
    final dark = isDark(context);
    return EvaTheme.buildTheme(
      isDark: dark,
      accent: _accent,
      density: _density,
      fontScale: _fontScale,
    );
  }

  bool get hasValidWallpaper {
    if (_wallpaperPath.trim().isEmpty) return false;
    final f = File(_wallpaperPath);
    return f.existsSync();
  }

  // Setters
  void setThemeMode(ThemeMode mode) {
    if (_themeMode != mode) {
      _themeMode = mode;
      notifyListeners();
      _saveToDisk();
    }
  }

  void setAccent(EvaAccentColor accent) {
    if (_accent != accent) {
      _accent = accent;
      notifyListeners();
      _saveToDisk();
    }
  }

  void setDensity(EvaDensity d) {
    if (_density != d) {
      _density = d;
      notifyListeners();
      _saveToDisk();
    }
  }

  void setFontScale(double scale) {
    if (_fontScale != scale) {
      _fontScale = scale;
      notifyListeners();
      _saveToDisk();
    }
  }

  void toggleSidebar() {
    _sidebarExpanded = !_sidebarExpanded;
    notifyListeners();
    _saveToDisk();
  }

  void setSidebarExpanded(bool val) {
    if (_sidebarExpanded != val) {
      _sidebarExpanded = val;
      notifyListeners();
      _saveToDisk();
    }
  }

  void setWallpaper(String path, {BoxFit? fit, double? dim}) {
    _wallpaperPath = path;
    if (fit != null) _wallpaperFit = fit;
    if (dim != null) _wallpaperDim = dim;
    notifyListeners();
    _saveToDisk();
  }

  void restoreDefaultWallpaper() {
    _wallpaperPath = '';
    notifyListeners();
    _saveToDisk();
  }

  void setWallpaperDim(double dim) {
    _wallpaperDim = dim.clamp(0.0, 0.85);
    notifyListeners();
    _saveToDisk();
  }

  void setWallpaperBlur(double blur) {
    _wallpaperBlur = blur.clamp(0.0, 25.0);
    notifyListeners();
    _saveToDisk();
  }

  void setWallpaperBrightness(double b) {
    _wallpaperBrightness = b.clamp(0.1, 1.5);
    notifyListeners();
    _saveToDisk();
  }

  void setAgenticVoiceActive(bool active) {
    _agenticVoiceActive = active;
    notifyListeners();
  }

  void setPrivacyMode(String mode) {
    _privacyMode = mode;
    notifyListeners();
    _saveToDisk();
  }

  void setGeminiApiKey(String key) {
    _geminiApiKey = key;
    notifyListeners();
    _saveToDisk();
  }

  void setWallpaperFit(BoxFit fit) {
    _wallpaperFit = fit;
    notifyListeners();
    _saveToDisk();
  }

  void setPanelOpacity(double op) {
    _panelOpacity = op.clamp(0.65, 1.0);
    notifyListeners();
    _saveToDisk();
  }

  void setTtsEnabled(bool enabled) {
    _ttsEnabled = enabled;
    notifyListeners();
    _saveToDisk();
  }

  void setTtsSpeed(double speed) {
    _ttsSpeed = speed.clamp(0.5, 2.5);
    notifyListeners();
    _saveToDisk();
  }

  void setVoiceMode(bool mode) {
    _voiceMode = mode;
    notifyListeners();
    _saveToDisk();
  }

  void setHistoryVisible(bool val) {
    _historyVisible = val;
    notifyListeners();
    _saveToDisk();
  }

  void setRequireConfirmHighRisk(bool val) {
    _requireConfirmHighRisk = val;
    notifyListeners();
    _saveToDisk();
  }

  // Persistence
  void _loadFromDisk() {
    final s = SettingsService.loadLocalSettings();
    if (s.containsKey('theme_mode')) {
      final tm = s['theme_mode'];
      if (tm == 'light') _themeMode = ThemeMode.light;
      if (tm == 'dark') _themeMode = ThemeMode.dark;
      if (tm == 'system') _themeMode = ThemeMode.system;
    }
    if (s.containsKey('accent_color')) {
      final a = s['accent_color'];
      for (final ac in EvaAccentColor.values) {
        if (ac.name == a) _accent = ac;
      }
    }
    if (s.containsKey('density')) {
      final d = s['density'];
      for (final dn in EvaDensity.values) {
        if (dn.name == d) _density = dn;
      }
    }
    if (s.containsKey('font_scale')) {
      _fontScale = (s['font_scale'] as num).toDouble();
    }
    if (s.containsKey('sidebar_expanded')) {
      _sidebarExpanded = s['sidebar_expanded'] == true;
    }
    if (s.containsKey('wallpaper_path')) {
      _wallpaperPath = s['wallpaper_path'] as String;
    }
    if (s.containsKey('wallpaper_fit')) {
      final f = s['wallpaper_fit'] as String;
      if (f == 'contain') {
        _wallpaperFit = BoxFit.contain;
      } else if (f == 'fill') {
        _wallpaperFit = BoxFit.fill;
      } else {
        _wallpaperFit = BoxFit.cover;
      }
    }
    if (s.containsKey('wallpaper_dim')) {
      _wallpaperDim = (s['wallpaper_dim'] as num).toDouble();
    }
    if (s.containsKey('wallpaper_blur')) {
      _wallpaperBlur = (s['wallpaper_blur'] as num).toDouble();
    }
    if (s.containsKey('wallpaper_brightness')) {
      _wallpaperBrightness = (s['wallpaper_brightness'] as num).toDouble();
    }
    if (s.containsKey('privacy_mode')) {
      _privacyMode = s['privacy_mode'] as String;
    }
    if (s.containsKey('gemini_api_key')) {
      _geminiApiKey = s['gemini_api_key'] as String;
    }
    if (s.containsKey('panel_opacity')) {
      _panelOpacity = (s['panel_opacity'] as num).toDouble();
    }
    if (s.containsKey('tts_enabled')) {
      _ttsEnabled = s['tts_enabled'] == true;
    }
    if (s.containsKey('tts_speed')) {
      _ttsSpeed = (s['tts_speed'] as num).toDouble();
    }
    if (s.containsKey('voice_mode')) {
      _voiceMode = s['voice_mode'] == true;
    }
    if (s.containsKey('history_visible')) {
      _historyVisible = s['history_visible'] == true;
    }
    if (s.containsKey('require_confirm_high_risk')) {
      _requireConfirmHighRisk = s['require_confirm_high_risk'] == true;
    }
  }

  void _saveToDisk() {
    final fitStr = _wallpaperFit == BoxFit.contain ? 'contain' : (_wallpaperFit == BoxFit.fill ? 'fill' : 'cover');
    final s = <String, dynamic>{
      'theme_mode': _themeMode == ThemeMode.light ? 'light' : (_themeMode == ThemeMode.system ? 'system' : 'dark'),
      'accent_color': _accent.name,
      'density': _density.name,
      'font_scale': _fontScale,
      'sidebar_expanded': _sidebarExpanded,
      'wallpaper_path': _wallpaperPath,
      'wallpaper_fit': fitStr,
      'wallpaper_dim': _wallpaperDim,
      'wallpaper_blur': _wallpaperBlur,
      'wallpaper_brightness': _wallpaperBrightness,
      'privacy_mode': _privacyMode,
      'gemini_api_key': _geminiApiKey,
      'panel_opacity': _panelOpacity,
      'tts_enabled': _ttsEnabled,
      'tts_speed': _ttsSpeed,
      'voice_mode': _voiceMode,
      'history_visible': _historyVisible,
      'require_confirm_high_risk': _requireConfirmHighRisk,
    };
    SettingsService.saveLocalSettings(s);
  }
}
