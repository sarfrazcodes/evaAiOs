import 'package:flutter/material.dart';
import 'eva_colors.dart';
import 'eva_tokens.dart';

class EvaTheme {
  static ThemeData buildTheme({
    required bool isDark,
    required EvaAccentColor accent,
    required EvaDensity density,
    required double fontScale,
  }) {
    final palette = isDark ? EvaPalette.dark : EvaPalette.light;
    final primaryAccent = accent.primary;
    final secondaryAccent = accent.secondary;

    final baseTextTheme = TextTheme(
      titleLarge: EvaTokens.fontTitle(palette.textPri, scale: fontScale),
      titleMedium: EvaTokens.fontSection(palette.textPri, scale: fontScale),
      bodyLarge: EvaTokens.fontBody(palette.textPri, scale: fontScale * 1.05),
      bodyMedium: EvaTokens.fontBody(palette.textPri, scale: fontScale),
      bodySmall: EvaTokens.fontCaption(palette.textSec, scale: fontScale),
      labelLarge: TextStyle(
        color: palette.textPri,
        fontSize: 12.5 * fontScale,
        fontWeight: FontWeight.w600,
      ),
      labelMedium: TextStyle(
        color: palette.textSec,
        fontSize: 11 * fontScale,
        fontWeight: FontWeight.w500,
      ),
      labelSmall: TextStyle(
        color: palette.textSec,
        fontSize: 9.5 * fontScale,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.5,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: isDark ? Brightness.dark : Brightness.light,
      scaffoldBackgroundColor: palette.bg,
      colorScheme: ColorScheme(
        brightness: isDark ? Brightness.dark : Brightness.light,
        primary: primaryAccent,
        onPrimary: isDark ? palette.bg : Colors.white,
        secondary: secondaryAccent,
        onSecondary: Colors.white,
        error: palette.error,
        onError: Colors.white,
        surface: palette.surface,
        onSurface: palette.textPri,
      ),
      textTheme: baseTextTheme,
      dividerColor: palette.border,
      dividerTheme: DividerThemeData(
        color: palette.border,
        thickness: 1,
        space: 1,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: palette.panel,
          borderRadius: EvaTokens.borderSm,
          border: Border.all(color: palette.border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        textStyle: TextStyle(
          color: palette.textPri,
          fontSize: 11 * fontScale,
          fontWeight: FontWeight.w500,
        ),
        waitDuration: const Duration(milliseconds: 350),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.inputBg,
        hintStyle: TextStyle(color: palette.textSec, fontSize: 13 * fontScale),
        contentPadding: EdgeInsets.symmetric(
          horizontal: density.horizontalPadding,
          vertical: density.verticalPadding,
        ),
        border: OutlineInputBorder(
          borderRadius: EvaTokens.borderMd,
          borderSide: BorderSide(color: palette.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: EvaTokens.borderMd,
          borderSide: BorderSide(color: palette.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: EvaTokens.borderMd,
          borderSide: BorderSide(color: primaryAccent, width: 1.5),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryAccent,
          foregroundColor: isDark ? palette.bg : Colors.white,
          elevation: 0,
          textStyle: TextStyle(fontSize: 12.5 * fontScale, fontWeight: FontWeight.w600),
          padding: EdgeInsets.symmetric(
            horizontal: density.horizontalPadding,
            vertical: density.verticalPadding,
          ),
          shape: RoundedRectangleBorder(borderRadius: EvaTokens.borderSm),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: palette.textPri,
          side: BorderSide(color: palette.border),
          textStyle: TextStyle(fontSize: 12 * fontScale, fontWeight: FontWeight.w500),
          padding: EdgeInsets.symmetric(
            horizontal: density.horizontalPadding * 0.8,
            vertical: density.verticalPadding * 0.7,
          ),
          shape: RoundedRectangleBorder(borderRadius: EvaTokens.borderSm),
        ),
      ),
      cardTheme: CardThemeData(
        color: palette.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: EvaTokens.borderMd,
          side: BorderSide(color: palette.border),
        ),
      ),
    );
  }
}
